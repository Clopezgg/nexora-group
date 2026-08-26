import uuid
from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from app.domain.errors import InvalidSafetyRecordError, InvalidSafetyStateError
from app.models.safety import SAFETY_SEVERITIES, SAFETY_SEVERITIES_REQUIRING_RESPONSIBLE, SafetyIncident, SafetyObservation
from app.repositories import safety_repository
from app.services.financial_validation_service import (
    assert_evidence_belongs_to_company,
    assert_user_belongs_to_company,
)

"""Safety: Observation / Incident (bloque CONSTRUCTION CONTROL, orden
maestra §84, NXR-REQ-0084).

INV-SAFETY-001: la severidad determina qué campos son obligatorios. Un
registro HIGH/CRITICAL sin `responsible_user_id` se rechaza ANTES de
persistir (mismo criterio "rechazo antes de cualquier db.add/flush" que
`assert_evidence_belongs_to_company`); un LOW/MEDIUM no lo exige. Esta
misma regla también vive como CHECK constraint real en PostgreSQL
(defensa en profundidad, ver app/models/safety.py)."""


def _assert_severity_requires_responsible(
    severity: str, responsible_user_id: uuid.UUID | None
) -> None:
    if severity not in SAFETY_SEVERITIES:
        raise InvalidSafetyRecordError(f"severity inválida: {severity!r}")
    if severity in SAFETY_SEVERITIES_REQUIRING_RESPONSIBLE and responsible_user_id is None:
        raise InvalidSafetyRecordError(
            f"severity={severity} requiere responsible_user_id"
        )


def create_observation(
    db: Session,
    *,
    project_id: uuid.UUID,
    company_id: uuid.UUID,
    observation_date: date,
    category: str,
    description: str,
    severity: str,
    responsible_user_id: uuid.UUID | None,
    corrective_action: str | None,
    evidence_id: uuid.UUID | None,
    commit: bool = True,
) -> SafetyObservation:
    _assert_severity_requires_responsible(severity, responsible_user_id)
    assert_evidence_belongs_to_company(db, evidence_id=evidence_id, company_id=company_id)
    assert_user_belongs_to_company(db, user_id=responsible_user_id, company_id=company_id)
    observation = safety_repository.create_observation(
        db,
        project_id=project_id,
        observation_date=observation_date,
        category=category,
        description=description,
        severity=severity,
        responsible_user_id=responsible_user_id,
        corrective_action=corrective_action,
        evidence_id=evidence_id,
    )
    if commit:
        db.commit()
        db.refresh(observation)
    else:
        db.flush()
    return observation


def get_observation(db: Session, observation_id: uuid.UUID) -> SafetyObservation | None:
    return safety_repository.get_observation(db, observation_id)


def list_observations(db: Session, *, project_id: uuid.UUID) -> list[SafetyObservation]:
    return safety_repository.list_observations_for_project(db, project_id)


def close_observation(db: Session, *, observation_id: uuid.UUID, commit: bool = True) -> SafetyObservation:
    observation = safety_repository.get_observation(db, observation_id)
    if observation is None:
        raise ValueError(f"SafetyObservation {observation_id} no existe")
    if observation.status != "OPEN":
        raise InvalidSafetyStateError(
            f"Solo se puede cerrar un SafetyObservation OPEN (estado actual: {observation.status})"
        )
    observation.status = "CLOSED"
    observation.closed_at = datetime.now(timezone.utc)
    if commit:
        db.commit()
        db.refresh(observation)
    else:
        db.flush()
    return observation


def create_incident(
    db: Session,
    *,
    project_id: uuid.UUID,
    company_id: uuid.UUID,
    incident_date: date,
    description: str,
    severity: str,
    responsible_user_id: uuid.UUID | None,
    corrective_action: str | None,
    evidence_id: uuid.UUID | None,
    commit: bool = True,
) -> SafetyIncident:
    _assert_severity_requires_responsible(severity, responsible_user_id)
    assert_evidence_belongs_to_company(db, evidence_id=evidence_id, company_id=company_id)
    assert_user_belongs_to_company(db, user_id=responsible_user_id, company_id=company_id)
    incident = safety_repository.create_incident(
        db,
        project_id=project_id,
        incident_date=incident_date,
        description=description,
        severity=severity,
        responsible_user_id=responsible_user_id,
        corrective_action=corrective_action,
        evidence_id=evidence_id,
    )
    if commit:
        db.commit()
        db.refresh(incident)
    else:
        db.flush()
    return incident


def get_incident(db: Session, incident_id: uuid.UUID) -> SafetyIncident | None:
    return safety_repository.get_incident(db, incident_id)


def list_incidents(db: Session, *, project_id: uuid.UUID) -> list[SafetyIncident]:
    return safety_repository.list_incidents_for_project(db, project_id)


def close_incident(db: Session, *, incident_id: uuid.UUID, commit: bool = True) -> SafetyIncident:
    incident = safety_repository.get_incident(db, incident_id)
    if incident is None:
        raise ValueError(f"SafetyIncident {incident_id} no existe")
    if incident.status != "OPEN":
        raise InvalidSafetyStateError(
            f"Solo se puede cerrar un SafetyIncident OPEN (estado actual: {incident.status})"
        )
    incident.status = "CLOSED"
    incident.closed_at = datetime.now(timezone.utc)
    if commit:
        db.commit()
        db.refresh(incident)
    else:
        db.flush()
    return incident
