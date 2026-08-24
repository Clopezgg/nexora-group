from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.schemas.dashboard import DashboardSummaryResponse
from app.services import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummaryResponse)
def summary(
    db: Session = Depends(get_db),
    _current: tuple = Depends(get_current_user),
) -> DashboardSummaryResponse:
    return dashboard_service.get_summary(db)
