import uuid
from collections.abc import Generator

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.domain.errors import NotAuthenticatedError
from app.models.user import User
from app.services import auth_service, rate_limit_service


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _client_ip(request: Request) -> str:
    """Return the rate-limit identity supplied by the trusted ingress hop.

    Azure Container Apps appends the address it observes to
    ``X-Forwarded-For`` and documents that only the *rightmost* value is
    provided by Container Apps; values to its left can originate in the
    client request and must not be trusted for anti-abuse decisions. Local
    development without ingress falls back to ``request.client.host``.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        addresses = [value.strip() for value in forwarded.split(",") if value.strip()]
        if addresses:
            return addresses[-1]
    return request.client.host if request.client else "unknown"


def enforce_login_rate_limit(request: Request, db: Session = Depends(get_db)) -> None:
    """NXR-REQ-0107: defensa de aplicación real, no delegada a
    Azure Front Door/WAF -- ver orden maestra §9. Por IP, no por cuenta;
    el lockout por cuenta (NXR-REQ-0008) ya protege una cuenta conocida.
    Deja que `RateLimitExceededError` se propague tal cual (mapeada a 429
    por `app.api.error_handlers`, mismo patrón que el resto de errores de
    dominio) -- el `finally` garantiza que el conteo del bucket se
    persista tanto si el request pasa como si se rechaza; sin el commit
    explícito aquí, `get_db()` haría rollback del incremento al cerrar la
    sesión y el rate limit nunca avanzaría."""
    settings = get_settings()
    try:
        rate_limit_service.check_and_increment(
            db,
            bucket_key=f"login:{_client_ip(request)}",
            limit=settings.login_rate_limit_max_attempts,
            window_seconds=settings.login_rate_limit_window_seconds,
            reject_on_limit=False,
        )
    finally:
        db.commit()


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
