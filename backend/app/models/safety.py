import uuid
from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

# Safety: Observation / Incident (bloque CONSTRUCTION CONTROL, orden maestra
# §84, NXR-REQ-0084). PROJECT-scoped obligatorio, mismo criterio que
# site_report.py/quality.py. `severity` determina qué campos son
# obligatorios (INV-SAFETY-001): un registro HIGH/CRITICAL SIEMPRE necesita
# `responsible_user_id`, un LOW/MEDIUM no lo requiere -- este invariante se
# aplica en el service (severity/responsible_user_id llegan juntos en el
# mismo payload y su combinación se valida antes de persistir) Y como CHECK
# constraint real de PostgreSQL (defensa en profundidad, mismo criterio que
# `ck_fuel_logs_operation_scope`).
SAFETY_SEVERITIES = ("LOW", "MEDIUM", "HIGH", "CRITICAL")
SAFETY_SEVERITIES_REQUIRING_RESPONSIBLE = ("HIGH", "CRITICAL")
SAFETY_RECORD_STATUSES = ("OPEN", "CLOSED")

_SEVERITY_CHECK_SQL = "severity IN ('LOW','MEDIUM','HIGH','CRITICAL')"
_STATUS_CHECK_SQL = "status IN ('OPEN','CLOSED')"
_HIGH_SEVERITY_REQUIRES_RESPONSIBLE_SQL = (
    "severity NOT IN ('HIGH','CRITICAL') OR responsible_user_id IS NOT NULL"
)


class SafetyObservation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "safety_observations"
    __table_args__ = (
        CheckConstraint(_SEVERITY_CHECK_SQL, name="ck_safety_observations_severity_valid"),
        CheckConstraint(_STATUS_CHECK_SQL, name="ck_safety_observations_status_valid"),
        CheckConstraint(
            _HIGH_SEVERITY_REQUIRES_RESPONSIBLE_SQL,
            name="ck_safety_observations_high_severity_requires_responsible",
        ),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    observation_date: Mapped[date] = mapped_column(Date, nullable=False)
    category: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(String(2000), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, default="LOW")
    responsible_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    corrective_action: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="OPEN")
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    evidence_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("evidence.id", ondelete="SET NULL"), nullable=True
    )


class SafetyIncident(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "safety_incidents"
    __table_args__ = (
        CheckConstraint(_SEVERITY_CHECK_SQL, name="ck_safety_incidents_severity_valid"),
        CheckConstraint(_STATUS_CHECK_SQL, name="ck_safety_incidents_status_valid"),
        CheckConstraint(
            _HIGH_SEVERITY_REQUIRES_RESPONSIBLE_SQL,
            name="ck_safety_incidents_high_severity_requires_responsible",
        ),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    incident_date: Mapped[date] = mapped_column(Date, nullable=False)
    description: Mapped[str] = mapped_column(String(2000), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    responsible_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    corrective_action: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="OPEN")
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    evidence_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("evidence.id", ondelete="SET NULL"), nullable=True
    )
