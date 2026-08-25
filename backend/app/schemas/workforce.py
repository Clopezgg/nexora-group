import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import Field

from app.schemas.base import CamelModel


class WorkerCreateRequest(CamelModel):
    company_id: uuid.UUID
    full_name: str
    role_title: str | None = None
    standard_hourly_rate: Decimal = Field(gt=0, max_digits=12, decimal_places=2)


class WorkerResponse(CamelModel):
    id: uuid.UUID
    company_id: uuid.UUID
    full_name: str
    role_title: str | None
    standard_hourly_rate: Decimal
    active: bool


class TimeEntryCreateRequest(CamelModel):
    company_id: uuid.UUID
    worker_id: uuid.UUID
    scope: Literal["CENTRAL", "GENERAL", "PROJECT"]
    project_id: uuid.UUID | None = None
    work_date: date
    hours_worked: Decimal = Field(gt=0, max_digits=6, decimal_places=2)
    hourly_rate: Decimal = Field(gt=0, max_digits=12, decimal_places=2)


class TimeEntryApproveRequest(CamelModel):
    approved_hours: Decimal | None = Field(default=None, ge=0, max_digits=6, decimal_places=2)


class TimeEntryResponse(CamelModel):
    id: uuid.UUID
    company_id: uuid.UUID
    worker_id: uuid.UUID
    scope: str
    project_id: uuid.UUID | None
    work_date: date
    hours_worked: Decimal
    hourly_rate: Decimal
    status: str
    approved_hours: Decimal | None
    labor_cost: Decimal | None
    approved_by_id: uuid.UUID | None
    approved_at: datetime | None
