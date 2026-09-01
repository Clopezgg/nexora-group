import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.core.logging import get_correlation_id
from app.domain.errors import (
    BudgetBaselineExistsError,
    BudgetCurrencyMismatchError,
    CrewMembershipError,
    DepreciationAlreadyPostedError,
    EvidenceStorageAccessError,
    EvidenceStorageAuthError,
    EvidenceStorageTemporaryError,
    EvidenceTooLargeError,
    FiscalPeriodClosedError,
    IdempotencyConflictError,
    ImmutableDocumentError,
    ImmutableMaintenanceOrderError,
    InsufficientStockError,
    InvalidAssetStateError,
    InvalidEquipmentStatusError,
    InvalidChangeOrderStateError,
    InvalidCommercialStateError,
    InvalidDocumentStateError,
    InvalidFinancialReferenceError,
    InvalidInvoiceStateError,
    InvalidOperationScopeError,
    InvalidProcurementStateError,
    InvalidQualityStateError,
    InvalidApprovalDecisionError,
    InvalidApprovalStateError,
    InvalidRfiStateError,
    InvalidSafetyRecordError,
    InvalidSafetyStateError,
    InvalidSiteReportStateError,
    InvalidSubmittalStateError,
    InvalidTimeEntryStateError,
    InvalidTransferError,
    NonConformanceRequiresCorrectiveActionError,
    NotAuthorizedError,
    OverpaymentError,
    ProcurementCurrencyMismatchError,
    RateLimitExceededError,
    SegregationOfDutiesError,
    InvalidCashFlowActivityError,
    RoleNotFoundError,
    TaxCodeExistsError,
    UserEmailExistsError,
    UnbalancedJournalEntryError,
    UnsupportedEvidenceMimeTypeError,
    VoucherNotOutflowError,
    NotFoundError,
)
from app.integrations.azure_blob import EvidenceStorageNotConfigured

"""API error standard (orden maestra §108): {"error": {"code", "message",
"field", "correlationId"}}. Cubre NXR-ACCOUNTING/NXR-IDEMPOTENCY/NXR-PERM
(Track 1) + NXR-TREASURY/NXR-AP/NXR-AR (Track A) -- el resto de familias
(NXR-AUTH, NXR-MASTER, NXR-PROJECT, NXR-BUDGET, NXR-PROCUREMENT,
NXR-INVENTORY, NXR-WORKFLOW, NXR-INTEGRATION) las registra cada track
dueño cuando construye las excepciones de su propio dominio, con el mismo
patrón."""

_ERROR_CODES: dict[type[Exception], tuple[str, int]] = {
    UnbalancedJournalEntryError: ("NXR-ACCOUNTING-001", 422),
    InvalidOperationScopeError: ("NXR-ACCOUNTING-002", 422),
    FiscalPeriodClosedError: ("NXR-ACCOUNTING-003", 409),
    ImmutableDocumentError: ("NXR-ACCOUNTING-004", 409),
    IdempotencyConflictError: ("NXR-IDEMPOTENCY-001", 409),
    NotAuthorizedError: ("NXR-PERM-001", 403),
    InvalidTransferError: ("NXR-TREASURY-001", 422),
    VoucherNotOutflowError: ("NXR-VOUCHER-NOT-OUTFLOW", 422),
    InvalidInvoiceStateError: ("NXR-AP-001", 409),
    OverpaymentError: ("NXR-AP-002", 422),
    InvalidFinancialReferenceError: ("NXR-FINANCIAL-001", 422),
    InsufficientStockError: ("NXR-INVENTORY-001", 409),
    InvalidProcurementStateError: ("NXR-PROCUREMENT-001", 409),
    ProcurementCurrencyMismatchError: ("NXR-PROCUREMENT-002", 409),
    BudgetBaselineExistsError: ("NXR-BUDGET-001", 409),
    BudgetCurrencyMismatchError: ("NXR-BUDGET-002", 409),
    InvalidChangeOrderStateError: ("NXR-PROJECT-001", 409),
    InvalidAssetStateError: ("NXR-ASSET-001", 409),
    DepreciationAlreadyPostedError: ("NXR-ASSET-002", 409),
    ImmutableMaintenanceOrderError: ("NXR-EQUIPMENT-001", 409),
    InvalidEquipmentStatusError: ("NXR-EQUIPMENT-002", 422),
    InvalidTimeEntryStateError: ("NXR-WORKFORCE-001", 409),
    CrewMembershipError: ("NXR-WORKFORCE-002", 409),
    TaxCodeExistsError: ("NXR-TAX-001", 409),
    UserEmailExistsError: ("NXR-USER-001", 409),
    RoleNotFoundError: ("NXR-USER-002", 422),
    InvalidCashFlowActivityError: ("NXR-ACCOUNTING-005", 422),
    InvalidCommercialStateError: ("NXR-CRM-001", 409),
    UnsupportedEvidenceMimeTypeError: ("NXR-EVIDENCE-002", 422),
    EvidenceTooLargeError: ("NXR-EVIDENCE-003", 422),
    EvidenceStorageNotConfigured: ("NXR-EVIDENCE-001", 503),
    EvidenceStorageAuthError: ("NXR-EVIDENCE-STORAGE-AUTH", 503),
    EvidenceStorageTemporaryError: ("NXR-EVIDENCE-STORAGE-TEMPORARY", 503),
    EvidenceStorageAccessError: ("NXR-EVIDENCE-STORAGE-ACCESS", 503),
    InvalidDocumentStateError: ("NXR-DOCUMENT-001", 409),
    InvalidRfiStateError: ("NXR-RFI-001", 409),
    InvalidSubmittalStateError: ("NXR-SUBMITTAL-001", 409),
    InvalidSiteReportStateError: ("NXR-SITE-001", 409),
    InvalidQualityStateError: ("NXR-QUALITY-001", 409),
    NonConformanceRequiresCorrectiveActionError: ("NXR-QUALITY-002", 409),
    InvalidSafetyRecordError: ("NXR-SAFETY-001", 422),
    InvalidSafetyStateError: ("NXR-SAFETY-002", 409),
    SegregationOfDutiesError: ("NXR-WORKFLOW-001", 422),
    InvalidApprovalStateError: ("NXR-WORKFLOW-002", 409),
    InvalidApprovalDecisionError: ("NXR-WORKFLOW-003", 422),
    RateLimitExceededError: ("NXR-SECURITY-001", 429),
    NotFoundError: ("NXR-DATA-002", 404),
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
                    "correlationId": get_correlation_id(),
                }
            },
        )

    return _handler


_logger = logging.getLogger(__name__)


async def _integrity_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    """Red de seguridad genérica (DEFERRED-FINAL-015): cualquier FK/unique
    de PostgreSQL violada que no pasó por un `assert_*_belongs_to_company`
    específico llega aquí en vez de tumbarse como un 500 sin controlar. El
    mensaje real de psycopg (nombres de tabla/columna) se loguea, nunca se
    devuelve al cliente."""
    _logger.warning("Unhandled IntegrityError: %s", exc)
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "NXR-DATA-001",
                "message": "La operación viola una restricción de datos (referencia inexistente o duplicada)",
                "field": None,
                "correlationId": get_correlation_id(),
            }
        },
    )


def register_error_handlers(app: FastAPI) -> None:
    for exc_type, (code, status_code) in _ERROR_CODES.items():
        app.add_exception_handler(exc_type, _make_handler(code, status_code))
    app.add_exception_handler(IntegrityError, _integrity_error_handler)
