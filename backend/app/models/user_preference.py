import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin


class UserPreference(TimestampMixin, Base):
    """Preferencias de UI por usuario (orden maestra FINAL, Phase 8). SOLO
    presentación -- tema y densidad. Nunca moneda/cálculo/permiso/estado."""

    __tablename__ = "user_preferences"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    theme_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    density: Mapped[str | None] = mapped_column(String(16), nullable=True)
