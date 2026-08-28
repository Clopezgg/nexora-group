import uuid

from app.schemas.base import CamelModel


class DimensionResponse(CamelModel):
    id: uuid.UUID
    company_id: uuid.UUID
    code: str
    name: str
