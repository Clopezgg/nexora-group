import uuid
from dataclasses import dataclass

from sqlalchemy import select
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
    db: Session, *, company_id: uuid.UUID, query: str, limit_per_type: int = 5
) -> list[SearchResult]:
    q = f"%{query}%"
    results: list[SearchResult] = []

    projects = db.execute(
        select(Project)
        .where(Project.company_id == company_id, Project.name.ilike(q))
        .limit(limit_per_type)
    ).scalars()
    results += [
        SearchResult(p.id, p.name, "Proyectos", "/proyectos", "project") for p in projects
    ]

    suppliers = db.execute(
        select(Supplier)
        .where(Supplier.company_id == company_id, Supplier.legal_name.ilike(q))
        .limit(limit_per_type)
    ).scalars()
    results += [
        SearchResult(s.id, s.legal_name, "Proveedores", "/abastecimiento/proveedores", "supplier")
        for s in suppliers
    ]

    customers = db.execute(
        select(Customer)
        .where(Customer.company_id == company_id, Customer.legal_name.ilike(q))
        .limit(limit_per_type)
    ).scalars()
    results += [
        SearchResult(c.id, c.legal_name, "Clientes", "/comercial/clientes", "customer")
        for c in customers
    ]

    supplier_invoices = db.execute(
        select(SupplierInvoice)
        .where(SupplierInvoice.company_id == company_id, SupplierInvoice.invoice_number.ilike(q))
        .limit(limit_per_type)
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

    customer_invoices = db.execute(
        select(CustomerInvoice)
        .where(CustomerInvoice.company_id == company_id, CustomerInvoice.invoice_number.ilike(q))
        .limit(limit_per_type)
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

    purchase_orders = db.execute(
        select(PurchaseOrder)
        .where(PurchaseOrder.company_id == company_id, PurchaseOrder.po_number.ilike(q))
        .limit(limit_per_type)
    ).scalars()
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

    documents = db.execute(
        select(Document)
        .where(Document.company_id == company_id, Document.title.ilike(q))
        .limit(limit_per_type)
    ).scalars()
    results += [
        SearchResult(d.id, d.title, "Documentos", "/control/documentos", "document")
        for d in documents
    ]

    rfis = db.execute(
        select(RequestForInformation)
        .where(
            RequestForInformation.company_id == company_id,
            RequestForInformation.subject.ilike(q),
        )
        .limit(limit_per_type)
    ).scalars()
    results += [
        SearchResult(r.id, r.subject, "RFI", "/proyectos/rfi-submittals", "rfi") for r in rfis
    ]

    fixed_assets = db.execute(
        select(FixedAsset)
        .where(FixedAsset.company_id == company_id, FixedAsset.name.ilike(q))
        .limit(limit_per_type)
    ).scalars()
    results += [
        SearchResult(fa.id, fa.name, "Activos fijos", "/finanzas/activos", "fixed_asset")
        for fa in fixed_assets
    ]

    equipment = db.execute(
        select(Equipment)
        .where(Equipment.company_id == company_id, Equipment.name.ilike(q))
        .limit(limit_per_type)
    ).scalars()
    results += [
        SearchResult(e.id, e.name, "Equipos", "/recursos/equipos", "equipment") for e in equipment
    ]

    return results
