import uuid
from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import Field, model_validator

from app.schemas.base import CamelModel


class FixedAssetCreateRequest(CamelModel):
    company_id: uuid.UUID
    category: str
    name: str
    acquisition_date: date
    cost: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    currency_code: str
    useful_life_months: int = Field(gt=0)
    salvage_value: Decimal = Field(default=Decimal("0"), ge=0, max_digits=18, decimal_places=2)
    location: str | None = None
    responsible: str | None = None
    scope: Literal["CENTRAL", "GENERAL", "PROJECT"]
    project_id: uuid.UUID | None = None
    cost_center_id: uuid.UUID | None = None
    depreciation_expense_account_id: uuid.UUID
    accumulated_depreciation_account_id: uuid.UUID


class FixedAssetResponse(CamelModel):
    id: uuid.UUID
    company_id: uuid.UUID
    category: str
    name: str
    acquisition_date: date
    cost: Decimal
    currency_code: str
    useful_life_months: int
    salvage_value: Decimal
    location: str | None
    responsible: str | None
    status: str
    scope: str
    project_id: uuid.UUID | None
    cost_center_id: uuid.UUID | None
    depreciation_expense_account_id: uuid.UUID
    accumulated_depreciation_account_id: uuid.UUID


class AssetStatusChangeRequest(CamelModel):
    status: Literal["ACTIVE", "UNDER_MAINTENANCE", "DISPOSED", "RETIRED"]


class DepreciationEntryCreateRequest(CamelModel):
    period_start: date
    period_end: date
    post: bool = True

    @model_validator(mode="after")
    def period_end_not_before_period_start(self) -> "DepreciationEntryCreateRequest":
        """Rechaza el request con un 422 limpio antes de llegar a
        `ck_depreciation_entries_period_valid` -- un `period_end` anterior a
        `period_start` no debe surgir como un IntegrityError de PostgreSQL
        sin manejar."""
        if self.period_end < self.period_start:
            raise ValueError("periodEnd no puede ser anterior a periodStart")
        return self


class DepreciationEntryResponse(CamelModel):
    id: uuid.UUID
    asset_id: uuid.UUID
    period_start: date
    period_end: date
    amount: Decimal
    accounting_document_id: uuid.UUID | None
