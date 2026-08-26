import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

# Work Breakdown Structure jerárquico (orden maestra §38). parent_id permite
# árbol arbitrario (TORRE NEXORA -> 01 PRELIMINARES -> 02 CIMENTACIÓN ->
# 02.01 EXCAVACIÓN ...). `level` se calcula al crear (0 = raíz).
WBS_STATUSES = ("PLANNING", "ACTIVE", "ON_HOLD", "COMPLETED", "CANCELLED")


class WBSNode(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "wbs_nodes"
    __table_args__ = (UniqueConstraint("project_id", "code", name="uq_wbs_nodes_project_code"),)

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("wbs_nodes.id", ondelete="CASCADE"), nullable=True
    )
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    level: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    manager: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PLANNING")
    planned_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    planned_finish: Mapped[date | None] = mapped_column(Date, nullable=True)
    actual_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    actual_finish: Mapped[date | None] = mapped_column(Date, nullable=True)
    progress_percent: Mapped[Numeric] = mapped_column(Numeric(5, 2), nullable=False, default=0)
