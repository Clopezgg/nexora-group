import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, Numeric, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

# Accounts Payable. `supplier_id` es una FK real a Supplier; la obligación,
# el pago, el asiento y la evidencia deben permanecer trazables como un solo
# evento económico.
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

SUPPLIER_PAYMENT_METHODS = ("TRANSFER", "DEPOSIT", "CHECK", "CASH", "OTHER")


class SupplierInvoice(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "supplier_invoices"
    __table_args__ = (
        Index("uq_supplier_invoice_business_number", "company_id", "supplier_id", "invoice_number_normalized", unique=True, postgresql_where=text("status <> 'CANCELLED'")),
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
    invoice_number_normalized: Mapped[str] = mapped_column(String(64), nullable=False)
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
    supplier_contract_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("supplier_contracts.id", ondelete="RESTRICT"), nullable=True
    )
    contract_installment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contract_payment_installments.id", ondelete="RESTRICT"),
        nullable=True,
    )
    purchase_order_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("purchase_orders.id", ondelete="RESTRICT"), nullable=True
    )


class SupplierPayment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Pago contra una factura.

    El método se congela en el pago original. TRANSFER/DEPOSIT/CHECK requieren
    evidencia validada antes de contabilizar; la evidencia queda enlazada al
    AccountingDocument emitido, que a su vez está unido a este pago.
    """

    __tablename__ = "supplier_payments"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_supplier_payments_amount_positive"),
        CheckConstraint(
            "payment_method IN ('TRANSFER','DEPOSIT','CHECK','CASH','OTHER')",
            name="ck_supplier_payments_method",
        ),
    )

    supplier_invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("supplier_invoices.id", ondelete="RESTRICT"), nullable=False
    )
    treasury_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("treasury_accounts.id", ondelete="RESTRICT"), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    payment_date: Mapped[date] = mapped_column(Date, nullable=False)
    payment_method: Mapped[str] = mapped_column(String(16), nullable=False, default="TRANSFER")
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
    bank_transaction_reference: Mapped[str | None] = mapped_column(String(120), nullable=True)
    payment_observations: Mapped[str | None] = mapped_column(String(500), nullable=True)


class SupplierInvoiceCashForecastItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Forecast-only due-date bucket for a non-contract AP invoice.

    This is not an executable contractual installment. Actual contractual
    payment obligations are owned by ContractPaymentSchedule instead.
    """

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


# Backward-compatible import name for existing integrations. Keeping the alias
# avoids a schema/API migration while making the runtime semantic explicit.
SupplierInvoicePaymentPlanItem = SupplierInvoiceCashForecastItem
