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


class InsufficientStockError(Exception):
    """INV-INV-001: intento de emitir/transferir más stock del disponible
    (no hay tal cosa como stock negativo silencioso)."""


class InvalidProcurementStateError(Exception):
    """Transición de estado inválida en el flujo de procurement (p.ej.
    recibir más de lo pendiente en una PO, o registrar un GR sobre una PO
    no aprobada)."""
