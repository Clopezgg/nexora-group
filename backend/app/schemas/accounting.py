import uuid
from datetime import date
from decimal import Decimal

from app.schemas.base import CamelModel


class JournalLineRequest(CamelModel):
    account_id: uuid.UUID
    debit_amount: Decimal = Decimal("0")
    credit_amount: Decimal = Decimal("0")
    description: str | None = None
    project_id: uuid.UUID | None = None
    cost_center_id: uuid.UUID | None = None


class JournalEntryCreateRequest(CamelModel):
    company_id: uuid.UUID
    scope: str
    project_id: uuid.UUID | None = None
    currency_code: str
    fx_rate: Decimal = Decimal("1")
    description: str | None = None
    # Fecha ECONÓMICA del hecho (ORDEN MAESTRA §28). Si se omite, el motor usa
    # la fecha de negocio actual. El reporting económico agrupa por esta fecha,
    # nunca por el timestamp técnico de contabilización.
    effective_date: date | None = None
    lines: list[JournalLineRequest]


class JournalLineResponse(CamelModel):
    id: uuid.UUID
    account_id: uuid.UUID
    debit_amount: Decimal
    credit_amount: Decimal
    description: str | None
    project_id: uuid.UUID | None
    cost_center_id: uuid.UUID | None


class JournalEntryResponse(CamelModel):
    id: uuid.UUID
    document_number: str
    document_type_code: str
    company_id: uuid.UUID
    scope: str
    project_id: uuid.UUID | None
    currency_code: str
    fx_rate: Decimal
    status: str
    description: str | None
    effective_date: date | None = None
    lines: list[JournalLineResponse]


class JournalEntryReverseRequest(CamelModel):
    reason: str
