import uuid
from datetime import date
from decimal import Decimal

from pydantic import Field

from app.schemas.base import CamelModel


class CustomerCreateRequest(CamelModel):
    company_id: uuid.UUID
    legal_name: str
    trade_name: str | None = None
    tax_id: str | None = None
    contact_name: str | None = None
    email: str | None = None
    phone: str | None = None
    address: str | None = None


class CustomerResponse(CamelModel):
    id: uuid.UUID
    company_id: uuid.UUID
    legal_name: str
    trade_name: str | None
    tax_id: str | None
    contact_name: str | None
    email: str | None
    phone: str | None
    address: str | None
    status: str


class LeadCreateRequest(CamelModel):
    company_id: uuid.UUID
    name: str
    contact_name: str | None = None
    email: str | None = None
    phone: str | None = None
    source: str | None = None


class LeadResponse(CamelModel):
    id: uuid.UUID
    company_id: uuid.UUID
    name: str
    contact_name: str | None
    email: str | None
    phone: str | None
    source: str | None
    status: str
    converted_customer_id: uuid.UUID | None


class OpportunityResponse(CamelModel):
    id: uuid.UUID
    company_id: uuid.UUID
    lead_id: uuid.UUID | None
    customer_id: uuid.UUID
    name: str
    stage: str
    estimated_amount: Decimal | None
    currency_code: str | None


class LeadConversionResponse(CamelModel):
    lead: LeadResponse
    customer: CustomerResponse
    opportunity: OpportunityResponse


class QuotationCreateRequest(CamelModel):
    company_id: uuid.UUID
    opportunity_id: uuid.UUID
    customer_id: uuid.UUID
    project_id: uuid.UUID | None = None
    quotation_number: str
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    currency_code: str
    valid_until: date | None = None
    description: str | None = None


class QuotationResponse(CamelModel):
    id: uuid.UUID
    company_id: uuid.UUID
    opportunity_id: uuid.UUID
    customer_id: uuid.UUID
    project_id: uuid.UUID | None
    quotation_number: str
    amount: Decimal
    currency_code: str
    status: str
    valid_until: date | None
    description: str | None


class SalesContractConvertRequest(CamelModel):
    contract_number: str
    start_date: date


class SalesContractResponse(CamelModel):
    id: uuid.UUID
    company_id: uuid.UUID
    quotation_id: uuid.UUID
    customer_id: uuid.UUID
    project_id: uuid.UUID | None
    contract_number: str
    scope: str
    amount: Decimal
    currency_code: str
    start_date: date
    status: str
    customer_invoice_id: uuid.UUID | None


class SalesContractBillRequest(CamelModel):
    invoice_number: str
    invoice_date: date
    due_date: date
    revenue_account_id: uuid.UUID
    receivable_account_id: uuid.UUID
    description: str | None = None
