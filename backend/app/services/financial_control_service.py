"""Financial Control Center — "Estado financiero del día" (orden maestra
FINAL, Phase 3). Reúne KPIs *accionables* del día de negocio a partir de las
fuentes de verdad existentes (Treasury Ledger, AP, AR, fiscal periods,
approval inbox). No introduce cálculos financieros nuevos ni cifras
hardcodeadas: cada número se deriva de la base de datos.
"""

from dataclasses import dataclass
from datetime import date, timedelta as _timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.business_time import business_today
from app.models.accounting import AccountingDocument
from app.models.approval_request import ApprovalRequest
from app.models.ap import SupplierInvoice
from app.models.ar import CustomerInvoice
from app.models.fiscal import FiscalPeriod, FiscalYear
from app.models.treasury import TreasuryAccount
from app.services import treasury_service

_AP_OPEN_STATUSES = ("APPROVED", "SCHEDULED", "PARTIALLY_PAID")
_AR_OPEN_STATUSES = ("APPROVED", "PARTIALLY_COLLECTED")


@dataclass(frozen=True)
class Kpi:
    key: str
    label: str
    value: str
    numeric: float
    severity: str  # "ok" | "info" | "warning" | "critical"
    hint: str
    route: str | None = None


@dataclass(frozen=True)
class DailyStatus:
    company_id: str
    as_of: date
    currency_code: str
    fiscal_period_label: str | None
    fiscal_period_status: str | None
    kpis: list[Kpi]


def _money(value: Decimal, currency: str) -> str:
    from app.core.money import format_money

    return format_money(value, currency)


def _ap_open_totals(db: Session, company_id, as_of: date) -> tuple[Decimal, Decimal]:
    rows = db.execute(
        select(SupplierInvoice.due_date, SupplierInvoice.amount, SupplierInvoice.tax_amount, SupplierInvoice.amount_paid)
        .where(SupplierInvoice.company_id == company_id)
        .where(SupplierInvoice.status.in_(_AP_OPEN_STATUSES))
    ).all()
    due_today = Decimal("0")
    overdue = Decimal("0")
    for due_date, amount, tax_amount, amount_paid in rows:
        remaining = (amount + tax_amount) - amount_paid
        if remaining <= 0:
            continue
        if due_date < as_of:
            overdue += remaining
        elif due_date == as_of:
            due_today += remaining
    return due_today, overdue


def _ar_open_totals(db: Session, company_id, as_of: date) -> tuple[Decimal, Decimal]:
    rows = db.execute(
        select(CustomerInvoice.due_date, CustomerInvoice.amount, CustomerInvoice.amount_collected)
        .where(CustomerInvoice.company_id == company_id)
        .where(CustomerInvoice.status.in_(_AR_OPEN_STATUSES))
    ).all()
    due_today = Decimal("0")
    overdue = Decimal("0")
    for due_date, amount, amount_collected in rows:
        remaining = amount - amount_collected
        if remaining <= 0:
            continue
        if due_date < as_of:
            overdue += remaining
        elif due_date == as_of:
            due_today += remaining
    return due_today, overdue


def daily_status(db: Session, *, company_id, as_of: date | None = None) -> DailyStatus:
    as_of = as_of or business_today()

    accounts = db.execute(
        select(TreasuryAccount).where(TreasuryAccount.company_id == company_id)
    ).scalars().all()
    cash_position = sum(
        (treasury_service.treasury_account_balance(db, account) for account in accounts),
        Decimal("0"),
    )
    currency = accounts[0].currency_code if accounts else "HNL"

    postings_today = db.execute(
        select(func.count(AccountingDocument.id))
        .where(AccountingDocument.company_id == company_id)
        .where(func.date(AccountingDocument.posted_at) == as_of)
    ).scalar_one()

    ap_due_today, ap_overdue = _ap_open_totals(db, company_id, as_of)
    ar_due_today, ar_overdue = _ar_open_totals(db, company_id, as_of)

    pending_approvals = db.execute(
        select(func.count(ApprovalRequest.id))
        .where(ApprovalRequest.company_id == company_id)
        .where(ApprovalRequest.status == "PENDING")
    ).scalar_one()

    period = db.execute(
        select(FiscalPeriod)
        .where(FiscalPeriod.company_id == company_id)
        .where(FiscalPeriod.start_date <= as_of)
        .where(FiscalPeriod.end_date >= as_of)
    ).scalars().first()
    period_label = None
    period_status = None
    if period is not None:
        year = db.get(FiscalYear, period.fiscal_year_id)
        year_code = year.code if year is not None else str(period.start_date.year)
        period_label = f"{year_code} · P{period.period_number:02d}"
        period_status = period.status

    kpis = [
        Kpi(
            key="cash_position",
            label="Posición de caja y bancos",
            value=_money(cash_position, currency),
            numeric=float(cash_position),
            severity="critical" if cash_position < 0 else "ok",
            hint="Saldo real consolidado de todas las cuentas de Tesorería.",
            route="/finanzas/tesoreria",
        ),
        Kpi(
            key="postings_today",
            label="Asientos posteados hoy",
            value=str(postings_today),
            numeric=float(postings_today),
            severity="info",
            hint="Documentos contables con fecha de posteo de hoy (zona horaria de negocio).",
            route="/finanzas/contabilidad",
        ),
        Kpi(
            key="ap_due_today",
            label="Cuentas por pagar que vencen hoy",
            value=_money(ap_due_today, currency),
            numeric=float(ap_due_today),
            severity="warning" if ap_due_today > 0 else "ok",
            hint="Saldo pendiente de facturas de proveedor con vencimiento hoy.",
            route="/finanzas/cuentas-por-pagar",
        ),
        Kpi(
            key="ap_overdue",
            label="Cuentas por pagar vencidas",
            value=_money(ap_overdue, currency),
            numeric=float(ap_overdue),
            severity="critical" if ap_overdue > 0 else "ok",
            hint="Saldo pendiente de facturas de proveedor con vencimiento anterior a hoy.",
            route="/finanzas/cuentas-por-pagar",
        ),
        Kpi(
            key="ar_due_today",
            label="Cuentas por cobrar que vencen hoy",
            value=_money(ar_due_today, currency),
            numeric=float(ar_due_today),
            severity="info" if ar_due_today > 0 else "ok",
            hint="Saldo por cobrar de facturas de cliente con vencimiento hoy.",
            route="/finanzas/cuentas-por-cobrar",
        ),
        Kpi(
            key="ar_overdue",
            label="Cuentas por cobrar vencidas",
            value=_money(ar_overdue, currency),
            numeric=float(ar_overdue),
            severity="warning" if ar_overdue > 0 else "ok",
            hint="Saldo por cobrar de facturas de cliente con vencimiento anterior a hoy.",
            route="/finanzas/cuentas-por-cobrar",
        ),
        Kpi(
            key="pending_approvals",
            label="Aprobaciones pendientes",
            value=str(pending_approvals),
            numeric=float(pending_approvals),
            severity="warning" if pending_approvals > 0 else "ok",
            hint="Solicitudes de aprobación financieras/operativas sin decidir.",
            route="/control/aprobaciones",
        ),
        Kpi(
            key="fiscal_period",
            label="Período fiscal actual",
            value=period_label or "No configurado",
            numeric=0.0,
            severity="critical" if period_label is None else (
                "ok" if period_status == "OPEN" else "info"
            ),
            hint="Período fiscal que cubre la fecha de hoy y su estado de cierre.",
            route="/control/configuracion",
        ),
    ]

    return DailyStatus(
        company_id=str(company_id),
        as_of=as_of,
        currency_code=currency,
        fiscal_period_label=period_label,
        fiscal_period_status=period_status,
        kpis=kpis,
    )


def ar_metrics(db: Session, *, company_id, as_of: date | None = None) -> dict:
    """DSO + aging de cuentas por cobrar (orden maestra Phase 7).

    DSO simple = (AR pendiente / ventas a crédito de los últimos 90 días) * 90.
    """
    as_of = as_of or business_today()
    trailing_start = as_of - _timedelta(days=90)

    open_rows = db.execute(
        select(CustomerInvoice.due_date, CustomerInvoice.amount, CustomerInvoice.amount_collected)
        .where(CustomerInvoice.company_id == company_id)
        .where(CustomerInvoice.status.in_(_AR_OPEN_STATUSES))
    ).all()
    ar_outstanding = Decimal("0")
    aging = {"current": Decimal("0"), "1_30": Decimal("0"), "31_60": Decimal("0"), "61_90": Decimal("0"), "over_90": Decimal("0")}
    for due_date, amount, amount_collected in open_rows:
        remaining = amount - amount_collected
        if remaining <= 0:
            continue
        ar_outstanding += remaining
        overdue_days = (as_of - due_date).days
        if overdue_days <= 0:
            aging["current"] += remaining
        elif overdue_days <= 30:
            aging["1_30"] += remaining
        elif overdue_days <= 60:
            aging["31_60"] += remaining
        elif overdue_days <= 90:
            aging["61_90"] += remaining
        else:
            aging["over_90"] += remaining

    trailing_sales = db.execute(
        select(func.coalesce(func.sum(CustomerInvoice.amount), Decimal("0")))
        .where(CustomerInvoice.company_id == company_id)
        .where(CustomerInvoice.status != "CANCELLED")
        .where(CustomerInvoice.invoice_date >= trailing_start)
        .where(CustomerInvoice.invoice_date <= as_of)
    ).scalar_one()
    trailing_sales = Decimal(trailing_sales)

    dso = None
    if trailing_sales > 0:
        dso = (ar_outstanding / trailing_sales * Decimal("90")).quantize(Decimal("0.1"))

    return {
        "asOf": as_of.isoformat(),
        "arOutstanding": str(ar_outstanding),
        "trailingCreditSales90d": str(trailing_sales),
        "dso": str(dso) if dso is not None else None,
        "aging": {k: str(v) for k, v in aging.items()},
    }
