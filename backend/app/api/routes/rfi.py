import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.rfi import RfiCreateRequest, RfiRespondRequest, RfiResponse
from app.services import rfi_service
from app.services.permission_service import assert_company_access, require_permission

router = APIRouter(prefix="/rfis", tags=["rfi"])


def _resolve_rfi(db: Session, rfi_id: uuid.UUID):
    rfi = rfi_service.get_rfi(db, rfi_id)
    if rfi is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RFI no encontrado")
    return rfi


@router.post("", response_model=RfiResponse, status_code=201)
def create_rfi(
    payload: RfiCreateRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("construction.rfi", "create")),
) -> RfiResponse:
    assert_company_access(
        db, user_id=user.id, resource="construction.rfi", action="create", company_id=payload.company_id
    )
    rfi = rfi_service.create_rfi(
        db,
        company_id=payload.company_id,
        project_id=payload.project_id,
        wbs_node_id=payload.wbs_node_id,
        subject=payload.subject,
        question=payload.question,
        responsible=payload.responsible,
        requested_by=user.id,
        due_date=payload.due_date,
    )
    return RfiResponse.model_validate(rfi, from_attributes=True)


@router.get("", response_model=list[RfiResponse])
def list_rfis(
    company_id: uuid.UUID = Query(alias="companyId"),
    project_id: uuid.UUID | None = Query(default=None, alias="projectId"),
    db: Session = Depends(get_db),
    user=Depends(require_permission("construction.rfi", "read")),
) -> list[RfiResponse]:
    assert_company_access(
        db, user_id=user.id, resource="construction.rfi", action="read", company_id=company_id
    )
    return [
        RfiResponse.model_validate(r, from_attributes=True)
        for r in rfi_service.list_rfis(db, company_id=company_id, project_id=project_id)
    ]


@router.get("/{rfi_id}", response_model=RfiResponse)
def get_rfi(
    rfi_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("construction.rfi", "read")),
) -> RfiResponse:
    rfi = _resolve_rfi(db, rfi_id)
    assert_company_access(
        db, user_id=user.id, resource="construction.rfi", action="read", company_id=rfi.company_id
    )
    return RfiResponse.model_validate(rfi, from_attributes=True)


@router.post("/{rfi_id}/respond", response_model=RfiResponse)
def respond_rfi(
    rfi_id: uuid.UUID,
    payload: RfiRespondRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("construction.rfi", "respond")),
) -> RfiResponse:
    rfi = _resolve_rfi(db, rfi_id)
    assert_company_access(
        db, user_id=user.id, resource="construction.rfi", action="respond", company_id=rfi.company_id
    )
    updated = rfi_service.respond_rfi(db, rfi_id=rfi_id, response=payload.response, responded_by=user.id)
    return RfiResponse.model_validate(updated, from_attributes=True)


@router.post("/{rfi_id}/close", response_model=RfiResponse)
def close_rfi(
    rfi_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("construction.rfi", "close")),
) -> RfiResponse:
    rfi = _resolve_rfi(db, rfi_id)
    assert_company_access(
        db, user_id=user.id, resource="construction.rfi", action="close", company_id=rfi.company_id
    )
    updated = rfi_service.close_rfi(db, rfi_id=rfi_id)
    return RfiResponse.model_validate(updated, from_attributes=True)
