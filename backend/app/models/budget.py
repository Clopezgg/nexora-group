import uuid
from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

BUDGET_VERSIONS = ("BASELINE", "REVISED")
BUDGET_STATUSES = ("ACTIVE", "SUPERSEDED")


class Budget(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "budgets"
    __table_args__ = (
        CheckConstraint("version IN ('BASELINE','REVISED')", name="ck_budgets_version_valid"),
        CheckConstraint("status IN ('ACTIVE','SUPERSEDED')", name="ck_budgets_status_valid"),
    )

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
    __table_args__ = (
        CheckConstraint("authorized_amount > 0", name="ck_budget_lines_amount_positive"),
    )

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
