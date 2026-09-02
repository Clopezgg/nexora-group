"""Centro de Control por Número de Documento (ORDEN MAESTRA §31/§32).

Un único punto de búsqueda: se escribe un número (factura, contrato, PO,
comprobante, referencia bancaria, asiento) y se resuelve el registro
empresarial correspondiente en cualquier dominio, con exact-match primero y
las acciones permitidas por estado.
"""

import uuid
from dataclasses import dataclass, field
from decimal import Decimal

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.accounting import AccountingDocument
from app.models.ap import SupplierInvoice, SupplierPayment
from app.models.ar import CustomerInvoice
from app.models.crm import SalesContract
from app.models.procurement import PurchaseOrder
from app.models.supplier import Supplier, SupplierContract
from app.models.treasury import Remittance
from app.models.voucher_issuance import VoucherIssuance


@dataclass
class DocumentHit:
    domain: str
    entity_type: str
    id: str
    number: str
    label: str
    status: str | None = None
    amount: str | None = None
    currency_code: str | None = None
    party: str | None = None
    project_id: str | None = None
    accounting_document_id: str | None = None
    exact: bool = False
    allowed_actions: list[str] = field(default_factory=list)


# --------------------------------------------------------------------------- #
# Action policy (§33) — allowedActions calculado por el backend.               #
# --------------------------------------------------------------------------- #

def allowed_actions_for(entity_type: str, status: str | None) -> list[str]:
    s = (status or "").upper()
    if entity_type == "SUPPLIER_INVOICE":
        return {
            "DRAFT": ["view", "edit", "submit", "approve", "cancel"],
            "REVIEW": ["view", "withdraw_approval", "cancel"],
            "APPROVED": ["view", "pay", "reverse_and_correct"],
            "SCHEDULED": ["view", "pay", "reverse_and_correct"],
            "PARTIALLY_PAID": ["view", "pay", "reverse_payment"],
            "PAID": ["view", "reverse_payment"],
            "RECONCILED": ["view"],
            "CANCELLED": ["view", "duplicate", "archive"],
        }.get(s, ["view"])
    if entity_type == "ACCOUNTING_DOCUMENT":
        return {
            "DRAFT": ["view", "post", "delete_draft"],
            "POSTED": ["view", "reverse_and_correct"],
            "REVERSED": ["view"],
        }.get(s, ["view"])
    if entity_type == "SUPPLIER_CONTRACT":
        return {
            "DRAFT": ["view", "edit", "activate", "cancel"],
            "ACTIVE": ["view", "amend_plan", "complete", "terminate"],
            "COMPLETED": ["view", "reopen"],
            "TERMINATED": ["view", "duplicate"],
        }.get(s, ["view"])
    if entity_type == "PURCHASE_ORDER":
        return {
            "DRAFT": ["view", "edit", "approve", "cancel"],
            "APPROVED": ["view", "send", "receive", "cancel"],
            "SENT": ["view", "receive"],
            "PARTIALLY_RECEIVED": ["view", "receive"],
            "RECEIVED": ["view", "invoice"],
        }.get(s, ["view"])
    if entity_type == "VOUCHER":
        return {"ISSUED": ["view", "download", "verify"], "VOID": ["view"], "REVERSED": ["view"]}.get(
            s, ["view", "download"]
        )
    return ["view"]


def _supplier_name(db: Session, supplier_id) -> str | None:
    supplier = db.get(Supplier, supplier_id)
    return supplier.legal_name if supplier else None


def lookup(
    db: Session, *, query: str, company_ids: list[uuid.UUID] | None
) -> list[DocumentHit]:
    """`company_ids=None` significa acceso global (admin)."""
    q = query.strip()
    if not q:
        return []
    like = f"%{q}%"
    hits: list[DocumentHit] = []

    def _scope(stmt, column):
        return stmt if company_ids is None else stmt.where(column.in_(company_ids))

    # --- SupplierInvoice --------------------------------------------------
    for inv in db.execute(
        _scope(
            select(SupplierInvoice).where(SupplierInvoice.invoice_number.ilike(like)),
            SupplierInvoice.company_id,
        ).limit(25)
    ).scalars():
        hits.append(
            DocumentHit(
                domain="Cuentas por pagar",
                entity_type="SUPPLIER_INVOICE",
                id=str(inv.id),
                number=inv.invoice_number,
                label=f"Factura de proveedor {inv.invoice_number}",
                status=inv.status,
                amount=str(inv.amount + inv.tax_amount),
                currency_code=inv.currency_code,
                party=_supplier_name(db, inv.supplier_id),
                project_id=str(inv.project_id) if inv.project_id else None,
                accounting_document_id=str(inv.accrual_document_id) if inv.accrual_document_id else None,
                exact=inv.invoice_number == q,
                allowed_actions=allowed_actions_for("SUPPLIER_INVOICE", inv.status),
            )
        )

    # --- CustomerInvoice ------------------------------------------------------
    for ci in db.execute(
        _scope(
            select(CustomerInvoice).where(CustomerInvoice.invoice_number.ilike(like)),
            CustomerInvoice.company_id,
        ).limit(25)
    ).scalars():
        hits.append(
            DocumentHit(
                domain="Cuentas por cobrar",
                entity_type="CUSTOMER_INVOICE",
                id=str(ci.id),
                number=ci.invoice_number,
                label=f"Factura de cliente {ci.invoice_number}",
                status=ci.status,
                amount=str(ci.amount),
                currency_code=ci.currency_code,
                project_id=str(ci.project_id) if ci.project_id else None,
                exact=ci.invoice_number == q,
            )
        )

    # --- PurchaseOrder -----------------------------------------------------
    for po in db.execute(
        _scope(select(PurchaseOrder).where(PurchaseOrder.po_number.ilike(like)), PurchaseOrder.company_id).limit(25)
    ).scalars():
        hits.append(
            DocumentHit(
                domain="Compras",
                entity_type="PURCHASE_ORDER",
                id=str(po.id),
                number=po.po_number,
                label=f"Orden de compra {po.po_number}",
                status=po.status,
                currency_code=po.currency_code,
                party=_supplier_name(db, po.supplier_id),
                project_id=str(po.project_id) if po.project_id else None,
                exact=po.po_number == q,
                allowed_actions=allowed_actions_for("PURCHASE_ORDER", po.status),
            )
        )

    # --- SupplierContract ------------------------------------------------------
    for c in db.execute(
        _scope(
            select(SupplierContract).where(SupplierContract.contract_number.ilike(like)),
            SupplierContract.company_id,
        ).limit(25)
    ).scalars():
        hits.append(
            DocumentHit(
                domain="Contratos de ejecución",
                entity_type="SUPPLIER_CONTRACT",
                id=str(c.id),
                number=c.contract_number,
                label=f"Contrato {c.contract_number}",
                status=c.status,
                amount=str(c.value),
                currency_code=c.currency_code,
                party=_supplier_name(db, c.supplier_id),
                project_id=str(c.project_id) if c.project_id else None,
                exact=c.contract_number == q,
                allowed_actions=allowed_actions_for("SUPPLIER_CONTRACT", c.status),
            )
        )

    # --- SalesContract -------------------------------------------------------
    for sc in db.execute(
        _scope(
            select(SalesContract).where(SalesContract.contract_number.ilike(like)),
            SalesContract.company_id,
        ).limit(25)
    ).scalars():
        hits.append(
            DocumentHit(
                domain="Contratos con cliente",
                entity_type="SALES_CONTRACT",
                id=str(sc.id),
                number=sc.contract_number,
                label=f"Contrato con cliente {sc.contract_number}",
                status=sc.status,
                amount=str(sc.amount),
                currency_code=sc.currency_code,
                project_id=str(sc.project_id) if sc.project_id else None,
                exact=sc.contract_number == q,
            )
        )

    # --- VoucherIssuance ---------------------------------------------------
    for v in db.execute(
        _scope(
            select(VoucherIssuance).where(
                or_(
                    VoucherIssuance.document_number.ilike(like),
                    VoucherIssuance.verification_code.ilike(like),
                )
            ),
            VoucherIssuance.company_id,
        ).limit(25)
    ).scalars():
        hits.append(
            DocumentHit(
                domain="Comprobantes",
                entity_type="VOUCHER",
                id=str(v.id),
                number=v.document_number,
                label=f"Comprobante {v.document_number}",
                status=v.status,
                amount=str(v.amount_snapshot),
                currency_code=v.currency_code_snapshot,
                party=v.beneficiary_name_snapshot,
                accounting_document_id=str(v.accounting_document_id),
                exact=q in (v.document_number, v.verification_code),
                allowed_actions=allowed_actions_for("VOUCHER", v.status),
            )
        )

    # --- AccountingDocument ------------------------------------------------
    for doc in db.execute(
        _scope(
            select(AccountingDocument).where(AccountingDocument.document_number.ilike(like)),
            AccountingDocument.company_id,
        ).limit(25)
    ).scalars():
        hits.append(
            DocumentHit(
                domain="Contabilidad",
                entity_type="ACCOUNTING_DOCUMENT",
                id=str(doc.id),
                number=doc.document_number,
                label=f"Asiento {doc.document_number}",
                status=doc.status,
                currency_code=doc.currency_code,
                project_id=str(doc.project_id) if doc.project_id else None,
                accounting_document_id=str(doc.id),
                exact=doc.document_number == q,
                allowed_actions=allowed_actions_for("ACCOUNTING_DOCUMENT", doc.status),
            )
        )

    # --- Remittance / bank reference -------------------------------------
    for rem in db.execute(
        _scope(
            select(Remittance).where(Remittance.reference.ilike(like)), Remittance.company_id
        ).limit(25)
    ).scalars():
        hits.append(
            DocumentHit(
                domain="Tesorería",
                entity_type="REMITTANCE",
                id=str(rem.id),
                number=rem.reference or "",
                label=f"Remesa de {rem.sender}",
                amount=str(rem.original_amount),
                currency_code=rem.currency_code,
                party=rem.sender,
                accounting_document_id=str(rem.accounting_document_id),
                exact=rem.reference == q,
            )
        )

    # --- SupplierPayment / bank transaction reference --------------------
    for pay in db.execute(
        select(SupplierPayment).where(SupplierPayment.bank_transaction_reference.ilike(like)).limit(25)
    ).scalars():
        inv = db.get(SupplierInvoice, pay.supplier_invoice_id)
        if inv is None or (company_ids is not None and inv.company_id not in company_ids):
            continue
        hits.append(
            DocumentHit(
                domain="Tesorería",
                entity_type="SUPPLIER_PAYMENT",
                id=str(pay.id),
                number=pay.bank_transaction_reference or "",
                label=f"Pago a proveedor · ref. {pay.bank_transaction_reference}",
                amount=str(pay.amount),
                party=inv.invoice_number,
                accounting_document_id=str(pay.accounting_document_id),
                exact=pay.bank_transaction_reference == q,
            )
        )

    # exact-match primero, luego por dominio
    hits.sort(key=lambda h: (not h.exact, h.domain, h.number))
    return hits
