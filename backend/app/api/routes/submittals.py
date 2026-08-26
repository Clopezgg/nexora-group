import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.deps_correlation import get_correlation_id
from app.schemas.submittal import (
    SubmittalCreateRequest,
    SubmittalDecisionRequest,
    SubmittalResponse,
    SubmittalResponseRequest,
)
from app.services import audit_service, submittal_service
from app.services.permission_service import assert_company_access, require_permission

router = APIRouter(prefix="/submittals", tags=["submittals"])


def _resolve_submittal(db: Session, submittal_id: uuid.UUID):
    submittal = submittal_service.get_submittal(db, submittal_id)
    if submittal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submittal no encontrado")
    return submittal


@router.post("", response_model=SubmittalResponse, status_code=201)
def create_submittal(
    payload: SubmittalCreateRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("construction.submittal", "create")),
    correlation_id: str = Depends(get_correlation_id),
) -> SubmittalResponse:
    assert_company_access(
        db,
        user_id=user.id,
        resource="construction.submittal",
        action="create",
        company_id=payload.company_id,
    )
    submittal = submittal_service.create_submittal(
        db,
        company_id=payload.company_id,
        project_id=payload.project_id,
        wbs_node_id=payload.wbs_node_id,
        title=payload.title,
        description=payload.description,
        supplier_id=payload.supplier_id,
        contract_id=payload.contract_id,
        submitted_by=user.id,
        submitted_at=payload.submitted_at,
        due_date=payload.due_date,
        evidence_id=payload.evidence_id,
        commit=False,
    )
    audit_service.record(
        db,
        actor_user_id=user.id,
        action="construction.submittal.create",
        entity_type="construction.submittal",
        entity_id=submittal.id,
        company_id=payload.company_id,
        project_id=payload.project_id,
        before=None,
        after={"number": submittal.number, "title": submittal.title},
        correlation_id=correlation_id,
    )
    db.commit()
    return SubmittalResponse.model_validate(submittal, from_attributes=True)


@router.get("", response_model=list[SubmittalResponse])
def list_submittals(
    company_id: uuid.UUID = Query(alias="companyId"),
    project_id: uuid.UUID | None = Query(default=None, alias="projectId"),
    db: Session = Depends(get_db),
    user=Depends(require_permission("construction.submittal", "read")),
) -> list[SubmittalResponse]:
    assert_company_access(
        db, user_id=user.id, resource="construction.submittal", action="read", company_id=company_id
    )
    return [
        SubmittalResponse.model_validate(s, from_attributes=True)
        for s in submittal_service.list_submittals(db, company_id=company_id, project_id=project_id)
    ]


@router.get("/{submittal_id}", response_model=SubmittalResponse)
def get_submittal(
    submittal_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("construction.submittal", "read")),
) -> SubmittalResponse:
    submittal = _resolve_submittal(db, submittal_id)
    assert_company_access(
        db,
        user_id=user.id,
        resource="construction.submittal",
        action="read",
        company_id=submittal.company_id,
    )
    return SubmittalResponse.model_validate(submittal, from_attributes=True)


@router.post("/{submittal_id}/response", response_model=SubmittalResponse)
def record_submittal_response(
    submittal_id: uuid.UUID,
    payload: SubmittalResponseRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("construction.submittal", "review")),
    correlation_id: str = Depends(get_correlation_id),
) -> SubmittalResponse:
    submittal = _resolve_submittal(db, submittal_id)
    assert_company_access(
        db,
        user_id=user.id,
        resource="construction.submittal",
        action="review",
        company_id=submittal.company_id,
    )
    before_status = submittal.status
    updated = submittal_service.record_submittal_response(
        db, submittal_id=submittal_id, response=payload.response, reviewed_by=user.id, commit=False
    )
    audit_service.record(
        db,
        actor_user_id=user.id,
        action="construction.submittal.response",
        entity_type="construction.submittal",
        entity_id=submittal_id,
        company_id=submittal.company_id,
        project_id=submittal.project_id,
        before={"status": before_status},
        after={"status": updated.status},
        correlation_id=correlation_id,
    )
    db.commit()
    return SubmittalResponse.model_validate(updated, from_attributes=True)


@router.post("/{submittal_id}/decision", response_model=SubmittalResponse)
def decide_submittal(
    submittal_id: uuid.UUID,
    payload: SubmittalDecisionRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("construction.submittal", "decide")),
    correlation_id: str = Depends(get_correlation_id),
) -> SubmittalResponse:
    submittal = _resolve_submittal(db, submittal_id)
    assert_company_access(
        db,
        user_id=user.id,
        resource="construction.submittal",
        action="decide",
        company_id=submittal.company_id,
    )
    before_status = submittal.status
    updated = submittal_service.decide_submittal(
        db, submittal_id=submittal_id, decision=payload.decision, decided_by=user.id, commit=False
    )
    audit_service.record(
        db,
        actor_user_id=user.id,
        action="construction.submittal.decide",
        entity_type="construction.submittal",
        entity_id=submittal_id,
        company_id=submittal.company_id,
        project_id=submittal.project_id,
        before={"status": before_status},
        after={"status": updated.status},
        correlation_id=correlation_id,
    )
    db.commit()
    return SubmittalResponse.model_validate(updated, from_attributes=True)
