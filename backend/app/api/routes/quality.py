import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.project import Project
from app.repositories import project_repository, quality_repository
from app.schemas.quality import (
    CorrectiveActionCreateRequest,
    CorrectiveActionResponse,
    NonConformanceCreateRequest,
    NonConformanceResponse,
    QualityInspectionCreateRequest,
    QualityInspectionResponse,
)
from app.services import quality_service
from app.services.permission_service import assert_company_access, require_permission

router = APIRouter(prefix="/quality", tags=["quality"])


def _resolve_project_or_404(db: Session, project_id: uuid.UUID) -> Project:
    project = project_repository.get_by_id(db, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proyecto no encontrado")
    return project


def _resolve_inspection_or_404(db: Session, inspection_id: uuid.UUID):
    inspection = quality_service.get_inspection(db, inspection_id)
    if inspection is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="QualityInspection no encontrada"
        )
    return inspection


def _resolve_non_conformance_or_404(db: Session, non_conformance_id: uuid.UUID):
    non_conformance = quality_service.get_non_conformance(db, non_conformance_id)
    if non_conformance is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="NonConformance no encontrada"
        )
    return non_conformance


def _resolve_corrective_action_or_404(db: Session, corrective_action_id: uuid.UUID):
    corrective_action = quality_repository.get_corrective_action(db, corrective_action_id)
    if corrective_action is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="CorrectiveAction no encontrada"
        )
    return corrective_action


@router.post("/inspections", response_model=QualityInspectionResponse, status_code=201)
def create_inspection(
    payload: QualityInspectionCreateRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("quality.inspection", "create")),
) -> QualityInspectionResponse:
    project = _resolve_project_or_404(db, payload.project_id)
    assert_company_access(
        db, user_id=user.id, resource="quality.inspection", action="create", company_id=project.company_id
    )
    inspection = quality_service.create_inspection(
        db,
        project_id=payload.project_id,
        company_id=project.company_id,
        wbs_node_id=payload.wbs_node_id,
        inspection_type=payload.inspection_type,
        inspection_date=payload.inspection_date,
        inspector_id=user.id,
        result=payload.result,
        notes=payload.notes,
        evidence_id=payload.evidence_id,
    )
    return QualityInspectionResponse.model_validate(inspection, from_attributes=True)


@router.get("/inspections", response_model=list[QualityInspectionResponse])
def list_inspections(
    project_id: uuid.UUID = Query(alias="projectId"),
    db: Session = Depends(get_db),
    user=Depends(require_permission("quality.inspection", "read")),
) -> list[QualityInspectionResponse]:
    project = _resolve_project_or_404(db, project_id)
    assert_company_access(
        db, user_id=user.id, resource="quality.inspection", action="read", company_id=project.company_id
    )
    return [
        QualityInspectionResponse.model_validate(i, from_attributes=True)
        for i in quality_service.list_inspections(db, project_id=project_id)
    ]


@router.get("/inspections/{inspection_id}", response_model=QualityInspectionResponse)
def get_inspection(
    inspection_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("quality.inspection", "read")),
) -> QualityInspectionResponse:
    inspection = _resolve_inspection_or_404(db, inspection_id)
    project = _resolve_project_or_404(db, inspection.project_id)
    assert_company_access(
        db, user_id=user.id, resource="quality.inspection", action="read", company_id=project.company_id
    )
    return QualityInspectionResponse.model_validate(inspection, from_attributes=True)


@router.post("/non-conformances", response_model=NonConformanceResponse, status_code=201)
def create_non_conformance(
    payload: NonConformanceCreateRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("quality.non_conformance", "create")),
) -> NonConformanceResponse:
    project = _resolve_project_or_404(db, payload.project_id)
    assert_company_access(
        db,
        user_id=user.id,
        resource="quality.non_conformance",
        action="create",
        company_id=project.company_id,
    )
    non_conformance = quality_service.create_non_conformance(
        db,
        project_id=payload.project_id,
        company_id=project.company_id,
        quality_inspection_id=payload.quality_inspection_id,
        description=payload.description,
        responsible_user_id=payload.responsible_user_id,
        due_date=payload.due_date,
        evidence_id=payload.evidence_id,
    )
    return NonConformanceResponse.model_validate(non_conformance, from_attributes=True)


@router.get("/non-conformances", response_model=list[NonConformanceResponse])
def list_non_conformances(
    project_id: uuid.UUID = Query(alias="projectId"),
    db: Session = Depends(get_db),
    user=Depends(require_permission("quality.non_conformance", "read")),
) -> list[NonConformanceResponse]:
    project = _resolve_project_or_404(db, project_id)
    assert_company_access(
        db,
        user_id=user.id,
        resource="quality.non_conformance",
        action="read",
        company_id=project.company_id,
    )
    return [
        NonConformanceResponse.model_validate(nc, from_attributes=True)
        for nc in quality_service.list_non_conformances(db, project_id=project_id)
    ]


@router.get("/non-conformances/{non_conformance_id}", response_model=NonConformanceResponse)
def get_non_conformance(
    non_conformance_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("quality.non_conformance", "read")),
) -> NonConformanceResponse:
    non_conformance = _resolve_non_conformance_or_404(db, non_conformance_id)
    project = _resolve_project_or_404(db, non_conformance.project_id)
    assert_company_access(
        db,
        user_id=user.id,
        resource="quality.non_conformance",
        action="read",
        company_id=project.company_id,
    )
    return NonConformanceResponse.model_validate(non_conformance, from_attributes=True)


@router.post(
    "/non-conformances/{non_conformance_id}/corrective-actions",
    response_model=CorrectiveActionResponse,
    status_code=201,
)
def create_corrective_action(
    non_conformance_id: uuid.UUID,
    payload: CorrectiveActionCreateRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("quality.corrective_action", "create")),
) -> CorrectiveActionResponse:
    non_conformance = _resolve_non_conformance_or_404(db, non_conformance_id)
    project = _resolve_project_or_404(db, non_conformance.project_id)
    assert_company_access(
        db,
        user_id=user.id,
        resource="quality.corrective_action",
        action="create",
        company_id=project.company_id,
    )
    corrective_action = quality_service.create_corrective_action(
        db,
        non_conformance_id=non_conformance_id,
        company_id=project.company_id,
        description=payload.description,
        responsible_user_id=payload.responsible_user_id,
        due_date=payload.due_date,
        evidence_id=payload.evidence_id,
    )
    return CorrectiveActionResponse.model_validate(corrective_action, from_attributes=True)


@router.get(
    "/non-conformances/{non_conformance_id}/corrective-actions",
    response_model=list[CorrectiveActionResponse],
)
def list_corrective_actions(
    non_conformance_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("quality.corrective_action", "read")),
) -> list[CorrectiveActionResponse]:
    non_conformance = _resolve_non_conformance_or_404(db, non_conformance_id)
    project = _resolve_project_or_404(db, non_conformance.project_id)
    assert_company_access(
        db,
        user_id=user.id,
        resource="quality.corrective_action",
        action="read",
        company_id=project.company_id,
    )
    return [
        CorrectiveActionResponse.model_validate(ca, from_attributes=True)
        for ca in quality_service.list_corrective_actions(db, non_conformance_id=non_conformance_id)
    ]


@router.post(
    "/corrective-actions/{corrective_action_id}/complete", response_model=CorrectiveActionResponse
)
def complete_corrective_action(
    corrective_action_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("quality.corrective_action", "complete")),
) -> CorrectiveActionResponse:
    corrective_action = _resolve_corrective_action_or_404(db, corrective_action_id)
    non_conformance = _resolve_non_conformance_or_404(db, corrective_action.non_conformance_id)
    project = _resolve_project_or_404(db, non_conformance.project_id)
    assert_company_access(
        db,
        user_id=user.id,
        resource="quality.corrective_action",
        action="complete",
        company_id=project.company_id,
    )
    corrective_action = quality_service.complete_corrective_action(
        db, corrective_action_id=corrective_action_id
    )
    return CorrectiveActionResponse.model_validate(corrective_action, from_attributes=True)


@router.post("/non-conformances/{non_conformance_id}/close", response_model=NonConformanceResponse)
def close_non_conformance(
    non_conformance_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("quality.non_conformance", "close")),
) -> NonConformanceResponse:
    non_conformance = _resolve_non_conformance_or_404(db, non_conformance_id)
    project = _resolve_project_or_404(db, non_conformance.project_id)
    assert_company_access(
        db,
        user_id=user.id,
        resource="quality.non_conformance",
        action="close",
        company_id=project.company_id,
    )
    non_conformance = quality_service.close_non_conformance(db, non_conformance_id=non_conformance_id)
    return NonConformanceResponse.model_validate(non_conformance, from_attributes=True)
