import uuid
from decimal import Decimal

from app.schemas.base import CamelModel


class ProjectCockpitResponse(CamelModel):
    project_id: uuid.UUID
    project_name: str
    currency_code: str
    budget_at_completion: Decimal
    committed: Decimal
    actual_cost: Decimal
    percent_complete: Decimal | None
    earned_value: Decimal | None
    cost_performance_index: Decimal | None
    estimate_to_complete: Decimal | None
    estimate_at_completion: Decimal | None
    variance_at_completion: Decimal | None
    contract_revenue: Decimal
    projected_margin: Decimal | None
    projected_margin_pct: Decimal | None
