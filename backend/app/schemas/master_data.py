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


class CompanyResponse(CamelModel):
    id: uuid.UUID
    name: str
    code: str | None
    legal_name: str | None
    functional_currency_code: str | None
    country: str | None
    fiscal_id: str | None


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
