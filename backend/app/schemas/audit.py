import uuid
from datetime import datetime

from app.schemas.base import CamelModel


class AuditLogResponse(CamelModel):
    id: uuid.UUID
    actor_user_id: uuid.UUID | None
    actor_full_name: str | None = None
    actor_email: str | None = None
    action: str
    entity_type: str
    entity_id: uuid.UUID
    company_id: uuid.UUID
    project_id: uuid.UUID | None
    before: dict | None
    after: dict | None
    correlation_id: str
    created_at: datetime
