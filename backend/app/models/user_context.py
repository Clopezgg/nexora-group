import uuid

from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin

# ActiveUIContext persistido: proyecto activo elegido por el usuario en la UI.
# Independiente de OperationScope (dominio/backend). Ver CLAUDE.md.


class UserContext(TimestampMixin, Base):
    __tablename__ = "user_context"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    active_project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True
    )
