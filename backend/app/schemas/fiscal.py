import uuid
from datetime import date
from typing import Literal

from pydantic import Field, model_validator

from app.schemas.base import CamelModel


class FiscalYearCreateRequest(CamelModel):
    company_id: uuid.UUID
    code: str = Field(min_length=1, max_length=16)
    start_date: date
    end_date: date

    @model_validator(mode="after")
    def validate_dates(self):
        if self.end_date < self.start_date:
            raise ValueError("La fecha final del año fiscal no puede ser anterior al inicio")
        return self


class FiscalYearResponse(CamelModel):
    id: uuid.UUID
    company_id: uuid.UUID
    code: str
    start_date: date
    end_date: date


class FiscalPeriodResponse(CamelModel):
    id: uuid.UUID
    fiscal_year_id: uuid.UUID
    company_id: uuid.UUID
    period_number: int
    start_date: date
    end_date: date
    status: Literal["OPEN", "SOFT_CLOSED", "CLOSED"]


class FiscalPeriodStatusRequest(CamelModel):
    status: Literal["OPEN", "SOFT_CLOSED", "CLOSED"]
    reason: str | None = Field(default=None, max_length=1000)


class CurrentFiscalPeriodResponse(CamelModel):
    fiscal_year: FiscalYearResponse | None = None
    period: FiscalPeriodResponse | None = None
