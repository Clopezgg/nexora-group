import uuid

from sqlalchemy.orm import Session

from app.domain.errors import RoleNotFoundError, UserEmailExistsError
from app.models.user import User
from app.repositories import permission_repository, role_repository, user_repository
from app.security.passwords import hash_password

"""DEFERRED-FINAL-015: hasta esta pieza no existía ninguna forma real de
crear un usuario más allá del bootstrap Administrator inicial
(`bootstrap_service.py`, una sola vez, por variables de entorno) --
confirmado por el Critical Journey E2E, que tuvo que crear un segundo
usuario llamando directamente a las funciones de repositorio (mismo
patrón que `tests/helpers.py::create_user_with_role`) porque no existía
ningún endpoint real. `create_user_with_role` es ahora ese endpoint real:
mismo código, ahora alcanzable desde la API, no solo desde tests."""


def create_user_with_role(
    db: Session,
    *,
    company_id: uuid.UUID,
    email: str,
    full_name: str,
    password: str,
    role_name: str,
) -> User:
    if user_repository.get_by_email(db, email) is not None:
        raise UserEmailExistsError(f"Ya existe un usuario con email {email!r}")
    role = role_repository.get_by_name(db, role_name)
    if role is None:
        raise RoleNotFoundError(f"role_name inválido: {role_name!r}")
    user = user_repository.create_user(
        db, email=email, full_name=full_name, password_hash=hash_password(password)
    )
    role_repository.assign_role(db, user_id=user.id, role_id=role.id)
    permission_repository.grant_company_access(db, user_id=user.id, company_id=company_id)
    db.commit()
    db.refresh(user)
    return user


def list_company_users(db: Session, *, company_id: uuid.UUID) -> list[User]:
    return user_repository.list_users_for_company(db, company_id=company_id)
