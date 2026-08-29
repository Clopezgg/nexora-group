import uuid
from decimal import Decimal

from pydantic import Field

from app.schemas.base import CamelModel


class ReversalRequest(CamelModel):
    reason: str = Field(min_length=3, max_length=1000)


class BusinessReversalResponse(CamelModel):
    original_id: uuid.UUID
    invoice_id: uuid.UUID
    original_accounting_document_id: uuid.UUID
    reversal_accounting_document_id: uuid.UUID
    invoice_status: str
    applied_amount_after_reversal: Decimal
