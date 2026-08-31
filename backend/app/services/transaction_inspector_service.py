"""Transaction Inspector (orden maestra FINAL, Phase 5). Dado un
`AccountingDocument`, reconstruye la foto completa: sus líneas con nombre de
cuenta, el **evento de negocio** que lo originó (drill-down inverso: del
asiento del GL al documento fuente), la cadena de reversos y la evidencia
adjunta. No muta nada; solo lee.
"""

from dataclasses import dataclass, field
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.accounting import AccountingDocument, JournalLine
from app.models.ap import SupplierInvoice, SupplierPayment
from app.models.ar import CustomerInvoice, CustomerReceipt
from app.models.chart_of_accounts import Account
from app.models.cost_center import CostCenter
from app.models.evidence import Evidence
from app.models.project import Project
from app.models.treasury import GeneralExpense, Remittance, TreasuryTransfer


@dataclass(frozen=True)
class InspectedLine:
    account_code: str
    account_name: str
    debit: Decimal
    credit: Decimal
    description: str | None
    project_name: str | None
    cost_center_name: str | None


@dataclass(frozen=True)
class SourceEvent:
    kind: str  # REMITTANCE | SUPPLIER_INVOICE_ACCRUAL | SUPPLIER_PAYMENT | ...
    label: str
    reference: str | None
    entity_id: str | None


@dataclass
class InspectionResult:
    document_id: str
    document_number: str
    document_type_code: str
    scope: str
    status: str
    currency_code: str
    description: str | None
    project_name: str | None
    posted_at: str | None
    total_debit: Decimal
    total_credit: Decimal
    balanced: bool
    source_event: SourceEvent
    lines: list[InspectedLine] = field(default_factory=list)
    reverses_document_id: str | None = None
    reversal_reason: str | None = None
    reversed_by_document_ids: list[str] = field(default_factory=list)
    evidence: list[dict] = field(default_factory=list)


def _resolve_source_event(db: Session, document_id) -> SourceEvent:
    remittance = db.execute(
        select(Remittance).where(Remittance.accounting_document_id == document_id)
    ).scalars().first()
    if remittance is not None:
        return SourceEvent("REMITTANCE", "Remesa recibida", remittance.sender, str(remittance.id))

    accrual = db.execute(
        select(SupplierInvoice).where(SupplierInvoice.accrual_document_id == document_id)
    ).scalars().first()
    if accrual is not None:
        return SourceEvent(
            "SUPPLIER_INVOICE_ACCRUAL",
            "Devengo de factura de proveedor",
            accrual.invoice_number,
            str(accrual.id),
        )

    payment = db.execute(
        select(SupplierPayment).where(SupplierPayment.accounting_document_id == document_id)
    ).scalars().first()
    if payment is not None:
        invoice = db.get(SupplierInvoice, payment.supplier_invoice_id)
        return SourceEvent(
            "SUPPLIER_PAYMENT",
            "Pago a proveedor",
            invoice.invoice_number if invoice else None,
            str(payment.id),
        )

    ci = db.execute(
        select(CustomerInvoice).where(CustomerInvoice.accounting_document_id == document_id)
    ).scalars().first()
    if ci is not None:
        return SourceEvent(
            "CUSTOMER_INVOICE", "Factura de cliente", ci.invoice_number, str(ci.id)
        )

    receipt = db.execute(
        select(CustomerReceipt).where(CustomerReceipt.accounting_document_id == document_id)
    ).scalars().first()
    if receipt is not None:
        inv = db.get(CustomerInvoice, receipt.customer_invoice_id)
        return SourceEvent(
            "CUSTOMER_RECEIPT",
            "Cobro de cliente",
            inv.invoice_number if inv else None,
            str(receipt.id),
        )

    expense = db.execute(
        select(GeneralExpense).where(GeneralExpense.accounting_document_id == document_id)
    ).scalars().first()
    if expense is not None:
        return SourceEvent("GENERAL_EXPENSE", "Gasto general", expense.category, str(expense.id))

    transfer = db.execute(
        select(TreasuryTransfer).where(TreasuryTransfer.accounting_document_id == document_id)
    ).scalars().first()
    if transfer is not None:
        return SourceEvent("TREASURY_TRANSFER", "Transferencia de tesorería", None, str(transfer.id))

    return SourceEvent("MANUAL_JOURNAL", "Asiento manual", None, None)


def inspect(db: Session, *, document_id) -> InspectionResult | None:
    document = db.get(AccountingDocument, document_id)
    if document is None:
        return None

    raw_lines = db.execute(
        select(JournalLine).where(JournalLine.accounting_document_id == document.id)
    ).scalars().all()

    account_ids = {line.account_id for line in raw_lines}
    accounts = {
        account.id: account
        for account in db.execute(select(Account).where(Account.id.in_(account_ids))).scalars()
    }
    project_ids = {line.project_id for line in raw_lines if line.project_id}
    if document.project_id:
        project_ids.add(document.project_id)
    projects = {
        p.id: p for p in db.execute(select(Project).where(Project.id.in_(project_ids))).scalars()
    } if project_ids else {}
    cc_ids = {line.cost_center_id for line in raw_lines if line.cost_center_id}
    cost_centers = {
        c.id: c for c in db.execute(select(CostCenter).where(CostCenter.id.in_(cc_ids))).scalars()
    } if cc_ids else {}

    lines: list[InspectedLine] = []
    total_debit = Decimal("0")
    total_credit = Decimal("0")
    for line in raw_lines:
        total_debit += line.debit_amount
        total_credit += line.credit_amount
        account = accounts.get(line.account_id)
        lines.append(
            InspectedLine(
                account_code=account.code if account else "?",
                account_name=account.name if account else "Cuenta no encontrada",
                debit=line.debit_amount,
                credit=line.credit_amount,
                description=line.description,
                project_name=projects[line.project_id].name if line.project_id in projects else None,
                cost_center_name=(
                    cost_centers[line.cost_center_id].name
                    if line.cost_center_id in cost_centers
                    else None
                ),
            )
        )

    # posting_service: al revertir, el ORIGINAL guarda `reversed_document_id`
    # (apunta a su anulación) y su `reversal_reason`.
    #  - si este documento es una anulación -> "reverses" = el original que lo
    #    tiene apuntado.
    #  - si este documento fue anulado -> "reversed_by" = su
    #    `reversed_document_id`.
    reverses_original = db.execute(
        select(AccountingDocument).where(
            AccountingDocument.reversed_document_id == document.id
        )
    ).scalars().first()
    reversed_by = (
        [document.reversed_document_id] if document.reversed_document_id else []
    )

    evidence_rows = db.execute(
        select(Evidence).where(
            Evidence.entity_id == document.id,
        )
    ).scalars().all()
    evidence = [
        {
            "id": str(e.id),
            "originalFilename": e.original_filename,
            "mimeType": e.mime_type,
            "sizeBytes": e.size_bytes,
        }
        for e in evidence_rows
        if (e.entity_type or "").upper() in {"ACCOUNTING_DOCUMENT", "PAYMENT_DOCUMENT", "VOUCHER"}
    ]

    return InspectionResult(
        document_id=str(document.id),
        document_number=document.document_number,
        document_type_code=document.document_type_code,
        scope=document.scope,
        status=document.status,
        currency_code=document.currency_code,
        description=document.description,
        project_name=projects[document.project_id].name if document.project_id in projects else None,
        posted_at=document.posted_at.isoformat() if document.posted_at else None,
        total_debit=total_debit,
        total_credit=total_credit,
        balanced=total_debit == total_credit,
        source_event=_resolve_source_event(db, document.id),
        lines=lines,
        reverses_document_id=str(reverses_original.id) if reverses_original is not None else None,
        reversal_reason=(
            reverses_original.reversal_reason if reverses_original is not None
            else document.reversal_reason
        ),
        reversed_by_document_ids=[str(r) for r in reversed_by],
        evidence=evidence,
    )
