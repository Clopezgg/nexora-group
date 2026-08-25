import uuid
from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from app.domain.errors import InvalidQualityStateError, NonConformanceRequiresCorrectiveActionError
from app.models.quality import CorrectiveAction, NonConformance, QualityInspection
from app.repositories import quality_repository
from app.services.financial_validation_service import assert_evidence_belongs_to_company

"""Quality: Inspection / Non-Conformance / Corrective Action (bloque
CONSTRUCTION CONTROL, orden maestra §82-83, NXR-REQ-0082/0083).

INV-QUALITY-001 (close_non_conformance): una NonConformance solo puede
pasar a CLOSED si tiene al menos una CorrectiveAction registrada -- no
importa si esa acción ya está COMPLETED o sigue OPEN, lo que se exige es
que exista evidencia de que se abrió un plan de corrección antes de dar por
cerrado el hallazgo."""


def create_inspection(
    db: Session,
    *,
    project_id: uuid.UUID,
    company_id: uuid.UUID,
    wbs_node_id: uuid.UUID | None,
    inspection_type: str,
    inspection_date: date,
    inspector_id: uuid.UUID,
    result: str,
    notes: str | None,
    evidence_id: uuid.UUID | None,
) -> QualityInspection:
    assert_evidence_belongs_to_company(db, evidence_id=evidence_id, company_id=company_id)
    inspection = quality_repository.create_inspection(
        db,
        project_id=project_id,
        wbs_node_id=wbs_node_id,
        inspection_type=inspection_type,
        inspection_date=inspection_date,
        inspector_id=inspector_id,
        result=result,
        notes=notes,
        evidence_id=evidence_id,
    )
    db.commit()
    db.refresh(inspection)
    return inspection


def get_inspection(db: Session, inspection_id: uuid.UUID) -> QualityInspection | None:
    return quality_repository.get_inspection(db, inspection_id)


def list_inspections(db: Session, *, project_id: uuid.UUID) -> list[QualityInspection]:
    return quality_repository.list_inspections_for_project(db, project_id)


def create_non_conformance(
    db: Session,
    *,
    project_id: uuid.UUID,
    company_id: uuid.UUID,
    quality_inspection_id: uuid.UUID | None,
    description: str,
    responsible_user_id: uuid.UUID,
    due_date: date | None,
    evidence_id: uuid.UUID | None,
) -> NonConformance:
    assert_evidence_belongs_to_company(db, evidence_id=evidence_id, company_id=company_id)
    non_conformance = quality_repository.create_non_conformance(
        db,
        project_id=project_id,
        quality_inspection_id=quality_inspection_id,
        description=description,
        responsible_user_id=responsible_user_id,
        due_date=due_date,
        evidence_id=evidence_id,
    )
    db.commit()
    db.refresh(non_conformance)
    return non_conformance


def get_non_conformance(db: Session, non_conformance_id: uuid.UUID) -> NonConformance | None:
    return quality_repository.get_non_conformance(db, non_conformance_id)


def list_non_conformances(db: Session, *, project_id: uuid.UUID) -> list[NonConformance]:
    return quality_repository.list_non_conformances_for_project(db, project_id)


def create_corrective_action(
    db: Session,
    *,
    non_conformance_id: uuid.UUID,
    company_id: uuid.UUID,
    description: str,
    responsible_user_id: uuid.UUID,
    due_date: date,
    evidence_id: uuid.UUID | None,
) -> CorrectiveAction:
    non_conformance = quality_repository.get_non_conformance(db, non_conformance_id)
    if non_conformance is None:
        raise ValueError(f"NonConformance {non_conformance_id} no existe")
    if non_conformance.status != "OPEN":
        raise InvalidQualityStateError(
            f"No se puede agregar una CorrectiveAction a una NonConformance {non_conformance.status}"
        )
    assert_evidence_belongs_to_company(db, evidence_id=evidence_id, company_id=company_id)
    corrective_action = quality_repository.create_corrective_action(
        db,
        non_conformance_id=non_conformance_id,
        description=description,
        responsible_user_id=responsible_user_id,
        due_date=due_date,
        evidence_id=evidence_id,
    )
    db.commit()
    db.refresh(corrective_action)
    return corrective_action


def list_corrective_actions(db: Session, *, non_conformance_id: uuid.UUID) -> list[CorrectiveAction]:
    return quality_repository.list_corrective_actions(db, non_conformance_id=non_conformance_id)


def complete_corrective_action(db: Session, *, corrective_action_id: uuid.UUID) -> CorrectiveAction:
    corrective_action = quality_repository.get_corrective_action(db, corrective_action_id)
    if corrective_action is None:
        raise ValueError(f"CorrectiveAction {corrective_action_id} no existe")
    if corrective_action.status != "OPEN":
        raise InvalidQualityStateError(
            f"Solo se puede completar una CorrectiveAction OPEN (estado actual: {corrective_action.status})"
        )
    corrective_action.status = "COMPLETED"
    corrective_action.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(corrective_action)
    return corrective_action


def close_non_conformance(db: Session, *, non_conformance_id: uuid.UUID) -> NonConformance:
    non_conformance = quality_repository.get_non_conformance(db, non_conformance_id)
    if non_conformance is None:
        raise ValueError(f"NonConformance {non_conformance_id} no existe")
    if non_conformance.status != "OPEN":
        raise InvalidQualityStateError(
            f"Solo se puede cerrar una NonConformance OPEN (estado actual: {non_conformance.status})"
        )
    corrective_actions = quality_repository.list_corrective_actions(
        db, non_conformance_id=non_conformance.id
    )
    if not corrective_actions:
        raise NonConformanceRequiresCorrectiveActionError(
            f"NonConformance {non_conformance.id} no puede cerrarse sin al menos una "
            "CorrectiveAction registrada"
        )
    non_conformance.status = "CLOSED"
    non_conformance.closed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(non_conformance)
    return non_conformance
