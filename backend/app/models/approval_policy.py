import uuid

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

# Track G (Platform) ya construyó el motor de Approval Inbox
# (ApprovalRequest, app/services/approval_service.py) sobre este esqueleto
# reservado por Foundation. `entity_type` liga una política a un dominio
# concreto (p.ej. "ap.supplier_invoice"); `requires_third_role` activa la
# verificación de un tercer ejecutor distinto de solicitante/aprobador en
# `approval_service.decide()` (Segregación de Funciones, NXR-REQ-0089). No
# existe todavía un WorkflowDefinition/WorkflowStep genérico -- ver Ruling
# de docs/superpowers/specs/2026-08-25-track-g-workflow-audit-design.md
# (Track G deliberadamente NO construye un motor de estados genérico).


class ApprovalPolicy(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "approval_policies"

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    entity_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    requires_third_role: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
