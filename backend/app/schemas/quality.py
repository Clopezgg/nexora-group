import uuid
from datetime import date, datetime
from typing import Literal

from app.schemas.base import CamelModel


class QualityInspectionCreateRequest(CamelModel):
    project_id: uuid.UUID
    wbs_node_id: uuid.UUID | None = None
    inspection_type: str
    inspection_date: date
    result: Literal["PENDING", "PASS", "FAIL"] = "PENDING"
    notes: str | None = None
    evidence_id: uuid.UUID | None = None


class QualityInspectionResponse(CamelModel):
    id: uuid.UUID
    project_id: uuid.UUID
    wbs_node_id: uuid.UUID | None
    inspection_type: str
    inspection_date: date
    inspector_id: uuid.UUID
    result: Literal["PENDING", "PASS", "FAIL"]
    notes: str | None
    evidence_id: uuid.UUID | None


class NonConformanceCreateRequest(CamelModel):
    project_id: uuid.UUID
    quality_inspection_id: uuid.UUID | None = None
    description: str
    responsible_user_id: uuid.UUID
    due_date: date | None = None
    evidence_id: uuid.UUID | None = None


class NonConformanceResponse(CamelModel):
    id: uuid.UUID
    project_id: uuid.UUID
    quality_inspection_id: uuid.UUID | None
    description: str
    responsible_user_id: uuid.UUID
    due_date: date | None
    status: Literal["OPEN", "CLOSED"]
    closed_at: datetime | None
    evidence_id: uuid.UUID | None


class CorrectiveActionCreateRequest(CamelModel):
    description: str
    responsible_user_id: uuid.UUID
    due_date: date
    evidence_id: uuid.UUID | None = None


class CorrectiveActionResponse(CamelModel):
    id: uuid.UUID
    non_conformance_id: uuid.UUID
    description: str
    responsible_user_id: uuid.UUID
    due_date: date
    status: Literal["OPEN", "COMPLETED"]
    completed_at: datetime | None
    evidence_id: uuid.UUID | None
