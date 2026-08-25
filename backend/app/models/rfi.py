import uuid
from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

# Request For Information (bloque CONSTRUCTION CONTROL, orden maestra §80,
# NXR-REQ-0085). `number` se genera vía el servicio de numeración
# concurrency-safe ya existente (app/services/numbering_service.py,
# document_type_code="RFI") -- nunca se inventa una segunda estrategia de
# numeración. El unique constraint es (company_id, number), NO solo
# `number`: dos compañías distintas pueden emitir cada una su propio
# "RFI-2026-000001" el mismo año sin colisionar (numeración
# company-scoped, ver docs/DOCUMENTS_EVIDENCE.md y CLAUDE.md INV-COMP-*).
RFI_STATUSES = ("OPEN", "ANSWERED", "CLOSED")


class RequestForInformation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "requests_for_information"
    __table_args__ = (
        CheckConstraint("status IN ('OPEN','ANSWERED','CLOSED')", name="ck_rfi_status_valid"),
        UniqueConstraint("company_id", "number", name="uq_rfi_company_number"),
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
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    question: Mapped[str] = mapped_column(String(4000), nullable=False)
    response: Mapped[str | None] = mapped_column(String(4000), nullable=True)
    responsible: Mapped[str | None] = mapped_column(String(255), nullable=True)
    requested_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    responded_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="OPEN")
