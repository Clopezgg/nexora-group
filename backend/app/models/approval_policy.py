import uuid

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

# Esqueleto de entidad únicamente. El motor de workflow completo
# (WorkflowDefinition/WorkflowVersion/WorkflowStep/WorkflowInstance) es
# responsabilidad del Track G (Platform) y se construye después. Esta tabla
# solo reserva dónde va a vivir la política para que otros tracks puedan
# referenciarla por FK desde ya sin bloquear su propio avance.


class ApprovalPolicy(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "approval_policies"

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
