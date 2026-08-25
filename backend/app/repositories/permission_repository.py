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
    # Track A - Financial Core (Treasury/AP/AR, orden maestra §26-36).
    ("treasury.account", "create", "Crear cuentas de tesorería"),
    ("treasury.account", "read", "Ver cuentas de tesorería"),
    ("treasury.remittance", "create", "Registrar remesas"),
    ("treasury.remittance", "read", "Ver remesas"),
    ("treasury.general_expense", "create", "Registrar gastos generales"),
    ("treasury.general_expense", "read", "Ver gastos generales"),
    ("treasury.transfer", "create", "Registrar transferencias de tesorería"),
    ("treasury.transfer", "read", "Ver transferencias de tesorería"),
    ("treasury.cash_closing", "create", "Registrar cierres de caja"),
    ("treasury.cash_closing", "approve", "Aprobar cierres de caja"),
    ("treasury.cash_closing", "read", "Ver cierres de caja"),
    ("treasury.bank_reconciliation", "create", "Cargar estados de cuenta bancarios"),
    ("treasury.bank_reconciliation", "match", "Conciliar líneas bancarias"),
    ("treasury.bank_reconciliation", "read", "Ver conciliación bancaria"),
    ("treasury.fund_restriction", "create", "Registrar restricciones de fondos"),
    ("treasury.fund_restriction", "read", "Ver restricciones de fondos"),
    ("treasury.voucher", "read", "Generar/descargar comprobantes"),
    ("ap.supplier_invoice", "create", "Registrar facturas de proveedor"),
    ("ap.supplier_invoice", "approve", "Aprobar facturas de proveedor"),
    ("ap.supplier_invoice", "read", "Ver facturas de proveedor"),
    ("ap.supplier_payment", "create", "Registrar pagos a proveedor"),
    ("ap.supplier_payment", "read", "Ver pagos a proveedor"),
    ("ar.customer_invoice", "create", "Registrar facturas de cliente"),
    ("ar.customer_invoice", "approve", "Aprobar facturas de cliente"),
    ("ar.customer_invoice", "read", "Ver facturas de cliente"),
    ("ar.customer_receipt", "create", "Registrar cobros de cliente"),
    ("ar.customer_receipt", "read", "Ver cobros de cliente"),
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
        ("treasury.account", "create", SCOPE_OWN),
        ("treasury.account", "read", SCOPE_OWN),
        ("treasury.remittance", "create", SCOPE_OWN),
        ("treasury.remittance", "read", SCOPE_OWN),
        ("treasury.general_expense", "create", SCOPE_OWN),
        ("treasury.general_expense", "read", SCOPE_OWN),
        ("treasury.transfer", "create", SCOPE_OWN),
        ("treasury.transfer", "read", SCOPE_OWN),
        ("treasury.cash_closing", "create", SCOPE_OWN),
        ("treasury.cash_closing", "approve", SCOPE_OWN),
        ("treasury.cash_closing", "read", SCOPE_OWN),
        ("treasury.bank_reconciliation", "create", SCOPE_OWN),
        ("treasury.bank_reconciliation", "match", SCOPE_OWN),
        ("treasury.bank_reconciliation", "read", SCOPE_OWN),
        ("treasury.fund_restriction", "create", SCOPE_OWN),
        ("treasury.fund_restriction", "read", SCOPE_OWN),
        ("treasury.voucher", "read", SCOPE_OWN),
        ("ap.supplier_invoice", "create", SCOPE_OWN),
        ("ap.supplier_invoice", "approve", SCOPE_OWN),
        ("ap.supplier_invoice", "read", SCOPE_OWN),
        ("ap.supplier_payment", "create", SCOPE_OWN),
        ("ap.supplier_payment", "read", SCOPE_OWN),
        ("ar.customer_invoice", "create", SCOPE_OWN),
        ("ar.customer_invoice", "approve", SCOPE_OWN),
        ("ar.customer_invoice", "read", SCOPE_OWN),
        ("ar.customer_receipt", "create", SCOPE_OWN),
        ("ar.customer_receipt", "read", SCOPE_OWN),
    ),
    "Treasury Manager": (
        ("core.company", "read", SCOPE_ANY),
        ("accounting.account", "read", SCOPE_OWN),
        ("treasury.account", "create", SCOPE_OWN),
        ("treasury.account", "read", SCOPE_OWN),
        ("treasury.remittance", "create", SCOPE_OWN),
        ("treasury.remittance", "read", SCOPE_OWN),
        ("treasury.general_expense", "create", SCOPE_OWN),
        ("treasury.general_expense", "read", SCOPE_OWN),
        ("treasury.transfer", "create", SCOPE_OWN),
        ("treasury.transfer", "read", SCOPE_OWN),
        ("treasury.cash_closing", "create", SCOPE_OWN),
        ("treasury.cash_closing", "approve", SCOPE_OWN),
        ("treasury.cash_closing", "read", SCOPE_OWN),
        ("treasury.bank_reconciliation", "create", SCOPE_OWN),
        ("treasury.bank_reconciliation", "match", SCOPE_OWN),
        ("treasury.bank_reconciliation", "read", SCOPE_OWN),
        ("treasury.fund_restriction", "create", SCOPE_OWN),
        ("treasury.fund_restriction", "read", SCOPE_OWN),
        ("treasury.voucher", "read", SCOPE_OWN),
        ("ap.supplier_payment", "create", SCOPE_OWN),
        ("ap.supplier_payment", "read", SCOPE_OWN),
        ("ar.customer_receipt", "create", SCOPE_OWN),
        ("ar.customer_receipt", "read", SCOPE_OWN),
    ),
    "Accountant": (
        ("core.company", "read", SCOPE_ANY),
        ("accounting.journal_entry", "create", SCOPE_OWN),
        ("accounting.journal_entry", "read", SCOPE_OWN),
        ("accounting.account", "read", SCOPE_OWN),
        ("treasury.account", "read", SCOPE_OWN),
        ("treasury.remittance", "read", SCOPE_OWN),
        ("treasury.general_expense", "read", SCOPE_OWN),
        ("treasury.transfer", "read", SCOPE_OWN),
        ("treasury.bank_reconciliation", "read", SCOPE_OWN),
        ("treasury.voucher", "read", SCOPE_OWN),
        ("ap.supplier_invoice", "create", SCOPE_OWN),
        ("ap.supplier_invoice", "read", SCOPE_OWN),
        ("ar.customer_invoice", "create", SCOPE_OWN),
        ("ar.customer_invoice", "read", SCOPE_OWN),
    ),
    "Auditor": (
        ("core.company", "read", SCOPE_ANY),
        ("accounting.journal_entry", "read", SCOPE_ANY),
        ("accounting.account", "read", SCOPE_ANY),
        ("treasury.account", "read", SCOPE_ANY),
        ("treasury.remittance", "read", SCOPE_ANY),
        ("treasury.general_expense", "read", SCOPE_ANY),
        ("treasury.transfer", "read", SCOPE_ANY),
        ("treasury.cash_closing", "read", SCOPE_ANY),
        ("treasury.bank_reconciliation", "read", SCOPE_ANY),
        ("treasury.fund_restriction", "read", SCOPE_ANY),
        ("treasury.voucher", "read", SCOPE_ANY),
        ("ap.supplier_invoice", "read", SCOPE_ANY),
        ("ap.supplier_payment", "read", SCOPE_ANY),
        ("ar.customer_invoice", "read", SCOPE_ANY),
        ("ar.customer_receipt", "read", SCOPE_ANY),
    ),
    "Viewer": (
        ("core.company", "read", SCOPE_ANY),
        ("accounting.journal_entry", "read", SCOPE_OWN),
        ("accounting.account", "read", SCOPE_OWN),
        ("treasury.account", "read", SCOPE_OWN),
        ("treasury.remittance", "read", SCOPE_OWN),
        ("ap.supplier_invoice", "read", SCOPE_OWN),
        ("ar.customer_invoice", "read", SCOPE_OWN),
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
