import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.deps_correlation import get_correlation_id
from app.models.project import Project
from app.repositories import project_repository
from app.schemas.safety import (
    SafetyIncidentCreateRequest,
    SafetyIncidentResponse,
    SafetyObservationCreateRequest,
    SafetyObservationResponse,
)
from app.services import audit_service, safety_service
from app.services.permission_service import assert_company_access, require_permission

router = APIRouter(prefix="/safety", tags=["safety"])


def _resolve_project_or_404(db: Session, project_id: uuid.UUID) -> Project:
    project = project_repository.get_by_id(db, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proyecto no encontrado")
    return project


def _resolve_observation_or_404(db: Session, observation_id: uuid.UUID):
    observation = safety_service.get_observation(db, observation_id)
    if observation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="SafetyObservation no encontrada"
        )
    return observation


def _resolve_incident_or_404(db: Session, incident_id: uuid.UUID):
    incident = safety_service.get_incident(db, incident_id)
    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="SafetyIncident no encontrado"
        )
    return incident


@router.post("/observations", response_model=SafetyObservationResponse, status_code=201)
def create_observation(
    payload: SafetyObservationCreateRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("safety.observation", "create")),
    correlation_id: str = Depends(get_correlation_id),
) -> SafetyObservationResponse:
    project = _resolve_project_or_404(db, payload.project_id)
    assert_company_access(
        db, user_id=user.id, resource="safety.observation", action="create", company_id=project.company_id
    )
    observation = safety_service.create_observation(
        db,
        project_id=payload.project_id,
        company_id=project.company_id,
        observation_date=payload.observation_date,
        category=payload.category,
        description=payload.description,
        severity=payload.severity,
        responsible_user_id=payload.responsible_user_id,
        corrective_action=payload.corrective_action,
        evidence_id=payload.evidence_id,
        commit=False,
    )
    audit_service.record(
        db,
        actor_user_id=user.id,
        action="safety.observation.create",
        entity_type="safety.observation",
        entity_id=observation.id,
        company_id=project.company_id,
        project_id=payload.project_id,
        before=None,
        after={"category": observation.category, "severity": observation.severity},
        correlation_id=correlation_id,
    )
    db.commit()
    return SafetyObservationResponse.model_validate(observation, from_attributes=True)


@router.get("/observations", response_model=list[SafetyObservationResponse])
def list_observations(
    project_id: uuid.UUID = Query(alias="projectId"),
    db: Session = Depends(get_db),
    user=Depends(require_permission("safety.observation", "read")),
) -> list[SafetyObservationResponse]:
    project = _resolve_project_or_404(db, project_id)
    assert_company_access(
        db, user_id=user.id, resource="safety.observation", action="read", company_id=project.company_id
    )
    return [
        SafetyObservationResponse.model_validate(o, from_attributes=True)
        for o in safety_service.list_observations(db, project_id=project_id)
    ]


@router.get("/observations/{observation_id}", response_model=SafetyObservationResponse)
def get_observation(
    observation_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("safety.observation", "read")),
) -> SafetyObservationResponse:
    observation = _resolve_observation_or_404(db, observation_id)
    project = _resolve_project_or_404(db, observation.project_id)
    assert_company_access(
        db, user_id=user.id, resource="safety.observation", action="read", company_id=project.company_id
    )
    return SafetyObservationResponse.model_validate(observation, from_attributes=True)


@router.post("/observations/{observation_id}/close", response_model=SafetyObservationResponse)
def close_observation(
    observation_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("safety.observation", "close")),
    correlation_id: str = Depends(get_correlation_id),
) -> SafetyObservationResponse:
    observation = _resolve_observation_or_404(db, observation_id)
    project = _resolve_project_or_404(db, observation.project_id)
    assert_company_access(
        db, user_id=user.id, resource="safety.observation", action="close", company_id=project.company_id
    )
    before_status = observation.status
    updated = safety_service.close_observation(db, observation_id=observation_id, commit=False)
    audit_service.record(
        db,
        actor_user_id=user.id,
        action="safety.observation.close",
        entity_type="safety.observation",
        entity_id=observation_id,
        company_id=project.company_id,
        project_id=observation.project_id,
        before={"status": before_status},
        after={"status": updated.status},
        correlation_id=correlation_id,
    )
    db.commit()
    return SafetyObservationResponse.model_validate(updated, from_attributes=True)


@router.post("/incidents", response_model=SafetyIncidentResponse, status_code=201)
def create_incident(
    payload: SafetyIncidentCreateRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("safety.incident", "create")),
    correlation_id: str = Depends(get_correlation_id),
) -> SafetyIncidentResponse:
    project = _resolve_project_or_404(db, payload.project_id)
    assert_company_access(
        db, user_id=user.id, resource="safety.incident", action="create", company_id=project.company_id
    )
    incident = safety_service.create_incident(
        db,
        project_id=payload.project_id,
        company_id=project.company_id,
        incident_date=payload.incident_date,
        description=payload.description,
        severity=payload.severity,
        responsible_user_id=payload.responsible_user_id,
        corrective_action=payload.corrective_action,
        evidence_id=payload.evidence_id,
        commit=False,
    )
    audit_service.record(
        db,
        actor_user_id=user.id,
        action="safety.incident.create",
        entity_type="safety.incident",
        entity_id=incident.id,
        company_id=project.company_id,
        project_id=payload.project_id,
        before=None,
        after={"severity": incident.severity, "description": incident.description[:100]},
        correlation_id=correlation_id,
    )
    db.commit()
    return SafetyIncidentResponse.model_validate(incident, from_attributes=True)


@router.get("/incidents", response_model=list[SafetyIncidentResponse])
def list_incidents(
    project_id: uuid.UUID = Query(alias="projectId"),
    db: Session = Depends(get_db),
    user=Depends(require_permission("safety.incident", "read")),
) -> list[SafetyIncidentResponse]:
    project = _resolve_project_or_404(db, project_id)
    assert_company_access(
        db, user_id=user.id, resource="safety.incident", action="read", company_id=project.company_id
    )
    return [
        SafetyIncidentResponse.model_validate(i, from_attributes=True)
        for i in safety_service.list_incidents(db, project_id=project_id)
    ]


@router.get("/incidents/{incident_id}", response_model=SafetyIncidentResponse)
def get_incident(
    incident_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("safety.incident", "read")),
) -> SafetyIncidentResponse:
    incident = _resolve_incident_or_404(db, incident_id)
    project = _resolve_project_or_404(db, incident.project_id)
    assert_company_access(
        db, user_id=user.id, resource="safety.incident", action="read", company_id=project.company_id
    )
    return SafetyIncidentResponse.model_validate(incident, from_attributes=True)


@router.post("/incidents/{incident_id}/close", response_model=SafetyIncidentResponse)
def close_incident(
    incident_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("safety.incident", "close")),
    correlation_id: str = Depends(get_correlation_id),
) -> SafetyIncidentResponse:
    incident = _resolve_incident_or_404(db, incident_id)
    project = _resolve_project_or_404(db, incident.project_id)
    assert_company_access(
        db, user_id=user.id, resource="safety.incident", action="close", company_id=project.company_id
    )
    before_status = incident.status
    updated = safety_service.close_incident(db, incident_id=incident_id, commit=False)
    audit_service.record(
        db,
        actor_user_id=user.id,
        action="safety.incident.close",
        entity_type="safety.incident",
        entity_id=incident_id,
        company_id=project.company_id,
        project_id=incident.project_id,
        before={"status": before_status},
        after={"status": updated.status},
        correlation_id=correlation_id,
    )
    db.commit()
    return SafetyIncidentResponse.model_validate(updated, from_attributes=True)
