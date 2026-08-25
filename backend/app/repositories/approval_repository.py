import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.approval_request import ApprovalRequest


def create(db: Session, **kwargs) -> ApprovalRequest:
    row = ApprovalRequest(**kwargs)
    db.add(row)
    db.flush()
    return row


def get_for_update(db: Session, *, request_id: uuid.UUID) -> ApprovalRequest:
    row = db.execute(
        select(ApprovalRequest).where(ApprovalRequest.id == request_id).with_for_update()
    ).scalar_one_or_none()
    if row is None:
        raise ValueError(f"ApprovalRequest {request_id} no existe")
    return row


def list_assigned_to(
    db: Session, *, user_id: uuid.UUID, company_id: uuid.UUID, module: str | None = None
) -> list[ApprovalRequest]:
    stmt = select(ApprovalRequest).where(
        ApprovalRequest.assigned_to == user_id,
        ApprovalRequest.company_id == company_id,
        ApprovalRequest.status == "PENDING",
    )
    if module is not None:
        stmt = stmt.where(ApprovalRequest.module == module)
    return list(db.execute(stmt).scalars())
