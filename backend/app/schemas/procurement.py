import uuid
from datetime import date
from decimal import Decimal

from app.schemas.base import CamelModel


class RequisitionLineRequest(CamelModel):
    item_id: uuid.UUID | None = None
    description: str
    quantity: Decimal
    estimated_unit_cost: Decimal = Decimal("0")


class RequisitionCreateRequest(CamelModel):
    company_id: uuid.UUID
    project_id: uuid.UUID | None = None
    justification: str | None = None
    priority: str = "NORMAL"
    required_date: date | None = None
    lines: list[RequisitionLineRequest]


class RequisitionLineResponse(CamelModel):
    id: uuid.UUID
    item_id: uuid.UUID | None
    description: str
    quantity: Decimal
    estimated_unit_cost: Decimal


class RequisitionResponse(CamelModel):
    id: uuid.UUID
    company_id: uuid.UUID
    requisition_number: str
    project_id: uuid.UUID | None
    justification: str | None
    priority: str
    required_date: date | None
    status: str
    lines: list[RequisitionLineResponse] = []


class RfqCreateRequest(CamelModel):
    company_id: uuid.UUID
    purchase_requisition_id: uuid.UUID | None = None
    due_date: date | None = None
    terms: str | None = None
    supplier_ids: list[uuid.UUID]


class RfqResponse(CamelModel):
    id: uuid.UUID
    rfq_number: str
    purchase_requisition_id: uuid.UUID | None
    due_date: date | None
    status: str


class QuotationLineRequest(CamelModel):
    purchase_requisition_line_id: uuid.UUID | None = None
    description: str
    quantity: Decimal
    unit_price: Decimal
    tax_amount: Decimal = Decimal("0")


class QuotationCreateRequest(CamelModel):
    supplier_id: uuid.UUID
    currency_code: str
    delivery_days: int | None = None
    payment_terms: str | None = None
    valid_until: date | None = None
    notes: str | None = None
    lines: list[QuotationLineRequest]


class QuotationLineResponse(CamelModel):
    id: uuid.UUID
    description: str
    quantity: Decimal
    unit_price: Decimal
    tax_amount: Decimal


class QuotationResponse(CamelModel):
    id: uuid.UUID
    request_for_quotation_id: uuid.UUID
    supplier_id: uuid.UUID
    currency_code: str
    status: str
    total: Decimal
    delivery_days: int | None
    payment_terms: str | None
    valid_until: date | None
    notes: str | None
    lines: list[QuotationLineResponse] = []


class PurchaseOrderLineRequest(CamelModel):
    item_id: uuid.UUID | None = None
    description: str
    quantity: Decimal
    unit_price: Decimal
    tax_amount: Decimal = Decimal("0")


class PurchaseOrderCreateRequest(CamelModel):
    company_id: uuid.UUID
    supplier_id: uuid.UUID
    project_id: uuid.UUID | None = None
    currency_code: str
    lines: list[PurchaseOrderLineRequest]


class PurchaseOrderFromQuotationRequest(CamelModel):
    company_id: uuid.UUID
    supplier_quotation_id: uuid.UUID
    project_id: uuid.UUID | None = None


class PurchaseOrderLineResponse(CamelModel):
    id: uuid.UUID
    item_id: uuid.UUID | None
    description: str
    quantity: Decimal
    unit_price: Decimal
    tax_amount: Decimal
    quantity_received: Decimal


class PurchaseOrderResponse(CamelModel):
    id: uuid.UUID
    company_id: uuid.UUID
    po_number: str
    supplier_id: uuid.UUID
    project_id: uuid.UUID | None
    currency_code: str
    status: str
    lines: list[PurchaseOrderLineResponse] = []


class GoodsReceiptLineRequest(CamelModel):
    purchase_order_line_id: uuid.UUID
    quantity_received: Decimal


class GoodsReceiptCreateRequest(CamelModel):
    purchase_order_id: uuid.UUID
    warehouse_id: uuid.UUID
    received_at: date
    quality_notes: str | None = None
    lines: list[GoodsReceiptLineRequest]


class GoodsReceiptResponse(CamelModel):
    id: uuid.UUID
    receipt_number: str
    purchase_order_id: uuid.UUID
    warehouse_id: uuid.UUID
    received_at: date


class ServiceEntryCreateRequest(CamelModel):
    purchase_order_id: uuid.UUID
    period_start: date
    period_end: date
    progress_percentage: Decimal
    accepted_value: Decimal


class ServiceEntryResponse(CamelModel):
    id: uuid.UUID
    entry_number: str
    purchase_order_id: uuid.UUID
    progress_percentage: Decimal
    accepted_value: Decimal


class ThreeWayMatchRequest(CamelModel):
    purchase_order_id: uuid.UUID
    supplier_invoice_id: uuid.UUID | None = None
    supplier_invoice_amount: Decimal
    supplier_invoice_quantity: Decimal
    quantity_tolerance_pct: Decimal = Decimal("0")
    amount_tolerance_pct: Decimal = Decimal("0")


class ThreeWayMatchResponse(CamelModel):
    id: uuid.UUID
    purchase_order_id: uuid.UUID
    status: str
    ordered_amount: Decimal
    received_quantity: Decimal
    exceptions: list = []
