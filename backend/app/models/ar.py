import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

# Accounts Receivable (orden maestra §36). Misma deuda intencional que AP:
# `customer_name` en texto libre hasta que Track E (Commercial) aterrice la
# entidad real `Customer` -- ver docs/ACCOUNTING.md.
CUSTOMER_INVOICE_STATUSES = (
    "DRAFT",
    "APPROVED",
    "PARTIALLY_COLLECTED",
    "COLLECTED",
    "CANCELLED",
)


class CustomerInvoice(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "customer_invoices"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_customer_invoices_amount_positive"),
        CheckConstraint(
            "amount_collected >= 0 AND amount_collected <= amount",
            name="ck_customer_invoices_collected_within_total",
        ),
        CheckConstraint(
            "(scope IN ('CENTRAL','GENERAL') AND project_id IS NULL) "
            "OR (scope = 'PROJECT' AND project_id IS NOT NULL)",
            name="ck_customer_invoices_operation_scope",
        ),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False
    )
    customer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    invoice_number: Mapped[str] = mapped_column(String(64), nullable=False)
    scope: Mapped[str] = mapped_column(String(16), nullable=False)
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="RESTRICT"), nullable=True
    )
    revenue_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False
    )
    receivable_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False
    )
    currency_code: Mapped[str] = mapped_column(String(3), ForeignKey("currencies.code"), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    amount_collected: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    invoice_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="DRAFT")
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    accounting_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounting_documents.id", ondelete="SET NULL"), nullable=True
    )


class CustomerReceipt(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "customer_receipts"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_customer_receipts_amount_positive"),
    )

    customer_invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customer_invoices.id", ondelete="RESTRICT"), nullable=False
    )
    treasury_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("treasury_accounts.id", ondelete="RESTRICT"), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    receipt_date: Mapped[date] = mapped_column(Date, nullable=False)
    accounting_document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounting_documents.id", ondelete="RESTRICT"), nullable=False
    )
