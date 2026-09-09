import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, ForeignKey, Integer, Numeric, String
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
    __table_args__ = (
        CheckConstraint(
            "status IN ('DRAFT','SUBMITTED','APPROVED','REJECTED','CONVERTED','CANCELLED')",
            name="ck_purchase_requisitions_status_valid",
        ),
    )

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
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_pr_lines_quantity_positive"),
        CheckConstraint("estimated_unit_cost >= 0", name="ck_pr_lines_cost_non_negative"),
    )

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
    __table_args__ = (
        CheckConstraint(
            "status IN ('DRAFT','SENT','CLOSED','CANCELLED')",
            name="ck_rfq_status_valid",
        ),
    )

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
    __table_args__ = (
        CheckConstraint(
            "status IN ('RECEIVED','SELECTED','REJECTED')",
            name="ck_supplier_quotations_status_valid",
        ),
        CheckConstraint("delivery_days >= 0", name="ck_supplier_quotations_delivery_non_negative"),
    )

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
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_quotation_lines_quantity_positive"),
        CheckConstraint("unit_price >= 0", name="ck_quotation_lines_price_non_negative"),
        CheckConstraint("tax_amount >= 0", name="ck_quotation_lines_tax_non_negative"),
    )

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
    __table_args__ = (
        CheckConstraint(
            "status IN ('DRAFT','APPROVAL_PENDING','APPROVED','SENT','PARTIALLY_RECEIVED','RECEIVED','CLOSED','CANCELLED')",
            name="ck_purchase_orders_status_valid",
        ),
    )

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
    # ORDEN MAESTRA §19-§20 — cuando la PO deriva de un contrato de ejecución
    # es un DESGLOSE del compromiso contractual, nunca un compromiso adicional.
    supplier_contract_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("supplier_contracts.id", ondelete="RESTRICT"), nullable=True
    )
    currency_code: Mapped[str] = mapped_column(String(3), ForeignKey("currencies.code"), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="DRAFT")


class PurchaseOrderLine(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "purchase_order_lines"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_po_lines_quantity_positive"),
        CheckConstraint("unit_price >= 0", name="ck_po_lines_price_non_negative"),
        CheckConstraint("tax_amount >= 0", name="ck_po_lines_tax_non_negative"),
        CheckConstraint("quantity_received >= 0", name="ck_po_lines_received_non_negative"),
    )

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
    __table_args__ = (
        CheckConstraint("quantity_received > 0", name="ck_gr_lines_quantity_positive"),
    )

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
    __table_args__ = (
        CheckConstraint(
            "progress_percentage >= 0 AND progress_percentage <= 100",
            name="ck_service_entries_progress_valid",
        ),
        CheckConstraint("accepted_value >= 0", name="ck_service_entries_value_non_negative"),
    )

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
    __table_args__ = (
        CheckConstraint(
            "status IN ('MATCHED','EXCEPTION')",
            name="ck_three_way_match_results_status_valid",
        ),
        CheckConstraint("supplier_invoice_amount >= 0", name="ck_twm_invoice_amount_non_negative"),
        CheckConstraint("supplier_invoice_quantity >= 0", name="ck_twm_invoice_quantity_non_negative"),
        CheckConstraint("received_quantity >= 0", name="ck_twm_received_quantity_non_negative"),
        CheckConstraint("ordered_amount >= 0", name="ck_twm_ordered_amount_non_negative"),
        CheckConstraint(
            "quantity_tolerance_pct >= 0 AND quantity_tolerance_pct <= 100",
            name="ck_twm_quantity_tolerance_valid",
        ),
        CheckConstraint(
            "amount_tolerance_pct >= 0 AND amount_tolerance_pct <= 100",
            name="ck_twm_amount_tolerance_valid",
        ),
    )

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
