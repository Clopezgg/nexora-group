import uuid
from collections.abc import Callable
from typing import Any

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.domain.errors import NotAuthorizedError
from app.models.accounting import AccountingDocument, JournalLine
from app.models.ap import SupplierInvoice, SupplierPayment
from app.models.ar import CustomerInvoice, CustomerReceipt
from app.models.asset import DepreciationEntry, FixedAsset
from app.models.document import Document
from app.models.equipment import Equipment, MaintenanceOrder
from app.models.permission import (
    SCOPE_ANY,
    SCOPE_NONE,
    SCOPE_OWN,
    Permission,
    RolePermission,
    UserCompanyAccess,
    UserProjectAccess,
)
from app.models.project import Project
from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole
from app.models.workforce import Crew, TimeEntry

"""Motor central de RBAC con aislamiento de compañía y proyecto.

El frontend solo utiliza permisos efectivos para UX. Toda autorización final se
resuelve aquí en servidor. `project_scope=OWN` requiere UserProjectAccess cuando
la operación tiene un proyecto concreto; `ANY` permite cualquier proyecto dentro
del company scope correspondiente; `NONE` no concede contexto de proyecto.
"""

PROJECT_AWARE_RESOURCE_PREFIXES = (
    "project",
    "document.",
    "construction.",
    "site.",
    "quality.",
    "safety.",
    "equipment.",
    "workforce.",
    "procurement.",
    "inventory.",
    "ap.",
    "ar.",
    "accounting.",
    "treasury.",
    "asset.",
    "crm.",
    "reports.",
)


def _is_project_aware_resource(resource: str) -> bool:
    return resource == "project" or resource.startswith(PROJECT_AWARE_RESOURCE_PREFIXES)


def _normalized_key(value: str) -> str:
    return "".join(character for character in value.lower() if character.isalnum())


def _collect_project_values(value: Any) -> list[Any]:
    """Collect project identifiers from arbitrary JSON without trusting aliases.

    Both snake_case and camelCase are accepted. Keys such as
    `restrictedForProjectId` also count because they end in `projectId`. Nested
    journal lines and other arrays are inspected so one request cannot smuggle a
    second unauthorized project through a child object.
    """
    result: list[Any] = []
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = _normalized_key(str(key))
            if normalized.endswith("projectid"):
                if child not in (None, ""):
                    result.append(child)
                continue
            if normalized.endswith("projectids") and isinstance(child, list):
                result.extend(item for item in child if item not in (None, ""))
                continue
            result.extend(_collect_project_values(child))
    elif isinstance(value, list):
        for child in value:
            result.extend(_collect_project_values(child))
    return result


def _uuid_path_value(request: Request, name: str) -> uuid.UUID | None:
    value = request.path_params.get(name)
    if value in (None, ""):
        return None
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError) as exc:
        raise NotAuthorizedError("Identificador de entidad inválido") from exc


def _indirect_entity_project_ids(
    db: Session, *, resource: str, request: Request
) -> set[uuid.UUID]:
    """Resolve project context hidden behind entity ids in the route.

    This prevents bypassing OWN project isolation by calling an entity endpoint
    that only exposes `invoice_id`, `equipment_id`, `document_id`, etc. Missing
    entities are intentionally ignored here and remain the domain route's 404.
    """
    project_ids: set[uuid.UUID] = set()

    def add(project_id: uuid.UUID | None) -> None:
        if project_id is not None:
            project_ids.add(project_id)

    accounting_document_id = _uuid_path_value(request, "accounting_document_id")
    document_id = _uuid_path_value(request, "document_id")
    if accounting_document_id is None and resource.startswith("accounting."):
        accounting_document_id = document_id
    if accounting_document_id is not None:
        accounting_document = db.get(AccountingDocument, accounting_document_id)
        if accounting_document is not None:
            add(accounting_document.project_id)
            line_projects = db.execute(
                select(JournalLine.project_id).where(
                    JournalLine.accounting_document_id == accounting_document.id,
                    JournalLine.project_id.is_not(None),
                )
            ).scalars()
            for project_id in line_projects:
                add(project_id)

    if resource.startswith("document.") and document_id is not None:
        document = db.get(Document, document_id)
        if document is not None:
            add(document.project_id)

    invoice_id = _uuid_path_value(request, "invoice_id")
    if invoice_id is not None:
        if resource.startswith("ap."):
            supplier_invoice = db.get(SupplierInvoice, invoice_id)
            if supplier_invoice is not None:
                add(supplier_invoice.project_id)
        elif resource.startswith("ar."):
            customer_invoice = db.get(CustomerInvoice, invoice_id)
            if customer_invoice is not None:
                add(customer_invoice.project_id)

    payment_id = _uuid_path_value(request, "payment_id")
    if payment_id is not None:
        payment = db.get(SupplierPayment, payment_id)
        if payment is not None:
            supplier_invoice = db.get(SupplierInvoice, payment.supplier_invoice_id)
            if supplier_invoice is not None:
                add(supplier_invoice.project_id)

    receipt_id = _uuid_path_value(request, "receipt_id")
    if receipt_id is not None:
        receipt = db.get(CustomerReceipt, receipt_id)
        if receipt is not None:
            customer_invoice = db.get(CustomerInvoice, receipt.customer_invoice_id)
            if customer_invoice is not None:
                add(customer_invoice.project_id)

    equipment_id = _uuid_path_value(request, "equipment_id")
    order_id = _uuid_path_value(request, "order_id")
    if equipment_id is None and order_id is not None:
        order = db.get(MaintenanceOrder, order_id)
        if order is not None:
            equipment_id = order.equipment_id
    if equipment_id is not None:
        equipment = db.get(Equipment, equipment_id)
        if equipment is not None:
            add(equipment.project_id)

    time_entry_id = _uuid_path_value(request, "time_entry_id")
    if time_entry_id is not None:
        entry = db.get(TimeEntry, time_entry_id)
        if entry is not None:
            add(entry.project_id)

    crew_id = _uuid_path_value(request, "crew_id")
    if crew_id is not None:
        crew = db.get(Crew, crew_id)
        if crew is not None:
            add(crew.project_id)

    asset_id = _uuid_path_value(request, "asset_id")
    depreciation_entry_id = _uuid_path_value(request, "depreciation_entry_id")
    if asset_id is None and depreciation_entry_id is not None:
        entry = db.get(DepreciationEntry, depreciation_entry_id)
        if entry is not None:
            asset_id = entry.asset_id
    if asset_id is not None:
        asset = db.get(FixedAsset, asset_id)
        if asset is not None:
            add(asset.project_id)

    return project_ids


async def _request_project_ids(request: Request) -> set[uuid.UUID]:
    raw_values: list[Any] = []

    for key, value in request.path_params.items():
        if _normalized_key(str(key)).endswith("projectid") and value not in (None, ""):
            raw_values.append(value)

    for key, value in request.query_params.multi_items():
        if _normalized_key(str(key)).endswith("projectid") and value not in (None, ""):
            raw_values.append(value)

    content_type = request.headers.get("content-type", "").lower()
    if request.method.upper() in {"POST", "PUT", "PATCH", "DELETE"} and "application/json" in content_type:
        try:
            raw_values.extend(_collect_project_values(await request.json()))
        except (ValueError, TypeError):
            # Request validation remains FastAPI/Pydantic's responsibility. We
            # only inspect valid JSON contexts for authorization hints.
            pass

    project_ids: set[uuid.UUID] = set()
    for value in raw_values:
        try:
            project_ids.add(uuid.UUID(str(value)))
        except (TypeError, ValueError) as exc:
            raise NotAuthorizedError("Identificador de proyecto inválido") from exc
    return project_ids


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
    """Permisos resource:action para filtrado visual; no codifica scopes."""
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


def _project_scopes_for_grant(
    db: Session, *, user_id: uuid.UUID, resource: str, action: str
) -> list[str]:
    stmt = (
        select(RolePermission.project_scope)
        .join(Permission, RolePermission.permission_id == Permission.id)
        .join(UserRole, UserRole.role_id == RolePermission.role_id)
        .where(
            UserRole.user_id == user_id,
            Permission.resource == resource,
            Permission.action == action,
        )
        .distinct()
    )
    return list(db.execute(stmt).scalars())


def user_has_project_access(db: Session, *, user_id: uuid.UUID, project_id: uuid.UUID) -> bool:
    stmt = select(UserProjectAccess.id).where(
        UserProjectAccess.user_id == user_id,
        UserProjectAccess.project_id == project_id,
    )
    return db.execute(stmt).first() is not None


def list_user_project_ids(db: Session, *, user_id: uuid.UUID) -> list[uuid.UUID]:
    return list(
        db.execute(
            select(UserProjectAccess.project_id).where(UserProjectAccess.user_id == user_id)
        ).scalars()
    )


def accessible_project_ids(
    db: Session, *, user_id: uuid.UUID, resource: str, action: str
) -> list[uuid.UUID] | None:
    """None significa ANY; lista significa el conjunto explícito permitido."""
    scopes = _project_scopes_for_grant(
        db, user_id=user_id, resource=resource, action=action
    )
    if SCOPE_ANY in scopes:
        return None
    if SCOPE_OWN in scopes:
        return list_user_project_ids(db, user_id=user_id)
    return []


def assert_project_access(
    db: Session,
    *,
    user_id: uuid.UUID,
    resource: str,
    action: str,
    project_id: uuid.UUID,
) -> None:
    project = db.get(Project, project_id)
    if project is None:
        raise NotAuthorizedError("El proyecto solicitado no existe o no está disponible")
    assert_company_access(
        db,
        user_id=user_id,
        resource=resource,
        action=action,
        company_id=project.company_id,
    )
    scopes = _project_scopes_for_grant(
        db, user_id=user_id, resource=resource, action=action
    )
    if SCOPE_ANY in scopes:
        return
    if SCOPE_OWN in scopes and user_has_project_access(
        db, user_id=user_id, project_id=project_id
    ):
        return
    raise NotAuthorizedError(
        f"El usuario no tiene acceso al proyecto {project_id} para {action} sobre {resource}"
    )


def grant_project_access(
    db: Session, *, user_id: uuid.UUID, project_id: uuid.UUID
) -> UserProjectAccess:
    existing = db.execute(
        select(UserProjectAccess).where(
            UserProjectAccess.user_id == user_id,
            UserProjectAccess.project_id == project_id,
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing
    grant = UserProjectAccess(user_id=user_id, project_id=project_id)
    db.add(grant)
    db.flush()
    return grant


def revoke_project_access(db: Session, *, user_id: uuid.UUID, project_id: uuid.UUID) -> bool:
    grant = db.execute(
        select(UserProjectAccess).where(
            UserProjectAccess.user_id == user_id,
            UserProjectAccess.project_id == project_id,
        )
    ).scalar_one_or_none()
    if grant is None:
        return False
    db.delete(grant)
    db.flush()
    return True


def normalize_project_scopes(db: Session) -> None:
    """Normaliza grants creados por bootstrap en fresh DB.

    La migración normaliza instalaciones existentes. Este paso hace lo mismo
    para grants que nacen después de migrar: recursos con contexto de proyecto
    heredan ANY/OWN del company scope; recursos puramente company usan NONE.
    """
    rows = db.execute(
        select(RolePermission, Permission).join(
            Permission, RolePermission.permission_id == Permission.id
        )
    ).all()
    for grant, permission in rows:
        if _is_project_aware_resource(permission.resource):
            desired = SCOPE_ANY if grant.company_scope == SCOPE_ANY else SCOPE_OWN
        else:
            desired = SCOPE_NONE
        if grant.project_scope != desired:
            grant.project_scope = desired
    db.flush()


def require_permission(resource: str, action: str) -> Callable:
    async def _dependency(
        request: Request,
        db: Session = Depends(get_db),
        current: tuple[User, list[str]] = Depends(get_current_user),
    ) -> User:
        user, _roles = current
        if not user_has_permission(db, user_id=user.id, resource=resource, action=action):
            raise NotAuthorizedError(f"No tiene permiso para {action} sobre {resource}")

        if _is_project_aware_resource(resource):
            project_ids = await _request_project_ids(request)
            project_ids.update(
                _indirect_entity_project_ids(db, resource=resource, request=request)
            )
            for project_id in project_ids:
                assert_project_access(
                    db,
                    user_id=user.id,
                    resource=resource,
                    action=action,
                    project_id=project_id,
                )
        return user

    return _dependency
