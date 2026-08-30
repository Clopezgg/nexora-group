import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.deps_correlation import get_correlation_id
from app.core.business_time import business_today
from app.repositories import company_repository
from app.schemas.fiscal import (
    CurrentFiscalPeriodResponse,
    FiscalPeriodResponse,
    FiscalPeriodStatusRequest,
    FiscalYearCreateRequest,
    FiscalYearResponse,
)
from app.services import audit_service, fiscal_service
from app.services.permission_service import assert_company_access, require_permission

router = APIRouter(prefix="/fiscal", tags=["fiscal"])


def _assert_company_exists(db: Session, company_id: uuid.UUID) -> None:
    if company_repository.get_by_id(db, company_id) is None:
        raise HTTPException(status_code=404, detail="Compañía no encontrada")


@router.get("/years", response_model=list[FiscalYearResponse])
def list_years(
    company_id: uuid.UUID = Query(alias="companyId"),
    db: Session = Depends(get_db),
    user=Depends(require_permission("core.company", "read")),
) -> list[FiscalYearResponse]:
    _assert_company_exists(db, company_id)
    assert_company_access(
        db, user_id=user.id, resource="core.company", action="read", company_id=company_id
    )
    return [
        FiscalYearResponse.model_validate(year, from_attributes=True)
        for year in fiscal_service.list_years(db, company_id=company_id)
    ]


@router.post("/years", response_model=FiscalYearResponse, status_code=201)
def create_year(
    payload: FiscalYearCreateRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("core.company", "update")),
    correlation_id: str = Depends(get_correlation_id),
) -> FiscalYearResponse:
    _assert_company_exists(db, payload.company_id)
    assert_company_access(
        db,
        user_id=user.id,
        resource="core.company",
        action="update",
        company_id=payload.company_id,
    )
    try:
        year = fiscal_service.create_year(
            db,
            company_id=payload.company_id,
            code=payload.code,
            start_date=payload.start_date,
            end_date=payload.end_date,
        )
        audit_service.record(
            db,
            actor_user_id=user.id,
            action="fiscal.year.create",
            entity_type="fiscal.year",
            entity_id=year.id,
            company_id=year.company_id,
            project_id=None,
            before=None,
            after={"code": year.code, "startDate": str(year.start_date), "endDate": str(year.end_date)},
            correlation_id=correlation_id,
        )
        db.commit()
        db.refresh(year)
        return FiscalYearResponse.model_validate(year, from_attributes=True)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/years/{fiscal_year_id}/generate-monthly-periods", response_model=list[FiscalPeriodResponse])
def generate_monthly_periods(
    fiscal_year_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("core.company", "update")),
    correlation_id: str = Depends(get_correlation_id),
) -> list[FiscalPeriodResponse]:
    from app.models.fiscal import FiscalYear

    year = db.get(FiscalYear, fiscal_year_id)
    if year is None:
        raise HTTPException(status_code=404, detail="Año fiscal no encontrado")
    assert_company_access(
        db, user_id=user.id, resource="core.company", action="update", company_id=year.company_id
    )
    try:
        periods = fiscal_service.generate_monthly_periods(db, fiscal_year_id=fiscal_year_id)
        audit_service.record(
            db,
            actor_user_id=user.id,
            action="fiscal.periods.generate",
            entity_type="fiscal.year",
            entity_id=year.id,
            company_id=year.company_id,
            project_id=None,
            before=None,
            after={"periodCount": len(periods)},
            correlation_id=correlation_id,
        )
        db.commit()
        return [FiscalPeriodResponse.model_validate(period, from_attributes=True) for period in periods]
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/periods", response_model=list[FiscalPeriodResponse])
def list_periods(
    company_id: uuid.UUID = Query(alias="companyId"),
    db: Session = Depends(get_db),
    user=Depends(require_permission("core.company", "read")),
) -> list[FiscalPeriodResponse]:
    _assert_company_exists(db, company_id)
    assert_company_access(
        db, user_id=user.id, resource="core.company", action="read", company_id=company_id
    )
    return [
        FiscalPeriodResponse.model_validate(period, from_attributes=True)
        for period in fiscal_service.list_periods(db, company_id=company_id)
    ]


@router.get("/periods/current", response_model=CurrentFiscalPeriodResponse)
def current_period(
    company_id: uuid.UUID = Query(alias="companyId"),
    on_date: date | None = Query(default=None, alias="onDate"),
    db: Session = Depends(get_db),
    user=Depends(require_permission("core.company", "read")),
) -> CurrentFiscalPeriodResponse:
    _assert_company_exists(db, company_id)
    assert_company_access(
        db, user_id=user.id, resource="core.company", action="read", company_id=company_id
    )
    year, period = fiscal_service.get_current_period(
        db, company_id=company_id, on_date=on_date or business_today()
    )
    return CurrentFiscalPeriodResponse(
        fiscal_year=FiscalYearResponse.model_validate(year, from_attributes=True) if year else None,
        period=FiscalPeriodResponse.model_validate(period, from_attributes=True) if period else None,
    )


@router.post("/periods/{period_id}/status", response_model=FiscalPeriodResponse)
def transition_period(
    period_id: uuid.UUID,
    payload: FiscalPeriodStatusRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("core.company", "update")),
    correlation_id: str = Depends(get_correlation_id),
) -> FiscalPeriodResponse:
    from app.models.fiscal import FiscalPeriod

    existing = db.get(FiscalPeriod, period_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Período fiscal no encontrado")
    assert_company_access(
        db, user_id=user.id, resource="core.company", action="update", company_id=existing.company_id
    )
    before_status = existing.status
    try:
        period = fiscal_service.transition_period_status(
            db, period_id=period_id, target_status=payload.status
        )
        audit_service.record(
            db,
            actor_user_id=user.id,
            action="fiscal.period.status",
            entity_type="fiscal.period",
            entity_id=period.id,
            company_id=period.company_id,
            project_id=None,
            before={"status": before_status},
            after={"status": period.status, "reason": payload.reason},
            correlation_id=correlation_id,
        )
        db.commit()
        db.refresh(period)
        return FiscalPeriodResponse.model_validate(period, from_attributes=True)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
