import uuid
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

# Budget versioning (orden maestra §41, docs/BUDGET_CONTROLLING.md).
# BASELINE se crea una sola vez y nunca se sobrescribe (sus BudgetLine no se
# tocan jamás). Una ChangeOrder aprobada crea un nuevo Budget version=REVISED
# enlazado a `previous_budget_id`, y el anterior pasa a status=SUPERSEDED
# (nunca se elimina -- se mantiene el historial completo).
BUDGET_VERSIONS = ("BASELINE", "REVISED")
BUDGET_STATUSES = ("ACTIVE", "SUPERSEDED")


class Budget(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "budgets"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ACTIVE")
    currency_code: Mapped[str] = mapped_column(String(3), ForeignKey("currencies.code"), nullable=False)
    previous_budget_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("budgets.id"), nullable=True
    )
    change_order_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("change_orders.id"), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)


class BudgetLine(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "budget_lines"

    budget_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("budgets.id", ondelete="CASCADE"), nullable=False
    )
    wbs_node_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("wbs_nodes.id", ondelete="SET NULL"), nullable=True
    )
    economic_category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("economic_categories.id", ondelete="SET NULL"), nullable=True
    )
    cost_center_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cost_centers.id", ondelete="SET NULL"), nullable=True
    )
    fiscal_period_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("fiscal_periods.id", ondelete="SET NULL"), nullable=True
    )
    authorized_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
