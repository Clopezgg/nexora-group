import uuid
from collections.abc import Callable

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.domain.errors import NotAuthorizedError
from app.models.permission import SCOPE_ANY, Permission, RolePermission, UserCompanyAccess
from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole

"""Motor de permisos central (orden maestra §87, docs/RBAC.md). Backend
autoritativo: el frontend puede ocultar botones por UX, pero la decisión
real siempre pasa por aquí. resource + action + company_scope +
project_scope + conditions."""


def user_has_permission(
    db: Session, *, user_id: uuid.UUID, resource: str, action: str
) -> bool:
    stmt = (
        select(RolePermission)
        .join(Permission, RolePermission.permission_id == Permission.id)
        .join(Role, RolePermission.role_id == Role.id)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(
            UserRole.user_id == user_id,
            Permission.resource == resource,
            Permission.action == action,
        )
    )
    return db.execute(stmt).first() is not None


def user_has_company_access(db: Session, *, user_id: uuid.UUID, company_id: uuid.UUID) -> bool:
    stmt = select(UserCompanyAccess).where(
        UserCompanyAccess.user_id == user_id, UserCompanyAccess.company_id == company_id
    )
    return db.execute(stmt).first() is not None


def _has_any_scope_grant(db: Session, *, user_id: uuid.UUID, resource: str, action: str) -> bool:
    """True si AL MENOS UNO de los roles del usuario otorga este
    resource/action con company_scope=ANY (p.ej. Administrator, Auditor)."""
    stmt = (
        select(RolePermission)
        .join(Permission, RolePermission.permission_id == Permission.id)
        .join(Role, RolePermission.role_id == Role.id)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(
            UserRole.user_id == user_id,
            Permission.resource == resource,
            Permission.action == action,
            RolePermission.company_scope == SCOPE_ANY,
        )
    )
    return db.execute(stmt).first() is not None


def assert_company_access(
    db: Session, *, user_id: uuid.UUID, resource: str, action: str, company_id: uuid.UUID
) -> None:
    """INV-COMP-001: aislamiento de company. Si el usuario tiene, para este
    resource/action, al menos un rol con company_scope=ANY, pasa sin más
    (Administrator/Auditor). Si no, se exige acceso explícito vía
    UserCompanyAccess a esa company puntual."""
    if _has_any_scope_grant(db, user_id=user_id, resource=resource, action=action):
        return
    if user_has_company_access(db, user_id=user_id, company_id=company_id):
        return
    raise NotAuthorizedError(
        f"El usuario no tiene acceso a la company {company_id} para {action} sobre {resource}"
    )


def require_permission(resource: str, action: str) -> Callable:
    """Factory de dependencia FastAPI: `Depends(require_permission("accounting.journal_entry", "create"))`."""

    def _dependency(
        db: Session = Depends(get_db),
        current: tuple[User, list[str]] = Depends(get_current_user),
    ) -> User:
        user, _roles = current
        if not user_has_permission(db, user_id=user.id, resource=resource, action=action):
            raise NotAuthorizedError(f"No tiene permiso para {action} sobre {resource}")
        return user

    return _dependency
