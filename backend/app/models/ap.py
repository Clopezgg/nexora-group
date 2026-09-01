import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

# Accounts Payable (orden maestra §34-35). `supplier_id` es una FK real a
# `Supplier` (Track C - Suppliers/Contracts, ver app/models/supplier.py);
# la deuda intencional de texto libre documentada anteriormente en
# docs/ACCOUNTING.md quedó resuelta al integrar Track C.
SUPPLIER_INVOICE_STATUSES = (
    "DRAFT",
    "REVIEW",
    "APPROVED",
    "SCHEDULED",
    "PARTIALLY_PAID",
    "PAID",
    "RECONCILED",
    "CANCELLED",
)


class SupplierInvoice(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "supplier_invoices"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_supplier_invoices_amount_positive"),
        CheckConstraint("tax_amount >= 0", name="ck_supplier_invoices_tax_non_negative"),
        CheckConstraint(
            "amount_paid >= 0 AND amount_paid <= amount + tax_amount",
            name="ck_supplier_invoices_paid_within_total",
        ),
        CheckConstraint(
            "(scope IN ('CENTRAL','GENERAL') AND project_id IS NULL) "
            "OR (scope = 'PROJECT' AND project_id IS NOT NULL)",
            name="ck_supplier_invoices_operation_scope",
        ),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False
    )
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="RESTRICT"), nullable=False
    )
    invoice_number: Mapped[str] = mapped_column(String(64), nullable=False)
    scope: Mapped[str] = mapped_column(String(16), nullable=False)
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="RESTRICT"), nullable=True
    )
    cost_center_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cost_centers.id", ondelete="RESTRICT"), nullable=True
    )
    expense_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False
    )
    payable_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False
    )
    currency_code: Mapped[str] = mapped_column(String(3), ForeignKey("currencies.code"), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    amount_paid: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    invoice_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="DRAFT")
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    accrual_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounting_documents.id", ondelete="SET NULL"), nullable=True
    )
    # Enlace explícito con el contrato de origen (orden maestra final §4).
    # Nullable sólo cuando la obligación realmente no proviene de un contrato.
    supplier_contract_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("supplier_contracts.id", ondelete="RESTRICT"), nullable=True
    )


class SupplierPayment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Pago simple contra UNA factura (sin allocation multi-factura todavía
    -- registrado como deuda intencional; ver docs/TREASURY.md)."""

    __tablename__ = "supplier_payments"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_supplier_payments_amount_positive"),
    )

    supplier_invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("supplier_invoices.id", ondelete="RESTRICT"), nullable=False
    )
    treasury_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("treasury_accounts.id", ondelete="RESTRICT"), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    payment_date: Mapped[date] = mapped_column(Date, nullable=False)
    accounting_document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounting_documents.id", ondelete="RESTRICT"), nullable=False
    )
    reversal_accounting_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounting_documents.id", ondelete="RESTRICT"), nullable=True
    )
    reversed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reversed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    reversal_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Referencia del MOVIMIENTO bancario (distinta de
    # TreasuryAccount.account_reference, que es el número de nuestra cuenta).
    # Orden maestra final §25 — se persiste, se audita, se imprime y la
    # conciliación puede aprovecharla.
    bank_transaction_reference: Mapped[str | None] = mapped_column(String(120), nullable=True)
    # Observaciones persistidas del pago (§24) — DB, audit, inspector, voucher.
    payment_observations: Mapped[str | None] = mapped_column(String(500), nullable=True)


class SupplierInvoicePaymentPlanItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Cuota de un plan de pago de una factura de proveedor (orden maestra
    Phase 2 -- planes/cuotas de pago). La suma de `amount` de todas las
    cuotas de una factura debe igualar su total (amount + tax_amount); esto
    se valida en `ap_service.set_payment_plan`, no en la base, porque el plan
    se reemplaza atómicamente."""

    __tablename__ = "supplier_invoice_payment_plan_items"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_supplier_invoice_plan_amount_positive"),
        CheckConstraint("sequence >= 1", name="ck_supplier_invoice_plan_sequence_positive"),
    )

    supplier_invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("supplier_invoices.id", ondelete="CASCADE"), nullable=False
    )
    sequence: Mapped[int] = mapped_column(nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
