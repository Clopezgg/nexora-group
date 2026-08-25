import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

"""Approval Inbox (Track G / Platform, NXR-REQ-0088). Entidad genérica que
cualquier dominio usa para pedir una decisión humana sin ceder su propia
lógica de transición: `app.services.approval_service.decide()` nunca muta
el estado del dominio directamente, llama de vuelta al adaptador
registrado por ese módulo (ver `register_decision_adapter`). Ver Ruling en
docs/superpowers/specs/2026-08-25-track-g-workflow-audit-design.md --
esto NO es un motor de workflow genérico que reemplace las transiciones ya
probadas de cada dominio."""


class ApprovalRequest(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "approval_requests"

    policy_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("approval_policies.id", ondelete="SET NULL"), nullable=True
    )
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True
    )
    module: Mapped[str] = mapped_column(String(50), nullable=False)
    requested_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    assigned_role: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    priority: Mapped[str] = mapped_column(String(10), nullable=False, default="NORMAL")
    amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    comment: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    decided_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
