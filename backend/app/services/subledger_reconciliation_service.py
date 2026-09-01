"""Subledger <-> General Ledger reconciliation (orden maestra FINAL, Phase 4).

"El General Ledger es la verdad contable" (CLAUDE.md §8): cada subledger
(AP, AR, Tesorería) debe cuadrar contra el saldo de su(s) cuenta(s) de
control en el GL. Un trial balance que cuadra NO es suficiente — puede
cuadrar y aun así tener el subledger de AP descuadrado contra su cuenta de
pasivo. Este servicio expone esa comparación explícitamente.
"""

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.ap import SupplierInvoice, SupplierPayment
from app.models.ar import CustomerInvoice
from app.models.contract_payment import (
    ContractPaymentAllocation,
    ContractPaymentInstallment,
    ContractPaymentSchedule,
)
from app.models.treasury import TreasuryAccount
from app.services import treasury_service

_AP_OPEN = ("APPROVED", "SCHEDULED", "PARTIALLY_PAID")
_AR_OPEN = ("APPROVED", "PARTIALLY_COLLECTED")


@dataclass(frozen=True)
class ReconciliationLine:
    subledger: str
    subledger_total: Decimal
    gl_total: Decimal
    difference: Decimal
    reconciled: bool
    detail: str


def _ap(db: Session, company_id) -> ReconciliationLine:
    rows = db.execute(
        select(
            SupplierInvoice.payable_account_id,
            SupplierInvoice.amount,
            SupplierInvoice.tax_amount,
            SupplierInvoice.amount_paid,
            SupplierInvoice.status,
        ).where(SupplierInvoice.company_id == company_id)
    ).all()
    subledger_total = Decimal("0")
    control_accounts: set = set()
    for payable_account_id, amount, tax_amount, amount_paid, invoice_status in rows:
        control_accounts.add(payable_account_id)
        if invoice_status in _AP_OPEN:
            remaining = (amount + tax_amount) - amount_paid
            if remaining > 0:
                subledger_total += remaining
    # Cuenta de control de pasivo: saldo acreedor = credit - debit.
    gl_total = Decimal("0")
    for account_id in control_accounts:
        gl_total += -treasury_service.account_balance(db, gl_account_id=account_id)
    difference = subledger_total - gl_total
    return ReconciliationLine(
        subledger="ACCOUNTS_PAYABLE",
        subledger_total=subledger_total,
        gl_total=gl_total,
        difference=difference,
        reconciled=difference == Decimal("0"),
        detail="Saldo pendiente de facturas de proveedor abiertas vs. saldo acreedor de la(s) cuenta(s) de pasivo de control.",
    )


def _ar(db: Session, company_id) -> ReconciliationLine:
    rows = db.execute(
        select(
            CustomerInvoice.receivable_account_id,
            CustomerInvoice.amount,
            CustomerInvoice.amount_collected,
            CustomerInvoice.status,
        ).where(CustomerInvoice.company_id == company_id)
    ).all()
    subledger_total = Decimal("0")
    control_accounts: set = set()
    for receivable_account_id, amount, amount_collected, invoice_status in rows:
        control_accounts.add(receivable_account_id)
        if invoice_status in _AR_OPEN:
            remaining = amount - amount_collected
            if remaining > 0:
                subledger_total += remaining
    gl_total = Decimal("0")
    for account_id in control_accounts:
        gl_total += treasury_service.account_balance(db, gl_account_id=account_id)
    difference = subledger_total - gl_total
    return ReconciliationLine(
        subledger="ACCOUNTS_RECEIVABLE",
        subledger_total=subledger_total,
        gl_total=gl_total,
        difference=difference,
        reconciled=difference == Decimal("0"),
        detail="Saldo por cobrar de facturas de cliente abiertas vs. saldo deudor de la(s) cuenta(s) por cobrar de control.",
    )


def _treasury(db: Session, company_id) -> ReconciliationLine:
    accounts = db.execute(
        select(TreasuryAccount).where(TreasuryAccount.company_id == company_id)
    ).scalars().all()
    subledger_total = sum(
        (treasury_service.treasury_account_balance(db, account) for account in accounts),
        Decimal("0"),
    )
    gl_total = sum(
        (treasury_service.account_balance(db, gl_account_id=account.gl_account_id) for account in accounts),
        Decimal("0"),
    )
    difference = subledger_total - gl_total
    return ReconciliationLine(
        subledger="TREASURY",
        subledger_total=subledger_total,
        gl_total=gl_total,
        difference=difference,
        reconciled=difference == Decimal("0"),
        detail="Saldo consolidado de cuentas de Tesorería vs. saldo de sus cuentas GL asociadas.",
    )


def _contract(db: Session, company_id) -> ReconciliationLine:
    """Subledger contractual: total asignado a cuotas (allocations no
    reversadas) vs. total de pagos a proveedor sobre facturas con contrato
    (§47). Deben cuadrar — `allocate_payment` exige que la suma asignada
    iguale el importe del pago; una diferencia revela pagos contractuales sin
    asignar a una cuota."""
    subledger_total = db.execute(
        select(func.coalesce(func.sum(ContractPaymentAllocation.amount_applied), 0))
        .join(
            ContractPaymentInstallment,
            ContractPaymentInstallment.id == ContractPaymentAllocation.installment_id,
        )
        .join(
            ContractPaymentSchedule,
            ContractPaymentSchedule.id == ContractPaymentInstallment.schedule_id,
        )
        .where(
            ContractPaymentSchedule.company_id == company_id,
            ContractPaymentAllocation.reversed_at.is_(None),
        )
    ).scalar_one()

    gl_total = db.execute(
        select(func.coalesce(func.sum(SupplierPayment.amount), 0))
        .join(SupplierInvoice, SupplierInvoice.id == SupplierPayment.supplier_invoice_id)
        .where(
            SupplierInvoice.company_id == company_id,
            SupplierInvoice.supplier_contract_id.is_not(None),
            SupplierPayment.reversed_at.is_(None),
        )
    ).scalar_one()

    subledger_total = Decimal(str(subledger_total))
    gl_total = Decimal(str(gl_total))
    difference = subledger_total - gl_total
    return ReconciliationLine(
        subledger="CONTRACT_PAYMENTS",
        subledger_total=subledger_total,
        gl_total=gl_total,
        difference=difference,
        reconciled=difference == Decimal("0"),
        detail="Total asignado a cuotas contractuales vs. total de pagos no reversados sobre facturas con contrato.",
    )


def reconcile(db: Session, *, company_id) -> list[ReconciliationLine]:
    return [
        _treasury(db, company_id),
        _ap(db, company_id),
        _ar(db, company_id),
        _contract(db, company_id),
    ]
