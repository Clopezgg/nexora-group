import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.company import Company

# Un Project nunca posee efectivo: solo referencia presupuesto/estado (INV-
# TRE-002, ver CLAUDE.md §7 y docs/PROJECTS_WBS.md). Deliberadamente esta
# tabla NO tiene ninguna columna de saldo/balance/cash -- ver
# tests/test_project_control.py::test_project_has_no_money_column.
PROJECT_STATUSES = (
    "PLANNING",
    "ACTIVE",
    "ON_HOLD",
    "COMPLETED",
    "CLOSED",
    "CANCELLED",
    # ARCHIVED = soft-delete empresarial (§1). El proyecto y todo su historial
    # (contratos, pagos, GL, Evidence, Audit) permanecen; solo se oculta de la
    # operación diaria y es restaurable.
    "ARCHIVED",
)


class Project(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "projects"

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="SET NULL"), nullable=True
    )
    customer_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # `manager` (texto libre) se conserva por compatibilidad; `manager_user_id`
    # es el responsable real como FK a users (orden maestra final §16).
    manager: Mapped[str | None] = mapped_column(String(255), nullable=True)
    manager_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    currency_code: Mapped[str | None] = mapped_column(
        String(3), ForeignKey("currencies.code"), nullable=True
    )
    cost_center_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cost_centers.id", ondelete="SET NULL"), nullable=True
    )
    planned_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    planned_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    actual_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PLANNING")
    # Marcas de ciclo de vida (§8). Nunca se borran en un reopen: son historia.
    completed_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    closed_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    reopened_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    archived_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    # Estado previo al archivado, para restaurar exactamente a donde estaba.
    status_before_archive: Mapped[str | None] = mapped_column(String(32), nullable=True)
    description: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    # Localización documental de la obra (orden maestra final §31).
    address_line_1: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address_line_2: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    state_department: Mapped[str | None] = mapped_column(String(120), nullable=True)
    country: Mapped[str | None] = mapped_column(String(2), nullable=True)
    location_reference: Mapped[str | None] = mapped_column(String(500), nullable=True)

    company: Mapped["Company"] = relationship(back_populates="projects")
