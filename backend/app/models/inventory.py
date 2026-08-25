import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

"""Stock Ledger append-only (orden maestra §54): NUNCA se hace UPDATE/DELETE
sobre una entrada existente para "corregir" una cantidad -- una corrección
es una nueva entrada ADJUSTMENT. Todo movimiento pasa por
`app.services.inventory_service`, nunca se inserta a mano desde un router."""

STOCK_MOVEMENT_TYPES = ("RECEIPT", "TRANSFER", "ISSUE", "RETURN", "ADJUSTMENT", "PHYSICAL_COUNT")
PHYSICAL_COUNT_STATUSES = ("DRAFT", "COUNTED", "APPROVED")


class StockLedgerEntry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "stock_ledger_entries"

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False
    )
    item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("items.id", ondelete="RESTRICT"), nullable=False
    )
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False
    )
    movement_type: Mapped[str] = mapped_column(String(16), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    resulting_qty_on_hand: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    resulting_avg_cost: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="RESTRICT"), nullable=True
    )
    source_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)


class PhysicalCount(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "physical_counts"

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False
    )
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False
    )
    count_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="DRAFT")
    approved_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )


class PhysicalCountLine(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "physical_count_lines"

    physical_count_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("physical_counts.id", ondelete="CASCADE"), nullable=False
    )
    item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("items.id", ondelete="RESTRICT"), nullable=False
    )
    expected_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    counted_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
