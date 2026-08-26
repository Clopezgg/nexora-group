import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.role import ROLE_NAMES, Role
from app.models.user_role import UserRole


def get_by_name(db: Session, name: str) -> Role | None:
    stmt = select(Role).where(Role.name == name)
    return db.execute(stmt).scalar_one_or_none()


def ensure_base_roles(db: Session) -> None:
    """Idempotente: crea los roles base si aún no existen."""
    existing = {role.name for role in db.execute(select(Role)).scalars()}
    for name in ROLE_NAMES:
        if name not in existing:
            db.add(Role(name=name))
    db.flush()


def assign_role(db: Session, *, user_id: uuid.UUID, role_id: uuid.UUID) -> UserRole:
    user_role = UserRole(user_id=user_id, role_id=role_id)
    db.add(user_role)
    db.flush()
    return user_role


def get_role_names_for_user(db: Session, user_id: uuid.UUID) -> list[str]:
    stmt = select(Role.name).join(UserRole, UserRole.role_id == Role.id).where(
        UserRole.user_id == user_id
    )
    return list(db.execute(stmt).scalars())
