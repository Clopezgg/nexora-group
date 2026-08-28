import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.config import get_settings
from app.models.user import User
from app.services import edit_access_service, rate_limit_service

router = APIRouter(prefix="/edit-access", tags=["edit-access"])


class EditAccessRequest(BaseModel):
    token: str = Field(min_length=1, max_length=32)


class EditAccessResponse(BaseModel):
    capability: str
    expires_at: int = Field(alias="expiresAt")

    model_config = {"populate_by_name": True}


@router.post("/verify", response_model=EditAccessResponse)
def verify_edit_access(
    payload: EditAccessRequest,
    request: Request,
    db: Session = Depends(get_db),
    current: tuple[User, list[str]] = Depends(get_current_user),
) -> EditAccessResponse:
    user, _roles = current
    settings = get_settings()
    if not edit_access_service.verify_pin(payload.token, settings):
        try:
            rate_limit_service.check_and_increment(
                db,
                bucket_key=f"edit-access:{user.id}",
                limit=settings.edit_access_max_attempts,
                window_seconds=settings.edit_access_window_seconds,
            )
        finally:
            db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token de edición incorrecto.",
        )

    session_token = request.cookies.get(settings.session_cookie_name)
    if not session_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sesión requerida.")

    capability, expires_at = edit_access_service.issue_capability(
        user_id=uuid.UUID(str(user.id)),
        session_token=session_token,
        settings=settings,
    )
    return EditAccessResponse(capability=capability, expiresAt=expires_at)
