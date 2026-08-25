import uuid
from datetime import date, datetime
from typing import Literal

from app.schemas.base import CamelModel


class RfiCreateRequest(CamelModel):
    company_id: uuid.UUID
    project_id: uuid.UUID
    wbs_node_id: uuid.UUID | None = None
    subject: str
    question: str
    responsible: str | None = None
    due_date: date | None = None


class RfiRespondRequest(CamelModel):
    response: str


class RfiResponse(CamelModel):
    id: uuid.UUID
    company_id: uuid.UUID
    project_id: uuid.UUID
    wbs_node_id: uuid.UUID | None
    number: str
    subject: str
    question: str
    response: str | None
    responsible: str | None
    requested_by: uuid.UUID
    responded_by: uuid.UUID | None
    due_date: date | None
    responded_at: datetime | None
    closed_at: datetime | None
    status: Literal["OPEN", "ANSWERED", "CLOSED"]
    created_at: datetime
