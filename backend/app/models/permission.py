import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

# Motor de permisos central (ver docs/RBAC.md). company_scope/project_scope
# determinan si el permiso aplica a CUALQUIER company/project o solo a
# los que el usuario tiene asignados explícitamente vía UserCompanyAccess
# (ver permission_service.py). "conditions" es un JSONB abierto para reglas
# adicionales que un módulo de dominio pueda necesitar (p.ej. límites de
# monto) sin tener que alterar el esquema del motor.
SCOPE_ANY = "ANY"
SCOPE_OWN = "OWN"
SCOPE_NONE = "NONE"
COMPANY_SCOPES = (SCOPE_ANY, SCOPE_OWN)
PROJECT_SCOPES = (SCOPE_ANY, SCOPE_OWN, SCOPE_NONE)


class Permission(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "permissions"
    __table_args__ = (UniqueConstraint("resource", "action", name="uq_permissions_resource_action"),)

    resource: Mapped[str] = mapped_column(String(128), nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)


class RolePermission(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "role_permissions"
    __table_args__ = (
        UniqueConstraint("role_id", "permission_id", name="uq_role_permissions_role_permission"),
    )

    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), nullable=False
    )
    permission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False
    )
    company_scope: Mapped[str] = mapped_column(String(8), nullable=False, default=SCOPE_ANY)
    project_scope: Mapped[str] = mapped_column(String(8), nullable=False, default=SCOPE_ANY)
    conditions: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class UserCompanyAccess(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Compañías a las que un usuario tiene acceso explícito. Usado por
    company_scope=OWN y por el aislamiento de company (INV-COMP-001)."""

    __tablename__ = "user_company_access"
    __table_args__ = (
        UniqueConstraint("user_id", "company_id", name="uq_user_company_access_user_company"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
