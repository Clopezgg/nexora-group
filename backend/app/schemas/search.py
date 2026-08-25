import uuid

from app.schemas.base import CamelModel


class SearchResultResponse(CamelModel):
    id: uuid.UUID
    label: str
    group: str
    path: str
    entity_type: str
