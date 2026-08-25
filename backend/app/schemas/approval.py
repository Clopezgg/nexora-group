import uuid
from datetime import datetime
from decimal import Decimal

from app.schemas.base import CamelModel


class ApprovalRequestResponse(CamelModel):
    id: uuid.UUID
    policy_id: uuid.UUID | None
    entity_type: str
    entity_id: uuid.UUID
    company_id: uuid.UUID
    project_id: uuid.UUID | None
    module: str
    requested_by: uuid.UUID
    assigned_to: uuid.UUID | None
    assigned_role: str | None
    status: str
    priority: str
    amount: Decimal | None
    comment: str | None
    decided_by: uuid.UUID | None
    decided_at: datetime | None
    created_at: datetime
