import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

# Treasury es dueño del dinero (CLAUDE.md §7 / orden maestra §17-33). Un
# TreasuryAccount NUNCA tiene project_id: solo Company. `gl_account_id`
# enlaza la cuenta de tesorería con su cuenta del catálogo contable (Banco/
# Caja) para que el Posting Engine pueda debitar/acreditarla directamente.
TREASURY_ACCOUNT_KINDS = ("BANK", "CASH", "OTHER")
TREASURY_ACCOUNT_STATUSES = ("ACTIVE", "CLOSED")


class TreasuryAccount(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "treasury_accounts"
    __table_args__ = (
        CheckConstraint("kind IN ('BANK','CASH','OTHER')", name="ck_treasury_accounts_kind"),
        CheckConstraint("status IN ('ACTIVE','CLOSED')", name="ck_treasury_accounts_status"),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    institution: Mapped[str | None] = mapped_column(String(255), nullable=True)
    account_reference: Mapped[str | None] = mapped_column(String(64), nullable=True)
    currency_code: Mapped[str] = mapped_column(String(3), ForeignKey("currencies.code"), nullable=False)
    gl_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ACTIVE")


class FundRestriction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Uso restringido de fondos (orden maestra §31). IMPORTANTE: esto NUNCA
    significa que el proyecto referenciado posee el dinero -- Treasury sigue
    siendo el dueño; esto solo documenta para qué puede usarse ese saldo."""

    __tablename__ = "fund_restrictions"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_fund_restrictions_amount_positive"),
    )

    treasury_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("treasury_accounts.id", ondelete="CASCADE"), nullable=False
    )
    restricted_for_project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    active: Mapped[bool] = mapped_column(nullable=False, default=True)


CASH_CLOSING_STATUSES = ("DRAFT", "APPROVED")


class CashClosing(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "cash_closings"
    __table_args__ = (
        CheckConstraint(
            "opening_amount >= 0 AND expected_amount >= 0 AND counted_amount >= 0",
            name="ck_cash_closings_amounts_non_negative",
        ),
        CheckConstraint("status IN ('DRAFT','APPROVED')", name="ck_cash_closings_status"),
    )

    treasury_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("treasury_accounts.id", ondelete="RESTRICT"), nullable=False
    )
    closing_date: Mapped[date] = mapped_column(Date, nullable=False)
    opening_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    expected_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    counted_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    difference_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    responsible_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="DRAFT")
    accounting_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounting_documents.id", ondelete="SET NULL"), nullable=True
    )


BANK_STATEMENT_LINE_STATUSES = ("UNMATCHED", "MATCHED", "PARTIAL", "EXCLUDED")


class BankStatement(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "bank_statements"

    treasury_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("treasury_accounts.id", ondelete="RESTRICT"), nullable=False
    )
    statement_date: Mapped[date] = mapped_column(Date, nullable=False)
    opening_balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    closing_balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    reference: Mapped[str | None] = mapped_column(String(128), nullable=True)


class BankStatementLine(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Append-only por diseño: una vez creada, una línea de estado de cuenta
    nunca se edita ni se borra -- solo cambia su `status` al conciliarla."""

    __tablename__ = "bank_statement_lines"
    __table_args__ = (
        CheckConstraint("amount <> 0", name="ck_bank_statement_lines_amount_non_zero"),
        CheckConstraint(
            "status IN ('UNMATCHED','MATCHED','PARTIAL','EXCLUDED')",
            name="ck_bank_statement_lines_status",
        ),
    )

    bank_statement_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bank_statements.id", ondelete="CASCADE"), nullable=False
    )
    line_date: Mapped[date] = mapped_column(Date, nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="UNMATCHED")


class ReconciliationMatch(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "reconciliation_matches"
    __table_args__ = (
        CheckConstraint("matched_amount > 0", name="ck_reconciliation_matches_amount_positive"),
    )

    bank_statement_line_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bank_statement_lines.id", ondelete="CASCADE"), nullable=False
    )
    accounting_document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounting_documents.id", ondelete="RESTRICT"), nullable=False
    )
    matched_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    matched_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    matched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Remittance(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Siempre scope=CENTRAL, project_id=NULL (orden maestra §27) -- se
    aplica al crear el AccountingDocument vía posting_service, que ya
    rechaza cualquier otra combinación (INV-OPS-001)."""

    __tablename__ = "remittances"
    __table_args__ = (
        CheckConstraint(
            "original_amount > 0 AND fx_rate > 0 AND base_amount > 0",
            name="ck_remittances_amounts_positive",
        ),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False
    )
    treasury_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("treasury_accounts.id", ondelete="RESTRICT"), nullable=False
    )
    counter_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False
    )
    sender: Mapped[str] = mapped_column(String(255), nullable=False)
    provider: Mapped[str | None] = mapped_column(String(255), nullable=True)
    channel: Mapped[str | None] = mapped_column(String(64), nullable=True)
    currency_code: Mapped[str] = mapped_column(String(3), ForeignKey("currencies.code"), nullable=False)
    original_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    fx_rate: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False, default=Decimal("1"))
    base_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    reference: Mapped[str | None] = mapped_column(String(128), nullable=True)
    remittance_date: Mapped[date] = mapped_column(Date, nullable=False)
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    accounting_document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounting_documents.id", ondelete="RESTRICT"), nullable=False
    )


class GeneralExpense(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Siempre scope=GENERAL, project_id=NULL. NO consume Project Budget
    (orden maestra §28) -- se paga de inmediato contra Treasury."""

    __tablename__ = "general_expenses"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_general_expenses_amount_positive"),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False
    )
    treasury_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("treasury_accounts.id", ondelete="RESTRICT"), nullable=False
    )
    expense_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False
    )
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency_code: Mapped[str] = mapped_column(String(3), ForeignKey("currencies.code"), nullable=False)
    expense_date: Mapped[date] = mapped_column(Date, nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    accounting_document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounting_documents.id", ondelete="RESTRICT"), nullable=False
    )


TRANSFER_KINDS = ("BANK_TO_BANK", "BANK_TO_CASH", "CASH_TO_BANK", "CASH_TO_CASH")


class TreasuryTransfer(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Movimiento de activos entre cuentas de tesorería. NO es Revenue ni
    Expense (orden maestra §30)."""

    __tablename__ = "treasury_transfers"
    __table_args__ = (
        CheckConstraint(
            "source_treasury_account_id <> destination_treasury_account_id",
            name="ck_treasury_transfers_distinct_accounts",
        ),
        CheckConstraint("amount > 0", name="ck_treasury_transfers_amount_positive"),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False
    )
    source_treasury_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("treasury_accounts.id", ondelete="RESTRICT"), nullable=False
    )
    destination_treasury_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("treasury_accounts.id", ondelete="RESTRICT"), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency_code: Mapped[str] = mapped_column(String(3), ForeignKey("currencies.code"), nullable=False)
    transfer_date: Mapped[date] = mapped_column(Date, nullable=False)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    accounting_document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounting_documents.id", ondelete="RESTRICT"), nullable=False
    )
