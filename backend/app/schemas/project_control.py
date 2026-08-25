import uuid
from datetime import date
from decimal import Decimal

from app.schemas.base import CamelModel


class ProjectCreateRequest(CamelModel):
    company_id: uuid.UUID
    name: str
    code: str | None = None
    customer_ref: str | None = None
    manager: str | None = None
    currency_code: str | None = None
    cost_center_id: uuid.UUID | None = None
    planned_start: date | None = None
    planned_end: date | None = None
    description: str | None = None


class ProjectResponse(CamelModel):
    id: uuid.UUID
    company_id: uuid.UUID
    name: str
    code: str | None
    customer_ref: str | None
    manager: str | None
    currency_code: str | None
    cost_center_id: uuid.UUID | None
    planned_start: date | None
    planned_end: date | None
    actual_end: date | None
    status: str
    description: str | None


class WBSNodeCreateRequest(CamelModel):
    code: str
    name: str
    parent_id: uuid.UUID | None = None
    manager: str | None = None
    planned_start: date | None = None
    planned_finish: date | None = None


class WBSNodeResponse(CamelModel):
    id: uuid.UUID
    project_id: uuid.UUID
    parent_id: uuid.UUID | None
    code: str
    name: str
    level: int
    manager: str | None
    status: str
    planned_start: date | None
    planned_finish: date | None
    progress_percent: Decimal


class TaskCreateRequest(CamelModel):
    name: str
    wbs_node_id: uuid.UUID | None = None
    owner: str | None = None
    planned_start: date | None = None
    planned_end: date | None = None
    depends_on_task_id: uuid.UUID | None = None


class TaskResponse(CamelModel):
    id: uuid.UUID
    project_id: uuid.UUID
    wbs_node_id: uuid.UUID | None
    name: str
    owner: str | None
    planned_start: date | None
    planned_end: date | None
    depends_on_task_id: uuid.UUID | None
    status: str


class MilestoneCreateRequest(CamelModel):
    name: str
    due_date: date
    wbs_node_id: uuid.UUID | None = None


class MilestoneResponse(CamelModel):
    id: uuid.UUID
    project_id: uuid.UUID
    wbs_node_id: uuid.UUID | None
    name: str
    due_date: date
    achieved_date: date | None
    status: str


class BudgetLineRequest(CamelModel):
    authorized_amount: Decimal
    wbs_node_id: uuid.UUID | None = None
    economic_category_id: uuid.UUID | None = None
    cost_center_id: uuid.UUID | None = None
    fiscal_period_id: uuid.UUID | None = None


class BudgetBaselineCreateRequest(CamelModel):
    currency_code: str
    lines: list[BudgetLineRequest]
    notes: str | None = None


class BudgetLineResponse(CamelModel):
    id: uuid.UUID
    wbs_node_id: uuid.UUID | None
    economic_category_id: uuid.UUID | None
    cost_center_id: uuid.UUID | None
    fiscal_period_id: uuid.UUID | None
    authorized_amount: Decimal


class BudgetResponse(CamelModel):
    id: uuid.UUID
    project_id: uuid.UUID
    version: str
    status: str
    currency_code: str
    previous_budget_id: uuid.UUID | None
    change_order_id: uuid.UUID | None
    lines: list[BudgetLineResponse]


class BudgetSummaryResponse(CamelModel):
    authorized: Decimal
    committed: Decimal
    accrued: Decimal
    paid: Decimal
    available: Decimal


class ForecastResponse(CamelModel):
    bac: Decimal
    pv: Decimal | None
    ev: Decimal | None
    ac: Decimal
    cpi: Decimal | None
    spi: Decimal | None
    etc: Decimal | None
    eac: Decimal | None
    vac: Decimal | None


class ChangeOrderCreateRequest(CamelModel):
    reason: str
    wbs_node_id: uuid.UUID | None = None
    scope_change: str | None = None
    budget_change_amount: Decimal = Decimal("0")
    schedule_change_days: int | None = None


class ChangeOrderResponse(CamelModel):
    id: uuid.UUID
    project_id: uuid.UUID
    wbs_node_id: uuid.UUID | None
    reason: str
    scope_change: str | None
    budget_change_amount: Decimal
    schedule_change_days: int | None
    requested_by: uuid.UUID
    approved_by: uuid.UUID | None
    status: str


class ChangeOrderSubmitRequest(CamelModel):
    pass


class ProgressRecordCreateRequest(CamelModel):
    record_date: date
    planned_percent: Decimal
    actual_percent: Decimal
    wbs_node_id: uuid.UUID | None = None
    description: str | None = None
    responsible: str | None = None
    evidence_id: uuid.UUID | None = None


class ProgressRecordResponse(CamelModel):
    id: uuid.UUID
    project_id: uuid.UUID
    wbs_node_id: uuid.UUID | None
    record_date: date
    planned_percent: Decimal
    actual_percent: Decimal
    description: str | None
    responsible: str | None
    evidence_id: uuid.UUID | None
