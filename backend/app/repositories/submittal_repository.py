import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.submittal import Submittal


def create_submittal(
    db: Session,
    *,
    company_id: uuid.UUID,
    project_id: uuid.UUID,
    wbs_node_id: uuid.UUID | None,
    number: str,
    title: str,
    description: str | None,
    supplier_id: uuid.UUID | None,
    contract_id: uuid.UUID | None,
    submitted_by: uuid.UUID,
    submitted_at: date,
    due_date: date | None,
    evidence_id: uuid.UUID | None,
) -> Submittal:
    submittal = Submittal(
        company_id=company_id,
        project_id=project_id,
        wbs_node_id=wbs_node_id,
        number=number,
        revision=1,
        title=title,
        description=description,
        supplier_id=supplier_id,
        contract_id=contract_id,
        submitted_by=submitted_by,
        submitted_at=submitted_at,
        due_date=due_date,
        evidence_id=evidence_id,
        status="SUBMITTED",
    )
    db.add(submittal)
    db.flush()
    return submittal


def get_submittal(db: Session, submittal_id: uuid.UUID) -> Submittal | None:
    return db.get(Submittal, submittal_id)


def list_submittals(
    db: Session, *, company_id: uuid.UUID, project_id: uuid.UUID | None = None
) -> list[Submittal]:
    stmt = (
        select(Submittal)
        .where(Submittal.company_id == company_id)
        .order_by(Submittal.created_at.desc())
    )
    if project_id is not None:
        stmt = stmt.where(Submittal.project_id == project_id)
    return list(db.execute(stmt).scalars())
