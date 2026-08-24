from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

# Roles base de NEXORA GROUP. Ver CLAUDE.md, sección 9 (RBAC base).
ROLE_NAMES = (
    "Administrator",
    "Treasury Manager",
    "Finance Manager",
    "Project Manager",
    "Operations User",
    "Auditor",
    "Viewer",
)


class Role(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    user_roles: Mapped[list["UserRole"]] = relationship(
        back_populates="role", cascade="all, delete-orphan"
    )
