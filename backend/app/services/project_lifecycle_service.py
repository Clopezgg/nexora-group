"""Project status lifecycle — servicio de negocio único (CORRECTIVA §1-§9).

El ciclo de vida del proyecto es un grafo gobernado, no un dropdown que escribe
cualquier string. Esta es la ÚNICA fuente de verdad: la usa el endpoint de
transición y el endpoint de lifecycle que el frontend consulta para pintar las
acciones permitidas.

`CLOSED` / `CANCELLED` / `ARCHIVED` NO destruyen nada: contratos, facturas,
pagos, AccountingDocuments, Evidence y Audit permanecen. `ARCHIVED` es
soft-delete empresarial.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.business_time import business_today
from app.models.project import Project

STATUS_LABELS_ES: dict[str, str] = {
    "PLANNING": "Planificación",
    "ACTIVE": "Activo",
    "ON_HOLD": "Pausado",
    "COMPLETED": "Completado",
    "CLOSED": "Cerrado",
    "CANCELLED": "Cancelado",
    "ARCHIVED": "Archivado",
}

# Transiciones normales (permiso `project:create`).
_TRANSITIONS: dict[str, set[str]] = {
    "PLANNING": {"ACTIVE", "CANCELLED", "ARCHIVED"},
    "ACTIVE": {"ON_HOLD", "COMPLETED", "CANCELLED", "ARCHIVED"},
    "ON_HOLD": {"ACTIVE", "CANCELLED", "ARCHIVED"},
    "COMPLETED": {"CLOSED", "ACTIVE", "CANCELLED", "ARCHIVED"},
    "CLOSED": {"ACTIVE", "COMPLETED", "ARCHIVED"},
    "CANCELLED": {"ACTIVE", "PLANNING", "ARCHIVED"},
    # ARCHIVED sólo restaura a su estado previo (se resuelve dinámicamente).
    "ARCHIVED": set(),
}

# Transiciones sensibles: exigen motivo (>=10 car.) + permiso
# `project.lifecycle:manage` + AuditLog. Reabrir/restaurar/archivar-con-actividad.
_SENSITIVE: set[tuple[str, str]] = {
    ("COMPLETED", "ACTIVE"),
    ("COMPLETED", "CANCELLED"),
    ("CLOSED", "ACTIVE"),
    ("CLOSED", "COMPLETED"),
    ("CANCELLED", "ACTIVE"),
    ("CANCELLED", "PLANNING"),
    ("PLANNING", "ARCHIVED"),
    ("ACTIVE", "ARCHIVED"),
    ("ON_HOLD", "ARCHIVED"),
    ("COMPLETED", "ARCHIVED"),
    ("CLOSED", "ARCHIVED"),
    ("CANCELLED", "ARCHIVED"),
}

_MIN_REASON_LEN = 10


class ProjectTransitionError(Exception):
    """Transición de proyecto no permitida o mal formada (→ 409/422)."""


@dataclass(frozen=True)
class TransitionResult:
    project: Project
    before_status: str
    after_status: str
    changed: bool
    was_sensitive: bool


def allowed_transitions(project: Project) -> list[str]:
    """Targets válidos desde el estado actual. Para ARCHIVED, restaura al estado
    previo guardado (o PLANNING por defecto)."""
    if project.status == "ARCHIVED":
        target = project.status_before_archive or "PLANNING"
        return [target]
    return sorted(_TRANSITIONS.get(project.status, set()))


def is_sensitive(current: str, target: str) -> bool:
    if current == "ARCHIVED":
        return True  # toda restauración desde ARCHIVED es sensible
    return (current, target) in _SENSITIVE


def lifecycle_view(project: Project) -> dict:
    return {
        "current_status": project.status,
        "current_status_label": STATUS_LABELS_ES.get(project.status, project.status),
        "allowed_transitions": [
            {
                "status": t,
                "label": STATUS_LABELS_ES.get(t, t),
                "sensitive": is_sensitive(project.status, t),
            }
            for t in allowed_transitions(project)
        ],
        "completed_at": project.completed_at.isoformat() if project.completed_at else None,
        "closed_at": project.closed_at.isoformat() if project.closed_at else None,
        "reopened_at": project.reopened_at.isoformat() if project.reopened_at else None,
        "archived_at": project.archived_at.isoformat() if project.archived_at else None,
    }


def apply_transition(
    *,
    project: Project,
    target: str,
    reason: str | None,
    has_lifecycle_permission: bool,
) -> TransitionResult:
    """Aplica la transición sobre el objeto en memoria (no hace commit).

    - Mismo estado (idempotente): devuelve el recurso sin cambios ni audit.
    - Transición inexistente: `ProjectTransitionError`.
    - Transición sensible sin motivo o sin permiso: `ProjectTransitionError`.
    """
    current = project.status
    if target == current:
        return TransitionResult(project, current, current, changed=False, was_sensitive=False)

    if target not in allowed_transitions(project):
        raise ProjectTransitionError(
            f"El proyecto está en «{STATUS_LABELS_ES.get(current, current)}» y no puede "
            f"pasar a «{STATUS_LABELS_ES.get(target, target)}»."
        )

    sensitive = is_sensitive(current, target)
    if sensitive:
        clean = (reason or "").strip()
        if len(clean) < _MIN_REASON_LEN:
            raise ProjectTransitionError(
                "Esta acción requiere un motivo de al menos "
                f"{_MIN_REASON_LEN} caracteres."
            )
        if not has_lifecycle_permission:
            raise ProjectTransitionError(
                "No tienes el permiso project.lifecycle:manage para reabrir, "
                "restaurar o archivar un proyecto."
            )

    today = business_today()

    if current == "ARCHIVED":
        # Restauración: volvemos al estado previo, conservamos historia.
        project.archived_at = None
        project.status_before_archive = None
        project.reopened_at = today
    elif target == "ARCHIVED":
        project.status_before_archive = current
        project.archived_at = today
    else:
        if target == "COMPLETED":
            if project.completed_at is None:
                project.completed_at = today
            if project.actual_end is None:
                project.actual_end = today
        elif target == "CLOSED":
            if project.closed_at is None:
                project.closed_at = today
            if project.actual_end is None:
                project.actual_end = today
        elif current in {"COMPLETED", "CLOSED", "CANCELLED"} and target in {"ACTIVE", "PLANNING"}:
            project.reopened_at = today

    project.status = target
    return TransitionResult(project, current, target, changed=True, was_sensitive=sensitive)
