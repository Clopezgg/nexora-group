import uuid
from datetime import date, datetime
from decimal import Decimal

from app.schemas.base import CamelModel


class BankStatementResponse(CamelModel):
    id: uuid.UUID
    treasury_account_id: uuid.UUID
    statement_date: date
    opening_balance: Decimal
    closing_balance: Decimal
    reference: str | None


class ReconciliationMatchResponse(CamelModel):
    id: uuid.UUID
    bank_statement_line_id: uuid.UUID
    accounting_document_id: uuid.UUID
    matched_amount: Decimal
    matched_by_user_id: uuid.UUID
    matched_at: datetime


class ReconciliationCandidateResponse(CamelModel):
    accounting_document_id: uuid.UUID
    document_number: str
    document_type_code: str
    description: str | None
    available_amount: Decimal
    exact_match: bool


class TreasuryAvailabilityResponse(CamelModel):
    treasury_account_id: uuid.UUID
    balance: Decimal
    reserved_amount: Decimal
    available_amount: Decimal
