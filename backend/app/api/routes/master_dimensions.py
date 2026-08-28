import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.cost_center import CostCenter, EconomicCategory
from app.schemas.dimensions import DimensionResponse
from app.services.permission_service import assert_company_access, require_permission

router = APIRouter(prefix="/master-data", tags=["master-data"])


@router.get("/cost-centers", response_model=list[DimensionResponse])
def list_cost_centers(
    company_id: uuid.UUID = Query(alias="companyId"),
    db: Session = Depends(get_db),
    user=Depends(require_permission("core.company", "read")),
) -> list[DimensionResponse]:
    assert_company_access(db, user_id=user.id, resource="core.company", action="read", company_id=company_id)
    rows = db.execute(
        select(CostCenter).where(CostCenter.company_id == company_id).order_by(CostCenter.code)
    ).scalars()
    return [DimensionResponse.model_validate(row, from_attributes=True) for row in rows]


@router.get("/economic-categories", response_model=list[DimensionResponse])
def list_economic_categories(
    company_id: uuid.UUID = Query(alias="companyId"),
    db: Session = Depends(get_db),
    user=Depends(require_permission("core.company", "read")),
) -> list[DimensionResponse]:
    assert_company_access(db, user_id=user.id, resource="core.company", action="read", company_id=company_id)
    rows = db.execute(
        select(EconomicCategory).where(EconomicCategory.company_id == company_id).order_by(EconomicCategory.code)
    ).scalars()
    return [DimensionResponse.model_validate(row, from_attributes=True) for row in rows]
