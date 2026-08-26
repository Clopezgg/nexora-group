import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

# Planificación funcional (orden maestra §39): Task/Milestone con
# dependencias, owners, planned/actual. No es un motor Gantt completo -- es
# lo suficiente para una vista de planeación usable.
TASK_STATUSES = ("PLANNED", "IN_PROGRESS", "DONE", "BLOCKED", "CANCELLED")
MILESTONE_STATUSES = ("PLANNED", "ACHIEVED", "MISSED", "CANCELLED")


class Task(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "tasks"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    wbs_node_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("wbs_nodes.id", ondelete="SET NULL"), nullable=True
    )
    depends_on_task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    owner: Mapped[str | None] = mapped_column(String(255), nullable=True)
    planned_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    planned_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    actual_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    actual_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PLANNED")


class Milestone(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "milestones"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    wbs_node_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("wbs_nodes.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    achieved_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PLANNED")
