from decimal import Decimal

from app.schemas.base import CamelModel


class ReconciliationLineResponse(CamelModel):
    subledger: str
    subledger_total: Decimal
    gl_total: Decimal
    difference: Decimal
    reconciled: bool
    detail: str


class SubledgerGlReconciliationResponse(CamelModel):
    all_reconciled: bool
    lines: list[ReconciliationLineResponse]
