"""Flujo de Caja REAL — rango de fechas + granularidad (ORDEN MAESTRA §10/§11).

Lo que YA OCURRIÓ, distinto del *forecast* (`cash_forecast_service`). Fuente
autoritativa: el movimiento real de las cuentas GL 1:1 con un
`TreasuryAccount` (CLAUDE.md §7). Para cada documento contabilizado que tocó
tesorería:

    doc_net = Σ debit − Σ credit  sobre sus líneas de tesorería

`doc_net > 0` es una ENTRADA real, `doc_net < 0` una SALIDA real. Una
transferencia interna tiene `doc_net == 0` y por eso no aparece — sin doble
conteo (§12). Se agrupa por la fecha ECONÓMICA (`effective_date`), no por el
timestamp técnico `posted_at` (§9/§26).

La UX NO obliga a interpretar S1..S13 (§10): se elige un rango real
(1M/3M/6M/12M/personalizado) y una granularidad (Auto/Día/Semana/Mes) con
etiquetas de calendario reales.
"""

from __future__ import annotations

import calendar
import uuid
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.business_time import business_today
from app.models.accounting import AccountingDocument, JournalLine
from app.models.chart_of_accounts import Account
from app.models.treasury import TreasuryAccount
from app.services import treasury_service
from app.services.transaction_inspector_service import _resolve_source_event

_ZERO = Decimal("0.00")
_LEDGER_STATUSES = ("POSTED", "REVERSED")

GRANULARITIES = ("day", "week", "month")

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

_MONTHS_ES = [
    "", "ene", "feb", "mar", "abr", "may", "jun",
    "jul", "ago", "sep", "oct", "nov", "dic",
]
_MONTHS_ES_FULL = [
    "", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
]


@dataclass
class CashFlowPeriod:
    index: int
    period_start: date
    period_end: date
    label: str
    inflows: Decimal = _ZERO
    outflows: Decimal = _ZERO
    net: Decimal = _ZERO
    closing_balance: Decimal = _ZERO
    movement_count: int = 0
    by_category: dict[str, Decimal] = field(default_factory=dict)


@dataclass
class CashFlowMovement:
    document_id: uuid.UUID
    document_number: str
    effective_date: date
    direction: str  # INFLOW | OUTFLOW
    category: str
    amount: Decimal
    concept: str | None
    counterparty: str | None


@dataclass
class CashFlowActual:
    date_from: date
    date_to: date
    granularity: str
    currency_code: str
    opening_balance: Decimal
    closing_balance: Decimal
    total_inflows: Decimal
    total_outflows: Decimal
    inflow_by_category: dict[str, Decimal]
    outflow_by_category: dict[str, Decimal]
    periods: list[CashFlowPeriod] = field(default_factory=list)


def _q(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal("0.01"))


def _week_start(anchor: date) -> date:
    return anchor - timedelta(days=anchor.weekday())


def resolve_granularity(date_from: date, date_to: date, requested: str | None) -> str:
    """`Auto` (§10): <=45 días → día · 46-120 → semana · 121-400 → mes."""
    if requested in GRANULARITIES:
        return requested
    span = (date_to - date_from).days
    if span <= 45:
        return "day"
    if span <= 120:
        return "week"
    return "month"


def _period_bounds(anchor: date, granularity: str) -> tuple[date, date]:
    if granularity == "day":
        return anchor, anchor
    if granularity == "week":
        s = _week_start(anchor)
        return s, s + timedelta(days=6)
    s = anchor.replace(day=1)
    last = calendar.monthrange(anchor.year, anchor.month)[1]
    return s, anchor.replace(day=last)


def _next_period(period_end: date, granularity: str) -> date:
    if granularity == "day":
        return period_end + timedelta(days=1)
    if granularity == "week":
        return period_end + timedelta(days=1)
    return (period_end + timedelta(days=1))


def _period_label(start: date, end: date, granularity: str) -> str:
    if granularity == "day":
        return f"{start.day} {_MONTHS_ES[start.month]}"
    if granularity == "week":
        if start.month == end.month:
            return f"{start.day}–{end.day} {_MONTHS_ES[start.month]}"
        return f"{start.day} {_MONTHS_ES[start.month]} – {end.day} {_MONTHS_ES[end.month]}"
    return f"{_MONTHS_ES_FULL[start.month]} {start.year}"


def _build_periods(date_from: date, date_to: date, granularity: str) -> list[CashFlowPeriod]:
    periods: list[CashFlowPeriod] = []
    cursor = _period_bounds(date_from, granularity)[0]
    i = 0
    while cursor <= date_to:
        p_start, p_end = _period_bounds(cursor, granularity)
        periods.append(
            CashFlowPeriod(
                index=i,
                period_start=p_start,
                period_end=p_end,
                label=_period_label(p_start, p_end, granularity),
            )
        )
        cursor = _next_period(p_end, granularity)
        i += 1
    return periods


def _categorize(
    db: Session, document: AccountingDocument, net: Decimal, counter_accounts: list[Account]
) -> str:
    kind = _resolve_source_event(db, document.id).kind
    if net > _ZERO:
        if kind == "CUSTOMER_RECEIPT":
            return "Cobros de clientes"
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
    if kind == "SUPPLIER_PAYMENT":
        return "Pagos de contratos" if _has_contract_allocation(db, document) else "Pagos a proveedores"
    if kind == "GENERAL_EXPENSE":
        return "Gastos pagados"
    if any(a.account_type == "ASSET" for a in counter_accounts):
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
    return list(db.execute(select(Account).where(Account.id.in_(account_ids))).scalars())


def _econ_date_col():
    return func.coalesce(
        AccountingDocument.effective_date, func.date(AccountingDocument.posted_at)
    )


def _doc_nets(
    db: Session, *, company_id: uuid.UUID, cash_gl_ids: set[uuid.UUID]
) -> dict[uuid.UUID, tuple[Decimal, date]]:
    """{doc_id: (net_treasury, economic_date)} para toda la historia."""
    rows = db.execute(
        select(
            JournalLine.accounting_document_id,
            JournalLine.debit_amount,
            JournalLine.credit_amount,
            _econ_date_col().label("economic_date"),
        )
        .join(AccountingDocument, AccountingDocument.id == JournalLine.accounting_document_id)
        .where(
            AccountingDocument.company_id == company_id,
            AccountingDocument.status.in_(_LEDGER_STATUSES),
            JournalLine.account_id.in_(cash_gl_ids),
        )
    ).all()
    acc: dict[uuid.UUID, list] = {}
    for doc_id, debit, credit, economic_date in rows:
        entry = acc.setdefault(doc_id, [_ZERO, None])
        entry[0] += Decimal(str(debit)) - Decimal(str(credit))
        entry[1] = (
            date.fromisoformat(economic_date) if isinstance(economic_date, str) else economic_date
        )
    return {k: (_q(v[0]), v[1]) for k, v in acc.items()}


def series(
    db: Session,
    *,
    company_id: uuid.UUID,
    date_from: date | None = None,
    date_to: date | None = None,
    granularity: str | None = None,
) -> CashFlowActual:
    today = business_today()
    date_to = date_to or today
    date_from = date_from or (date_to - timedelta(days=89))
    if date_from > date_to:
        date_from, date_to = date_to, date_from
    gran = resolve_granularity(date_from, date_to, granularity)

    accounts = db.execute(
        select(TreasuryAccount).where(TreasuryAccount.company_id == company_id)
    ).scalars().all()
    currency = accounts[0].currency_code if accounts else "HNL"
    cash_gl_ids = {a.gl_account_id for a in accounts}

    closing_balance = _q(
        sum((treasury_service.treasury_account_balance(db, a) for a in accounts), Decimal("0"))
    )

    periods = _build_periods(date_from, date_to, gran)
    result = CashFlowActual(
        date_from=date_from,
        date_to=date_to,
        granularity=gran,
        currency_code=currency,
        opening_balance=closing_balance,
        closing_balance=closing_balance,
        total_inflows=_ZERO,
        total_outflows=_ZERO,
        inflow_by_category={c: _ZERO for c in INFLOW_CATEGORIES},
        outflow_by_category={c: _ZERO for c in OUTFLOW_CATEGORIES},
        periods=periods,
    )
    if not cash_gl_ids or not periods:
        return result

    nets = _doc_nets(db, company_id=company_id, cash_gl_ids=cash_gl_ids)
    window_start, window_end = periods[0].period_start, periods[-1].period_end

    # Índice rápido de período por fecha.
    def _period_for(d: date) -> CashFlowPeriod | None:
        for p in periods:
            if p.period_start <= d <= p.period_end:
                return p
        return None

    net_in_window = _ZERO
    net_outside = _ZERO
    for doc_id, (net, econ_date) in nets.items():
        if net == _ZERO or econ_date is None:
            continue
        if econ_date < window_start or econ_date > window_end:
            if econ_date > window_end:
                net_outside += net  # posterior a la ventana → fuera del saldo de apertura
            continue
        period = _period_for(econ_date)
        if period is None:
            continue
        document = db.get(AccountingDocument, doc_id)
        category = _categorize(db, document, net, _counter_accounts(db, doc_id, cash_gl_ids))
        period.by_category[category] = period.by_category.get(category, _ZERO) + net
        period.movement_count += 1
        net_in_window += net
        if net > _ZERO:
            period.inflows += net
            result.inflow_by_category[category] += net
        else:
            period.outflows += -net
            result.outflow_by_category[category] += -net

    running = _q(closing_balance - net_in_window - net_outside)
    result.opening_balance = running
    for p in periods:
        p.inflows = _q(p.inflows)
        p.outflows = _q(p.outflows)
        p.net = _q(p.inflows - p.outflows)
        running += p.net
        p.closing_balance = _q(running)
        p.by_category = {k: _q(v) for k, v in p.by_category.items() if v != _ZERO}

    result.total_inflows = _q(sum(result.inflow_by_category.values(), Decimal("0")))
    result.total_outflows = _q(sum(result.outflow_by_category.values(), Decimal("0")))
    result.inflow_by_category = {k: _q(v) for k, v in result.inflow_by_category.items()}
    result.outflow_by_category = {k: _q(v) for k, v in result.outflow_by_category.items()}
    return result


def movements(
    db: Session, *, company_id: uuid.UUID, date_from: date, date_to: date
) -> list[CashFlowMovement]:
    """Drill-down (§10/§11): los movimientos individuales de tesorería en el
    rango, ordenados por fecha económica descendente."""
    if date_from > date_to:
        date_from, date_to = date_to, date_from
    accounts = db.execute(
        select(TreasuryAccount).where(TreasuryAccount.company_id == company_id)
    ).scalars().all()
    cash_gl_ids = {a.gl_account_id for a in accounts}
    if not cash_gl_ids:
        return []

    nets = _doc_nets(db, company_id=company_id, cash_gl_ids=cash_gl_ids)
    out: list[CashFlowMovement] = []
    for doc_id, (net, econ_date) in nets.items():
        if net == _ZERO or econ_date is None or not (date_from <= econ_date <= date_to):
            continue
        document = db.get(AccountingDocument, doc_id)
        counter = _counter_accounts(db, doc_id, cash_gl_ids)
        source = _resolve_source_event(db, doc_id)
        out.append(
            CashFlowMovement(
                document_id=doc_id,
                document_number=document.document_number,
                effective_date=econ_date,
                direction="INFLOW" if net > _ZERO else "OUTFLOW",
                category=_categorize(db, document, net, counter),
                amount=_q(abs(net)),
                concept=document.description or source.label,
                counterparty=source.reference,
            )
        )
    out.sort(key=lambda m: (m.effective_date, m.document_number), reverse=True)
    return out


# --- Compatibilidad: `actual()` sigue devolviendo la forma "weeks" ---------
@dataclass
class ActualWeek:
    week_index: int
    week_start: date
    week_end: date
    inflows: Decimal
    outflows: Decimal
    net: Decimal
    closing_balance: Decimal
    by_category: dict[str, Decimal]


@dataclass
class _ActualCompat:
    as_of: date
    currency_code: str
    opening_balance: Decimal
    closing_balance: Decimal
    total_inflows: Decimal
    total_outflows: Decimal
    inflow_by_category: dict[str, Decimal]
    outflow_by_category: dict[str, Decimal]
    weeks: list[ActualWeek]


def actual(db: Session, *, company_id: uuid.UUID, as_of: date | None = None) -> _ActualCompat:
    as_of = as_of or business_today()
    end = as_of
    start = _week_start(as_of) - timedelta(days=12 * 7)
    s = series(db, company_id=company_id, date_from=start, date_to=end, granularity="week")
    weeks = [
        ActualWeek(
            week_index=p.index,
            week_start=p.period_start,
            week_end=p.period_end,
            inflows=p.inflows,
            outflows=p.outflows,
            net=p.net,
            closing_balance=p.closing_balance,
            by_category=p.by_category,
        )
        for p in s.periods
    ]
    return _ActualCompat(
        as_of=as_of,
        currency_code=s.currency_code,
        opening_balance=s.opening_balance,
        closing_balance=s.closing_balance,
        total_inflows=s.total_inflows,
        total_outflows=s.total_outflows,
        inflow_by_category=s.inflow_by_category,
        outflow_by_category=s.outflow_by_category,
        weeks=weeks,
    )
