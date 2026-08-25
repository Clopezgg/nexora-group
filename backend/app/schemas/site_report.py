import uuid
from datetime import date, datetime
from typing import Literal

from app.schemas.base import CamelModel


class DailySiteReportCreateRequest(CamelModel):
    project_id: uuid.UUID
    report_date: date
    weather: str | None = None
    workforce_summary: str | None = None
    activities_performed: str
    equipment_used: str | None = None
    materials_used: str | None = None
    incidents: str | None = None
    observations: str | None = None


class DailySiteReportPhotoResponse(CamelModel):
    id: uuid.UUID
    daily_site_report_id: uuid.UUID
    evidence_id: uuid.UUID
    created_at: datetime


class DailySiteReportPhotoAttachRequest(CamelModel):
    evidence_id: uuid.UUID


class DailySiteReportResponse(CamelModel):
    id: uuid.UUID
    project_id: uuid.UUID
    report_date: date
    weather: str | None
    workforce_summary: str | None
    activities_performed: str
    equipment_used: str | None
    materials_used: str | None
    incidents: str | None
    observations: str | None
    author_id: uuid.UUID
    status: Literal["DRAFT", "SUBMITTED", "APPROVED", "REJECTED"]
    approved_by_id: uuid.UUID | None
    approved_at: datetime | None
    photos: list[DailySiteReportPhotoResponse] = []
