import uuid
from typing import Literal

from pydantic import Field, field_validator

from app.schemas.base import CamelModel


class CompanyCreateRequest(CamelModel):
    name: str = Field(min_length=1, max_length=255)
    code: str | None = Field(default=None, min_length=1, max_length=32)
    legal_name: str | None = Field(default=None, max_length=255)
    functional_currency_code: str | None = Field(default=None, min_length=3, max_length=3)
    country: str | None = Field(default=None, min_length=2, max_length=2)
    fiscal_id: str | None = Field(default=None, max_length=64)


class CompanyUpdateRequest(CamelModel):
    """Company profile update.

    Code and functional currency are one-time configurable when the historic
    company row still has NULL. Once assigned, both remain immutable.
    """

    name: str | None = Field(default=None, min_length=1, max_length=255)
    code: str | None = Field(default=None, min_length=1, max_length=32)
    legal_name: str | None = Field(default=None, max_length=255)
    functional_currency_code: str | None = Field(default=None, min_length=3, max_length=3)
    country: str | None = Field(default=None, min_length=2, max_length=2)
    fiscal_id: str | None = Field(default=None, max_length=64)
    # Identidad de comprobantes (orden maestra Phase 2). El pagador se asigna
    # una sola vez (immutable una vez que la fila deja de tener NULL, mismo
    # patrón que `code`); el aprobador es siempre editable.
    voucher_payer_name: str | None = Field(default=None, min_length=1, max_length=255)
    voucher_approver_name: str | None = Field(default=None, max_length=255)
    default_theme_id: str | None = Field(default=None, max_length=64)
    default_density: str | None = Field(default=None, max_length=16)
    trade_name: str | None = Field(default=None, max_length=255)
    address_line_1: str | None = Field(default=None, max_length=255)
    address_line_2: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, max_length=120)
    state_department: str | None = Field(default=None, max_length=120)
    phone: str | None = Field(default=None, max_length=64)
    email: str | None = Field(default=None, max_length=255)
    website: str | None = Field(default=None, max_length=255)
    voucher_footer_text: str | None = Field(default=None, max_length=500)


class CompanyResponse(CamelModel):
    id: uuid.UUID
    name: str
    code: str | None
    legal_name: str | None
    functional_currency_code: str | None
    country: str | None
    fiscal_id: str | None
    voucher_payer_name: str | None = None
    voucher_approver_name: str | None = None
    default_theme_id: str | None = None
    default_density: str | None = None
    trade_name: str | None = None
    address_line_1: str | None = None
    address_line_2: str | None = None
    city: str | None = None
    state_department: str | None = None
    phone: str | None = None
    email: str | None = None
    website: str | None = None
    voucher_footer_text: str | None = None


class AccountCreateRequest(CamelModel):
    company_id: uuid.UUID
    code: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=255)
    account_type: Literal["ASSET", "LIABILITY", "EQUITY", "REVENUE", "EXPENSE"]
    parent_id: uuid.UUID | None = None
    is_postable: bool = True

    @field_validator("code", "name", mode="before")
    @classmethod
    def strip_account_text(cls, value):
        return value.strip() if isinstance(value, str) else value


class AccountUpdateRequest(CamelModel):
    cash_flow_activity: str | None = None


class AccountResponse(CamelModel):
    id: uuid.UUID
    code: str
    name: str
    account_type: str
    parent_id: uuid.UUID | None
    is_postable: bool
    cash_flow_activity: str | None


class UserCreateRequest(CamelModel):
    company_id: uuid.UUID
    email: str
    full_name: str
    password: str
    role_name: str


class UserResponse(CamelModel):
    id: uuid.UUID
    email: str
    full_name: str
    roles: list[str]


ResourcePostingSource = Literal["FUEL", "MAINTENANCE", "LABOR"]


class ResourcePostingConfigRequest(CamelModel):
    source_type: ResourcePostingSource
    expense_account_id: uuid.UUID
    offset_account_id: uuid.UUID
    active: bool = True


class ResourcePostingConfigResponse(CamelModel):
    id: uuid.UUID
    company_id: uuid.UUID
    source_type: ResourcePostingSource
    expense_account_id: uuid.UUID
    offset_account_id: uuid.UUID
    active: bool
