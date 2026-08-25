import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.asset import (
    AssetStatusChangeRequest,
    DepreciationEntryCreateRequest,
    DepreciationEntryResponse,
    FixedAssetCreateRequest,
    FixedAssetResponse,
)
from app.services import asset_service
from app.services.permission_service import assert_company_access, require_permission

router = APIRouter(prefix="/assets", tags=["assets"])


def _resolve_asset(db: Session, asset_id: uuid.UUID):
    asset = asset_service.get_fixed_asset(db, asset_id)
    if asset is None:
        raise ValueError(f"FixedAsset {asset_id} no existe")
    return asset


@router.post("", response_model=FixedAssetResponse, status_code=201)
def create_fixed_asset(
    payload: FixedAssetCreateRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("asset.fixed_asset", "create")),
) -> FixedAssetResponse:
    assert_company_access(
        db, user_id=user.id, resource="asset.fixed_asset", action="create", company_id=payload.company_id
    )
    asset = asset_service.create_fixed_asset(
        db,
        company_id=payload.company_id,
        category=payload.category,
        name=payload.name,
        acquisition_date=payload.acquisition_date,
        cost=payload.cost,
        currency_code=payload.currency_code,
        useful_life_months=payload.useful_life_months,
        salvage_value=payload.salvage_value,
        location=payload.location,
        responsible=payload.responsible,
        scope=payload.scope,
        project_id=payload.project_id,
        cost_center_id=payload.cost_center_id,
        depreciation_expense_account_id=payload.depreciation_expense_account_id,
        accumulated_depreciation_account_id=payload.accumulated_depreciation_account_id,
    )
    return FixedAssetResponse.model_validate(asset, from_attributes=True)


@router.get("", response_model=list[FixedAssetResponse])
def list_fixed_assets(
    company_id: uuid.UUID = Query(alias="companyId"),
    db: Session = Depends(get_db),
    user=Depends(require_permission("asset.fixed_asset", "read")),
) -> list[FixedAssetResponse]:
    assert_company_access(
        db, user_id=user.id, resource="asset.fixed_asset", action="read", company_id=company_id
    )
    return [
        FixedAssetResponse.model_validate(asset, from_attributes=True)
        for asset in asset_service.list_fixed_assets(db, company_id=company_id)
    ]


@router.get("/{asset_id}", response_model=FixedAssetResponse)
def get_fixed_asset(
    asset_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("asset.fixed_asset", "read")),
) -> FixedAssetResponse:
    asset = _resolve_asset(db, asset_id)
    assert_company_access(
        db, user_id=user.id, resource="asset.fixed_asset", action="read", company_id=asset.company_id
    )
    return FixedAssetResponse.model_validate(asset, from_attributes=True)


@router.post("/{asset_id}/status", response_model=FixedAssetResponse)
def change_asset_status(
    asset_id: uuid.UUID,
    payload: AssetStatusChangeRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("asset.fixed_asset", "update")),
) -> FixedAssetResponse:
    asset = _resolve_asset(db, asset_id)
    assert_company_access(
        db, user_id=user.id, resource="asset.fixed_asset", action="update", company_id=asset.company_id
    )
    asset = asset_service.change_asset_status(db, asset_id=asset_id, status=payload.status)
    return FixedAssetResponse.model_validate(asset, from_attributes=True)


@router.post(
    "/{asset_id}/depreciation-entries", response_model=DepreciationEntryResponse, status_code=201
)
def generate_depreciation_entry(
    asset_id: uuid.UUID,
    payload: DepreciationEntryCreateRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("asset.depreciation", "create")),
) -> DepreciationEntryResponse:
    asset = _resolve_asset(db, asset_id)
    assert_company_access(
        db, user_id=user.id, resource="asset.depreciation", action="create", company_id=asset.company_id
    )
    entry = asset_service.generate_depreciation_entry(
        db,
        asset_id=asset_id,
        period_start=payload.period_start,
        period_end=payload.period_end,
        post=payload.post,
    )
    return DepreciationEntryResponse.model_validate(entry, from_attributes=True)


@router.get("/{asset_id}/depreciation-entries", response_model=list[DepreciationEntryResponse])
def list_depreciation_entries(
    asset_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("asset.depreciation", "read")),
) -> list[DepreciationEntryResponse]:
    asset = _resolve_asset(db, asset_id)
    assert_company_access(
        db, user_id=user.id, resource="asset.depreciation", action="read", company_id=asset.company_id
    )
    return [
        DepreciationEntryResponse.model_validate(entry, from_attributes=True)
        for entry in asset_service.list_depreciation_entries(db, asset_id=asset_id)
    ]
