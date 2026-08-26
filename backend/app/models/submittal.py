import uuid
from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

# Submittal (bloque CONSTRUCTION CONTROL, orden maestra §80, NXR-REQ-0086).
# `number` vía NumberSequence (document_type_code="SUB"), mismo patrón que
# RequestForInformation. `supplier_id`/`contract_id` son referencias
# OPCIONALES a Track C (Supplier/SupplierContract) -- un Submittal puede no
# tener proveedor asociado (p.ej. un submittal de diseño interno).
#
# Flujo de revisión de dos pasos (INV real, ver test_submittals.py): primero
# se registra la respuesta del revisor (`reviewer_response`, `reviewed_by`,
# `response_recorded_at`), y solo después se puede decidir (`decide_submittal`
# en app/services/submittal_service.py) -- aprobar/rechazar sin una respuesta
# ya registrada se rechaza con InvalidSubmittalStateError. `evidence_id` es
# el adjunto único (contrato de adjunto de docs/DOCUMENTS_EVIDENCE.md).
SUBMITTAL_STATUSES = ("SUBMITTED", "UNDER_REVIEW", "APPROVED", "REJECTED")


class Submittal(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "submittals"
    __table_args__ = (
        CheckConstraint(
            "status IN ('SUBMITTED','UNDER_REVIEW','APPROVED','REJECTED')",
            name="ck_submittal_status_valid",
        ),
        CheckConstraint("revision > 0", name="ck_submittal_revision_positive"),
        UniqueConstraint("company_id", "number", name="uq_submittal_company_number"),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="RESTRICT"), nullable=False
    )
    wbs_node_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("wbs_nodes.id", ondelete="SET NULL"), nullable=True
    )
    number: Mapped[str] = mapped_column(String(32), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    supplier_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True
    )
    contract_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("supplier_contracts.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="SUBMITTED")
    submitted_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    submitted_at: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    reviewer_response: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    response_recorded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    decided_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    evidence_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("evidence.id", ondelete="SET NULL"), nullable=True
    )
