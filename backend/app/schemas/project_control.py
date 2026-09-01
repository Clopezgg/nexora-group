import uuid
from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import Field, model_validator

from app.schemas.base import CamelModel


PROJECT_STATUS_VALUES = Literal["PLANNING", "ACTIVE", "ON_HOLD", "COMPLETED", "CLOSED", "CANCELLED"]
WBS_STATUS_VALUES = Literal["PLANNING", "ACTIVE", "ON_HOLD", "COMPLETED", "CANCELLED"]


class ProjectCreateRequest(CamelModel):
    company_id: uuid.UUID
    name: str = Field(min_length=1, max_length=255)
    code: str | None = Field(default=None, max_length=32)
    customer_id: uuid.UUID | None = None
    customer_ref: str | None = Field(default=None, max_length=255)
    manager: str | None = Field(default=None, max_length=255)
    currency_code: str | None = Field(default=None, min_length=3, max_length=3)
    cost_center_id: uuid.UUID | None = None
    planned_start: date | None = None
    planned_end: date | None = None
    description: str | None = Field(default=None, max_length=2000)
    address_line_1: str | None = Field(default=None, max_length=255)
    address_line_2: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, max_length=120)
    state_department: str | None = Field(default=None, max_length=120)
    country: str | None = Field(default=None, min_length=2, max_length=2)
    location_reference: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def validate_planned_dates(self):
        if self.planned_start and self.planned_end and self.planned_end < self.planned_start:
            raise ValueError("La fecha final prevista no puede ser anterior a la fecha de inicio")
        return self


class ProjectUpdateRequest(CamelModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    code: str | None = Field(default=None, max_length=32)
    customer_id: uuid.UUID | None = None
    customer_ref: str | None = Field(default=None, max_length=255)
    manager: str | None = Field(default=None, max_length=255)
    currency_code: str | None = Field(default=None, min_length=3, max_length=3)
    cost_center_id: uuid.UUID | None = None
    planned_start: date | None = None
    planned_end: date | None = None
    description: str | None = Field(default=None, max_length=2000)
    # Localización documental de la obra (orden maestra final §31).
    address_line_1: str | None = Field(default=None, max_length=255)
    address_line_2: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, max_length=120)
    state_department: str | None = Field(default=None, max_length=120)
    country: str | None = Field(default=None, min_length=2, max_length=2)
    location_reference: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def validate_planned_dates(self):
        if self.planned_start and self.planned_end and self.planned_end < self.planned_start:
            raise ValueError("La fecha final prevista no puede ser anterior a la fecha de inicio")
        return self


class ProjectStatusTransitionRequest(CamelModel):
    status: PROJECT_STATUS_VALUES
    reason: str | None = Field(default=None, max_length=1000)


class ProjectResponse(CamelModel):
    id: uuid.UUID
    company_id: uuid.UUID
    name: str
    code: str | None
    customer_id: uuid.UUID | None
    customer_ref: str | None
    manager: str | None
    currency_code: str | None
    cost_center_id: uuid.UUID | None
    planned_start: date | None
    planned_end: date | None
    actual_end: date | None
    status: str
    description: str | None
    address_line_1: str | None = None
    address_line_2: str | None = None
    city: str | None = None
    state_department: str | None = None
    country: str | None = None
    location_reference: str | None = None


class ProjectFinancialSummaryResponse(CamelModel):
    project_id: uuid.UUID
    currency_code: str
    contract_value: Decimal | None
    baseline_budget: Decimal | None
    current_budget: Decimal | None
    committed: Decimal
    accrued: Decimal
    paid: Decimal
    available: Decimal | None
    invoiced: Decimal
    collected: Decimal
    receivables_outstanding: Decimal
    recognized_revenue: Decimal
    actual_cost: Decimal
    expected_profit: Decimal | None
    expected_margin_percent: Decimal | None
    actual_profit: Decimal | None
    actual_margin_percent: Decimal | None
    progress_percent: Decimal | None
    bac: Decimal | None
    pv: Decimal | None
    ev: Decimal | None
    ac: Decimal | None
    cpi: Decimal | None
    spi: Decimal | None
    etc: Decimal | None
    eac: Decimal | None
    vac: Decimal | None


class WBSNodeCreateRequest(CamelModel):
    code: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=255)
    parent_id: uuid.UUID | None = None
    manager: str | None = Field(default=None, max_length=255)
    planned_start: date | None = None
    planned_finish: date | None = None

    @model_validator(mode="after")
    def validate_planned_dates(self):
        if self.planned_start and self.planned_finish and self.planned_finish < self.planned_start:
            raise ValueError("La fecha final del WBS no puede ser anterior a la fecha de inicio")
        return self


class WBSNodeUpdateRequest(CamelModel):
    code: str | None = Field(default=None, min_length=1, max_length=32)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    parent_id: uuid.UUID | None = None
    manager: str | None = Field(default=None, max_length=255)
    planned_start: date | None = None
    planned_finish: date | None = None
    status: WBS_STATUS_VALUES | None = None
    progress_percent: Decimal | None = Field(default=None, ge=0, le=100)

    @model_validator(mode="after")
    def validate_planned_dates(self):
        if self.planned_start and self.planned_finish and self.planned_finish < self.planned_start:
            raise ValueError("La fecha final del WBS no puede ser anterior a la fecha de inicio")
        return self


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


class WBSFinancialResponse(CamelModel):
    wbs_node_id: uuid.UUID
    authorized: Decimal
    committed: Decimal | None = None
    actual_cost: Decimal | None = None
    variance: Decimal | None = None


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
    authorized_amount: Decimal = Field(gt=0)
    wbs_node_id: uuid.UUID | None = None
    economic_category_id: uuid.UUID | None = None
    cost_center_id: uuid.UUID | None = None
    fiscal_period_id: uuid.UUID | None = None


class BudgetBaselineCreateRequest(CamelModel):
    currency_code: str
    lines: list[BudgetLineRequest] = Field(min_length=1)
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
    reason: str = Field(min_length=1, max_length=1000)
    wbs_node_id: uuid.UUID | None = None
    scope_change: str | None = Field(default=None, max_length=2000)
    budget_change_amount: Decimal = Decimal("0")
    contract_change_amount: Decimal = Decimal("0")
    schedule_change_days: int | None = None


class ChangeOrderResponse(CamelModel):
    id: uuid.UUID
    project_id: uuid.UUID
    wbs_node_id: uuid.UUID | None
    reason: str
    scope_change: str | None
    budget_change_amount: Decimal
    contract_change_amount: Decimal
    schedule_change_days: int | None
    requested_by: uuid.UUID
    approved_by: uuid.UUID | None
    status: str


class ChangeOrderSubmitRequest(CamelModel):
    pass


class ProgressRecordCreateRequest(CamelModel):
    record_date: date
    planned_percent: Decimal = Field(ge=0, le=100)
    actual_percent: Decimal = Field(ge=0, le=100)
    wbs_node_id: uuid.UUID | None = None
    description: str | None = Field(default=None, max_length=2000)
    responsible: str | None = Field(default=None, max_length=255)
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
