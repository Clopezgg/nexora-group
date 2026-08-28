from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.services import edit_access_service

_PROTECTED_METHODS = {"PUT", "PATCH", "DELETE"}


def register_edit_access_guard(app: FastAPI) -> None:
    """Add a secondary confirmation to mutations of existing information.

    POST stays untouched because creating/approving/posting documents is already
    governed by the normal RBAC/SoD workflow. PUT/PATCH/DELETE represent edits or
    deletions of data that already exists and therefore require the short-lived
    edit capability in addition to the route's existing authentication/RBAC.
    """

    @app.middleware("http")
    async def edit_access_guard(request: Request, call_next):
        settings = get_settings()
        if (
            settings.edit_access_required
            and request.method in _PROTECTED_METHODS
            and request.url.path.startswith("/api/")
        ):
            capability = request.headers.get("x-nexora-edit-access")
            if not edit_access_service.verify_capability(capability, settings):
                return JSONResponse(
                    status_code=status.HTTP_428_PRECONDITION_REQUIRED,
                    content={
                        "detail": "Esta modificación requiere desbloquear la edición con el token de seguridad."
                    },
                )
        return await call_next(request)
