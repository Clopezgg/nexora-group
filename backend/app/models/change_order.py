import uuid
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

# Change Orders (orden maestra §43). Al aprobarse (ver budget_service.
# approve_change_order) genera un nuevo Budget version=REVISED -- nunca
# modifica el BASELINE. `budget_change_amount` es exclusivamente impacto en
# COSTO interno. `contract_change_amount` documenta por separado el impacto
# comercial esperado; no modifica silenciosamente ningún SalesContract.
CHANGE_ORDER_STATUSES = ("DRAFT", "SUBMITTED", "APPROVED", "REJECTED", "IMPLEMENTED", "CANCELLED")


class ChangeOrder(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "change_orders"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    wbs_node_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("wbs_nodes.id", ondelete="SET NULL"), nullable=True
    )
    reason: Mapped[str] = mapped_column(String(1000), nullable=False)
    scope_change: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    budget_change_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    contract_change_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    schedule_change_days: Mapped[int | None] = mapped_column(nullable=True)
    requested_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="DRAFT")
