import uuid
from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import Field, model_validator

from app.schemas.base import CamelModel
from app.schemas.project_control import ProjectCreateRequest


class ProjectSetupWbs(CamelModel):
    code: str | None = Field(default=None, max_length=32)
    name: str | None = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def complete_or_empty(self):
        if bool(self.code and self.code.strip()) != bool(self.name and self.name.strip()):
            raise ValueError("Código y nombre WBS deben estar ambos completos o ambos vacíos")
        return self


class ProjectSetupContract(CamelModel):
    supplier_id: uuid.UUID
    contract_number: str = Field(min_length=1, max_length=255)
    contract_category: str = "OTHER"
    value: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    start_date: date
    end_date: date | None = None
    advance_amount: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=2)
    advance_due_date: date | None = None
    retention_percentage: Decimal = Field(default=Decimal(0), ge=0, le=100)
    payment_terms_type: Literal["LUMP_SUM", "MONTHLY", "CUSTOM"] = "MONTHLY"
    regular_months: int | None = Field(default=None, ge=1, le=600)
    due_day: int | None = Field(default=None, ge=1, le=31)

    @model_validator(mode="after")
    def valid_contract(self):
        if self.end_date and self.end_date < self.start_date:
            raise ValueError("La fecha final del contrato no puede ser anterior al inicio")
        if self.advance_amount and self.advance_amount > self.value:
            raise ValueError("El anticipo no puede superar el valor contractual")
        if self.advance_amount and self.advance_amount > 0 and not self.advance_due_date:
            raise ValueError("El anticipo requiere fecha de vencimiento")
        if self.payment_terms_type != "LUMP_SUM" and (self.regular_months is None or self.due_day is None):
            raise ValueError("El plan contractual requiere mensualidades y día de vencimiento")
        return self


class ProjectSetupRequest(CamelModel):
    project: ProjectCreateRequest
    wbs: ProjectSetupWbs = Field(default_factory=ProjectSetupWbs)
    baseline_amount: Decimal | None = Field(default=None, gt=0, max_digits=18, decimal_places=2)
    contract: ProjectSetupContract | None = None
    activate: bool = False


class ProjectSetupRunResponse(CamelModel):
    id: uuid.UUID
    company_id: uuid.UUID
    status: str
    activate: bool
    project_id: uuid.UUID | None
    failure_step: str | None
    failure_message: str | None
    staged_document_count: int = 0
