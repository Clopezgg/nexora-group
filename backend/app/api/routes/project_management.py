import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.deps_correlation import get_correlation_id
from app.models.cost_center import CostCenter
from app.models.crm import Customer
from app.models.project import Project
from app.repositories import project_repository
from app.schemas.project_control import (
    ProjectFinancialSummaryResponse,
    ProjectLifecycleResponse,
    ProjectResponse,
    ProjectStatusTransitionRequest,
    ProjectUpdateRequest,
)
from app.services import audit_service, project_financial_service, project_lifecycle_service
from app.services.permission_service import (
    assert_company_access,
    require_permission,
    user_has_permission,
)

router = APIRouter(prefix="/projects", tags=["projects"])


def _get_project_or_404(db: Session, project_id: uuid.UUID) -> Project:
    project = project_repository.get_by_id(db, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proyecto no encontrado")
    return project


def _validate_project_references(db: Session, *, project: Project, values: dict) -> None:
    customer_id = values.get("customer_id")
    if customer_id is not None:
        customer = db.get(Customer, customer_id)
        if customer is None or customer.company_id != project.company_id:
            raise HTTPException(status_code=422, detail="El cliente no pertenece a la compañía del proyecto")

    cost_center_id = values.get("cost_center_id")
    if cost_center_id is not None:
        cost_center = db.get(CostCenter, cost_center_id)
        if cost_center is None or cost_center.company_id != project.company_id:
            raise HTTPException(status_code=422, detail="El centro de costo no pertenece a la compañía del proyecto")

    planned_start = values.get("planned_start", project.planned_start)
    planned_end = values.get("planned_end", project.planned_end)
    if planned_start and planned_end and planned_end < planned_start:
        raise HTTPException(
            status_code=422,
            detail="La fecha final prevista no puede ser anterior a la fecha de inicio",
        )


@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: uuid.UUID,
    payload: ProjectUpdateRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("project", "create")),
    correlation_id: str = Depends(get_correlation_id),
) -> ProjectResponse:
    """Edit project master data.

    The existing RBAC model does not yet define project/update; project/create
    is deliberately reused as the stronger project-management privilege so we
    do not invent an unseeded permission that would lock production users out.
    """
    project = _get_project_or_404(db, project_id)
    assert_company_access(
        db, user_id=user.id, resource="project", action="create", company_id=project.company_id
    )
    values = payload.model_dump(exclude_unset=True)
    _validate_project_references(db, project=project, values=values)

    before = {
        "name": project.name,
        "code": project.code,
        "customerId": str(project.customer_id) if project.customer_id else None,
        "manager": project.manager,
        "plannedStart": str(project.planned_start) if project.planned_start else None,
        "plannedEnd": str(project.planned_end) if project.planned_end else None,
    }
    project_repository.update_project(db, project=project, values=values)
    audit_service.record(
        db,
        actor_user_id=user.id,
        action="project.update",
        entity_type="project",
        entity_id=project.id,
        company_id=project.company_id,
        project_id=project.id,
        before=before,
        after={
            "name": project.name,
            "code": project.code,
            "customerId": str(project.customer_id) if project.customer_id else None,
            "manager": project.manager,
            "plannedStart": str(project.planned_start) if project.planned_start else None,
            "plannedEnd": str(project.planned_end) if project.planned_end else None,
        },
        correlation_id=correlation_id,
    )
    db.commit()
    db.refresh(project)
    return ProjectResponse.model_validate(project, from_attributes=True)


@router.get("/{project_id}/lifecycle", response_model=ProjectLifecycleResponse)
def project_lifecycle(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("project", "read")),
) -> ProjectLifecycleResponse:
    """Vista autoritativa del ciclo de vida: estado actual + transiciones
    permitidas (con etiqueta ES y si son sensibles). El frontend NO debe tener
    su propio grafo de transiciones — consume esto."""
    project = _get_project_or_404(db, project_id)
    assert_company_access(
        db, user_id=user.id, resource="project", action="read", company_id=project.company_id
    )
    return ProjectLifecycleResponse.model_validate(
        project_lifecycle_service.lifecycle_view(project)
    )


@router.post("/{project_id}/status", response_model=ProjectResponse)
def transition_project_status(
    project_id: uuid.UUID,
    payload: ProjectStatusTransitionRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("project", "create")),
    correlation_id: str = Depends(get_correlation_id),
) -> ProjectResponse:
    project = _get_project_or_404(db, project_id)
    assert_company_access(
        db, user_id=user.id, resource="project", action="create", company_id=project.company_id
    )
    has_lifecycle = user_has_permission(
        db, user_id=user.id, resource="project.lifecycle", action="manage"
    )
    try:
        result = project_lifecycle_service.apply_transition(
            project=project,
            target=payload.status,
            reason=payload.reason,
            has_lifecycle_permission=has_lifecycle,
        )
    except project_lifecycle_service.ProjectTransitionError as exc:
        # Error de negocio entendible (§7/§24): 409 para el conflicto de estado,
        # 422 para motivo/permiso faltante.
        detail = str(exc)
        code = 422 if ("motivo" in detail or "permiso" in detail) else 409
        raise HTTPException(status_code=code, detail=detail) from exc

    if not result.changed:
        # Idempotente: ya estaba en ese estado, sin mutación ni audit duplicado.
        return ProjectResponse.model_validate(project, from_attributes=True)

    db.flush()
    audit_service.record(
        db,
        actor_user_id=user.id,
        action=(
            "project.lifecycle.sensitive"
            if result.was_sensitive
            else "project.status.transition"
        ),
        entity_type="project",
        entity_id=project.id,
        company_id=project.company_id,
        project_id=project.id,
        before={"status": result.before_status},
        after={"status": result.after_status, "reason": payload.reason},
        correlation_id=correlation_id,
    )
    db.commit()
    db.refresh(project)
    return ProjectResponse.model_validate(project, from_attributes=True)


@router.get("/{project_id}/financial-summary", response_model=ProjectFinancialSummaryResponse)
def project_financial_summary(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("project", "read")),
) -> ProjectFinancialSummaryResponse:
    project = _get_project_or_404(db, project_id)
    assert_company_access(
        db, user_id=user.id, resource="project", action="read", company_id=project.company_id
    )
    summary = project_financial_service.get_summary(db, project_id=project_id)
    return ProjectFinancialSummaryResponse(**summary.__dict__)
