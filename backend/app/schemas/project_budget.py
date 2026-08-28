from pydantic import Field

from app.schemas.base import CamelModel
from app.schemas.project_control import BudgetLineRequest


class BudgetRedistributionRequest(CamelModel):
    lines: list[BudgetLineRequest] = Field(min_length=1)
    notes: str | None = Field(default=None, max_length=1000)
