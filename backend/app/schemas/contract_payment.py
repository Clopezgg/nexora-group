import uuid
from datetime import date
from decimal import Decimal

from pydantic import Field

from app.schemas.base import CamelModel


class InstallmentInput(CamelModel):
    period_year: int = Field(ge=2000, le=2100)
    period_month: int = Field(ge=1, le=12)
    due_date: date
    scheduled_amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    retention_amount: Decimal = Field(default=Decimal("0"), ge=0, max_digits=18, decimal_places=2)
    description: str | None = None


class ScheduleCreateRequest(CamelModel):
    supplier_contract_id: uuid.UUID
    schedule_type: str = "MONTHLY"
    # Modo A: cuotas explícitas.
    installments: list[InstallmentInput] | None = None
    # Modo B: mensual — se generan `months` cuotas iguales desde `start_period`.
    start_period: date | None = None
    months: int | None = Field(default=None, ge=1, le=600)
    monthly_amount: Decimal | None = Field(default=None, gt=0, max_digits=18, decimal_places=2)


class InstallmentResponse(CamelModel):
    installment_id: uuid.UUID
    sequence: int
    period_year: int
    period_month: int
    period_label: str
    due_date: date
    scheduled_amount: Decimal
    retention_amount: Decimal
    net_due: Decimal
    paid: Decimal
    remaining: Decimal
    status: str


class ScheduleResponse(CamelModel):
    id: uuid.UUID
    company_id: uuid.UUID
    supplier_contract_id: uuid.UUID
    project_id: uuid.UUID | None
    currency_code: str
    schedule_type: str
    total_scheduled: Decimal
    status: str
    installments: list[InstallmentResponse]


class ContractSummaryResponse(CamelModel):
    contract_value: Decimal
    total_scheduled_to_date: Decimal
    paid_accumulated: Decimal
    contract_balance: Decimal
    overdue_balance: Decimal
    next_due_period: str | None
    next_due_amount: Decimal | None
    currency_code: str


class FifoPreviewRequest(CamelModel):
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    as_of: date | None = None


class FifoPreviewItem(CamelModel):
    installment_id: uuid.UUID
    period_label: str
    amount_applied: Decimal


class LedgerAllocationResponse(CamelModel):
    payment_id: uuid.UUID
    payment_date: date
    installment_sequence: int
    installment_period_label: str
    amount_applied: Decimal
    bank_transaction_reference: str | None
    reversed: bool


class ContractLedgerEntryResponse(CamelModel):
    schedule_id: uuid.UUID
    supplier_contract_id: uuid.UUID
    contract_number: str
    supplier_legal_name: str | None
    project_id: uuid.UUID | None
    currency_code: str
    contract_value: Decimal
    scheduled_to_date: Decimal
    paid_accumulated: Decimal
    contract_balance: Decimal
    overdue_balance: Decimal
    installments: list[InstallmentResponse]
    allocations: list[LedgerAllocationResponse]


class ContractPaymentLedgerResponse(CamelModel):
    company_id: uuid.UUID
    as_of: date
    entries: list[ContractLedgerEntryResponse]
    total_contract_value: Decimal
    total_paid_accumulated: Decimal
    total_contract_balance: Decimal
