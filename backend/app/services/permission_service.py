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

"""Motor de permisos central. Backend autoritativo: el frontend puede ocultar
navegación/acciones por UX, pero la decisión real siempre pasa por aquí."""


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


def list_user_permissions(db: Session, *, user_id: uuid.UUID) -> list[str]:
    """Return deduplicated effective resource/action grants for UX filtering.

    This does not encode company/project authorization and must never be used as
    an authorization decision by the client. Route dependencies remain final.
    """
    stmt = (
        select(Permission.resource, Permission.action)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(Role, RolePermission.role_id == Role.id)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user_id)
        .distinct()
        .order_by(Permission.resource, Permission.action)
    )
    return [f"{resource}:{action}" for resource, action in db.execute(stmt).all()]


def user_has_company_access(db: Session, *, user_id: uuid.UUID, company_id: uuid.UUID) -> bool:
    stmt = select(UserCompanyAccess).where(
        UserCompanyAccess.user_id == user_id, UserCompanyAccess.company_id == company_id
    )
    return db.execute(stmt).first() is not None


def _has_any_scope_grant(db: Session, *, user_id: uuid.UUID, resource: str, action: str) -> bool:
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


def user_has_any_company_scope(db: Session, *, user_id: uuid.UUID, resource: str, action: str) -> bool:
    return _has_any_scope_grant(db, user_id=user_id, resource=resource, action=action)


def list_user_company_ids(db: Session, *, user_id: uuid.UUID) -> list[uuid.UUID]:
    stmt = select(UserCompanyAccess.company_id).where(UserCompanyAccess.user_id == user_id)
    return list(db.execute(stmt).scalars())


def assert_company_access(
    db: Session, *, user_id: uuid.UUID, resource: str, action: str, company_id: uuid.UUID
) -> None:
    if _has_any_scope_grant(db, user_id=user_id, resource=resource, action=action):
        return
    if user_has_company_access(db, user_id=user_id, company_id=company_id):
        return
    raise NotAuthorizedError(
        f"El usuario no tiene acceso a la company {company_id} para {action} sobre {resource}"
    )


def require_permission(resource: str, action: str) -> Callable:
    def _dependency(
        db: Session = Depends(get_db),
        current: tuple[User, list[str]] = Depends(get_current_user),
    ) -> User:
        user, _roles = current
        if not user_has_permission(db, user_id=user.id, resource=resource, action=action):
            raise NotAuthorizedError(f"No tiene permiso para {action} sobre {resource}")
        return user

    return _dependency
