from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.services import edit_access_service

_PROTECTED_METHODS = {"PUT", "PATCH", "DELETE"}
_EXEMPT_PATHS = {"/api/context"}


def register_edit_access_guard(app: FastAPI) -> None:
    """Add a secondary confirmation to mutations of existing business information.

    POST stays untouched because creating/approving/posting documents is already
    governed by the normal RBAC/SoD workflow. PUT/PATCH/DELETE represent edits or
    deletions of existing business data and therefore require the short-lived edit
    capability in addition to the route's existing authentication/RBAC.

    ActiveUIContext is navigation state, not business data, so changing the selected
    project must remain usable without unlocking edit access.
    """

    @app.middleware("http")
    async def edit_access_guard(request: Request, call_next):
        settings = get_settings()
        if (
            settings.edit_access_required
            and request.method in _PROTECTED_METHODS
            and request.url.path.startswith("/api/")
            and request.url.path not in _EXEMPT_PATHS
        ):
            capability = request.headers.get("x-nexora-edit-access")
            session_token = request.cookies.get(settings.session_cookie_name)
            if not edit_access_service.verify_capability(
                capability,
                session_token=session_token,
                settings=settings,
            ):
                return JSONResponse(
                    status_code=status.HTTP_428_PRECONDITION_REQUIRED,
                    content={
                        "detail": "Esta modificación requiere desbloquear la edición con el token de seguridad."
                    },
                )
        return await call_next(request)
