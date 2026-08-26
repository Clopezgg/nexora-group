import uuid
from decimal import Decimal

from pydantic import Field

from app.schemas.base import CamelModel


class TaxCodeCreateRequest(CamelModel):
    company_id: uuid.UUID
    code: str
    name: str
    rate_percent: Decimal = Field(ge=0, le=100, max_digits=5, decimal_places=2)


class TaxCodeResponse(CamelModel):
    id: uuid.UUID
    company_id: uuid.UUID
    code: str
    name: str
    rate_percent: Decimal
