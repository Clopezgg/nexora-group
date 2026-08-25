import uuid
from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

# Quality: Inspection / Non-Conformance / Corrective Action (bloque
# CONSTRUCTION CONTROL, orden maestra §82-83, NXR-REQ-0082/0083). Igual que
# DailySiteReport (app/models/site_report.py), estos tres modelos son
# PROJECT-scoped de forma obligatoria -- una inspección de calidad siempre
# ocurre sobre una obra concreta. `evidence_id` sigue el contrato de adjunto
# único (docs/DOCUMENTS_EVIDENCE.md) -- una foto/evidencia por registro.
QUALITY_INSPECTION_RESULTS = ("PENDING", "PASS", "FAIL")
NON_CONFORMANCE_STATUSES = ("OPEN", "CLOSED")
CORRECTIVE_ACTION_STATUSES = ("OPEN", "COMPLETED")


class QualityInspection(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "quality_inspections"
    __table_args__ = (
        CheckConstraint(
            "result IN ('PENDING','PASS','FAIL')", name="ck_quality_inspections_result_valid"
        ),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    wbs_node_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("wbs_nodes.id", ondelete="SET NULL"), nullable=True
    )
    inspection_type: Mapped[str] = mapped_column(String(128), nullable=False)
    inspection_date: Mapped[date] = mapped_column(Date, nullable=False)
    inspector_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    result: Mapped[str] = mapped_column(String(16), nullable=False, default="PENDING")
    notes: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    evidence_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("evidence.id", ondelete="SET NULL"), nullable=True
    )


class NonConformance(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """INV-QUALITY-001 (quality_service.close_non_conformance): no se puede
    pasar a CLOSED sin al menos una CorrectiveAction registrada -- validado
    en el service layer (la relación 1:N no puede expresarse como CHECK
    constraint de una sola tabla en PostgreSQL)."""

    __tablename__ = "non_conformances"
    __table_args__ = (
        CheckConstraint("status IN ('OPEN','CLOSED')", name="ck_non_conformances_status_valid"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    quality_inspection_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("quality_inspections.id", ondelete="SET NULL"), nullable=True
    )
    description: Mapped[str] = mapped_column(String(2000), nullable=False)
    responsible_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="OPEN")
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    evidence_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("evidence.id", ondelete="SET NULL"), nullable=True
    )

    corrective_actions: Mapped[list["CorrectiveAction"]] = relationship(
        "CorrectiveAction", back_populates="non_conformance"
    )


class CorrectiveAction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "corrective_actions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('OPEN','COMPLETED')", name="ck_corrective_actions_status_valid"
        ),
    )

    non_conformance_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("non_conformances.id", ondelete="CASCADE"), nullable=False
    )
    description: Mapped[str] = mapped_column(String(2000), nullable=False)
    responsible_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="OPEN")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    evidence_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("evidence.id", ondelete="SET NULL"), nullable=True
    )

    non_conformance: Mapped["NonConformance"] = relationship(
        "NonConformance", back_populates="corrective_actions"
    )
