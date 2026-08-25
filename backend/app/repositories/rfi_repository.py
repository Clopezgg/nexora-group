import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.rfi import RequestForInformation


def create_rfi(
    db: Session,
    *,
    company_id: uuid.UUID,
    project_id: uuid.UUID,
    wbs_node_id: uuid.UUID | None,
    number: str,
    subject: str,
    question: str,
    responsible: str | None,
    requested_by: uuid.UUID,
    due_date: date | None,
) -> RequestForInformation:
    rfi = RequestForInformation(
        company_id=company_id,
        project_id=project_id,
        wbs_node_id=wbs_node_id,
        number=number,
        subject=subject,
        question=question,
        responsible=responsible,
        requested_by=requested_by,
        due_date=due_date,
        status="OPEN",
    )
    db.add(rfi)
    db.flush()
    return rfi


def get_rfi(db: Session, rfi_id: uuid.UUID) -> RequestForInformation | None:
    return db.get(RequestForInformation, rfi_id)


def list_rfis(
    db: Session, *, company_id: uuid.UUID, project_id: uuid.UUID | None = None
) -> list[RequestForInformation]:
    stmt = (
        select(RequestForInformation)
        .where(RequestForInformation.company_id == company_id)
        .order_by(RequestForInformation.created_at.desc())
    )
    if project_id is not None:
        stmt = stmt.where(RequestForInformation.project_id == project_id)
    return list(db.execute(stmt).scalars())
