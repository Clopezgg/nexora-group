from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.api.deps import enforce_login_rate_limit, get_current_user, get_db
from app.core.config import get_settings
from app.domain.errors import AccountLockedError, InvalidCredentialsError
from app.models.user import User
from app.schemas.auth import CurrentUserResponse, LoginRequest
from app.services import auth_service, permission_service

router = APIRouter(prefix="/auth", tags=["auth"])


def _response(db: Session, user: User, roles: list[str]) -> CurrentUserResponse:
    return CurrentUserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        roles=roles,
        permissions=permission_service.list_user_permissions(db, user_id=user.id),
    )


@router.post("/login", response_model=CurrentUserResponse, dependencies=[Depends(enforce_login_rate_limit)])
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
    response.set_cookie(
        key=settings.session_cookie_name,
        value=raw_token,
        httponly=True,
        secure=settings.is_production,
        samesite="none" if settings.is_production else "lax",
        max_age=max(max_age, 0),
        path="/",
    )
    return _response(db, user, roles)


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
def me(
    current: tuple[User, list[str]] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CurrentUserResponse:
    user, roles = current
    return _response(db, user, roles)
