import uuid
from datetime import date
from decimal import Decimal

from app.schemas.base import CamelModel


class KpiResponse(CamelModel):
    key: str
    label: str
    value: str
    numeric: float
    severity: str
    hint: str
    route: str | None = None


class DailyStatusResponse(CamelModel):
    company_id: uuid.UUID
    as_of: date
    currency_code: str
    fiscal_period_label: str | None
    fiscal_period_status: str | None
    kpis: list[KpiResponse]


class ForecastWeekResponse(CamelModel):
    week_index: int
    week_start: date
    week_end: date
    inflows: Decimal
    outflows: Decimal
    net: Decimal
    projected_balance: Decimal


class CashForecastResponse(CamelModel):
    as_of: date
    currency_code: str
    opening_balance: Decimal
    weeks: list[ForecastWeekResponse]
    min_projected_balance: Decimal
    first_negative_week_index: int | None
    has_liquidity_alert: bool


class ActualWeekResponse(CamelModel):
    week_index: int
    week_start: date
    week_end: date
    inflows: Decimal
    outflows: Decimal
    net: Decimal
    closing_balance: Decimal
    by_category: dict[str, Decimal]


class CashFlowActualResponse(CamelModel):
    """Flujo de caja REALIZADO — últimas 13 semanas. Distinto del forecast:
    esto ya ocurrió, leído del movimiento real de las cuentas de tesorería."""

    as_of: date
    currency_code: str
    opening_balance: Decimal
    closing_balance: Decimal
    total_inflows: Decimal
    total_outflows: Decimal
    inflow_by_category: dict[str, Decimal]
    outflow_by_category: dict[str, Decimal]
    weeks: list[ActualWeekResponse]
