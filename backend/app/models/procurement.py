import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

"""Procurement end-to-end (orden maestra §44-51). Cada etapa es un documento
distinto -- NO un mega-documento. Flujo: PR -> approval -> RFQ -> Supplier
Quotations -> Bid Comparison -> PO -> Goods Receipt / Service Entry ->
Three-Way Match -> (Supplier Invoice / pago los construye Track A)."""

PR_STATUSES = ("DRAFT", "SUBMITTED", "APPROVED", "REJECTED", "CONVERTED", "CANCELLED")
RFQ_STATUSES = ("DRAFT", "SENT", "CLOSED", "CANCELLED")
QUOTATION_STATUSES = ("RECEIVED", "SELECTED", "REJECTED")
PO_STATUSES = (
    "DRAFT",
    "APPROVAL_PENDING",
    "APPROVED",
    "SENT",
    "PARTIALLY_RECEIVED",
    "RECEIVED",
    "CLOSED",
    "CANCELLED",
)
THREE_WAY_MATCH_STATUSES = ("MATCHED", "EXCEPTION")


class PurchaseRequisition(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "purchase_requisitions"

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False
    )
    requisition_number: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    requester_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="RESTRICT"), nullable=True
    )
    justification: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    priority: Mapped[str] = mapped_column(String(16), nullable=False, default="NORMAL")
    required_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="DRAFT")
    approved_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )


class PurchaseRequisitionLine(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "purchase_requisition_lines"

    purchase_requisition_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("purchase_requisitions.id", ondelete="CASCADE"), nullable=False
    )
    item_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("items.id", ondelete="RESTRICT"), nullable=True
    )
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    estimated_unit_cost: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0"))


class RequestForQuotation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "requests_for_quotation"

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False
    )
    rfq_number: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    purchase_requisition_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("purchase_requisitions.id", ondelete="RESTRICT"), nullable=True
    )
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    terms: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="DRAFT")


class RfqSupplier(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """RFQ enviado a un supplier específico (una RFQ puede ir a varios)."""

    __tablename__ = "rfq_suppliers"

    request_for_quotation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("requests_for_quotation.id", ondelete="CASCADE"), nullable=False
    )
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="RESTRICT"), nullable=False
    )


class SupplierQuotation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "supplier_quotations"

    request_for_quotation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("requests_for_quotation.id", ondelete="CASCADE"), nullable=False
    )
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="RESTRICT"), nullable=False
    )
    currency_code: Mapped[str] = mapped_column(String(3), ForeignKey("currencies.code"), nullable=False)
    delivery_days: Mapped[int | None] = mapped_column(nullable=True)
    payment_terms: Mapped[str | None] = mapped_column(String(255), nullable=True)
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="RECEIVED")


class SupplierQuotationLine(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "supplier_quotation_lines"

    supplier_quotation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("supplier_quotations.id", ondelete="CASCADE"), nullable=False
    )
    purchase_requisition_line_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("purchase_requisition_lines.id", ondelete="RESTRICT"), nullable=True
    )
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))


class PurchaseOrder(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "purchase_orders"

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False
    )
    po_number: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="RESTRICT"), nullable=False
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="RESTRICT"), nullable=True
    )
    supplier_quotation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("supplier_quotations.id", ondelete="RESTRICT"), nullable=True
    )
    currency_code: Mapped[str] = mapped_column(String(3), ForeignKey("currencies.code"), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="DRAFT")


class PurchaseOrderLine(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "purchase_order_lines"

    purchase_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False
    )
    item_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("items.id", ondelete="RESTRICT"), nullable=True
    )
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    quantity_received: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0"))


class GoodsReceipt(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "goods_receipts"

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False
    )
    receipt_number: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    purchase_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("purchase_orders.id", ondelete="RESTRICT"), nullable=False
    )
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False
    )
    received_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    received_at: Mapped[date] = mapped_column(Date, nullable=False)
    quality_notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)


class GoodsReceiptLine(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "goods_receipt_lines"

    goods_receipt_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("goods_receipts.id", ondelete="CASCADE"), nullable=False
    )
    purchase_order_line_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("purchase_order_lines.id", ondelete="RESTRICT"), nullable=False
    )
    quantity_received: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)


class ServiceEntry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Para subcontratos/servicios (orden maestra §51) -- equivalente a un
    Goods Receipt pero para avance de servicio, no recepción física."""

    __tablename__ = "service_entries"

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False
    )
    entry_number: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    purchase_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("purchase_orders.id", ondelete="RESTRICT"), nullable=False
    )
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    progress_percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    accepted_value: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    approved_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )


class ThreeWayMatchResult(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """INV-PROC-001: las diferencias entre PO / Goods Receipt-Service Entry /
    Supplier Invoice nunca desaparecen silenciosamente -- siempre queda un
    registro, MATCHED o EXCEPTION con el detalle de la discrepancia. El
    `supplier_invoice_id` es una referencia libre (UUID) porque el
    SupplierInvoice real lo construye Track A en paralelo -- ver
    docs/PROCUREMENT.md para el contrato de integración exacto."""

    __tablename__ = "three_way_match_results"

    purchase_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("purchase_orders.id", ondelete="RESTRICT"), nullable=False
    )
    supplier_invoice_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    supplier_invoice_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    supplier_invoice_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    received_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    ordered_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    quantity_tolerance_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=Decimal("0"))
    amount_tolerance_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=Decimal("0"))
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    exceptions: Mapped[list | None] = mapped_column(JSONB, nullable=True)
