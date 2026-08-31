"""Project Contract Payment Control (orden maestra final §1-§16, §46-§53).

Subledger contractual: CONTRATO → PLAN → CUOTA → ALLOCATION → PAGO. Nunca
sustituye la contabilidad (el pago sigue generando un AccountingDocument
POSTED por el Posting Engine); esto explica *qué mes contractual* liquidó
*qué dinero*.

CLAVE (§52/§53): `period_year`/`period_month` de la cuota es el PERÍODO
CONTRACTUAL y es INDEPENDIENTE de `payment_date` y del período contable
(`fiscal_period_id` del AccountingDocument).
"""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

SCHEDULE_TYPES = ("MONTHLY", "CUSTOM")
SCHEDULE_STATUSES = ("ACTIVE", "COMPLETED", "CANCELLED")
INSTALLMENT_STATUSES = ("UPCOMING", "DUE", "PARTIALLY_PAID", "PAID", "OVERDUE", "CANCELLED")


class ContractPaymentSchedule(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "contract_payment_schedules"
    __table_args__ = (
        UniqueConstraint("supplier_contract_id", name="uq_contract_payment_schedule_contract"),
        CheckConstraint("total_scheduled >= 0", name="ck_contract_payment_schedule_total"),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False
    )
    supplier_contract_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("supplier_contracts.id", ondelete="RESTRICT"), nullable=False
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="RESTRICT"), nullable=True
    )
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False)
    schedule_type: Mapped[str] = mapped_column(String(16), nullable=False, default="MONTHLY")
    start_period: Mapped[date] = mapped_column(Date, nullable=False)
    end_period: Mapped[date | None] = mapped_column(Date, nullable=True)
    total_scheduled: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ACTIVE")


class ContractPaymentInstallment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "contract_payment_installments"
    __table_args__ = (
        UniqueConstraint("schedule_id", "sequence", name="uq_contract_installment_sequence"),
        UniqueConstraint(
            "schedule_id", "period_year", "period_month",
            name="uq_contract_installment_period",
        ),
        CheckConstraint("scheduled_amount > 0", name="ck_contract_installment_amount"),
        CheckConstraint("retention_amount >= 0", name="ck_contract_installment_retention"),
        CheckConstraint("sequence >= 1", name="ck_contract_installment_sequence"),
        CheckConstraint("period_month BETWEEN 1 AND 12", name="ck_contract_installment_month"),
    )

    schedule_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contract_payment_schedules.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sequence: Mapped[int] = mapped_column(nullable=False)
    period_year: Mapped[int] = mapped_column(nullable=False)
    period_month: Mapped[int] = mapped_column(nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    scheduled_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    retention_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    net_due: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="UPCOMING")
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)


class ContractPaymentAllocation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Qué SupplierPayment liquidó qué cuota contractual y por cuánto (§8)."""

    __tablename__ = "contract_payment_allocations"
    __table_args__ = (
        UniqueConstraint(
            "supplier_payment_id", "installment_id",
            name="uq_contract_allocation_payment_installment",
        ),
        CheckConstraint("amount_applied > 0", name="ck_contract_allocation_amount"),
    )

    supplier_payment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("supplier_payments.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    installment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contract_payment_installments.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    amount_applied: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    applied_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reversed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    override_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
