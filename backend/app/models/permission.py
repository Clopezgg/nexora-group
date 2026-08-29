import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

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
    """Compañías asignadas explícitamente cuando company_scope=OWN."""

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


class UserProjectAccess(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Proyectos asignados explícitamente cuando project_scope=OWN.

    La pertenencia de cada proyecto a una compañía sigue siendo autoridad del
    modelo Project; esta tabla nunca reemplaza el aislamiento por compañía.
    """

    __tablename__ = "user_project_access"
    __table_args__ = (
        UniqueConstraint("user_id", "project_id", name="uq_user_project_access_user_project"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )