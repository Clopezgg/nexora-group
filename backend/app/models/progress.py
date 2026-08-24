import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

# ProgressRecord (orden maestra §72). `evidence_ref` es una referencia libre
# (URL/id) hasta que el track de Document Management (Azure Blob) aterrice
# la entidad Document real -- documentado como deuda intencional.


class ProgressRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "progress_records"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    wbs_node_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("wbs_nodes.id", ondelete="SET NULL"), nullable=True
    )
    record_date: Mapped[date] = mapped_column(Date, nullable=False)
    planned_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    actual_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    description: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    responsible: Mapped[str | None] = mapped_column(String(255), nullable=True)
    evidence_ref: Mapped[str | None] = mapped_column(String(500), nullable=True)
