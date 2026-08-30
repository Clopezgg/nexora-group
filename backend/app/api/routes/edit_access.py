import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.api.deps_correlation import get_correlation_id
from app.core.config import get_settings
from app.domain.errors import RateLimitExceededError
from app.models.edit_access import EditAccessEvent
from app.models.user import User
from app.services import edit_access_service, rate_limit_service

router = APIRouter(prefix="/edit-access", tags=["edit-access"])


class EditAccessRequest(BaseModel):
    # Protected Edit may reuse a strong account re-authentication secret when
    # a dedicated PIN has not been provisioned. Keep the bound finite while
    # allowing password-manager generated credentials longer than 32 chars.
    token: str = Field(min_length=1, max_length=256)


class EditAccessResponse(BaseModel):
    capability: str
    expires_at: int = Field(alias="expiresAt")
    uses_remaining: int = Field(alias="usesRemaining")

    model_config = {"populate_by_name": True}


def _record_event(
    db: Session,
    *,
    user_id: uuid.UUID,
    success: bool,
    outcome: str,
    correlation_id: str,
) -> None:
    db.add(
        EditAccessEvent(
            user_id=user_id,
            success=success,
            outcome=outcome,
            correlation_id=correlation_id,
        )
    )
    db.flush()


@router.post("/verify", response_model=EditAccessResponse)
def verify_edit_access(
    payload: EditAccessRequest,
    request: Request,
    db: Session = Depends(get_db),
    current: tuple[User, list[str]] = Depends(get_current_user),
    correlation_id: str = Depends(get_correlation_id),
) -> EditAccessResponse:
    user, _roles = current
    settings = get_settings()
    bucket_key = f"edit-access:{user.id}"

    if not settings.edit_access_configured:
        _record_event(
            db,
            user_id=user.id,
            success=False,
            outcome="NOT_CONFIGURED",
            correlation_id=correlation_id,
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="La autorización de edición protegida no está configurada en el servidor.",
        )

    try:
        rate_limit_service.assert_not_limited(
            db,
            bucket_key=bucket_key,
            limit=settings.edit_access_max_attempts,
            window_seconds=settings.edit_access_window_seconds,
        )
    except RateLimitExceededError:
        _record_event(
            db,
            user_id=user.id,
            success=False,
            outcome="LOCKED",
            correlation_id=correlation_id,
        )
        db.commit()
        raise

    if not edit_access_service.verify_pin(payload.token, settings):
        try:
            rate_limit_service.check_and_increment(
                db,
                bucket_key=bucket_key,
                limit=settings.edit_access_max_attempts,
                window_seconds=settings.edit_access_window_seconds,
            )
        except RateLimitExceededError:
            _record_event(
                db,
                user_id=user.id,
                success=False,
                outcome="LOCKED",
                correlation_id=correlation_id,
            )
            db.commit()
            raise
        _record_event(
            db,
            user_id=user.id,
            success=False,
            outcome="INVALID",
            correlation_id=correlation_id,
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Autorización de edición incorrecta.",
        )

    session_token = request.cookies.get(settings.session_cookie_name)
    if not session_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sesión requerida.")

    rate_limit_service.reset_bucket(db, bucket_key=bucket_key)
    capability, expires_at = edit_access_service.issue_capability(
        user_id=uuid.UUID(str(user.id)),
        session_token=session_token,
        settings=settings,
    )
    row = edit_access_service.persist_capability(
        db,
        token=capability,
        session_token=session_token,
        user_id=uuid.UUID(str(user.id)),
        settings=settings,
    )
    _record_event(
        db,
        user_id=user.id,
        success=True,
        outcome="UNLOCKED",
        correlation_id=correlation_id,
    )
    db.commit()
    return EditAccessResponse(
        capability=capability,
        expiresAt=expires_at,
        usesRemaining=row.uses_remaining,
    )
