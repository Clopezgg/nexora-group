import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.asset import DepreciationEntry, FixedAsset


def create_fixed_asset(
    db: Session,
    *,
    company_id: uuid.UUID,
    category: str,
    name: str,
    acquisition_date: date,
    cost: Decimal,
    currency_code: str,
    useful_life_months: int,
    salvage_value: Decimal,
    location: str | None,
    responsible: str | None,
    scope: str,
    project_id: uuid.UUID | None,
    cost_center_id: uuid.UUID | None,
    depreciation_expense_account_id: uuid.UUID,
    accumulated_depreciation_account_id: uuid.UUID,
) -> FixedAsset:
    asset = FixedAsset(
        company_id=company_id,
        category=category,
        name=name,
        acquisition_date=acquisition_date,
        cost=cost,
        currency_code=currency_code,
        useful_life_months=useful_life_months,
        salvage_value=salvage_value,
        location=location,
        responsible=responsible,
        scope=scope,
        project_id=project_id,
        cost_center_id=cost_center_id,
        depreciation_expense_account_id=depreciation_expense_account_id,
        accumulated_depreciation_account_id=accumulated_depreciation_account_id,
    )
    db.add(asset)
    db.flush()
    return asset


def get_fixed_asset(db: Session, asset_id: uuid.UUID) -> FixedAsset | None:
    return db.get(FixedAsset, asset_id)


def list_fixed_assets(db: Session, *, company_id: uuid.UUID) -> list[FixedAsset]:
    stmt = select(FixedAsset).where(FixedAsset.company_id == company_id).order_by(FixedAsset.name)
    return list(db.execute(stmt).scalars())


def get_depreciation_entry_for_period(
    db: Session, *, asset_id: uuid.UUID, period_start: date
) -> DepreciationEntry | None:
    stmt = select(DepreciationEntry).where(
        DepreciationEntry.asset_id == asset_id, DepreciationEntry.period_start == period_start
    )
    return db.execute(stmt).scalar_one_or_none()


def create_depreciation_entry(
    db: Session,
    *,
    asset_id: uuid.UUID,
    period_start: date,
    period_end: date,
    amount: Decimal,
) -> DepreciationEntry:
    entry = DepreciationEntry(
        asset_id=asset_id, period_start=period_start, period_end=period_end, amount=amount
    )
    db.add(entry)
    db.flush()
    return entry


def list_depreciation_entries(db: Session, *, asset_id: uuid.UUID) -> list[DepreciationEntry]:
    stmt = (
        select(DepreciationEntry)
        .where(DepreciationEntry.asset_id == asset_id)
        .order_by(DepreciationEntry.period_start)
    )
    return list(db.execute(stmt).scalars())
