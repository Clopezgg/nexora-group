import uuid

from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.repositories import audit_repository


def record(
    db: Session,
    *,
    actor_user_id: uuid.UUID | None,
    action: str,
    entity_type: str,
    entity_id: uuid.UUID,
    company_id: uuid.UUID,
    correlation_id: str,
    project_id: uuid.UUID | None = None,
    before: dict | None = None,
    after: dict | None = None,
) -> AuditLog:
    return audit_repository.create(
        db,
        actor_user_id=actor_user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        company_id=company_id,
        project_id=project_id,
        before=before,
        after=after,
        correlation_id=correlation_id,
    )
