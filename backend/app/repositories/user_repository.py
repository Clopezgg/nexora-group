import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.permission import SCOPE_ANY, Permission, RolePermission, UserCompanyAccess
from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole


def get_by_email(db: Session, email: str) -> User | None:
    stmt = select(User).where(func.lower(User.email) == email.lower())
    return db.execute(stmt).scalar_one_or_none()


def get_by_id(db: Session, user_id: uuid.UUID) -> User | None:
    return db.get(User, user_id)


def count_users(db: Session) -> int:
    stmt = select(func.count()).select_from(User)
    return db.execute(stmt).scalar_one()


def create_user(db: Session, *, email: str, full_name: str, password_hash: str) -> User:
    user = User(email=email, full_name=full_name, password_hash=password_hash)
    db.add(user)
    db.flush()
    return user


def list_users_for_company(db: Session, *, company_id: uuid.UUID) -> list[User]:
    """DEFERRED-FINAL-015: directorio de usuarios "de una compañía" --
    incluye acceso explícito (`UserCompanyAccess`) y cualquier usuario
    company-agnóstico de verdad. `core.user`/`create` (Administrator-only,
    ver `_BASE_PERMISSIONS`) es la señal de "company-agnóstico", igual
    que en `assert_user_belongs_to_company` -- NO "cualquier resource/
    action en SCOPE_ANY": varios roles operativos (p.ej. Project Manager)
    tienen SCOPE_ANY solo en lecturas puntuales (dashboards
    cross-company) sin ser miembros reales de cada compañía, y Auditor
    tiene SCOPE_ANY en lecturas de todo el sistema pero ninguna acción de
    escritura/asignación real -- ninguno de los dos debe aparecer como
    "miembro" de una compañía a la que no tiene acceso explícito."""
    explicit_ids = select(UserCompanyAccess.user_id).where(UserCompanyAccess.company_id == company_id)
    company_agnostic_ids = (
        select(UserRole.user_id)
        .join(Role, UserRole.role_id == Role.id)
        .join(RolePermission, RolePermission.role_id == Role.id)
        .join(Permission, RolePermission.permission_id == Permission.id)
        .where(
            Permission.resource == "core.user",
            Permission.action == "create",
            RolePermission.company_scope == SCOPE_ANY,
        )
    )
    stmt = (
        select(User)
        .where(User.id.in_(explicit_ids) | User.id.in_(company_agnostic_ids))
        .order_by(User.full_name)
    )
    return list(db.execute(stmt).scalars().unique())
