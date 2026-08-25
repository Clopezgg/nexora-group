import uuid

from app.schemas.base import CamelModel


class CompanyCreateRequest(CamelModel):
    name: str
    code: str | None = None
    legal_name: str | None = None
    functional_currency_code: str | None = None
    country: str | None = None
    fiscal_id: str | None = None


class CompanyUpdateRequest(CamelModel):
    """Solo legal_name/fiscal_id son editables desde Settings -- code y
    functional_currency_code son inmutables post-creación (CLAUDE.md)."""

    legal_name: str | None = None
    fiscal_id: str | None = None


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
    code: str
    name: str
    account_type: str
    parent_id: uuid.UUID | None = None


class AccountResponse(CamelModel):
    id: uuid.UUID
    code: str
    name: str
    account_type: str
    parent_id: uuid.UUID | None
    is_postable: bool
