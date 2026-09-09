from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.logging import get_correlation_id
from app.domain.errors import NotAuthenticatedError
from app.models.edit_access import EditAccessEvent
from app.services import auth_service, edit_access_service

_PROTECTED_METHODS = {"PUT", "PATCH", "DELETE"}
_EXEMPT_PATHS = {"/api/context"}


def _requires_protected_edit(method: str, path: str) -> bool:
    """Classify mutation semantics centrally; HTTP POST is not inherently safe.

    Normal resource creation remains governed by RBAC only.  Existing-resource
    transitions, approvals and financial commands are protected regardless of
    their transport verb.
    """
    if method in _PROTECTED_METHODS:
        return path not in _EXEMPT_PATHS
    if method != "POST":
        return False
    parts = [part for part in path.split("/") if part]
    sensitive_suffixes = {"status", "decide", "reverse", "reopen", "close", "post", "pay", "collect"}
    return bool(parts and parts[-1] in sensitive_suffixes)


def register_edit_access_guard(app: FastAPI) -> None:
    """Add finite secondary confirmation to mutations of existing business data."""

    @app.middleware("http")
    async def edit_access_guard(request: Request, call_next):
        settings = get_settings()
        if (
            settings.edit_access_required
            and _requires_protected_edit(request.method, request.url.path)
            and request.url.path.startswith("/api/")
            and request.url.path not in _EXEMPT_PATHS
        ):
            if not settings.edit_access_configured:
                return JSONResponse(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    content={
                        "detail": "La autorización de edición protegida todavía no está configurada en el servidor."
                    },
                )
            capability = request.headers.get("x-nexora-edit-access")
            session_token = request.cookies.get(settings.session_cookie_name)
            correlation_id = get_correlation_id()
            with SessionLocal() as db:
                try:
                    try:
                        current_user, _roles = auth_service.get_current_user(
                            db, raw_token=session_token
                        )
                    except NotAuthenticatedError:
                        current_user = None
                    allowed = edit_access_service.consume_capability(
                        db,
                        capability,
                        session_token=session_token,
                        settings=settings,
                    )
                    db.add(
                        EditAccessEvent(
                            user_id=current_user.id if current_user is not None else None,
                            success=allowed,
                            outcome="MUTATION_ALLOWED" if allowed else "MUTATION_DENIED",
                            correlation_id=correlation_id,
                        )
                    )
                    db.commit()
                except Exception:
                    db.rollback()
                    raise
            if not allowed:
                return JSONResponse(
                    status_code=status.HTTP_428_PRECONDITION_REQUIRED,
                    content={
                        "detail": "Esta modificación requiere desbloquear la edición con la autorización de seguridad."
                    },
                )
        return await call_next(request)
