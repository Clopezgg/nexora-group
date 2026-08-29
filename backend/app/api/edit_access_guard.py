from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.services import edit_access_service

_PROTECTED_METHODS = {"PUT", "PATCH", "DELETE"}
_EXEMPT_PATHS = {"/api/context"}


def register_edit_access_guard(app: FastAPI) -> None:
    """Add finite secondary confirmation to mutations of existing business data."""

    @app.middleware("http")
    async def edit_access_guard(request: Request, call_next):
        settings = get_settings()
        if (
            settings.edit_access_required
            and request.method in _PROTECTED_METHODS
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
            with SessionLocal() as db:
                try:
                    allowed = edit_access_service.consume_capability(
                        db,
                        capability,
                        session_token=session_token,
                        settings=settings,
                    )
                    if allowed:
                        db.commit()
                    else:
                        db.rollback()
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
