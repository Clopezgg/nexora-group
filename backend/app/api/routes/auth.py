from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.config import get_settings
from app.domain.errors import AccountLockedError, InvalidCredentialsError
from app.models.user import User
from app.schemas.auth import CurrentUserResponse, LoginRequest
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=CurrentUserResponse)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> CurrentUserResponse:
    settings = get_settings()
    try:
        user, roles, raw_token, expires_at = auth_service.login(
            db,
            email=payload.email,
            password=payload.password,
            user_agent=request.headers.get("user-agent"),
        )
    except InvalidCredentialsError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(error)
        ) from error
    except AccountLockedError as error:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail=str(error)) from error

    max_age = int((expires_at - datetime.now(timezone.utc)).total_seconds())
    # En producción frontend y backend viven en subdominios distintos (Render):
    # el cookie debe poder viajar cross-site, lo que exige SameSite=None + Secure.
    # En local ambos son "localhost" (mismo site), así que Lax es suficiente y
    # no requiere HTTPS.
    response.set_cookie(
        key=settings.session_cookie_name,
        value=raw_token,
        httponly=True,
        secure=settings.is_production,
        samesite="none" if settings.is_production else "lax",
        max_age=max(max_age, 0),
        path="/",
    )
    return CurrentUserResponse(id=user.id, email=user.email, full_name=user.full_name, roles=roles)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> None:
    settings = get_settings()
    raw_token = request.cookies.get(settings.session_cookie_name)
    if raw_token:
        auth_service.logout(db, raw_token=raw_token)
    response.delete_cookie(settings.session_cookie_name, path="/")


@router.get("/me", response_model=CurrentUserResponse)
def me(current: tuple[User, list[str]] = Depends(get_current_user)) -> CurrentUserResponse:
    user, roles = current
    return CurrentUserResponse(id=user.id, email=user.email, full_name=user.full_name, roles=roles)
