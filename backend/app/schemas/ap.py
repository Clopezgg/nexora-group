import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import Field

from app.schemas.base import CamelModel


class SupplierInvoiceCreateRequest(CamelModel):
    company_id: uuid.UUID
    supplier_id: uuid.UUID
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
    supplier_contract_id: uuid.UUID | None = None
    purchase_order_id: uuid.UUID | None = None


class SupplierInvoiceSubmitRequest(CamelModel):
    assigned_to: uuid.UUID
    priority: str = "NORMAL"


class SupplierInvoiceResponse(CamelModel):
    id: uuid.UUID
    company_id: uuid.UUID
    supplier_id: uuid.UUID
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
    supplier_contract_id: uuid.UUID | None = None
    purchase_order_id: uuid.UUID | None = None


class ContractAllocationInput(CamelModel):
    installment_id: uuid.UUID
    amount_applied: Decimal = Field(gt=0, max_digits=18, decimal_places=2)


class SupplierPaymentCreateRequest(CamelModel):
    treasury_account_id: uuid.UUID
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    payment_date: date
    # Asignación a cuotas contractuales (orden maestra final §8/§17). La suma
    # debe igualar `amount`. Opcional: sólo aplica a facturas de contrato.
    contract_allocations: list[ContractAllocationInput] | None = None
    contract_override_reason: str | None = None
    bank_transaction_reference: str | None = Field(default=None, max_length=120)
    payment_observations: str | None = Field(default=None, max_length=500)


class SupplierPaymentResponse(CamelModel):
    id: uuid.UUID
    supplier_invoice_id: uuid.UUID
    treasury_account_id: uuid.UUID
    amount: Decimal
    payment_date: date
    accounting_document_id: uuid.UUID
    reversal_accounting_document_id: uuid.UUID | None = None
    reversed_at: datetime | None = None
    reversed_by_user_id: uuid.UUID | None = None
    reversal_reason: str | None = None
    bank_transaction_reference: str | None = None
    payment_observations: str | None = None


class PaymentPlanItemInput(CamelModel):
    due_date: date
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    note: str | None = Field(default=None, max_length=255)


class PaymentPlanRequest(CamelModel):
    installments: list[PaymentPlanItemInput] = Field(min_length=1)


class PaymentPlanItemResponse(CamelModel):
    id: uuid.UUID
    supplier_invoice_id: uuid.UUID
    sequence: int
    due_date: date
    amount: Decimal
    note: str | None = None
