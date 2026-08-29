import uuid
from dataclasses import dataclass

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.ap import SupplierInvoice
from app.models.ar import CustomerInvoice
from app.models.asset import FixedAsset
from app.models.crm import Customer
from app.models.document import Document
from app.models.equipment import Equipment
from app.models.procurement import PurchaseOrder
from app.models.project import Project
from app.models.rfi import RequestForInformation
from app.models.supplier import Supplier

# Global Search (NXR-REQ-0092). Cada bloque hace una consulta ilike
# acotada por company_id de su propio modelo (INV-COMP-001) y por
# limit_per_type -- nunca una búsqueda global sin scope de company.


@dataclass
class SearchResult:
    id: uuid.UUID
    label: str
    group: str
    path: str
    entity_type: str


def search(
    db: Session,
    *,
    company_id: uuid.UUID,
    query: str,
    allowed_project_ids: list[uuid.UUID] | None,
    user_permissions: set[str],
    limit_per_type: int = 5,
) -> list[SearchResult]:
    q = f"%{query}%"
    results: list[SearchResult] = []

    def may_read(resource: str) -> bool:
        return f"{resource}:read" in user_permissions

    def project_filter(column):
        if allowed_project_ids is None:
            return None
        return or_(column.is_(None), column.in_(allowed_project_ids))

    if may_read("project"):
        project_query = select(Project).where(
            Project.company_id == company_id,
            Project.name.ilike(q),
        )
        if allowed_project_ids is not None:
            project_query = project_query.where(Project.id.in_(allowed_project_ids))
        projects = db.execute(project_query.limit(limit_per_type)).scalars()
        results += [
            SearchResult(p.id, p.name, "Proyectos", "/proyectos", "project") for p in projects
        ]

    if may_read("procurement.supplier"):
        suppliers = db.execute(
            select(Supplier)
            .where(Supplier.company_id == company_id, Supplier.legal_name.ilike(q))
            .limit(limit_per_type)
        ).scalars()
        results += [
            SearchResult(s.id, s.legal_name, "Proveedores", "/abastecimiento/proveedores", "supplier")
            for s in suppliers
        ]

    if may_read("crm.customer"):
        customers = db.execute(
            select(Customer)
            .where(Customer.company_id == company_id, Customer.legal_name.ilike(q))
            .limit(limit_per_type)
        ).scalars()
        results += [
            SearchResult(c.id, c.legal_name, "Clientes", "/comercial/clientes", "customer")
            for c in customers
        ]

    if may_read("ap.supplier_invoice"):
        supplier_invoice_query = select(SupplierInvoice).where(
            SupplierInvoice.company_id == company_id,
            SupplierInvoice.invoice_number.ilike(q),
        )
        project_condition = project_filter(SupplierInvoice.project_id)
        if project_condition is not None:
            supplier_invoice_query = supplier_invoice_query.where(project_condition)
        supplier_invoices = db.execute(
            supplier_invoice_query.limit(limit_per_type)
        ).scalars()
        results += [
            SearchResult(
                si.id,
                si.invoice_number,
                "Facturas de proveedor",
                "/finanzas/cuentas-por-pagar",
                "supplier_invoice",
            )
            for si in supplier_invoices
        ]

    if may_read("ar.customer_invoice"):
        customer_invoice_query = select(CustomerInvoice).where(
            CustomerInvoice.company_id == company_id,
            CustomerInvoice.invoice_number.ilike(q),
        )
        project_condition = project_filter(CustomerInvoice.project_id)
        if project_condition is not None:
            customer_invoice_query = customer_invoice_query.where(project_condition)
        customer_invoices = db.execute(
            customer_invoice_query.limit(limit_per_type)
        ).scalars()
        results += [
            SearchResult(
                ci.id,
                ci.invoice_number,
                "Facturas de cliente",
                "/finanzas/cuentas-por-cobrar",
                "customer_invoice",
            )
            for ci in customer_invoices
        ]

    if may_read("procurement.purchase_order"):
        purchase_order_query = select(PurchaseOrder).where(
            PurchaseOrder.company_id == company_id,
            PurchaseOrder.po_number.ilike(q),
        )
        project_condition = project_filter(PurchaseOrder.project_id)
        if project_condition is not None:
            purchase_order_query = purchase_order_query.where(project_condition)
        purchase_orders = db.execute(purchase_order_query.limit(limit_per_type)).scalars()
        results += [
            SearchResult(
                po.id,
                po.po_number,
                "Órdenes de compra",
                "/abastecimiento/ordenes-de-compra",
                "purchase_order",
            )
            for po in purchase_orders
        ]

    if may_read("document.document"):
        document_query = select(Document).where(
            Document.company_id == company_id,
            Document.title.ilike(q),
        )
        project_condition = project_filter(Document.project_id)
        if project_condition is not None:
            document_query = document_query.where(project_condition)
        documents = db.execute(document_query.limit(limit_per_type)).scalars()
        results += [
            SearchResult(d.id, d.title, "Documentos", "/control/documentos", "document")
            for d in documents
        ]

    if may_read("construction.rfi"):
        rfi_query = select(RequestForInformation).where(
            RequestForInformation.company_id == company_id,
            RequestForInformation.subject.ilike(q),
        )
        if allowed_project_ids is not None:
            rfi_query = rfi_query.where(RequestForInformation.project_id.in_(allowed_project_ids))
        rfis = db.execute(rfi_query.limit(limit_per_type)).scalars()
        results += [
            SearchResult(r.id, r.subject, "RFI", "/proyectos/rfi-submittals", "rfi") for r in rfis
        ]

    if may_read("asset.fixed_asset"):
        fixed_asset_query = select(FixedAsset).where(
            FixedAsset.company_id == company_id,
            FixedAsset.name.ilike(q),
        )
        project_condition = project_filter(FixedAsset.project_id)
        if project_condition is not None:
            fixed_asset_query = fixed_asset_query.where(project_condition)
        fixed_assets = db.execute(fixed_asset_query.limit(limit_per_type)).scalars()
        results += [
            SearchResult(fa.id, fa.name, "Activos fijos", "/finanzas/activos", "fixed_asset")
            for fa in fixed_assets
        ]

    if may_read("equipment.equipment"):
        equipment_query = select(Equipment).where(
            Equipment.company_id == company_id,
            Equipment.name.ilike(q),
        )
        project_condition = project_filter(Equipment.project_id)
        if project_condition is not None:
            equipment_query = equipment_query.where(project_condition)
        equipment = db.execute(equipment_query.limit(limit_per_type)).scalars()
        results += [
            SearchResult(e.id, e.name, "Equipos", "/recursos/equipos", "equipment")
            for e in equipment
        ]

    return results
