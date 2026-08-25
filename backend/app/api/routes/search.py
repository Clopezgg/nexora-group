import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.search import SearchResultResponse
from app.services import search_service
from app.services.permission_service import assert_company_access, require_permission

# Global Search (NXR-REQ-0092). GET /api/search -- ojo, NO /api/v1/search
# (ningún router de este backend usa prefijo /api/v1, ver CommandPalette.tsx
# y el diseño de este track).
router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=list[SearchResultResponse])
def global_search(
    company_id: uuid.UUID = Query(alias="companyId"),
    q: str = Query(default=""),
    db: Session = Depends(get_db),
    user=Depends(require_permission("search.global", "read")),
) -> list[SearchResultResponse]:
    assert_company_access(
        db, user_id=user.id, resource="search.global", action="read", company_id=company_id
    )
    if not q or len(q.strip()) < 2:
        return []
    results = search_service.search(db, company_id=company_id, query=q.strip())
    return [
        SearchResultResponse(
            id=r.id, label=r.label, group=r.group, path=r.path, entity_type=r.entity_type
        )
        for r in results
    ]
