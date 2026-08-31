import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.repositories import audit_repository
from app.schemas.audit import AuditLogResponse
from app.services.permission_service import assert_company_access, require_permission

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=list[AuditLogResponse])
def list_audit_logs(
    company_id: uuid.UUID = Query(alias="companyId"),
    entity_type: str | None = Query(default=None, alias="entityType"),
    entity_id: uuid.UUID | None = Query(default=None, alias="entityId"),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    user=Depends(require_permission("audit.log", "read")),
) -> list[AuditLogResponse]:
    assert_company_access(
        db, user_id=user.id, resource="audit.log", action="read", company_id=company_id
    )
    rows = audit_repository.list_for_company(
        db,
        company_id=company_id,
        entity_type=entity_type,
        entity_id=entity_id,
        offset=offset,
        limit=limit,
    )
    return [
        AuditLogResponse(
            id=r.id,
            actor_user_id=r.actor_user_id,
            actor_full_name=r.actor.full_name if r.actor else None,
            actor_email=r.actor.email if r.actor else None,
            action=r.action,
            entity_type=r.entity_type,
            entity_id=r.entity_id,
            company_id=r.company_id,
            project_id=r.project_id,
            before=r.before,
            after=r.after,
            correlation_id=r.correlation_id,
            created_at=r.created_at,
        )
        for r in rows
    ]
