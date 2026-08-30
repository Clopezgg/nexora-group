import uuid
from collections.abc import Callable
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.domain.errors import (
    InvalidApprovalDecisionError,
    InvalidApprovalStateError,
    NotAuthorizedError,
    SegregationOfDutiesError,
)
from app.models.approval_policy import ApprovalPolicy
from app.models.approval_request import ApprovalRequest
from app.repositories import approval_repository
from app.services import notification_service

# Mismo patrón que submittal_service.py::SUBMITTAL_DECISIONS -- whitelist
# explícito, no un enum de dominio separado por módulo. `decide()` valida
# contra esto ANTES de tocar la base de datos (ver InvalidApprovalDecisionError):
# la validación de Pydantic en la ruta (`Literal["APPROVED", "REJECTED"]`)
# cubre el caso HTTP, pero `decide()` es también un entry point de servicio
# llamado directamente por otro código (Task 3, tests) que no pasa por la
# ruta -- no se puede confiar solo en la capa de schema.
APPROVAL_DECISIONS = ("APPROVED", "REJECTED")

"""Approval Inbox (Track G / Platform, NXR-REQ-0087/0088/0089). Segregación
de funciones (INV-WORKFLOW-001): `requested_by != decided_by` siempre; si
la ApprovalPolicy resuelta exige `requires_third_role`, el `executed_by`
(quien luego ejecuta la acción aprobada, p.ej. libera un pago) también debe
ser distinto de ambos. `decide()` nunca muta el estado del dominio
directamente -- llama al adaptador registrado por el módulo dueño de
`entity_type` (ver `register_decision_adapter`), que a su vez llama a la
función de transición real y ya probada de ese dominio."""

# Per-module decision adapters: entity_type -> callable(db, entity_id,
# decision, decided_by) -> None. Registered explicitly here rather than via
# a dynamic plugin mechanism -- matches this codebase's preference for
# explicit over magic (ver main.py::create_app). `decided_by` se pasa
# porque algunos dominios (p.ej. Submittal) registran quién decidió sobre
# su propia fila -- no todos los adaptadores lo necesitan, pero el
# contrato es uniforme para los tres parámetros de negocio siempre
# disponibles en decide().
DecisionAdapter = Callable[[Session, uuid.UUID, str, uuid.UUID], None]
_DECISION_ADAPTERS: dict[str, DecisionAdapter] = {}


def register_decision_adapter(entity_type: str, adapter: DecisionAdapter) -> None:
    _DECISION_ADAPTERS[entity_type] = adapter


def create_request(
    db: Session,
    *,
    policy_id: uuid.UUID | None,
    entity_type: str,
    entity_id: uuid.UUID,
    company_id: uuid.UUID,
    requested_by: uuid.UUID,
    module: str,
    assigned_to: uuid.UUID | None = None,
    assigned_role: str | None = None,
    priority: str = "NORMAL",
    amount: Decimal | None = None,
    project_id: uuid.UUID | None = None,
) -> ApprovalRequest:
    request = approval_repository.create(
        db,
        policy_id=policy_id,
        entity_type=entity_type,
        entity_id=entity_id,
        company_id=company_id,
        project_id=project_id,
        module=module,
        requested_by=requested_by,
        assigned_to=assigned_to,
        assigned_role=assigned_role,
        priority=priority,
        amount=amount,
        status="PENDING",
    )
    # Notifica a `assigned_to` -- si la solicitud solo tiene `assigned_role`
    # (sin un usuario puntual todavía), no hay destinatario único a quien
    # notificar; ese caso queda para cuando el inbox resuelva el rol a un
    # usuario concreto, no se inventa un fan-out a todo el rol aquí.
    if assigned_to is not None:
        notification_service.notify(
            db,
            recipient_user_id=assigned_to,
            type="approval.assigned",
            title="Nueva aprobación pendiente",
            body=f"Tienes una solicitud de aprobación de {module} esperando tu decisión",
            entity_type=entity_type,
            entity_id=entity_id,
        )
    return request


def decide(
    db: Session,
    *,
    request_id: uuid.UUID,
    decided_by: uuid.UUID,
    decision: str,
    comment: str | None = None,
    executed_by: uuid.UUID | None = None,
) -> ApprovalRequest:
    if decision not in APPROVAL_DECISIONS:
        raise InvalidApprovalDecisionError(
            f"decision inválida: {decision!r} (debe ser uno de {APPROVAL_DECISIONS})"
        )
    request = approval_repository.get_for_update(db, request_id=request_id)
    if request.status != "PENDING":
        raise InvalidApprovalStateError(
            f"ApprovalRequest {request_id} ya fue decidido (estado: {request.status})"
        )
    if not approval_repository.user_matches_assignment(
        db, request=request, user_id=decided_by
    ):
        raise NotAuthorizedError(
            "La solicitud de aprobación está asignada a otro usuario o rol"
        )
    if request.requested_by == decided_by:
        raise SegregationOfDutiesError(
            "El solicitante no puede decidir su propia solicitud de aprobación"
        )
    policy = db.get(ApprovalPolicy, request.policy_id) if request.policy_id else None
    if policy is not None and policy.requires_third_role:
        if executed_by is not None and executed_by in (request.requested_by, decided_by):
            raise SegregationOfDutiesError(
                "Esta política exige un tercer rol distinto de solicitante y aprobador"
            )

    request.status = decision
    request.decided_by = decided_by
    request.comment = comment
    request.decided_at = datetime.now(timezone.utc)

    adapter = _DECISION_ADAPTERS.get(request.entity_type)
    if adapter is not None:
        adapter(db, request.entity_id, decision, decided_by)

    db.flush()

    decision_label = "aprobada" if decision == "APPROVED" else "rechazada"
    notification_service.notify(
        db,
        recipient_user_id=request.requested_by,
        type="approval.decided",
        title="Tu solicitud de aprobación fue decidida",
        body=f"Tu solicitud de {request.module} fue {decision_label}",
        entity_type=request.entity_type,
        entity_id=request.entity_id,
    )

    return request
