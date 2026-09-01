import uuid
from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import Field, field_validator

from app.schemas.base import CamelModel


class TreasuryAccountCreateRequest(CamelModel):
    company_id: uuid.UUID
    name: str
    kind: Literal["BANK", "CASH", "OTHER"]
    institution: str | None = None
    account_reference: str | None = None
    currency_code: str
    gl_account_id: uuid.UUID


class TreasuryAccountResponse(CamelModel):
    id: uuid.UUID
    company_id: uuid.UUID
    name: str
    kind: str
    institution: str | None
    account_reference: str | None
    currency_code: str
    gl_account_id: uuid.UUID
    status: str
    balance: Decimal


class RemittanceCreateRequest(CamelModel):
    company_id: uuid.UUID
    treasury_account_id: uuid.UUID
    counter_account_id: uuid.UUID
    origin_type: Literal["CAPITAL_CONTRIBUTION", "FINANCING", "OTHER_INCOME"] = "CAPITAL_CONTRIBUTION"
    sender: str
    provider: str | None = None
    channel: str | None = None
    currency_code: str
    original_amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    fx_rate: Decimal = Field(default=Decimal("1"), gt=0, max_digits=18, decimal_places=6)
    reference: str | None = None
    remittance_date: date
    notes: str | None = None


class RemittanceResponse(CamelModel):
    id: uuid.UUID
    company_id: uuid.UUID
    treasury_account_id: uuid.UUID
    sender: str
    provider: str | None = None
    channel: str | None = None
    reference: str | None = None
    currency_code: str
    original_amount: Decimal
    fx_rate: Decimal
    base_amount: Decimal
    remittance_date: date
    accounting_document_id: uuid.UUID


class GeneralExpenseCreateRequest(CamelModel):
    company_id: uuid.UUID
    treasury_account_id: uuid.UUID
    expense_account_id: uuid.UUID
    scope: Literal["GENERAL", "PROJECT"] = "GENERAL"
    project_id: uuid.UUID | None = None
    category: str
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    currency_code: str
    expense_date: date
    description: str


class GeneralExpenseResponse(CamelModel):
    id: uuid.UUID
    company_id: uuid.UUID
    treasury_account_id: uuid.UUID
    category: str
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    expense_date: date
    accounting_document_id: uuid.UUID


class TreasuryTransferCreateRequest(CamelModel):
    company_id: uuid.UUID
    source_treasury_account_id: uuid.UUID
    destination_treasury_account_id: uuid.UUID
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    currency_code: str
    transfer_date: date
    notes: str | None = None


class TreasuryTransferResponse(CamelModel):
    id: uuid.UUID
    source_treasury_account_id: uuid.UUID
    destination_treasury_account_id: uuid.UUID
    amount: Decimal
    transfer_date: date
    accounting_document_id: uuid.UUID


class CashClosingCreateRequest(CamelModel):
    treasury_account_id: uuid.UUID
    closing_date: date
    opening_amount: Decimal = Field(ge=0, max_digits=18, decimal_places=2)
    expected_amount: Decimal = Field(ge=0, max_digits=18, decimal_places=2)
    counted_amount: Decimal = Field(ge=0, max_digits=18, decimal_places=2)


class CashClosingApproveRequest(CamelModel):
    difference_account_id: uuid.UUID | None = None


class CashClosingResponse(CamelModel):
    id: uuid.UUID
    treasury_account_id: uuid.UUID
    closing_date: date
    opening_amount: Decimal
    expected_amount: Decimal
    counted_amount: Decimal
    difference_amount: Decimal
    status: str
    accounting_document_id: uuid.UUID | None


class BankStatementCreateRequest(CamelModel):
    treasury_account_id: uuid.UUID
    statement_date: date
    opening_balance: Decimal = Field(max_digits=18, decimal_places=2)
    closing_balance: Decimal = Field(max_digits=18, decimal_places=2)
    reference: str | None = None


class BankStatementLineCreateRequest(CamelModel):
    line_date: date
    description: str
    amount: Decimal = Field(max_digits=18, decimal_places=2)

    @field_validator("amount")
    @classmethod
    def amount_must_be_non_zero(cls, value: Decimal) -> Decimal:
        if value == 0:
            raise ValueError("amount must be non-zero")
        return value


class BankStatementLineResponse(CamelModel):
    id: uuid.UUID
    bank_statement_id: uuid.UUID
    line_date: date
    description: str
    amount: Decimal
    status: str


class ReconciliationMatchRequest(CamelModel):
    accounting_document_id: uuid.UUID
    matched_amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)


class FundRestrictionCreateRequest(CamelModel):
    treasury_account_id: uuid.UUID
    restricted_for_project_id: uuid.UUID | None = None
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    description: str


class FundRestrictionResponse(CamelModel):
    id: uuid.UUID
    treasury_account_id: uuid.UUID
    restricted_for_project_id: uuid.UUID | None
    amount: Decimal
    description: str
    active: bool


class BeneficiaryOption(CamelModel):
    """Beneficiario elegible para un comprobante. Reúne Supplier / Worker /
    Customer en una lista buscable (orden maestra Phase 2) sin duplicar
    entidades: el `id` sigue siendo el de la tabla de origen."""

    beneficiary_type: str  # SUPPLIER | WORKER | CUSTOMER
    id: uuid.UUID
    name: str
    reference: str | None = None


class VoucherCandidateResponse(CamelModel):
    """AccountingDocument elegible para Payment Voucher: EXCLUSIVAMENTE
    documentos cuya dirección de tesorería es OUTFLOW. Los inflows (remesas,
    cobros, aportes, financiamiento) y las transferencias internas nunca
    aparecen aquí — el filtro es server-side, no se ocultan en el browser."""

    id: uuid.UUID
    document_number: str
    company_id: uuid.UUID
    scope: str
    project_id: uuid.UUID | None = None
    currency_code: str
    status: str
    description: str | None = None
    treasury_direction: str
    treasury_net: Decimal


class TreasuryDirectionResponse(CamelModel):
    accounting_document_id: uuid.UUID
    direction: str  # INFLOW | OUTFLOW | INTERNAL_TRANSFER | NON_TREASURY
    treasury_debits: Decimal
    treasury_credits: Decimal
    treasury_net: Decimal
    treasury_account_count: int
    voucher_eligible: bool
