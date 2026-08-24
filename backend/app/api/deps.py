import uuid
from collections.abc import Generator

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.domain.errors import NotAuthenticatedError
from app.models.user import User
from app.services import auth_service


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    request: Request, db: Session = Depends(get_db)
) -> tuple[User, list[str]]:
    settings = get_settings()
    raw_token = request.cookies.get(settings.session_cookie_name)
    try:
        return auth_service.get_current_user(db, raw_token=raw_token)
    except NotAuthenticatedError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(error)
        ) from error


def get_current_user_id(
    current: tuple[User, list[str]] = Depends(get_current_user),
) -> uuid.UUID:
    user, _roles = current
    return user.id
