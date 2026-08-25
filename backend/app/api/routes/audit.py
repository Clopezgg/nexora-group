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
    db: Session = Depends(get_db),
    user=Depends(require_permission("audit.log", "read")),
) -> list[AuditLogResponse]:
    assert_company_access(
        db, user_id=user.id, resource="audit.log", action="read", company_id=company_id
    )
    rows = audit_repository.list_for_company(
        db, company_id=company_id, entity_type=entity_type, entity_id=entity_id
    )
    return [AuditLogResponse.model_validate(r, from_attributes=True) for r in rows]
