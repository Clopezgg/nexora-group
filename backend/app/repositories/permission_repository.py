from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.permission import SCOPE_ANY, SCOPE_OWN, Permission, RolePermission
from app.models.role import Role

# Matriz de permisos inicial (docs/RBAC.md). Solo cubre los recursos que
# YA existen en este track (core/company, accounting) -- cada track de
# dominio agrega sus propias filas cuando construye su módulo, no se
# inventan permisos para recursos que todavía no existen.
_BASE_PERMISSIONS: tuple[tuple[str, str, str], ...] = (
    ("core.company", "create", "Crear compañías"),
    ("core.company", "read", "Ver compañías"),
    ("accounting.journal_entry", "create", "Crear asientos contables"),
    ("accounting.journal_entry", "read", "Ver asientos contables"),
    ("accounting.journal_entry", "reverse", "Revertir asientos contables"),
    ("accounting.account", "create", "Crear cuentas del catálogo contable"),
    ("accounting.account", "read", "Ver el catálogo contable"),
)
# NOTA: ActiveUIContext (GET/PUT /api/context) NO pasa por este motor de
# permisos -- es una preferencia personal del usuario autenticado (su
# proyecto activo en la UI), no un recurso protegido por rol. Solo requiere
# sesión válida, igual que antes de este track.

# (resource, action, company_scope). company_scope=OWN significa que el
# otorgamiento solo aplica a las companies que el usuario tiene en
# UserCompanyAccess (INV-COMP-001); ANY = sin restricción de company.
# Administrator/Auditor son ANY (necesitan ver/administrar todo). Los roles
# operativos (Finance Manager, Accountant) son OWN por defecto -- un
# Accountant normal no debe poder escribir en una company a la que no fue
# asignado explícitamente.
_ROLE_GRANTS: dict[str, tuple[tuple[str, str, str], ...]] = {
    "Administrator": tuple((resource, action, SCOPE_ANY) for resource, action, _ in _BASE_PERMISSIONS),
    "Finance Manager": (
        ("core.company", "read", SCOPE_ANY),
        ("accounting.journal_entry", "create", SCOPE_OWN),
        ("accounting.journal_entry", "read", SCOPE_OWN),
        ("accounting.journal_entry", "reverse", SCOPE_OWN),
        ("accounting.account", "create", SCOPE_OWN),
        ("accounting.account", "read", SCOPE_OWN),
    ),
    "Accountant": (
        ("core.company", "read", SCOPE_ANY),
        ("accounting.journal_entry", "create", SCOPE_OWN),
        ("accounting.journal_entry", "read", SCOPE_OWN),
        ("accounting.account", "read", SCOPE_OWN),
    ),
    "Auditor": (
        ("core.company", "read", SCOPE_ANY),
        ("accounting.journal_entry", "read", SCOPE_ANY),
        ("accounting.account", "read", SCOPE_ANY),
    ),
    "Viewer": (
        ("core.company", "read", SCOPE_ANY),
        ("accounting.journal_entry", "read", SCOPE_OWN),
        ("accounting.account", "read", SCOPE_OWN),
    ),
}


def ensure_base_permissions(db: Session) -> None:
    """Idempotente. Crea el catálogo de permisos y los otorgamientos por rol
    si aún no existen (y corrige company_scope si la matriz cambió)."""
    existing_permissions = {
        (permission.resource, permission.action): permission
        for permission in db.execute(select(Permission)).scalars()
    }
    for resource, action, description in _BASE_PERMISSIONS:
        if (resource, action) not in existing_permissions:
            permission = Permission(resource=resource, action=action, description=description)
            db.add(permission)
            db.flush()
            existing_permissions[(resource, action)] = permission

    roles_by_name = {role.name: role for role in db.execute(select(Role)).scalars()}
    existing_grants = {
        (grant.role_id, grant.permission_id): grant
        for grant in db.execute(select(RolePermission)).scalars()
    }

    for role_name, grants in _ROLE_GRANTS.items():
        role = roles_by_name.get(role_name)
        if role is None:
            continue
        for resource, action, company_scope in grants:
            permission = existing_permissions.get((resource, action))
            if permission is None:
                continue
            key = (role.id, permission.id)
            if key not in existing_grants:
                db.add(
                    RolePermission(
                        role_id=role.id, permission_id=permission.id, company_scope=company_scope
                    )
                )
            elif existing_grants[key].company_scope != company_scope:
                existing_grants[key].company_scope = company_scope

    db.flush()
