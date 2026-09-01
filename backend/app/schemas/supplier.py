import uuid
from datetime import date
from decimal import Decimal

from pydantic import field_validator

from app.models.supplier import SUPPLIER_CONTRACT_CATEGORIES
from app.schemas.base import CamelModel


class SupplierCreateRequest(CamelModel):
    company_id: uuid.UUID
    legal_name: str
    trade_name: str | None = None
    tax_id: str | None = None
    contact_name: str | None = None
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    classification: str | None = None
    payment_terms: str | None = None
    banking_details: dict | None = None


class SupplierResponse(CamelModel):
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
    classification: str | None
    payment_terms: str | None
    qualification: str | None


class SupplierContractCreateRequest(CamelModel):
    company_id: uuid.UUID
    supplier_id: uuid.UUID
    project_id: uuid.UUID | None = None
    contract_number: str
    contract_category: str = "OTHER"
    scope_description: str | None = None
    value: Decimal
    currency_code: str
    start_date: date
    end_date: date | None = None
    advance_percentage: Decimal = Decimal("0")
    retention_percentage: Decimal = Decimal("0")
    payment_terms: str | None = None

    @field_validator("contract_category")
    @classmethod
    def _validate_category(cls, value: str) -> str:
        if value not in SUPPLIER_CONTRACT_CATEGORIES:
            raise ValueError(
                f"contract_category inválida: {value!r}. "
                f"Debe ser una de {SUPPLIER_CONTRACT_CATEGORIES}"
            )
        return value


class SupplierContractResponse(CamelModel):
    id: uuid.UUID
    company_id: uuid.UUID
    supplier_id: uuid.UUID
    project_id: uuid.UUID | None
    contract_number: str
    contract_category: str
    scope_description: str | None
    value: Decimal
    currency_code: str
    start_date: date
    end_date: date | None
    advance_percentage: Decimal
    retention_percentage: Decimal
    payment_terms: str | None
    status: str
