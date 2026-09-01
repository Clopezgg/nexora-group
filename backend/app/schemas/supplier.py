import uuid
from datetime import date
from decimal import Decimal

from pydantic import Field, field_validator

from app.models.supplier import (
    SUPPLIER_CONTRACT_CATEGORIES,
    SUPPLIER_PARTY_ROLES,
    SUPPLIER_STATUSES,
)
from app.schemas.base import CamelModel


def _validate_party_role(value: str) -> str:
    if value not in SUPPLIER_PARTY_ROLES:
        raise ValueError(f"party_role debe ser uno de {SUPPLIER_PARTY_ROLES}")
    return value


class SupplierCreateRequest(CamelModel):
    company_id: uuid.UUID
    legal_name: str
    trade_name: str | None = None
    tax_id: str | None = None
    contact_name: str | None = None
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    address_line_1: str | None = None
    address_line_2: str | None = None
    city: str | None = None
    state_department: str | None = None
    country: str | None = None
    party_role: str = "SUPPLIER"
    classification: str | None = None
    payment_terms: str | None = None
    banking_details: dict | None = None

    _pr = field_validator("party_role")(classmethod(lambda cls, v: _validate_party_role(v)))


class SupplierUpdateRequest(CamelModel):
    legal_name: str | None = Field(default=None, min_length=1, max_length=255)
    trade_name: str | None = None
    tax_id: str | None = None
    contact_name: str | None = None
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    address_line_1: str | None = None
    address_line_2: str | None = None
    city: str | None = None
    state_department: str | None = None
    country: str | None = None
    party_role: str | None = None
    classification: str | None = None
    payment_terms: str | None = None
    banking_details: dict | None = None

    @field_validator("party_role")
    @classmethod
    def _pr(cls, v: str | None) -> str | None:
        return None if v is None else _validate_party_role(v)


class SupplierStatusChangeRequest(CamelModel):
    status: str
    reason: str | None = Field(default=None, max_length=1000)

    @field_validator("status")
    @classmethod
    def _status(cls, v: str) -> str:
        if v not in SUPPLIER_STATUSES:
            raise ValueError(f"status debe ser uno de {SUPPLIER_STATUSES}")
        return v


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
    address_line_1: str | None = None
    address_line_2: str | None = None
    city: str | None = None
    state_department: str | None = None
    country: str | None = None
    status: str
    party_role: str = "SUPPLIER"
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
    payment_terms_type: str = "LUMP_SUM"

    @field_validator("payment_terms_type")
    @classmethod
    def _validate_payment_terms_type(cls, value: str) -> str:
        if value not in ("LUMP_SUM", "MONTHLY", "CUSTOM"):
            raise ValueError(
                "payment_terms_type debe ser LUMP_SUM, MONTHLY o CUSTOM"
            )
        return value

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
    payment_terms_type: str
    status: str
