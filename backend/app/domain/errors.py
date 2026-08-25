class InvalidCredentialsError(Exception):
    pass


class NotAuthenticatedError(Exception):
    pass


class NotAuthorizedError(Exception):
    """Usuario autenticado pero sin permiso para la acción (INV-COMP-001,
    motor de permisos)."""


class UnbalancedJournalEntryError(Exception):
    """INV-ACC-001: total débito != total crédito."""


class ImmutableDocumentError(Exception):
    """INV-ACC-002: intento de mutar/eliminar un AccountingDocument posted."""


class FiscalPeriodClosedError(Exception):
    """INV-ACC-003: intento de postear en un período fiscal CLOSED."""


class InvalidOperationScopeError(Exception):
    """INV-OPS-*: combinación scope/project_id inválida."""


class IdempotencyConflictError(Exception):
    """INV-IDEM-002: misma idempotency key con payload distinto."""


class InvalidTransferError(Exception):
    """Track A: transferencia de tesorería inválida (misma cuenta origen/
    destino, moneda incompatible, etc.)."""


class InvalidInvoiceStateError(Exception):
    """Track A: transición de estado inválida sobre SupplierInvoice/
    CustomerInvoice (p.ej. pagar una factura CANCELLED)."""


class OverpaymentError(Exception):
    """Track A: un pago/cobro excede el saldo pendiente de la factura."""


class InvalidFinancialReferenceError(Exception):
    """Track A: una FK financiera no pertenece a la compañía propietaria."""
