from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.domain.errors import InvalidCredentialsError, NotAuthenticatedError
from app.models.user import User
from app.repositories import role_repository, session_repository, user_repository
from app.security.passwords import verify_password
from app.security.tokens import generate_session_token, hash_token


def login(
    db: Session, *, email: str, password: str, user_agent: str | None
) -> tuple[User, list[str], str, datetime]:
    settings = get_settings()
    user = user_repository.get_by_email(db, email)
    if user is None or not user.is_active or not verify_password(password, user.password_hash):
        raise InvalidCredentialsError("Correo o contraseña incorrectos.")

    raw_token = generate_session_token()
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.session_ttl_days)
    session_repository.create_session(
        db,
        user_id=user.id,
        token_hash=hash_token(raw_token),
        expires_at=expires_at,
        user_agent=user_agent,
    )
    db.commit()

    roles = role_repository.get_role_names_for_user(db, user.id)
    return user, roles, raw_token, expires_at


def logout(db: Session, *, raw_token: str) -> None:
    session_repository.delete_session(db, token_hash=hash_token(raw_token))
    db.commit()


def get_current_user(db: Session, *, raw_token: str | None) -> tuple[User, list[str]]:
    if not raw_token:
        raise NotAuthenticatedError("No hay sesión activa.")

    session = session_repository.get_valid_session(
        db, token_hash=hash_token(raw_token), now=datetime.now(timezone.utc)
    )
    if session is None:
        raise NotAuthenticatedError("La sesión expiró o no es válida.")

    user = user_repository.get_by_id(db, session.user_id)
    if user is None or not user.is_active:
        raise NotAuthenticatedError("El usuario ya no está disponible.")

    roles = role_repository.get_role_names_for_user(db, user.id)
    return user, roles
