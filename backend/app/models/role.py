from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

# Roles base de NEXORA GROUP (orden maestra §87 -- 14 roles). El motor de
# permisos central vive en app/models/permission.py + app/services/
# permission_service.py; estos roles son el catálogo, no la matriz de
# permisos (que cada track de dominio va completando incrementalmente,
# ver docs/RBAC.md).
ROLE_NAMES = (
    "Administrator",
    "Finance Manager",
    "Treasury Manager",
    "Accountant",
    "Project Manager",
    "Project Controller",
    "Procurement Manager",
    "Buyer",
    "Warehouse Manager",
    "Operations User",
    "Sales Manager",
    "Equipment Manager",
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
