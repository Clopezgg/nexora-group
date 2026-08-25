import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

# Workforce / Time (orden maestra §65-66). `labor_cost` NUNCA se acepta del
# cliente: siempre se calcula en workforce_service como
# hourly_rate * approved_hours en el momento de aprobación (INV-WFC-001) --
# nunca un número hardcodeado. `project_id`/`scope` reusan el mismo patrón de
# atribución que AP/Assets (CLAUDE.md §1/§7): el trabajador cobra vía
# Treasury/nómina (fuera de alcance de este track), el Project solo recibe la
# atribución de costo, nunca custodia el dinero.
TIME_ENTRY_STATUSES = ("SUBMITTED", "APPROVED", "REJECTED")


class Worker(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "workers"
    __table_args__ = (
        CheckConstraint("standard_hourly_rate > 0", name="ck_workers_standard_rate_positive"),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role_title: Mapped[str | None] = mapped_column(String(128), nullable=True)
    standard_hourly_rate: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    active: Mapped[bool] = mapped_column(nullable=False, default=True)


class TimeEntry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "time_entries"
    __table_args__ = (
        CheckConstraint("hours_worked > 0", name="ck_time_entries_hours_worked_positive"),
        CheckConstraint("hourly_rate > 0", name="ck_time_entries_hourly_rate_positive"),
        CheckConstraint(
            "approved_hours IS NULL OR approved_hours >= 0",
            name="ck_time_entries_approved_hours_non_negative",
        ),
        CheckConstraint(
            "labor_cost IS NULL OR labor_cost >= 0", name="ck_time_entries_labor_cost_non_negative"
        ),
        CheckConstraint(
            "status IN ('SUBMITTED','APPROVED','REJECTED')", name="ck_time_entries_status_valid"
        ),
        CheckConstraint(
            "(scope IN ('CENTRAL','GENERAL') AND project_id IS NULL) "
            "OR (scope = 'PROJECT' AND project_id IS NOT NULL)",
            name="ck_time_entries_operation_scope",
        ),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    worker_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workers.id", ondelete="RESTRICT"), nullable=False
    )
    scope: Mapped[str] = mapped_column(String(16), nullable=False, default="GENERAL")
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="RESTRICT"), nullable=True
    )
    work_date: Mapped[date] = mapped_column(Date, nullable=False)
    hours_worked: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    hourly_rate: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="SUBMITTED")
    approved_hours: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    labor_cost: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    approved_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Crew(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """NXR-REQ-0074. Grupo nombrado de `Worker` opcionalmente asignado a un
    proyecto -- mismo patrón que `Warehouse.project_id` (nullable, sin el
    motor de OperationScope, que es exclusivo de documentos financieros/
    administrativos, CLAUDE.md §7). Sin alcance de scheduling/rotación de
    miembros por fecha -- membresía simple (`CrewMember`), mismo criterio
    minimalista que `Worker` ya usa ("cubre lo mínimo que TimeEntry
    necesita, no un módulo de RRHH completo")."""

    __tablename__ = "crews"
    __table_args__ = (UniqueConstraint("company_id", "name", name="uq_crews_company_name"),)

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="RESTRICT"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ACTIVE")


class CrewMember(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "crew_members"
    __table_args__ = (UniqueConstraint("crew_id", "worker_id", name="uq_crew_members_crew_worker"),)

    crew_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("crews.id", ondelete="CASCADE"), nullable=False
    )
    worker_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workers.id", ondelete="RESTRICT"), nullable=False
    )
