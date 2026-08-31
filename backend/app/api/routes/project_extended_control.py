import uuid
from collections import defaultdict
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.api.deps_correlation import get_correlation_id
from app.repositories import budget_repository, project_control_repository, project_repository
from app.schemas.project_control import (
    ChangeOrderCreateRequest,
    ChangeOrderResponse,
    WBSFinancialResponse,
    WBSNodeResponse,
    WBSNodeUpdateRequest,
)
from app.services import audit_service
from app.services.permission_service import assert_company_access, require_permission

router = APIRouter(prefix="/projects", tags=["projects"])


def _project_or_404(db: Session, project_id: uuid.UUID):
    project = project_repository.get_by_id(db, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    return project


@router.patch("/{project_id}/wbs/{node_id}", response_model=WBSNodeResponse)
def update_wbs_node(
    project_id: uuid.UUID,
    node_id: uuid.UUID,
    payload: WBSNodeUpdateRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("project.wbs", "create")),
    correlation_id: str = Depends(get_correlation_id),
) -> WBSNodeResponse:
    project = _project_or_404(db, project_id)
    assert_company_access(
        db, user_id=user.id, resource="project.wbs", action="create", company_id=project.company_id
    )
    node = project_control_repository.get_wbs_node(db, node_id)
    if node is None or node.project_id != project_id:
        raise HTTPException(status_code=404, detail="Nodo WBS no encontrado en este proyecto")
    before = {
        "code": node.code,
        "name": node.name,
        "parentId": str(node.parent_id) if node.parent_id else None,
        "status": node.status,
        "progressPercent": str(node.progress_percent),
    }
    try:
        project_control_repository.update_wbs_node(
            db, node=node, values=payload.model_dump(exclude_unset=True)
        )
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    audit_service.record(
        db,
        actor_user_id=user.id,
        action="project.wbs.update",
        entity_type="project.wbs",
        entity_id=node.id,
        company_id=project.company_id,
        project_id=project.id,
        before=before,
        after={
            "code": node.code,
            "name": node.name,
            "parentId": str(node.parent_id) if node.parent_id else None,
            "status": node.status,
            "progressPercent": str(node.progress_percent),
        },
        correlation_id=correlation_id,
    )
    db.commit()
    db.refresh(node)
    return WBSNodeResponse.model_validate(node, from_attributes=True)


@router.get("/{project_id}/wbs/financial-summary", response_model=list[WBSFinancialResponse])
def wbs_financial_summary(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("project.wbs", "read")),
) -> list[WBSFinancialResponse]:
    """Return only metrics that can be sourced authoritatively today.

    Budget lines have a real WBS FK, so authorized cost is exact. Procurement
    commitments and GL actuals are project-dimensional today but do not yet
    carry a mandatory WBS dimension; returning 0 would falsely claim they are
    attributable. Those values therefore remain NULL/"—" until a source
    document actually carries WBS, per the no-fake-data invariant.
    """
    project = _project_or_404(db, project_id)
    assert_company_access(
        db, user_id=user.id, resource="project.wbs", action="read", company_id=project.company_id
    )
    nodes = project_control_repository.list_wbs_for_project(db, project_id)
    active_budget = budget_repository.get_active_budget(db, project_id)
    authorized: dict[uuid.UUID, Decimal] = defaultdict(lambda: Decimal("0"))
    if active_budget is not None:
        for line in budget_repository.list_lines(db, active_budget.id):
            if line.wbs_node_id is not None:
                authorized[line.wbs_node_id] += line.authorized_amount
    return [
        WBSFinancialResponse(
            wbs_node_id=node.id,
            authorized=authorized[node.id],
            committed=None,
            actual_cost=None,
            variance=None,
        )
        for node in nodes
    ]


@router.post(
    "/{project_id}/change-orders/detailed",
    response_model=ChangeOrderResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_detailed_change_order(
    project_id: uuid.UUID,
    payload: ChangeOrderCreateRequest,
    db: Session = Depends(get_db),
    current=Depends(get_current_user),
    _user=Depends(require_permission("project.change_order", "create")),
    correlation_id: str = Depends(get_correlation_id),
) -> ChangeOrderResponse:
    user, _roles = current
    project = _project_or_404(db, project_id)
    assert_company_access(
        db,
        user_id=user.id,
        resource="project.change_order",
        action="create",
        company_id=project.company_id,
    )
    try:
        change_order = project_control_repository.create_change_order(
            db,
            project_id=project_id,
            reason=payload.reason,
            requested_by=user.id,
            wbs_node_id=payload.wbs_node_id,
            scope_change=payload.scope_change,
            budget_change_amount=payload.budget_change_amount,
            contract_change_amount=payload.contract_change_amount,
            schedule_change_days=payload.schedule_change_days,
        )
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    audit_service.record(
        db,
        actor_user_id=user.id,
        action="project.change_order.create",
        entity_type="project.change_order",
        entity_id=change_order.id,
        company_id=project.company_id,
        project_id=project.id,
        before=None,
        after={
            "status": change_order.status,
            "reason": change_order.reason,
            "costImpact": str(change_order.budget_change_amount),
            "contractImpact": str(change_order.contract_change_amount),
        },
        correlation_id=correlation_id,
    )
    db.commit()
    db.refresh(change_order)
    return ChangeOrderResponse.model_validate(change_order, from_attributes=True)


@router.get(
    "/{project_id}/financial-cockpit",
    response_model=None,
)
def project_financial_cockpit(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("project.budget", "read")),
):
    from app.schemas.project_cockpit import ProjectCockpitResponse
    from app.services import project_cockpit_service
    from app.services.permission_service import assert_project_access

    project = _project_or_404(db, project_id)
    assert_company_access(
        db, user_id=user.id, resource="project.budget", action="read", company_id=project.company_id
    )
    assert_project_access(
        db, user_id=user.id, resource="project.budget", action="read", project_id=project_id
    )
    cockpit = project_cockpit_service.build(db, project_id=project_id)
    assert cockpit is not None
    return ProjectCockpitResponse(
        project_id=uuid.UUID(cockpit.project_id),
        project_name=cockpit.project_name,
        currency_code=cockpit.currency_code,
        budget_at_completion=cockpit.budget_at_completion,
        committed=cockpit.committed,
        actual_cost=cockpit.actual_cost,
        percent_complete=cockpit.percent_complete,
        earned_value=cockpit.earned_value,
        cost_performance_index=cockpit.cost_performance_index,
        estimate_to_complete=cockpit.estimate_to_complete,
        estimate_at_completion=cockpit.estimate_at_completion,
        variance_at_completion=cockpit.variance_at_completion,
        contract_revenue=cockpit.contract_revenue,
        projected_margin=cockpit.projected_margin,
        projected_margin_pct=cockpit.projected_margin_pct,
    )
