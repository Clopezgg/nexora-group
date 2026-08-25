import uuid
from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import Field

from app.schemas.base import CamelModel


class CustomerInvoiceCreateRequest(CamelModel):
    company_id: uuid.UUID
    customer_id: uuid.UUID
    invoice_number: str
    scope: Literal["CENTRAL", "GENERAL", "PROJECT"]
    project_id: uuid.UUID | None = None
    revenue_account_id: uuid.UUID
    receivable_account_id: uuid.UUID
    currency_code: str
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    invoice_date: date
    due_date: date
    description: str | None = None


class CustomerInvoiceResponse(CamelModel):
    id: uuid.UUID
    company_id: uuid.UUID
    customer_id: uuid.UUID
    invoice_number: str
    scope: str
    project_id: uuid.UUID | None
    currency_code: str
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    amount_collected: Decimal
    due_date: date
    status: str
    accounting_document_id: uuid.UUID | None


class CustomerReceiptCreateRequest(CamelModel):
    treasury_account_id: uuid.UUID
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    receipt_date: date


class CustomerReceiptResponse(CamelModel):
    id: uuid.UUID
    customer_invoice_id: uuid.UUID
    treasury_account_id: uuid.UUID
    amount: Decimal
    receipt_date: date
    accounting_document_id: uuid.UUID
