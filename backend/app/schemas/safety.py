import uuid
from datetime import date, datetime
from typing import Literal

from app.schemas.base import CamelModel


class SafetyObservationCreateRequest(CamelModel):
    project_id: uuid.UUID
    observation_date: date
    category: str
    description: str
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = "LOW"
    responsible_user_id: uuid.UUID | None = None
    corrective_action: str | None = None
    evidence_id: uuid.UUID | None = None


class SafetyObservationResponse(CamelModel):
    id: uuid.UUID
    project_id: uuid.UUID
    observation_date: date
    category: str
    description: str
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    responsible_user_id: uuid.UUID | None
    corrective_action: str | None
    status: Literal["OPEN", "CLOSED"]
    closed_at: datetime | None
    evidence_id: uuid.UUID | None


class SafetyIncidentCreateRequest(CamelModel):
    project_id: uuid.UUID
    incident_date: date
    description: str
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    responsible_user_id: uuid.UUID | None = None
    corrective_action: str | None = None
    evidence_id: uuid.UUID | None = None


class SafetyIncidentResponse(CamelModel):
    id: uuid.UUID
    project_id: uuid.UUID
    incident_date: date
    description: str
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    responsible_user_id: uuid.UUID | None
    corrective_action: str | None
    status: Literal["OPEN", "CLOSED"]
    closed_at: datetime | None
    evidence_id: uuid.UUID | None
