"""Reconciliación de un anticipo contractual registrado por duplicado
(ORDEN MAESTRA DE CIERRE §4-§12).

Caso: la salida de caja del anticipo se registró como `GeneralExpense`
(Debit gasto / Credit Tesorería) Y, además, se creó una `SupplierInvoice`
por el mismo hecho (Debit gasto / Credit CxP). Resultado: costo GL duplicado
y una obligación AP fantasma.

Corrección formal, sin borrar ni mutar documentos POSTED:

1. Se revierte el accrual de la factura duplicada (Posting Engine) → la
   factura queda CANCELLED; CxP y su gasto vuelven a cero.
2. Se contabiliza un asiento de RECLASIFICACIÓN enlazado al GeneralExpense:
   Debit(cuenta ASSET de anticipos) / Credit(cuenta de gasto original). Neto
   con el GeneralExpense original: Debit ASSET / Credit Tesorería. La caja no
   se toca — la salida real de L50k queda una sola vez.
3. Se crea la `ContractPaymentAllocation` de la cuota ADVANCE (fuente:
   GeneralExpense), de modo que el anticipo queda pagado y el saldo
   contractual baja.
4. AuditLog por cada paso humano.
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.errors import InvalidFinancialReferenceError
from app.models.accounting import (
    LEDGER_EFFECTIVE_STATUSES,
    AccountingDocument,
    AccountingSourceLink,
    JournalLine,
)
from app.models.ap import SupplierInvoice
from app.models.chart_of_accounts import Account, ChartOfAccount
from app.models.company import Company
from app.models.contract_payment import (
    ContractPaymentAllocation,
    ContractPaymentInstallment,
    ContractPaymentSchedule,
)
from app.models.supplier import SupplierContract
from app.models.treasury import GeneralExpense
from app.services import audit_service, posting_service
from app.services import contract_payment_service as cps
from app.services.financial_validation_service import (
    assert_supplier_advance_account_eligible,
)
from app.services.posting_service import JournalLineInput

_ZERO = Decimal("0.00")


def _q(v) -> Decimal:
    return Decimal(str(v)).quantize(Decimal("0.01"))


def _account_gl_total(db: Session, *, account_id: uuid.UUID, project_id: uuid.UUID | None) -> Decimal:
    """Saldo neto (debit − credit) POSTED/REVERSED de una cuenta, opcionalmente
    acotado a un proyecto."""
    stmt = (
        select(func.coalesce(func.sum(JournalLine.debit_amount - JournalLine.credit_amount), 0))
        .join(AccountingDocument, AccountingDocument.id == JournalLine.accounting_document_id)
        .where(
            JournalLine.account_id == account_id,
            AccountingDocument.status.in_(LEDGER_EFFECTIVE_STATUSES),
        )
    )
    if project_id is not None:
        stmt = stmt.where(JournalLine.project_id == project_id)
    return _q(db.execute(stmt).scalar_one())


def _snapshot(
    db: Session,
    *,
    gge: GeneralExpense,
    invoice: SupplierInvoice,
    schedule_id: uuid.UUID,
    advance_installment_id: uuid.UUID,
) -> dict:
    gge_expense = _account_gl_total(
        db, account_id=gge.expense_account_id, project_id=invoice.project_id
    )
    inv_expense = _account_gl_total(
        db, account_id=invoice.expense_account_id, project_id=invoice.project_id
    )
    inv = db.get(SupplierInvoice, invoice.id)
    paid_map = cps.installment_summaries(db, schedule_id=schedule_id)
    adv = next(s for s in paid_map if s.installment_id == advance_installment_id)
    return {
        "generalExpenseId": str(gge.id),
        "generalExpenseExpenseAccountBalance": str(gge_expense),
        "invoiceId": str(invoice.id),
        "invoiceNumber": invoice.invoice_number,
        "invoiceStatus": inv.status if inv else None,
        "invoiceExpenseAccountBalance": str(inv_expense),
        "invoiceAmountPaid": str(inv.amount_paid) if inv else None,
        "advanceInstallmentPaid": str(adv.paid),
        "advanceInstallmentRemaining": str(adv.remaining),
        "contractPaidAccumulated": str(sum((s.paid for s in paid_map), _ZERO)),
    }


def reconcile_duplicated_advance(
    db: Session,
    *,
    general_expense_id: uuid.UUID,
    supplier_invoice_id: uuid.UUID,
    contract_number: str,
    advance_account_id: uuid.UUID | None = None,
    advance_account_code: str | None = None,
    actor_user_id: uuid.UUID | None = None,
    reason: str,
    correlation_id: str,
    commit: bool = False,
) -> dict:
    gge = db.get(GeneralExpense, general_expense_id)
    if gge is None:
        raise InvalidFinancialReferenceError(f"GeneralExpense {general_expense_id} no existe")
    gge_doc = db.get(AccountingDocument, gge.accounting_document_id)
    if gge_doc is None or gge_doc.status not in LEDGER_EFFECTIVE_STATUSES:
        raise InvalidFinancialReferenceError("El GeneralExpense no tiene un asiento POSTED válido")

    invoice = db.get(SupplierInvoice, supplier_invoice_id)
    if invoice is None:
        raise InvalidFinancialReferenceError(f"SupplierInvoice {supplier_invoice_id} no existe")
    if invoice.company_id != gge.company_id:
        raise InvalidFinancialReferenceError("La factura y el gasto son de compañías distintas")
    if invoice.status != "APPROVED":
        raise InvalidFinancialReferenceError(
            f"Solo se reconcilia una factura APPROVED (estado actual: {invoice.status})"
        )
    if invoice.amount_paid and Decimal(invoice.amount_paid) > 0:
        raise InvalidFinancialReferenceError("La factura duplicada ya tiene pagos; requiere revisión")
    if invoice.accrual_document_id is None:
        raise InvalidFinancialReferenceError("La factura no tiene accrual contabilizado que revertir")

    amount = _q(gge.amount)
    if _q(invoice.amount + invoice.tax_amount) != amount:
        raise InvalidFinancialReferenceError(
            f"Los importes no coinciden: gasto {amount} vs factura {invoice.amount + invoice.tax_amount}"
        )

    contract = db.execute(
        select(SupplierContract).where(
            SupplierContract.company_id == gge.company_id,
            SupplierContract.contract_number == contract_number,
        )
    ).scalar_one_or_none()
    if contract is None:
        raise InvalidFinancialReferenceError(f"No existe el contrato {contract_number}")
    if invoice.supplier_contract_id not in (None, contract.id):
        raise InvalidFinancialReferenceError("La factura pertenece a otro contrato")
    schedule = db.execute(
        select(ContractPaymentSchedule).where(
            ContractPaymentSchedule.supplier_contract_id == contract.id
        )
    ).scalar_one_or_none()
    if schedule is None:
        raise InvalidFinancialReferenceError("El contrato no tiene plan de pagos")
    advance_inst = db.execute(
        select(ContractPaymentInstallment).where(
            ContractPaymentInstallment.schedule_id == schedule.id,
            ContractPaymentInstallment.installment_kind == "ADVANCE",
        )
    ).scalar_one_or_none()
    if advance_inst is None:
        raise InvalidFinancialReferenceError(
            "El plan del contrato no tiene una cuota ADVANCE; corrige el plan primero"
        )
    if _q(advance_inst.scheduled_amount) != amount:
        raise InvalidFinancialReferenceError(
            f"La cuota ADVANCE es {advance_inst.scheduled_amount}, no {amount}"
        )
    existing_alloc = db.execute(
        select(ContractPaymentAllocation.id).where(
            ContractPaymentAllocation.installment_id == advance_inst.id,
            ContractPaymentAllocation.reversed_at.is_(None),
        )
    ).first()
    if existing_alloc is not None:
        raise InvalidFinancialReferenceError("La cuota ADVANCE ya tiene una asignación activa")

    # --- cuenta ASSET de anticipos ---
    company = db.get(Company, gge.company_id)
    resolved_advance_account_id = advance_account_id or company.supplier_advance_account_id
    if resolved_advance_account_id is None and advance_account_code:
        resolved_advance_account_id = db.execute(
            select(Account.id)
            .join(ChartOfAccount, ChartOfAccount.id == Account.chart_of_account_id)
            .where(
                ChartOfAccount.company_id == company.id,
                Account.code == advance_account_code.strip(),
            )
        ).scalar_one_or_none()
        if resolved_advance_account_id is None:
            raise InvalidFinancialReferenceError(
                f"No existe una cuenta con código {advance_account_code!r} en la compañía"
            )
    if resolved_advance_account_id is None:
        raise InvalidFinancialReferenceError(
            "No hay cuenta ASSET de anticipos configurada (company.supplier_advance_account_id) "
            "ni se indicó advance_account_code"
        )
    advance_account = assert_supplier_advance_account_eligible(
        db, account_id=resolved_advance_account_id, company_id=company.id
    )
    if company.supplier_advance_account_id is None:
        company.supplier_advance_account_id = advance_account.id

    before = _snapshot(
        db, gge=gge, invoice=invoice, schedule_id=schedule.id, advance_installment_id=advance_inst.id
    )

    # 1) Revertir el accrual de la factura duplicada (hook pone la factura CANCELLED).
    invoice_reversal = posting_service.reverse_document(
        db,
        document_id=invoice.accrual_document_id,
        reason=(
            f"Registro duplicado del anticipo contractual {contract_number}; "
            "operación reconciliada con la salida de Tesorería existente."
        ),
        commit=False,
    )
    # Defensa: el hook de reversión "supplier_invoice" (que pone la factura
    # CANCELLED) sólo está registrado si el proceso importó `app.main` o
    # `app.services.reversal_hooks`. Forzamos la transición de forma idempotente
    # para no dejar la factura APPROVED apuntando a un accrual REVERSED
    # (pagable de nuevo pese a que el GL ya no refleja el gasto).
    db.flush()
    db.refresh(invoice)
    if invoice.status != "CANCELLED":
        invoice.status = "CANCELLED"

    audit_service.record(
        db,
        actor_user_id=actor_user_id,
        action="ap.supplier_invoice.reverse.duplicate_advance",
        entity_type="ap.supplier_invoice",
        entity_id=invoice.id,
        company_id=company.id,
        project_id=invoice.project_id,
        before={"status": "APPROVED"},
        after={"status": "CANCELLED", "reversalDocumentId": str(invoice_reversal.id), "reason": reason},
        correlation_id=correlation_id,
    )

    # 2) Reclasificación: Debit(ASSET anticipos) / Credit(cuenta de gasto del GeneralExpense).
    reclass = posting_service.post_manual(
        db,
        company_id=company.id,
        document_type_code="JRN",
        scope=gge_doc.scope,
        project_id=gge_doc.project_id,
        currency_code=gge_doc.currency_code,
        effective_date=gge_doc.effective_date,
        lines=[
            JournalLineInput(
                account_id=advance_account.id,
                debit_amount=amount,
                project_id=gge_doc.project_id,
                description=(
                    f"Reclasificación del anticipo contractual {contract_number} "
                    f"(gasto {gge_doc.document_number}) a anticipos a proveedores/contratistas"
                ),
            ),
            JournalLineInput(
                account_id=gge.expense_account_id,
                credit_amount=amount,
                project_id=gge_doc.project_id,
                description=(
                    f"Reversión de la clasificación como gasto del anticipo {contract_number} "
                    f"({gge_doc.document_number})"
                ),
            ),
        ],
        description=(
            f"Reclasificación contable del anticipo contractual {contract_number}: "
            f"{gge_doc.document_number} deja de reconocer costo y pasa a activo (anticipo)."
        ),
        source_type="advance_reclassification",
        source_id=gge.id,
        commit=False,
    )
    db.add(
        AccountingSourceLink(
            accounting_document_id=reclass.id,
            source_type="general_expense",
            source_id=gge.id,
        )
    )
    audit_service.record(
        db,
        actor_user_id=actor_user_id,
        action="accounting.advance.reclassify",
        entity_type="treasury.general_expense",
        entity_id=gge.id,
        company_id=company.id,
        project_id=gge_doc.project_id,
        before={"debitAccount": str(gge.expense_account_id)},
        after={
            "reclassDocumentId": str(reclass.id),
            "advanceAssetAccountId": str(advance_account.id),
            "amount": str(amount),
            "reason": reason,
        },
        correlation_id=correlation_id,
    )

    # 3) Asignación de la cuota ADVANCE con fuente GeneralExpense.
    alloc = ContractPaymentAllocation(
        supplier_payment_id=None,
        general_expense_id=gge.id,
        installment_id=advance_inst.id,
        amount_applied=amount,
        applied_at=datetime.now(timezone.utc),
        override_reason=(
            f"Anticipo pagado vía {gge_doc.document_number} (GeneralExpense) y conciliado "
            f"con el contrato {contract_number}. {reason}"
        ),
    )
    db.add(alloc)
    db.flush()
    audit_service.record(
        db,
        actor_user_id=actor_user_id,
        action="contract.advance.reconcile_allocation",
        entity_type="contract.payment_schedule",
        entity_id=schedule.id,
        company_id=company.id,
        project_id=schedule.project_id,
        before={"advancePaid": before["advanceInstallmentPaid"]},
        after={
            "allocationId": str(alloc.id),
            "installmentId": str(advance_inst.id),
            "amount": str(amount),
            "source": "general_expense",
            "generalExpenseId": str(gge.id),
            "reason": reason,
        },
        correlation_id=correlation_id,
    )

    db.flush()
    db.expire_all()
    after = _snapshot(
        db, gge=gge, invoice=invoice, schedule_id=schedule.id, advance_installment_id=advance_inst.id
    )

    if commit:
        db.commit()

    return {
        "contractNumber": contract_number,
        "amount": str(amount),
        "invoiceReversalDocumentId": str(invoice_reversal.id),
        "reclassificationDocumentId": str(reclass.id),
        "allocationId": str(alloc.id),
        "before": before,
        "after": after,
    }
