import uuid
from datetime import date
from decimal import Decimal

from app.schemas.base import CamelModel


class ItemCreateRequest(CamelModel):
    company_id: uuid.UUID
    sku: str
    name: str
    item_type: str = "MATERIAL"
    category: str | None = None
    uom: str = "UND"
    description: str | None = None
    track_inventory: bool = True


class ItemResponse(CamelModel):
    id: uuid.UUID
    company_id: uuid.UUID
    sku: str
    name: str
    item_type: str
    category: str | None
    uom: str
    description: str | None
    track_inventory: bool
    active: bool


class WarehouseCreateRequest(CamelModel):
    company_id: uuid.UUID
    project_id: uuid.UUID | None = None
    code: str
    name: str


class WarehouseResponse(CamelModel):
    id: uuid.UUID
    company_id: uuid.UUID
    project_id: uuid.UUID | None
    code: str
    name: str
    status: str


class StockPositionResponse(CamelModel):
    item_id: uuid.UUID
    warehouse_id: uuid.UUID
    quantity_on_hand: Decimal
    average_cost: Decimal


class StockReceiveRequest(CamelModel):
    company_id: uuid.UUID
    item_id: uuid.UUID
    warehouse_id: uuid.UUID
    quantity: Decimal
    unit_cost: Decimal


class StockIssueToProjectRequest(CamelModel):
    company_id: uuid.UUID
    item_id: uuid.UUID
    warehouse_id: uuid.UUID
    project_id: uuid.UUID
    quantity: Decimal


class StockTransferRequest(CamelModel):
    company_id: uuid.UUID
    item_id: uuid.UUID
    from_warehouse_id: uuid.UUID
    to_warehouse_id: uuid.UUID
    quantity: Decimal


class StockLedgerEntryResponse(CamelModel):
    id: uuid.UUID
    item_id: uuid.UUID
    warehouse_id: uuid.UUID
    movement_type: str
    quantity: Decimal
    unit_cost: Decimal
    resulting_qty_on_hand: Decimal
    resulting_avg_cost: Decimal
    project_id: uuid.UUID | None


class PhysicalCountLineRequest(CamelModel):
    item_id: uuid.UUID
    expected_quantity: Decimal
    counted_quantity: Decimal


class PhysicalCountCreateRequest(CamelModel):
    company_id: uuid.UUID
    warehouse_id: uuid.UUID
    count_date: date
    lines: list[PhysicalCountLineRequest]


class PhysicalCountResponse(CamelModel):
    id: uuid.UUID
    warehouse_id: uuid.UUID
    count_date: date
    status: str
