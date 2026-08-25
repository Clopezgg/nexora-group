import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit import AuditLog


def create(db: Session, **kwargs) -> AuditLog:
    row = AuditLog(**kwargs)
    db.add(row)
    db.flush()
    return row


def list_for_company(
    db: Session,
    *,
    company_id: uuid.UUID,
    entity_type: str | None = None,
    entity_id: uuid.UUID | None = None,
    actor_user_id: uuid.UUID | None = None,
) -> list[AuditLog]:
    stmt = select(AuditLog).where(AuditLog.company_id == company_id)
    if entity_type is not None:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
    if entity_id is not None:
        stmt = stmt.where(AuditLog.entity_id == entity_id)
    if actor_user_id is not None:
        stmt = stmt.where(AuditLog.actor_user_id == actor_user_id)
    stmt = stmt.order_by(AuditLog.created_at.desc())
    return list(db.execute(stmt).scalars())
