import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id, get_db
from app.schemas.context import ActiveUIContextResponse, ActiveUIContextUpdateRequest
from app.services import context_service

router = APIRouter(prefix="/context", tags=["context"])


@router.get("", response_model=ActiveUIContextResponse)
def get_context(
    db: Session = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> ActiveUIContextResponse:
    return context_service.get_active_context(db, user_id)


@router.put("", response_model=ActiveUIContextResponse)
def update_context(
    payload: ActiveUIContextUpdateRequest,
    db: Session = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> ActiveUIContextResponse:
    try:
        return context_service.set_active_context(db, user_id, payload.active_project_id)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
