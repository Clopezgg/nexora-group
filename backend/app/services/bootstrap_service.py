import logging

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.repositories import role_repository, user_repository
from app.security.passwords import hash_password

logger = logging.getLogger(__name__)


def bootstrap_admin_if_needed(db: Session) -> None:
    """Crea el usuario Administrator inicial una sola vez, si no existen usuarios
    y las variables BOOTSTRAP_ADMIN_EMAIL / BOOTSTRAP_ADMIN_PASSWORD están definidas."""
    settings = get_settings()
    role_repository.ensure_base_roles(db)

    if user_repository.count_users(db) > 0:
        return

    if not settings.bootstrap_admin_email or not settings.bootstrap_admin_password:
        logger.info(
            "No hay usuarios y no se definieron BOOTSTRAP_ADMIN_EMAIL/BOOTSTRAP_ADMIN_PASSWORD; "
            "se omite el bootstrap de administrador."
        )
        return

    admin_role = role_repository.get_by_name(db, "Administrator")
    if admin_role is None:
        raise RuntimeError("El rol Administrator no existe; ejecuta las migraciones primero.")

    user = user_repository.create_user(
        db,
        email=settings.bootstrap_admin_email,
        full_name="Administrador Nexora",
        password_hash=hash_password(settings.bootstrap_admin_password),
    )
    role_repository.assign_role(db, user_id=user.id, role_id=admin_role.id)
    db.commit()
    logger.info("Usuario Administrator inicial creado: %s", settings.bootstrap_admin_email)
