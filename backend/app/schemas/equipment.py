import uuid
from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import Field

from app.schemas.base import CamelModel


class EquipmentCreateRequest(CamelModel):
    company_id: uuid.UUID
    asset_id: uuid.UUID | None = None
    project_id: uuid.UUID | None = None
    equipment_type: str
    name: str
    serial_number: str | None = None
    plate_number: str | None = None
    operator: str | None = None


class EquipmentResponse(CamelModel):
    id: uuid.UUID
    company_id: uuid.UUID
    asset_id: uuid.UUID | None
    project_id: uuid.UUID | None
    equipment_type: str
    name: str
    serial_number: str | None
    plate_number: str | None
    operator: str | None
    hour_meter: Decimal
    odometer: Decimal
    status: str


class EquipmentStatusChangeRequest(CamelModel):
    status: Literal["AVAILABLE", "IN_USE", "UNDER_MAINTENANCE", "OUT_OF_SERVICE"]


class FuelLogCreateRequest(CamelModel):
    company_id: uuid.UUID
    equipment_id: uuid.UUID | None = None
    vehicle_description: str | None = None
    log_date: date
    quantity: Decimal = Field(gt=0, max_digits=12, decimal_places=3)
    unit_cost: Decimal = Field(gt=0, max_digits=12, decimal_places=4)
    scope: Literal["GENERAL", "PROJECT"]
    project_id: uuid.UUID | None = None


class FuelLogResponse(CamelModel):
    id: uuid.UUID
    company_id: uuid.UUID
    equipment_id: uuid.UUID | None
    vehicle_description: str | None
    log_date: date
    quantity: Decimal
    unit_cost: Decimal
    total_cost: Decimal
    scope: str
    project_id: uuid.UUID | None


class MaintenancePlanCreateRequest(CamelModel):
    name: str
    trigger_type: Literal["DATE", "HOURS", "ODOMETER"]
    trigger_value: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    description: str | None = None


class MaintenancePlanResponse(CamelModel):
    id: uuid.UUID
    equipment_id: uuid.UUID
    name: str
    trigger_type: str
    trigger_value: Decimal
    description: str | None
    active: bool


class MaintenanceOrderCreateRequest(CamelModel):
    plan_id: uuid.UUID | None = None
    order_type: Literal["PREVENTIVE", "CORRECTIVE"]
    opened_at: date
    supplier_id: uuid.UUID | None = None
    supplier_ref: str | None = None
    description: str | None = None


class MaintenanceOrderUpdateRequest(CamelModel):
    status: Literal["OPEN", "IN_PROGRESS", "CLOSED", "CANCELLED"] | None = None
    parts_cost: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=2)
    labor_cost: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=2)
    downtime_hours: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    description: str | None = None
    closed_at: date | None = None


class MaintenanceOrderResponse(CamelModel):
    id: uuid.UUID
    equipment_id: uuid.UUID
    plan_id: uuid.UUID | None
    order_type: str
    status: str
    opened_at: date
    closed_at: date | None
    supplier_id: uuid.UUID | None
    supplier_ref: str | None
    parts_cost: Decimal
    labor_cost: Decimal
    downtime_hours: Decimal
    description: str | None
