import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.quality import CorrectiveAction, NonConformance, QualityInspection


def create_inspection(
    db: Session,
    *,
    project_id: uuid.UUID,
    wbs_node_id: uuid.UUID | None,
    inspection_type: str,
    inspection_date: date,
    inspector_id: uuid.UUID,
    result: str,
    notes: str | None,
    evidence_id: uuid.UUID | None,
) -> QualityInspection:
    inspection = QualityInspection(
        project_id=project_id,
        wbs_node_id=wbs_node_id,
        inspection_type=inspection_type,
        inspection_date=inspection_date,
        inspector_id=inspector_id,
        result=result,
        notes=notes,
        evidence_id=evidence_id,
    )
    db.add(inspection)
    db.flush()
    return inspection


def get_inspection(db: Session, inspection_id: uuid.UUID) -> QualityInspection | None:
    return db.get(QualityInspection, inspection_id)


def list_inspections_for_project(db: Session, project_id: uuid.UUID) -> list[QualityInspection]:
    stmt = (
        select(QualityInspection)
        .where(QualityInspection.project_id == project_id)
        .order_by(QualityInspection.inspection_date.desc())
    )
    return list(db.execute(stmt).scalars())


def create_non_conformance(
    db: Session,
    *,
    project_id: uuid.UUID,
    quality_inspection_id: uuid.UUID | None,
    description: str,
    responsible_user_id: uuid.UUID,
    due_date: date | None,
    evidence_id: uuid.UUID | None,
) -> NonConformance:
    non_conformance = NonConformance(
        project_id=project_id,
        quality_inspection_id=quality_inspection_id,
        description=description,
        responsible_user_id=responsible_user_id,
        due_date=due_date,
        evidence_id=evidence_id,
        status="OPEN",
    )
    db.add(non_conformance)
    db.flush()
    return non_conformance


def get_non_conformance(db: Session, non_conformance_id: uuid.UUID) -> NonConformance | None:
    return db.get(NonConformance, non_conformance_id)


def list_non_conformances_for_project(db: Session, project_id: uuid.UUID) -> list[NonConformance]:
    stmt = (
        select(NonConformance)
        .where(NonConformance.project_id == project_id)
        .order_by(NonConformance.created_at.desc())
    )
    return list(db.execute(stmt).scalars())


def create_corrective_action(
    db: Session,
    *,
    non_conformance_id: uuid.UUID,
    description: str,
    responsible_user_id: uuid.UUID,
    due_date: date,
    evidence_id: uuid.UUID | None,
) -> CorrectiveAction:
    corrective_action = CorrectiveAction(
        non_conformance_id=non_conformance_id,
        description=description,
        responsible_user_id=responsible_user_id,
        due_date=due_date,
        evidence_id=evidence_id,
        status="OPEN",
    )
    db.add(corrective_action)
    db.flush()
    return corrective_action


def get_corrective_action(db: Session, corrective_action_id: uuid.UUID) -> CorrectiveAction | None:
    return db.get(CorrectiveAction, corrective_action_id)


def list_corrective_actions(db: Session, *, non_conformance_id: uuid.UUID) -> list[CorrectiveAction]:
    stmt = (
        select(CorrectiveAction)
        .where(CorrectiveAction.non_conformance_id == non_conformance_id)
        .order_by(CorrectiveAction.created_at)
    )
    return list(db.execute(stmt).scalars())
