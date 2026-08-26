import uuid

from app.schemas.base import CamelModel


class ActiveUIContextResponse(CamelModel):
    active_project_id: uuid.UUID | None
    active_project_name: str | None


class ActiveUIContextUpdateRequest(CamelModel):
    active_project_id: uuid.UUID | None = None
