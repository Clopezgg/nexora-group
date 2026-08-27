from app.schemas.base import CamelModel


class DashboardSummaryResponse(CamelModel):
    treasury_balance: float
    period_income: float
    period_expense: float
    active_projects: int
    currency: str = "HNL"
