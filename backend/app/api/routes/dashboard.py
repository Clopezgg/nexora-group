import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.schemas.dashboard import DashboardSummaryResponse
from app.services import dashboard_service
from app.services.permission_service import assert_company_access

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummaryResponse)
def summary(
    company_id: uuid.UUID | None = Query(default=None, alias="companyId"),
    db: Session = Depends(get_db),
    current: tuple = Depends(get_current_user),
) -> DashboardSummaryResponse:
    user, _roles = current
    if company_id is not None:
        assert_company_access(
            db,
            user_id=user.id,
            resource="core.company",
            action="read",
            company_id=company_id,
        )
    return dashboard_service.get_summary(db, user_id=user.id, company_id=company_id)
