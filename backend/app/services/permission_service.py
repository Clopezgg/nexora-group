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
from app.models.approval_request import ApprovalRequest
from app.models.ar import CustomerInvoice, CustomerReceipt
from app.models.asset import DepreciationEntry, FixedAsset
from app.models.change_order import ChangeOrder
from app.models.crm import Quotation as CustomerQuotation
from app.models.crm import SalesContract
from app.models.document import Document
from app.models.equipment import Equipment, MaintenanceOrder
from app.models.inventory import PhysicalCount
from app.models.procurement import (
    GoodsReceipt,
    PurchaseOrder,
    PurchaseRequisition,
    RequestForQuotation,
    ServiceEntry,
    SupplierQuotation,
)
from app.models.quality import CorrectiveAction, NonConformance, QualityInspection
from app.models.rfi import RequestForInformation
from app.models.safety import SafetyIncident, SafetyObservation
from app.models.site_report import DailySiteReport
from app.models.submittal import Submittal
from app.models.treasury import FundRestriction
from app.models.warehouse import Warehouse
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
    "search.",
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


def _collect_entity_values(value: Any) -> dict[str, list[Any]]:
    """Collect named entity identifiers from nested request JSON.

    Project isolation cannot trust only explicit projectId fields. A caller may
    instead submit purchaseOrderId, quotationId or another source entity whose
    project is stored server-side. The normalized key disambiguates shared
    names such as invoiceId by resource.
    """
    result: dict[str, list[Any]] = {}

    def visit(child: Any) -> None:
        if isinstance(child, dict):
            for key, nested in child.items():
                normalized = _normalized_key(str(key))
                if normalized.endswith("id") and nested not in (None, ""):
                    result.setdefault(normalized, []).append(nested)
                elif normalized.endswith("ids") and isinstance(nested, list):
                    result.setdefault(normalized, []).extend(
                        item for item in nested if item not in (None, "")
                    )
                visit(nested)
        elif isinstance(child, list):
            for nested in child:
                visit(nested)

    visit(value)
    return result


async def _request_entity_values(request: Request) -> dict[str, list[Any]]:
    result: dict[str, list[Any]] = {}

    def add(key: str, value: Any) -> None:
        if value in (None, ""):
            return
        result.setdefault(_normalized_key(key), []).append(value)

    for key, value in request.path_params.items():
        add(str(key), value)
    for key, value in request.query_params.multi_items():
        add(str(key), value)

    content_type = request.headers.get("content-type", "").lower()
    if request.method.upper() in {"POST", "PUT", "PATCH", "DELETE"} and "application/json" in content_type:
        try:
            nested = _collect_entity_values(await request.json())
            for key, values in nested.items():
                result.setdefault(key, []).extend(values)
        except (ValueError, TypeError):
            pass
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
    db: Session, *, resource: str, entity_values: dict[str, list[Any]]
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

    def ids(*names: str) -> list[uuid.UUID]:
        parsed: list[uuid.UUID] = []
        for name in names:
            for value in entity_values.get(_normalized_key(name), []):
                try:
                    parsed.append(uuid.UUID(str(value)))
                except (TypeError, ValueError) as exc:
                    raise NotAuthorizedError("Identificador de entidad inválido") from exc
        return parsed

    def add_direct(model: type, names: tuple[str, ...], attribute: str = "project_id") -> None:
        for entity_id in ids(*names):
            entity = db.get(model, entity_id)
            if entity is not None:
                add(getattr(entity, attribute, None))

    document_ids = ids("document_id", "documentId")
    accounting_document_ids = ids("accounting_document_id", "accountingDocumentId")
    if resource.startswith("accounting."):
        accounting_document_ids.extend(document_ids)
    for accounting_document_id in accounting_document_ids:
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

    for document_id in document_ids if resource.startswith("document.") else []:
        document = db.get(Document, document_id)
        if document is not None:
            add(document.project_id)

    for invoice_id in ids("invoice_id", "invoiceId"):
        if resource.startswith("ap."):
            supplier_invoice = db.get(SupplierInvoice, invoice_id)
            if supplier_invoice is not None:
                add(supplier_invoice.project_id)
        elif resource.startswith("ar."):
            customer_invoice = db.get(CustomerInvoice, invoice_id)
            if customer_invoice is not None:
                add(customer_invoice.project_id)

    for payment_id in ids("payment_id", "paymentId"):
        payment = db.get(SupplierPayment, payment_id)
        if payment is not None:
            supplier_invoice = db.get(SupplierInvoice, payment.supplier_invoice_id)
            if supplier_invoice is not None:
                add(supplier_invoice.project_id)

    for receipt_id in ids("receipt_id", "receiptId"):
        receipt = db.get(CustomerReceipt, receipt_id)
        if receipt is not None:
            customer_invoice = db.get(CustomerInvoice, receipt.customer_invoice_id)
            if customer_invoice is not None:
                add(customer_invoice.project_id)

    equipment_ids = ids("equipment_id", "equipmentId")
    order_ids = ids("order_id", "orderId", "maintenance_order_id", "maintenanceOrderId")
    for order_id in order_ids:
        order = db.get(MaintenanceOrder, order_id)
        if order is not None:
            equipment_ids.append(order.equipment_id)
    for equipment_id in equipment_ids:
        equipment = db.get(Equipment, equipment_id)
        if equipment is not None:
            add(equipment.project_id)

    for time_entry_id in ids("time_entry_id", "timeEntryId"):
        entry = db.get(TimeEntry, time_entry_id)
        if entry is not None:
            add(entry.project_id)

    for crew_id in ids("crew_id", "crewId"):
        crew = db.get(Crew, crew_id)
        if crew is not None:
            add(crew.project_id)

    asset_ids = ids("asset_id", "assetId")
    depreciation_entry_ids = ids("depreciation_entry_id", "depreciationEntryId")
    for depreciation_entry_id in depreciation_entry_ids:
        entry = db.get(DepreciationEntry, depreciation_entry_id)
        if entry is not None:
            asset_ids.append(entry.asset_id)
    for asset_id in asset_ids:
        asset = db.get(FixedAsset, asset_id)
        if asset is not None:
            add(asset.project_id)

    add_direct(ChangeOrder, ("change_order_id", "changeOrderId"))
    add_direct(DailySiteReport, ("report_id", "reportId", "daily_site_report_id", "dailySiteReportId"))
    add_direct(QualityInspection, ("inspection_id", "inspectionId"))
    add_direct(NonConformance, ("non_conformance_id", "nonConformanceId"))
    for corrective_action_id in ids("corrective_action_id", "correctiveActionId"):
        action = db.get(CorrectiveAction, corrective_action_id)
        if action is not None:
            non_conformance = db.get(NonConformance, action.non_conformance_id)
            if non_conformance is not None:
                add(non_conformance.project_id)
    add_direct(SafetyObservation, ("observation_id", "observationId"))
    add_direct(SafetyIncident, ("incident_id", "incidentId"))
    add_direct(Submittal, ("submittal_id", "submittalId"))
    add_direct(RequestForInformation, ("rfi_id", "rfiId"))
    add_direct(ApprovalRequest, ("request_id", "requestId"))
    add_direct(FundRestriction, ("restriction_id", "restrictionId"), "restricted_for_project_id")
    add_direct(Warehouse, ("warehouse_id", "warehouseId"))

    for physical_count_id in ids("physical_count_id", "physicalCountId"):
        count = db.get(PhysicalCount, physical_count_id)
        if count is not None:
            warehouse = db.get(Warehouse, count.warehouse_id)
            if warehouse is not None:
                add(warehouse.project_id)

    for requisition_id in ids(
        "requisition_id", "requisitionId", "purchase_requisition_id", "purchaseRequisitionId"
    ):
        requisition = db.get(PurchaseRequisition, requisition_id)
        if requisition is not None:
            add(requisition.project_id)

    def add_rfq(rfq_id: uuid.UUID) -> None:
        rfq = db.get(RequestForQuotation, rfq_id)
        if rfq is not None and rfq.purchase_requisition_id is not None:
            requisition = db.get(PurchaseRequisition, rfq.purchase_requisition_id)
            if requisition is not None:
                add(requisition.project_id)

    for rfq_id in ids("rfq_id", "rfqId", "request_for_quotation_id", "requestForQuotationId"):
        add_rfq(rfq_id)

    quotation_ids = ids("quotation_id", "quotationId", "supplier_quotation_id", "supplierQuotationId")
    if resource.startswith("crm."):
        for quotation_id in quotation_ids:
            quotation = db.get(CustomerQuotation, quotation_id)
            if quotation is not None:
                add(quotation.project_id)
    elif resource.startswith("procurement."):
        for quotation_id in quotation_ids:
            quotation = db.get(SupplierQuotation, quotation_id)
            if quotation is not None:
                add_rfq(quotation.request_for_quotation_id)

    add_direct(SalesContract, ("sales_contract_id", "salesContractId"))

    purchase_order_ids = ids("po_id", "poId", "purchase_order_id", "purchaseOrderId")
    for purchase_order_id in purchase_order_ids:
        purchase_order = db.get(PurchaseOrder, purchase_order_id)
        if purchase_order is not None:
            add(purchase_order.project_id)

    for goods_receipt_id in ids("goods_receipt_id", "goodsReceiptId"):
        receipt = db.get(GoodsReceipt, goods_receipt_id)
        if receipt is not None:
            purchase_order = db.get(PurchaseOrder, receipt.purchase_order_id)
            if purchase_order is not None:
                add(purchase_order.project_id)

    for service_entry_id in ids("service_entry_id", "serviceEntryId"):
        entry = db.get(ServiceEntry, service_entry_id)
        if entry is not None:
            purchase_order = db.get(PurchaseOrder, entry.purchase_order_id)
            if purchase_order is not None:
                add(purchase_order.project_id)

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
            payload = await request.json()
            if isinstance(payload, dict) and str(payload.get("scope", "")).upper() in {"CENTRAL", "GENERAL"}:
                # Invalid global scopes with a top-level project must reach the
                # domain guard, which returns the scope-invariant 422 response.
                # Nested dimensions remain authorization-checked below.
                payload = {
                    key: value
                    for key, value in payload.items()
                    if not _normalized_key(str(key)).endswith("projectid")
                }
            raw_values.extend(_collect_project_values(payload))
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
            entity_values = await _request_entity_values(request)
            project_ids.update(
                _indirect_entity_project_ids(
                    db, resource=resource, entity_values=entity_values
                )
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
