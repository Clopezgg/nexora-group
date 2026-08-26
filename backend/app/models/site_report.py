import uuid
from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

# Daily Site Report (bloque CONSTRUCTION CONTROL, orden maestra §81,
# NXR-REQ-0081). A diferencia de la mayoría de recursos de Track D
# (Equipment/FuelLog/TimeEntry: company_id directo + project_id OPCIONAL vía
# OperationScope GENERAL/PROJECT), un Daily Site Report es inherentemente
# PROJECT-scoped -- no existe un "reporte diario" sin una obra concreta.
# `project_id` es NOT NULL a nivel de dominio Y de constraint real de
# PostgreSQL (mismo criterio que WBSNode/ChangeOrder/ProgressRecord); no hay
# columna `company_id` propia -- la compañía se deriva de `project.company_id`
# (mismo patrón que esos tres modelos).
DAILY_SITE_REPORT_STATUSES = ("DRAFT", "SUBMITTED", "APPROVED", "REJECTED")


class DailySiteReport(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "daily_site_reports"
    __table_args__ = (
        CheckConstraint(
            "status IN ('DRAFT','SUBMITTED','APPROVED','REJECTED')",
            name="ck_daily_site_reports_status_valid",
        ),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    report_date: Mapped[date] = mapped_column(Date, nullable=False)
    weather: Mapped[str | None] = mapped_column(String(64), nullable=True)
    workforce_summary: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    activities_performed: Mapped[str] = mapped_column(String(4000), nullable=False)
    equipment_used: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    materials_used: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    incidents: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    observations: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    author_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="DRAFT")
    approved_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    photos: Mapped[list["DailySiteReportPhoto"]] = relationship(
        "DailySiteReportPhoto", back_populates="daily_site_report", order_by="DailySiteReportPhoto.created_at"
    )


class DailySiteReportPhoto(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Adjuntos múltiples (docs/DOCUMENTS_EVIDENCE.md, "Adjuntos múltiples --
    tabla de unión"): un Daily Site Report puede tener varias fotos, así que
    no se agrega una sola columna `evidence_id` -- se usa esta tabla de
    unión (mismo patrón que `RfqSupplier`)."""

    __tablename__ = "daily_site_report_photos"

    daily_site_report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("daily_site_reports.id", ondelete="CASCADE"), nullable=False
    )
    evidence_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("evidence.id", ondelete="RESTRICT"), nullable=False
    )

    daily_site_report: Mapped["DailySiteReport"] = relationship(
        "DailySiteReport", back_populates="photos"
    )
