import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.domain.errors import (
    BudgetBaselineExistsError,
    BudgetCurrencyMismatchError,
    FiscalPeriodClosedError,
    IdempotencyConflictError,
    ImmutableDocumentError,
    InsufficientStockError,
    InvalidChangeOrderStateError,
    InvalidOperationScopeError,
    InvalidProcurementStateError,
    NotAuthorizedError,
    ProcurementCurrencyMismatchError,
    UnbalancedJournalEntryError,
)

"""API error standard (orden maestra §108): {"error": {"code", "message",
"field", "correlationId"}}. Solo cubre las familias NXR-ACCOUNTING/
NXR-IDEMPOTENCY/NXR-PERM que ya tienen excepciones de dominio reales en
este track -- el resto de familias (NXR-AUTH, NXR-MASTER, NXR-TREASURY,
NXR-AP, NXR-AR, NXR-PROJECT, NXR-BUDGET, NXR-PROCUREMENT, NXR-INVENTORY,
NXR-WORKFLOW, NXR-INTEGRATION) las registra cada track cuando construye
las excepciones de su propio dominio, usando el mismo patrón."""

_ERROR_CODES: dict[type[Exception], tuple[str, int]] = {
    UnbalancedJournalEntryError: ("NXR-ACCOUNTING-001", 422),
    InvalidOperationScopeError: ("NXR-ACCOUNTING-002", 422),
    FiscalPeriodClosedError: ("NXR-ACCOUNTING-003", 409),
    ImmutableDocumentError: ("NXR-ACCOUNTING-004", 409),
    IdempotencyConflictError: ("NXR-IDEMPOTENCY-001", 409),
    NotAuthorizedError: ("NXR-PERM-001", 403),
    InsufficientStockError: ("NXR-INVENTORY-001", 409),
    InvalidProcurementStateError: ("NXR-PROCUREMENT-001", 409),
    ProcurementCurrencyMismatchError: ("NXR-PROCUREMENT-002", 409),
    BudgetBaselineExistsError: ("NXR-BUDGET-001", 409),
    BudgetCurrencyMismatchError: ("NXR-BUDGET-002", 409),
    InvalidChangeOrderStateError: ("NXR-PROJECT-001", 409),
}


def _make_handler(code: str, status_code: int):
    async def _handler(_request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=status_code,
            content={
                "error": {
                    "code": code,
                    "message": str(exc),
                    "field": None,
                    "correlationId": str(uuid.uuid4()),
                }
            },
        )

    return _handler


def register_error_handlers(app: FastAPI) -> None:
    for exc_type, (code, status_code) in _ERROR_CODES.items():
        app.add_exception_handler(exc_type, _make_handler(code, status_code))
