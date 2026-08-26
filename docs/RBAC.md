# NEXORA GROUP — RBAC

## Roles (orden maestra §87)

`Administrator, Finance Manager, Treasury Manager, Accountant, Project
Manager, Project Controller, Procurement Manager, Buyer, Warehouse
Manager, Operations User, Sales Manager, Equipment Manager, Auditor,
Viewer` — catálogo en `app/models/role.py::ROLE_NAMES`, seedeado
idempotentemente por `role_repository.ensure_base_roles`.

## Motor de permisos

Backend autoritativo (`app/services/permission_service.py`). Modelo:

- `Permission(resource, action)` — catálogo de acciones posibles.
- `RolePermission(role_id, permission_id, company_scope, project_scope, conditions)`
  — qué rol puede hacer qué, y con qué alcance:
  - `company_scope=ANY`: el rol puede operar en cualquier company (p.ej.
    Administrator, Auditor).
  - `company_scope=OWN`: el rol solo puede operar en las companies donde
    el usuario tiene un `UserCompanyAccess` explícito (INV-COMP-001).
  - `project_scope` existe en el modelo con la misma semántica (`ANY` /
    `OWN` / `NONE`) pero **todavía no se aplica** en ningún endpoint de
    este track — ningún dominio construido hasta ahora necesita
    restricción a nivel de proyecto. El siguiente track que sí la
    necesite (p.ej. Project Control) debe seguir el mismo patrón que
    `assert_company_access` para `assert_project_access`.

Uso en un endpoint:

```python
from app.services.permission_service import assert_company_access, require_permission

@router.post("/mi-recurso")
def crear(
    payload: MiPayload,
    db: Session = Depends(get_db),
    user = Depends(require_permission("mi_modulo.mi_recurso", "create")),
):
    assert_company_access(
        db, user_id=user.id, resource="mi_modulo.mi_recurso", action="create",
        company_id=payload.company_id,
    )
    ...
```

`require_permission` responde 403 (`NXR-PERM-001`) si el rol del usuario
no tiene el permiso en absoluto. `assert_company_access` responde el mismo
403 si el rol lo tiene pero con `company_scope=OWN` y el usuario no tiene
acceso a esa company puntual.

## Matriz actual (solo recursos que existen hoy)

Ver `app/repositories/permission_repository.py::_BASE_PERMISSIONS` /
`_ROLE_GRANTS` — es la fuente de verdad ejecutable. Cada track de dominio
nuevo AGREGA sus propias filas a esa matriz cuando construye su módulo; no
se inventan permisos para recursos que todavía no existen (eso violaría
"no placeholders" del CLAUDE.md).

## UserCompanyAccess

`app/models/permission.py::UserCompanyAccess` — tabla simple
`(user_id, company_id)`. Todavía no tiene API de administración (crear/
revocar acceso vía HTTP); por ahora se otorga directo en base de datos.
Registrado como pendiente para el track que construya la pantalla de
administración de usuarios/RBAC (Track G).
