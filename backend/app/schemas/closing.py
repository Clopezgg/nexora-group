import uuid

from app.schemas.base import CamelModel


class ClosingCheckResponse(CamelModel):
    key: str
    label: str
    passed: bool
    blocking: bool
    detail: str


class PreCloseChecklistResponse(CamelModel):
    period_id: uuid.UUID
    period_label: str
    period_status: str
    can_hard_close: bool
    checks: list[ClosingCheckResponse]


class HardCloseRequest(CamelModel):
    force: bool = False
    reason: str | None = None


class ClosingManifestResponse(CamelModel):
    period_id: uuid.UUID
    period_label: str
    company_id: uuid.UUID
    closed_at: str
    forced: bool
    force_reason: str | None
    checks: list[ClosingCheckResponse]
