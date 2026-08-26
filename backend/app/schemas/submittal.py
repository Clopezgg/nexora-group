import uuid
from datetime import date, datetime
from typing import Literal

from app.schemas.base import CamelModel


class SubmittalCreateRequest(CamelModel):
    company_id: uuid.UUID
    project_id: uuid.UUID
    wbs_node_id: uuid.UUID | None = None
    title: str
    description: str | None = None
    supplier_id: uuid.UUID | None = None
    contract_id: uuid.UUID | None = None
    submitted_at: date
    due_date: date | None = None
    evidence_id: uuid.UUID | None = None


class SubmittalResponseRequest(CamelModel):
    response: str


class SubmittalDecisionRequest(CamelModel):
    decision: Literal["APPROVED", "REJECTED"]


class SubmittalResponse(CamelModel):
    id: uuid.UUID
    company_id: uuid.UUID
    project_id: uuid.UUID
    wbs_node_id: uuid.UUID | None
    number: str
    revision: int
    title: str
    description: str | None
    supplier_id: uuid.UUID | None
    contract_id: uuid.UUID | None
    status: Literal["SUBMITTED", "UNDER_REVIEW", "APPROVED", "REJECTED"]
    submitted_by: uuid.UUID
    submitted_at: date
    due_date: date | None
    reviewer_response: str | None
    reviewed_by: uuid.UUID | None
    response_recorded_at: datetime | None
    decided_by: uuid.UUID | None
    decided_at: datetime | None
    evidence_id: uuid.UUID | None
    created_at: datetime
