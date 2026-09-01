"""Flujo de Caja REAL — últimas 13 semanas (ORDEN MAESTRA — FIORI / CASH
FLOW / TREASURY DIRECTION, §4, §12-§14).

Distinto del *forecast* (`cash_forecast_service`, que proyecta AP/AR futuros
por fecha de vencimiento): esto es lo que YA OCURRIÓ. La fuente autoritativa
es el movimiento real de las cuentas GL 1:1 con un `TreasuryAccount`
(CLAUDE.md §7). Para cada documento contabilizado que tocó tesorería en la
ventana:

    doc_net = Σ debit − Σ credit  sobre sus líneas de tesorería

`doc_net > 0` es una ENTRADA real, `doc_net < 0` una SALIDA real. Una
transferencia interna tiene `doc_net == 0` (ambas patas en el mismo asiento)
y por eso no aparece — sin doble conteo (§12): se lee la línea del asiento,
nunca la tabla `Remittance.amount` en paralelo.

Un aporte de capital o un financiamiento **es** una entrada de caja pero
**no** es ingreso (§13): aquí solo medimos caja, la contabilidad de devengo
(P&L) no se toca.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.business_time import business_today
from app.models.accounting import AccountingDocument, JournalLine
from app.models.chart_of_accounts import Account
from app.models.treasury import TreasuryAccount
from app.services import treasury_service
from app.services.transaction_inspector_service import _resolve_source_event

_WEEKS = 13
_ZERO = Decimal("0.00")
_LEDGER_STATUSES = ("POSTED", "REVERSED")

# Categorías estables (orden = orden de presentación).
INFLOW_CATEGORIES = (
    "Cobros de clientes",
    "Aportes de capital",
    "Financiamiento recibido",
    "Remesas",
    "Otros ingresos",
)
OUTFLOW_CATEGORIES = (
    "Pagos a proveedores",
    "Pagos de contratos",
    "Gastos pagados",
    "Pagos de activos",
    "Otros egresos",
)


@dataclass
class ActualWeek:
    week_index: int
    week_start: date
    week_end: date
    inflows: Decimal = _ZERO
    outflows: Decimal = _ZERO
    net: Decimal = _ZERO
    closing_balance: Decimal = _ZERO
    by_category: dict[str, Decimal] = field(default_factory=dict)


@dataclass
class CashFlowActual:
    as_of: date
    currency_code: str
    opening_balance: Decimal
    closing_balance: Decimal
    total_inflows: Decimal
    total_outflows: Decimal
    inflow_by_category: dict[str, Decimal]
    outflow_by_category: dict[str, Decimal]
    weeks: list[ActualWeek] = field(default_factory=list)


def _q(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal("0.01"))


def _week_start(anchor: date) -> date:
    """Lunes de la semana que contiene `anchor`."""
    return anchor - timedelta(days=anchor.weekday())


def _categorize(db: Session, document: AccountingDocument, net: Decimal, counter_accounts: list[Account]) -> str:
    source = _resolve_source_event(db, document.id)
    kind = source.kind

    if net > _ZERO:  # entrada
        if kind == "CUSTOMER_RECEIPT":
            return "Cobros de clientes"
        # La naturaleza de la contrapartida define el origen del efectivo:
        # EQUITY = aporte de socios, LIABILITY = financiamiento (préstamo),
        # REVENUE = otro ingreso operativo. (Un `Remittance` no persiste su
        # `origin_type`, pero sí la cuenta de contrapartida exigida por él.)
        types = {a.account_type for a in counter_accounts}
        if "EQUITY" in types:
            return "Aportes de capital"
        if "LIABILITY" in types or any(
            (a.cash_flow_activity or "").upper() == "FINANCING" for a in counter_accounts
        ):
            return "Financiamiento recibido"
        if kind == "REMITTANCE" and "REVENUE" not in types:
            return "Remesas"
        return "Otros ingresos"

    # salida
    if kind == "SUPPLIER_PAYMENT":
        if _has_contract_allocation(db, document):
            return "Pagos de contratos"
        return "Pagos a proveedores"
    if kind == "GENERAL_EXPENSE":
        return "Gastos pagados"
    for account in counter_accounts:
        if account.account_type == "ASSET":
            return "Pagos de activos"
    return "Otros egresos"


def _has_contract_allocation(db: Session, document: AccountingDocument) -> bool:
    from app.models.ap import SupplierPayment
    from app.models.contract_payment import ContractPaymentAllocation

    payment = db.execute(
        select(SupplierPayment).where(SupplierPayment.accounting_document_id == document.id)
    ).scalars().first()
    if payment is None:
        return False
    return db.execute(
        select(ContractPaymentAllocation.id).where(
            ContractPaymentAllocation.supplier_payment_id == payment.id,
            ContractPaymentAllocation.reversed_at.is_(None),
        )
    ).first() is not None


def actual(db: Session, *, company_id: uuid.UUID, as_of: date | None = None) -> CashFlowActual:
    as_of = as_of or business_today()
    accounts = db.execute(
        select(TreasuryAccount).where(TreasuryAccount.company_id == company_id)
    ).scalars().all()
    currency = accounts[0].currency_code if accounts else "HNL"
    cash_gl_ids = {a.gl_account_id for a in accounts}

    current_week_start = _week_start(as_of)
    window_start = current_week_start - timedelta(days=(_WEEKS - 1) * 7)
    window_end = current_week_start + timedelta(days=6)

    closing_balance = _q(
        sum((treasury_service.treasury_account_balance(db, a) for a in accounts), Decimal("0"))
    )

    result = CashFlowActual(
        as_of=as_of,
        currency_code=currency,
        opening_balance=_ZERO,
        closing_balance=closing_balance,
        total_inflows=_ZERO,
        total_outflows=_ZERO,
        inflow_by_category={c: _ZERO for c in INFLOW_CATEGORIES},
        outflow_by_category={c: _ZERO for c in OUTFLOW_CATEGORIES},
    )
    weeks = [
        ActualWeek(
            week_index=i,
            week_start=window_start + timedelta(days=i * 7),
            week_end=window_start + timedelta(days=i * 7 + 6),
        )
        for i in range(_WEEKS)
    ]

    if not cash_gl_ids:
        result.weeks = weeks
        return result

    # Todas las líneas de tesorería de documentos POSTED en la ventana.
    rows = db.execute(
        select(
            JournalLine.accounting_document_id,
            JournalLine.account_id,
            JournalLine.debit_amount,
            JournalLine.credit_amount,
            AccountingDocument.posted_at,
        )
        .join(AccountingDocument, AccountingDocument.id == JournalLine.accounting_document_id)
        .where(
            AccountingDocument.company_id == company_id,
            AccountingDocument.status.in_(_LEDGER_STATUSES),
            AccountingDocument.posted_at.is_not(None),
            JournalLine.account_id.in_(cash_gl_ids),
        )
    ).all()

    per_doc: dict[uuid.UUID, list] = {}
    for doc_id, _account_id, debit, credit, posted_at in rows:
        entry = per_doc.setdefault(doc_id, [_ZERO, None])
        entry[0] += Decimal(str(debit)) - Decimal(str(credit))
        entry[1] = posted_at.date() if posted_at else None

    # El saldo de apertura de la ventana = saldo actual − todo lo que se
    # movió DENTRO (y después) de la ventana. Lo anterior ya está incluido.
    net_in_window = _ZERO
    net_after_window = _ZERO
    for doc_id, (raw_net, posted_date) in per_doc.items():
        net = _q(raw_net)
        if net == _ZERO or posted_date is None or posted_date < window_start:
            continue
        if posted_date > window_end:
            net_after_window += net
            continue

        document = db.get(AccountingDocument, doc_id)
        counter_accounts = _counter_accounts(db, doc_id, cash_gl_ids)
        category = _categorize(db, document, net, counter_accounts)

        week_index = min((posted_date - window_start).days // 7, _WEEKS - 1)
        week = weeks[week_index]
        week.by_category[category] = week.by_category.get(category, _ZERO) + net
        net_in_window += net

        if net > _ZERO:
            week.inflows += net
            result.inflow_by_category[category] = result.inflow_by_category.get(category, _ZERO) + net
        else:
            week.outflows += -net
            result.outflow_by_category[category] = result.outflow_by_category.get(category, _ZERO) + (-net)

    running = _q(closing_balance - net_in_window - net_after_window)
    result.opening_balance = running
    for week in weeks:
        week.inflows = _q(week.inflows)
        week.outflows = _q(week.outflows)
        week.net = _q(week.inflows - week.outflows)
        running += week.net
        week.closing_balance = _q(running)
        week.by_category = {k: _q(v) for k, v in week.by_category.items() if v != _ZERO}

    result.weeks = weeks
    result.total_inflows = _q(sum(result.inflow_by_category.values(), Decimal("0")))
    result.total_outflows = _q(sum(result.outflow_by_category.values(), Decimal("0")))
    result.inflow_by_category = {k: _q(v) for k, v in result.inflow_by_category.items()}
    result.outflow_by_category = {k: _q(v) for k, v in result.outflow_by_category.items()}
    return result


def _counter_accounts(db: Session, document_id: uuid.UUID, cash_gl_ids: set[uuid.UUID]) -> list[Account]:
    account_ids = set(
        db.execute(
            select(JournalLine.account_id).where(
                JournalLine.accounting_document_id == document_id,
                JournalLine.account_id.not_in(cash_gl_ids),
            )
        ).scalars()
    )
    if not account_ids:
        return []
    return list(
        db.execute(select(Account).where(Account.id.in_(account_ids))).scalars()
    )
