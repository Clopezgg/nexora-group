import uuid
from datetime import date

from app.schemas.base import CamelModel


class KpiResponse(CamelModel):
    key: str
    label: str
    value: str
    numeric: float
    severity: str
    hint: str
    route: str | None = None


class DailyStatusResponse(CamelModel):
    company_id: uuid.UUID
    as_of: date
    currency_code: str
    fiscal_period_label: str | None
    fiscal_period_status: str | None
    kpis: list[KpiResponse]
