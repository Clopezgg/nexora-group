import uuid
from datetime import datetime

from app.schemas.base import CamelModel


class NotificationResponse(CamelModel):
    id: uuid.UUID
    recipient_user_id: uuid.UUID
    type: str
    title: str
    body: str
    entity_type: str | None
    entity_id: uuid.UUID | None
    read_at: datetime | None
    created_at: datetime
