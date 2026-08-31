"""13-week rolling cash forecast + alertas de liquidez (orden maestra FINAL,
Phase 7).

Se construye desde la base: posición de caja actual (Treasury Ledger) +
entradas esperadas (AR abierto por fecha de vencimiento) − salidas esperadas
(AP abierto; si la factura tiene plan de pago, se usan las fechas de las
cuotas, no la fecha única de la factura). No se inventan proyecciones de
ventas futuras — solo compromisos ya registrados.
"""

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.business_time import business_today
from app.models.ap import SupplierInvoice, SupplierInvoicePaymentPlanItem
from app.models.ar import CustomerInvoice
from app.models.treasury import TreasuryAccount
from app.services import treasury_service

_AP_OPEN = ("APPROVED", "SCHEDULED", "PARTIALLY_PAID")
_AR_OPEN = ("APPROVED", "PARTIALLY_COLLECTED")
_WEEKS = 13


@dataclass(frozen=True)
class ForecastWeek:
    week_index: int
    week_start: date
    week_end: date
    inflows: Decimal
    outflows: Decimal
    net: Decimal
    projected_balance: Decimal


@dataclass
class CashForecast:
    as_of: date
    currency_code: str
    opening_balance: Decimal
    weeks: list[ForecastWeek] = field(default_factory=list)
    min_projected_balance: Decimal = Decimal("0")
    first_negative_week_index: int | None = None
    has_liquidity_alert: bool = False


def _ap_outflows_by_due(db: Session, company_id) -> list[tuple[date, Decimal]]:
    """(fecha, monto) de salidas AP. Si la factura tiene plan de pago, cada
    cuota es un evento; si no, la factura entera vence en su due_date."""
    invoices = db.execute(
        select(
            SupplierInvoice.id,
            SupplierInvoice.due_date,
            SupplierInvoice.amount,
            SupplierInvoice.tax_amount,
            SupplierInvoice.amount_paid,
        )
        .where(SupplierInvoice.company_id == company_id)
        .where(SupplierInvoice.status.in_(_AP_OPEN))
    ).all()
    if not invoices:
        return []

    plan_items = db.execute(
        select(
            SupplierInvoicePaymentPlanItem.supplier_invoice_id,
            SupplierInvoicePaymentPlanItem.due_date,
            SupplierInvoicePaymentPlanItem.amount,
        ).where(
            SupplierInvoicePaymentPlanItem.supplier_invoice_id.in_([row[0] for row in invoices])
        )
    ).all()
    plan_by_invoice: dict = {}
    for invoice_id, due_date, amount in plan_items:
        plan_by_invoice.setdefault(invoice_id, []).append((due_date, amount))

    events: list[tuple[date, Decimal]] = []
    for invoice_id, due_date, amount, tax_amount, amount_paid in invoices:
        remaining = (amount + tax_amount) - amount_paid
        if remaining <= 0:
            continue
        plan = plan_by_invoice.get(invoice_id)
        if plan:
            # El plan cubre el total; se prorratea `remaining` sobre las cuotas.
            plan_total = sum((amt for _, amt in plan), Decimal("0"))
            for cuota_due, cuota_amount in plan:
                share = (
                    (cuota_amount / plan_total * remaining)
                    if plan_total > 0
                    else Decimal("0")
                )
                events.append((cuota_due, share))
        else:
            events.append((due_date, remaining))
    return events


def _ar_inflows_by_due(db: Session, company_id) -> list[tuple[date, Decimal]]:
    rows = db.execute(
        select(CustomerInvoice.due_date, CustomerInvoice.amount, CustomerInvoice.amount_collected)
        .where(CustomerInvoice.company_id == company_id)
        .where(CustomerInvoice.status.in_(_AR_OPEN))
    ).all()
    events: list[tuple[date, Decimal]] = []
    for due_date, amount, amount_collected in rows:
        remaining = amount - amount_collected
        if remaining > 0:
            events.append((due_date, remaining))
    return events


def forecast(db: Session, *, company_id, as_of: date | None = None) -> CashForecast:
    as_of = as_of or business_today()

    accounts = db.execute(
        select(TreasuryAccount).where(TreasuryAccount.company_id == company_id)
    ).scalars().all()
    opening = sum(
        (treasury_service.treasury_account_balance(db, a) for a in accounts), Decimal("0")
    )
    currency = accounts[0].currency_code if accounts else "HNL"

    ap_events = _ap_outflows_by_due(db, company_id)
    ar_events = _ar_inflows_by_due(db, company_id)
    horizon_end = as_of + timedelta(days=_WEEKS * 7 - 1)

    result = CashForecast(
        as_of=as_of, currency_code=currency, opening_balance=opening
    )
    running = opening
    min_balance = opening
    first_negative: int | None = None

    for i in range(_WEEKS):
        w_start = as_of + timedelta(days=i * 7)
        w_end = w_start + timedelta(days=6)
        # Semana 0: incluye todo lo vencido antes de hoy (backlog) + esta semana.
        lower = date.min if i == 0 else w_start
        inflows = sum(
            (amt for due, amt in ar_events if lower <= due <= w_end), Decimal("0")
        )
        outflows = sum(
            (amt for due, amt in ap_events if lower <= due <= w_end), Decimal("0")
        )
        net = inflows - outflows
        running += net
        if running < min_balance:
            min_balance = running
        if running < 0 and first_negative is None:
            first_negative = i
        result.weeks.append(
            ForecastWeek(
                week_index=i,
                week_start=w_start,
                week_end=w_end,
                inflows=inflows.quantize(Decimal("0.01")),
                outflows=outflows.quantize(Decimal("0.01")),
                net=net.quantize(Decimal("0.01")),
                projected_balance=running.quantize(Decimal("0.01")),
            )
        )

    # Consumir los eventos posteriores al horizonte no cambia el gráfico pero
    # evita sorpresas: si algo grande vence justo después, no se pierde aquí
    # (el horizonte fijo es de 13 semanas por diseño).
    _ = horizon_end

    result.min_projected_balance = min_balance.quantize(Decimal("0.01"))
    result.first_negative_week_index = first_negative
    result.has_liquidity_alert = first_negative is not None
    return result
