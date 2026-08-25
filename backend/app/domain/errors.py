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


class InsufficientStockError(Exception):
    """INV-INV-001: intento de emitir/transferir más stock del disponible
    (no hay tal cosa como stock negativo silencioso)."""


class InvalidProcurementStateError(Exception):
    """Transición de estado inválida en el flujo de procurement (p.ej.
    recibir más de lo pendiente en una PO, o registrar un GR sobre una PO
    no aprobada)."""


class ProcurementCurrencyMismatchError(Exception):
    """Una PO de proyecto no puede alimentar compromisos en una moneda
    distinta de la moneda funcional sin una política FX autoritativa."""


class BudgetCurrencyMismatchError(Exception):
    """Un Budget debe usar la moneda funcional de su company mientras no
    exista una política FX autoritativa."""


class BudgetBaselineExistsError(Exception):
    """INV-BUD-001-adyacente: un proyecto solo puede tener un BASELINE; nunca
    se sobrescribe, ver docs/BUDGET_CONTROLLING.md."""


class InvalidChangeOrderStateError(Exception):
    """Transición de estado de ChangeOrder inválida (orden maestra §43)."""


# Track D -- Enterprise Resources (orden maestra §62-66).
class InvalidAssetStateError(Exception):
    """Transición de estado de FixedAsset inválida (p.ej. depreciar un
    activo DISPOSED/RETIRED)."""


class DepreciationAlreadyPostedError(Exception):
    """INV-AST-001: ya existe un DepreciationEntry para ese asset+periodo;
    nunca se genera un segundo posting DEP para el mismo periodo."""


class ImmutableMaintenanceOrderError(Exception):
    """INV-EQP-001: un MaintenanceOrder CLOSED/CANCELLED es terminal -- no se
    permite ninguna mutación posterior, solo lectura."""


class InvalidTimeEntryStateError(Exception):
    """Transición de estado de TimeEntry inválida (p.ej. aprobar/rechazar un
    registro que ya fue decidido)."""


# Track E -- Commercial (orden maestra §72-76).
class InvalidCommercialStateError(Exception):
    """Transición de estado inválida en el flujo comercial (p.ej. convertir
    una Quotation que no está ACCEPTED, o volver a facturar un SalesContract
    ya BILLED)."""


# Track D -- Construction Control: Documents/Evidence (orden maestra
# §77-79, docs/DOCUMENTS_EVIDENCE.md).
class UnsupportedEvidenceMimeTypeError(Exception):
    """El MIME type del archivo subido no está en el allowlist
    (PDF/JPEG/PNG/WEBP). Se rechaza ANTES de llamar a
    get_evidence_container_client() -- nunca se intenta un upload real de
    un archivo no permitido."""


class EvidenceTooLargeError(Exception):
    """El archivo excede `settings.max_evidence_mb`. Se rechaza ANTES de
    llamar a get_evidence_container_client()."""


class InvalidDocumentStateError(Exception):
    """Transición de estado inválida sobre Document/DocumentVersion (p.ej.
    subir una nueva versión sobre un Document ARCHIVED)."""


# Track D -- Construction Control: RFI / Submittals (orden maestra §80,
# NXR-REQ-0085/0086).
class InvalidRfiStateError(Exception):
    """Transición de estado inválida sobre un RequestForInformation (p.ej.
    responder un RFI que ya no está OPEN, o cerrar uno ya CLOSED)."""


class InvalidSubmittalStateError(Exception):
    """Transición de estado inválida sobre un Submittal (p.ej. aprobar/
    rechazar sin una respuesta de revisor previamente registrada, o decidir
    sobre un Submittal que ya tiene una decisión final)."""


# Track D -- Construction Control: Daily Site Reports / Quality / Safety
# (orden maestra §81-84).
class InvalidSiteReportStateError(Exception):
    """Transición de estado inválida de DailySiteReport (p.ej. aprobar uno
    que no está SUBMITTED, o enviar uno que ya fue aprobado)."""


class InvalidQualityStateError(Exception):
    """Transición de estado inválida de NonConformance/CorrectiveAction
    (p.ej. completar una CorrectiveAction ya COMPLETED, o volver a cerrar
    una NonConformance ya CLOSED)."""


class NonConformanceRequiresCorrectiveActionError(Exception):
    """INV-QUALITY-001: una NonConformance no puede cerrarse sin al menos
    una CorrectiveAction registrada."""


class InvalidSafetyRecordError(Exception):
    """INV-SAFETY-001: un SafetyObservation/SafetyIncident de severidad
    HIGH/CRITICAL requiere responsible_user_id -- la severidad determina qué
    campos son obligatorios, nunca al revés."""


class InvalidSafetyStateError(Exception):
    """Transición de estado inválida de SafetyObservation/SafetyIncident
    (p.ej. volver a cerrar un registro ya CLOSED)."""


# Track G -- Platform: Approval Inbox / Segregation of Duties (orden
# maestra §87-89, NXR-REQ-0087/0088/0089).
class SegregationOfDutiesError(Exception):
    """INV-WORKFLOW-001: requested_by == decided_by, o el tercer rol
    exigido por la ApprovalPolicy no fue distinto de solicitante y
    aprobador, al decidir un ApprovalRequest."""


class InvalidApprovalStateError(Exception):
    """Se intentó decidir un ApprovalRequest que ya no está PENDING
    (doble decisión)."""


class InvalidApprovalDecisionError(Exception):
    """`decision` fuera del whitelist {"APPROVED", "REJECTED"} pasado a
    `approval_service.decide()` -- se rechaza ANTES de persistir nada
    sobre el ApprovalRequest ni de llamar al adaptador del dominio, para
    que `ApprovalRequest.status` nunca quede desincronizado del estado
    real de la entidad de dominio (p.ej. un adaptador que solo maneja
    APPROVED/REJECTED haciendo no-op silencioso sobre un valor
    desconocido)."""


# NXR-REQ-0074, Crews.
class CrewMembershipError(Exception):
    """Se intentó agregar un Worker que ya es miembro de la Crew, o quitar
    uno que no lo es."""
