import uuid
from decimal import Decimal

from app.schemas.base import CamelModel


class DocumentLookupHit(CamelModel):
    domain: str
    entity_type: str
    id: str
    number: str
    label: str
    status: str | None = None
    amount: str | None = None
    currency_code: str | None = None
    party: str | None = None
    project_id: str | None = None
    accounting_document_id: str | None = None
    exact: bool = False
    allowed_actions: list[str] = []


class DocumentLookupResponse(CamelModel):
    query: str
    results: list[DocumentLookupHit]


class InspectedLineResponse(CamelModel):
    account_code: str
    account_name: str
    debit: Decimal
    credit: Decimal
    description: str | None
    project_name: str | None
    cost_center_name: str | None


class SourceEventResponse(CamelModel):
    kind: str
    label: str
    reference: str | None
    entity_id: str | None


class InspectionResponse(CamelModel):
    document_id: uuid.UUID
    document_number: str
    document_type_code: str
    scope: str
    status: str
    currency_code: str
    description: str | None
    project_name: str | None
    posted_at: str | None
    total_debit: Decimal
    total_credit: Decimal
    balanced: bool
    source_event: SourceEventResponse
    lines: list[InspectedLineResponse]
    reverses_document_id: uuid.UUID | None
    reversal_reason: str | None
    reversed_by_document_ids: list[uuid.UUID]
    evidence: list[dict]
    contract: dict | None = None
