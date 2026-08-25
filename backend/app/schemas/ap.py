import uuid
from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import Field

from app.schemas.base import CamelModel


class SupplierInvoiceCreateRequest(CamelModel):
    company_id: uuid.UUID
    supplier_name: str
    supplier_tax_id: str | None = None
    invoice_number: str
    scope: Literal["CENTRAL", "GENERAL", "PROJECT"]
    project_id: uuid.UUID | None = None
    cost_center_id: uuid.UUID | None = None
    expense_account_id: uuid.UUID
    payable_account_id: uuid.UUID
    currency_code: str
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    tax_amount: Decimal = Field(default=Decimal("0"), ge=0, max_digits=18, decimal_places=2)
    invoice_date: date
    due_date: date
    description: str | None = None


class SupplierInvoiceResponse(CamelModel):
    id: uuid.UUID
    company_id: uuid.UUID
    supplier_name: str
    invoice_number: str
    scope: str
    project_id: uuid.UUID | None
    currency_code: str
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    tax_amount: Decimal
    amount_paid: Decimal
    due_date: date
    status: str
    accrual_document_id: uuid.UUID | None


class SupplierPaymentCreateRequest(CamelModel):
    treasury_account_id: uuid.UUID
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    payment_date: date


class SupplierPaymentResponse(CamelModel):
    id: uuid.UUID
    supplier_invoice_id: uuid.UUID
    treasury_account_id: uuid.UUID
    amount: Decimal
    payment_date: date
    accounting_document_id: uuid.UUID
