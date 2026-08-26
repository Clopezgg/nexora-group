import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.safety import SafetyIncident, SafetyObservation


def create_observation(
    db: Session,
    *,
    project_id: uuid.UUID,
    observation_date: date,
    category: str,
    description: str,
    severity: str,
    responsible_user_id: uuid.UUID | None,
    corrective_action: str | None,
    evidence_id: uuid.UUID | None,
) -> SafetyObservation:
    observation = SafetyObservation(
        project_id=project_id,
        observation_date=observation_date,
        category=category,
        description=description,
        severity=severity,
        responsible_user_id=responsible_user_id,
        corrective_action=corrective_action,
        evidence_id=evidence_id,
        status="OPEN",
    )
    db.add(observation)
    db.flush()
    return observation


def get_observation(db: Session, observation_id: uuid.UUID) -> SafetyObservation | None:
    return db.get(SafetyObservation, observation_id)


def list_observations_for_project(db: Session, project_id: uuid.UUID) -> list[SafetyObservation]:
    stmt = (
        select(SafetyObservation)
        .where(SafetyObservation.project_id == project_id)
        .order_by(SafetyObservation.observation_date.desc())
    )
    return list(db.execute(stmt).scalars())


def create_incident(
    db: Session,
    *,
    project_id: uuid.UUID,
    incident_date: date,
    description: str,
    severity: str,
    responsible_user_id: uuid.UUID | None,
    corrective_action: str | None,
    evidence_id: uuid.UUID | None,
) -> SafetyIncident:
    incident = SafetyIncident(
        project_id=project_id,
        incident_date=incident_date,
        description=description,
        severity=severity,
        responsible_user_id=responsible_user_id,
        corrective_action=corrective_action,
        evidence_id=evidence_id,
        status="OPEN",
    )
    db.add(incident)
    db.flush()
    return incident


def get_incident(db: Session, incident_id: uuid.UUID) -> SafetyIncident | None:
    return db.get(SafetyIncident, incident_id)


def list_incidents_for_project(db: Session, project_id: uuid.UUID) -> list[SafetyIncident]:
    stmt = (
        select(SafetyIncident)
        .where(SafetyIncident.project_id == project_id)
        .order_by(SafetyIncident.incident_date.desc())
    )
    return list(db.execute(stmt).scalars())
