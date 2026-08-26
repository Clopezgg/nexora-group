import uuid

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class UserRole(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "user_roles"
    __table_args__ = (UniqueConstraint("user_id", "role_id", name="uq_user_roles_user_role"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="user_roles")
    role: Mapped["Role"] = relationship(back_populates="user_roles")
