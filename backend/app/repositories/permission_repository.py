from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.permission import SCOPE_ANY, SCOPE_OWN, Permission, RolePermission
from app.models.role import Role

# Matriz de permisos (docs/RBAC.md). Cubre los recursos que YA existen:
# core/company, accounting (Track 1) y project/project.wbs/project.planning/
# project.budget/project.change_order/project.progress (Track B), más
# procurement/inventory (Track C). No se inventan permisos para recursos que
# todavía no existen.
_BASE_PERMISSIONS: tuple[tuple[str, str, str], ...] = (
    ("core.company", "create", "Crear compañías"),
    ("core.company", "read", "Ver compañías"),
    ("accounting.journal_entry", "create", "Crear asientos contables"),
    ("accounting.journal_entry", "read", "Ver asientos contables"),
    ("accounting.journal_entry", "reverse", "Revertir asientos contables"),
    ("accounting.account", "create", "Crear cuentas del catálogo contable"),
    ("accounting.account", "read", "Ver el catálogo contable"),
    # Track B -- Project Control (orden maestra §37-43, §72).
    ("project", "create", "Crear proyectos"),
    ("project", "read", "Ver proyectos"),
    ("project.wbs", "create", "Crear nodos de WBS"),
    ("project.wbs", "read", "Ver WBS"),
    ("project.planning", "create", "Crear tareas/hitos de planeación"),
    ("project.planning", "read", "Ver planeación del proyecto"),
    ("project.budget", "create", "Crear/aprobar presupuesto de proyecto"),
    ("project.budget", "read", "Ver presupuesto y forecast del proyecto"),
    ("project.change_order", "create", "Crear órdenes de cambio"),
    ("project.change_order", "read", "Ver órdenes de cambio"),
    ("project.change_order", "submit", "Enviar orden de cambio a aprobación"),
    ("project.change_order", "approve", "Aprobar orden de cambio"),
    ("project.progress", "create", "Registrar avance de proyecto"),
    ("project.progress", "read", "Ver avance de proyecto"),
    # Track C -- Supply Chain (orden maestra §44-60).
    ("procurement.supplier", "create", "Crear proveedores"),
    ("procurement.supplier", "read", "Ver proveedores"),
    ("procurement.contract", "create", "Crear contratos/subcontratos"),
    ("procurement.contract", "read", "Ver contratos/subcontratos"),
    ("procurement.requisition", "create", "Crear solicitudes de compra"),
    ("procurement.requisition", "read", "Ver solicitudes de compra"),
    ("procurement.requisition", "approve", "Aprobar solicitudes de compra"),
    ("procurement.rfq", "create", "Crear RFQ"),
    ("procurement.rfq", "read", "Ver RFQ"),
    ("procurement.quotation", "create", "Registrar cotizaciones de proveedor"),
    ("procurement.quotation", "read", "Ver cotizaciones de proveedor"),
    ("procurement.quotation", "select", "Seleccionar cotización ganadora"),
    ("procurement.purchase_order", "create", "Crear órdenes de compra"),
    ("procurement.purchase_order", "read", "Ver órdenes de compra"),
    ("procurement.purchase_order", "approve", "Aprobar órdenes de compra"),
    ("procurement.goods_receipt", "create", "Registrar recepciones de mercadería"),
    ("procurement.goods_receipt", "read", "Ver recepciones de mercadería"),
    ("procurement.service_entry", "create", "Registrar entradas de servicio"),
    ("procurement.service_entry", "read", "Ver entradas de servicio"),
    ("procurement.three_way_match", "create", "Ejecutar three-way match"),
    ("procurement.three_way_match", "read", "Ver resultados de three-way match"),
    ("inventory.item", "create", "Crear ítems de inventario"),
    ("inventory.item", "read", "Ver ítems de inventario"),
    ("inventory.warehouse", "create", "Crear almacenes"),
    ("inventory.warehouse", "read", "Ver almacenes"),
    ("inventory.stock", "read", "Ver stock y movimientos"),
    ("inventory.stock", "move", "Registrar movimientos de stock"),
    ("inventory.physical_count", "create", "Crear conteos físicos"),
    ("inventory.physical_count", "approve", "Aprobar conteos físicos"),
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
        ("core.company", "read", SCOPE_OWN),
        ("accounting.journal_entry", "create", SCOPE_OWN),
        ("accounting.journal_entry", "read", SCOPE_OWN),
        ("accounting.journal_entry", "reverse", SCOPE_OWN),
        ("accounting.account", "create", SCOPE_OWN),
        ("accounting.account", "read", SCOPE_OWN),
    ),
    "Accountant": (
        ("core.company", "read", SCOPE_OWN),
        ("accounting.journal_entry", "create", SCOPE_OWN),
        ("accounting.journal_entry", "read", SCOPE_OWN),
        ("accounting.account", "read", SCOPE_OWN),
    ),
    "Auditor": (
        ("core.company", "read", SCOPE_ANY),
        ("accounting.journal_entry", "read", SCOPE_ANY),
        ("accounting.account", "read", SCOPE_ANY),
        ("project", "read", SCOPE_ANY),
        ("project.wbs", "read", SCOPE_ANY),
        ("project.planning", "read", SCOPE_ANY),
        ("project.budget", "read", SCOPE_ANY),
        ("project.change_order", "read", SCOPE_ANY),
        ("project.progress", "read", SCOPE_ANY),
        ("procurement.supplier", "read", SCOPE_ANY),
        ("procurement.contract", "read", SCOPE_ANY),
        ("procurement.requisition", "read", SCOPE_ANY),
        ("procurement.rfq", "read", SCOPE_ANY),
        ("procurement.quotation", "read", SCOPE_ANY),
        ("procurement.purchase_order", "read", SCOPE_ANY),
        ("procurement.goods_receipt", "read", SCOPE_ANY),
        ("procurement.service_entry", "read", SCOPE_ANY),
        ("procurement.three_way_match", "read", SCOPE_ANY),
        ("inventory.item", "read", SCOPE_ANY),
        ("inventory.warehouse", "read", SCOPE_ANY),
        ("inventory.stock", "read", SCOPE_ANY),
    ),
    "Viewer": (
        ("core.company", "read", SCOPE_OWN),
        ("accounting.journal_entry", "read", SCOPE_OWN),
        ("accounting.account", "read", SCOPE_OWN),
        ("project", "read", SCOPE_OWN),
        ("project.wbs", "read", SCOPE_OWN),
        ("project.planning", "read", SCOPE_OWN),
        ("project.budget", "read", SCOPE_OWN),
        ("project.change_order", "read", SCOPE_OWN),
        ("project.progress", "read", SCOPE_OWN),
    ),
    "Project Manager": (
        ("core.company", "read", SCOPE_ANY),
        ("project", "create", SCOPE_OWN),
        ("project", "read", SCOPE_OWN),
        ("project.wbs", "create", SCOPE_OWN),
        ("project.wbs", "read", SCOPE_OWN),
        ("project.planning", "create", SCOPE_OWN),
        ("project.planning", "read", SCOPE_OWN),
        ("project.budget", "read", SCOPE_OWN),
        ("project.change_order", "create", SCOPE_OWN),
        ("project.change_order", "read", SCOPE_OWN),
        ("project.change_order", "submit", SCOPE_OWN),
        ("project.progress", "create", SCOPE_OWN),
        ("project.progress", "read", SCOPE_OWN),
    ),
    "Project Controller": (
        ("core.company", "read", SCOPE_ANY),
        ("project", "read", SCOPE_OWN),
        ("project.wbs", "read", SCOPE_OWN),
        ("project.planning", "read", SCOPE_OWN),
        ("project.budget", "create", SCOPE_OWN),
        ("project.budget", "read", SCOPE_OWN),
        ("project.change_order", "read", SCOPE_OWN),
        ("project.change_order", "approve", SCOPE_OWN),
        ("project.progress", "read", SCOPE_OWN),
    ),
    "Procurement Manager": (
        ("core.company", "read", SCOPE_OWN),
        ("procurement.supplier", "create", SCOPE_OWN),
        ("procurement.supplier", "read", SCOPE_OWN),
        ("procurement.contract", "create", SCOPE_OWN),
        ("procurement.contract", "read", SCOPE_OWN),
        ("procurement.requisition", "read", SCOPE_OWN),
        ("procurement.requisition", "approve", SCOPE_OWN),
        ("procurement.rfq", "create", SCOPE_OWN),
        ("procurement.rfq", "read", SCOPE_OWN),
        ("procurement.quotation", "create", SCOPE_OWN),
        ("procurement.quotation", "read", SCOPE_OWN),
        ("procurement.quotation", "select", SCOPE_OWN),
        ("procurement.purchase_order", "create", SCOPE_OWN),
        ("procurement.purchase_order", "read", SCOPE_OWN),
        ("procurement.purchase_order", "approve", SCOPE_OWN),
        ("procurement.goods_receipt", "read", SCOPE_OWN),
        ("procurement.service_entry", "read", SCOPE_OWN),
        ("procurement.three_way_match", "create", SCOPE_OWN),
        ("procurement.three_way_match", "read", SCOPE_OWN),
        ("inventory.item", "read", SCOPE_OWN),
        ("inventory.warehouse", "read", SCOPE_OWN),
        ("inventory.stock", "read", SCOPE_OWN),
    ),
    "Buyer": (
        ("core.company", "read", SCOPE_OWN),
        ("procurement.supplier", "read", SCOPE_OWN),
        ("procurement.requisition", "create", SCOPE_OWN),
        ("procurement.requisition", "read", SCOPE_OWN),
        ("procurement.rfq", "create", SCOPE_OWN),
        ("procurement.rfq", "read", SCOPE_OWN),
        ("procurement.quotation", "create", SCOPE_OWN),
        ("procurement.quotation", "read", SCOPE_OWN),
        ("procurement.purchase_order", "create", SCOPE_OWN),
        ("procurement.purchase_order", "read", SCOPE_OWN),
        ("procurement.goods_receipt", "read", SCOPE_OWN),
        ("procurement.service_entry", "read", SCOPE_OWN),
        ("procurement.three_way_match", "read", SCOPE_OWN),
        ("inventory.item", "read", SCOPE_OWN),
        ("inventory.warehouse", "read", SCOPE_OWN),
    ),
    "Warehouse Manager": (
        ("core.company", "read", SCOPE_OWN),
        ("procurement.purchase_order", "read", SCOPE_OWN),
        ("procurement.goods_receipt", "create", SCOPE_OWN),
        ("procurement.goods_receipt", "read", SCOPE_OWN),
        ("inventory.item", "create", SCOPE_OWN),
        ("inventory.item", "read", SCOPE_OWN),
        ("inventory.warehouse", "create", SCOPE_OWN),
        ("inventory.warehouse", "read", SCOPE_OWN),
        ("inventory.stock", "read", SCOPE_OWN),
        ("inventory.stock", "move", SCOPE_OWN),
        ("inventory.physical_count", "create", SCOPE_OWN),
        ("inventory.physical_count", "approve", SCOPE_OWN),
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
