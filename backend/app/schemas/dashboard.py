from pydantic import Field

from app.schemas.base import CamelModel


class CashFlowPointResponse(CamelModel):
    period: str
    income: float
    expense: float


class ScopeAmountResponse(CamelModel):
    scope: str
    amount: float


class DashboardSummaryResponse(CamelModel):
    treasury_balance: float
    period_income: float
    period_expense: float
    active_projects: int
    pending_approvals: int = 0
    overdue_payables: int = 0
    overdue_payables_amount: float = 0
    receivables_outstanding: float = 0
    cash_flow: list[CashFlowPointResponse] = Field(default_factory=list)
    expenses_by_scope: list[ScopeAmountResponse] = Field(default_factory=list)
    currency: str = "HNL"
