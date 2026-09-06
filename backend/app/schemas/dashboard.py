from datetime import date
from decimal import Decimal

from pydantic import Field

from app.schemas.base import CamelModel


class CashFlowPointResponse(CamelModel):
    period: str
    income: Decimal
    expense: Decimal


class ScopeAmountResponse(CamelModel):
    scope: str
    amount: Decimal


class DashboardSummaryResponse(CamelModel):
    treasury_balance: Decimal
    period_income: Decimal
    period_expense: Decimal
    active_projects: int
    pending_approvals: int = 0
    overdue_payables: int = 0
    overdue_payables_amount: Decimal = Decimal("0")
    receivables_outstanding: Decimal = Decimal("0")
    cash_flow: list[CashFlowPointResponse] = Field(default_factory=list)
    expenses_by_scope: list[ScopeAmountResponse] = Field(default_factory=list)
    currency: str = "HNL"
    fiscal_period_label: str | None = None
    fiscal_period_status: str | None = None
    fiscal_period_start: date | None = None
    fiscal_period_end: date | None = None
