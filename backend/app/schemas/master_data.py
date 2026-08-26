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


class AccountUpdateRequest(CamelModel):
    """NXR-REQ-0016/0093, Cash Flow. Única pieza editable de una cuenta
    post-creación por ahora -- code/name/account_type/parent_id se
    mantienen inmutables (no hay caso de uso real todavía que los
    requiera; el catálogo contable es create-only fuera de esto)."""

    cash_flow_activity: str | None = None


class AccountResponse(CamelModel):
    id: uuid.UUID
    code: str
    name: str
    account_type: str
    parent_id: uuid.UUID | None
    is_postable: bool
    cash_flow_activity: str | None


# DEFERRED-FINAL-015: directorio de usuarios por compañía.
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
