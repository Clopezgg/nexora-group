import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.schemas.exceptions import ExceptionCenterResponse, ExceptionResponse
from app.schemas.financial_control import (
    ActualWeekResponse,
    CashFlowActualResponse,
    CashForecastResponse,
    DailyStatusResponse,
    ForecastWeekResponse,
    KpiResponse,
)
from app.services import (
    cash_flow_actual_service,
    cash_forecast_service,
    exception_service,
    financial_control_service,
)
from app.services.permission_service import assert_company_access

router = APIRouter(prefix="/financial-control", tags=["financial-control"])


@router.get("/daily-status", response_model=DailyStatusResponse)
def daily_status(
    company_id: uuid.UUID = Query(alias="companyId"),
    db: Session = Depends(get_db),
    current: tuple = Depends(get_current_user),
) -> DailyStatusResponse:
    user, _roles = current
    assert_company_access(
        db, user_id=user.id, resource="core.company", action="read", company_id=company_id
    )
    status = financial_control_service.daily_status(db, company_id=company_id)
    return DailyStatusResponse(
        company_id=uuid.UUID(status.company_id),
        as_of=status.as_of,
        currency_code=status.currency_code,
        fiscal_period_label=status.fiscal_period_label,
        fiscal_period_status=status.fiscal_period_status,
        kpis=[
            KpiResponse(
                key=k.key,
                label=k.label,
                value=k.value,
                numeric=k.numeric,
                severity=k.severity,
                hint=k.hint,
                route=k.route,
            )
            for k in status.kpis
        ],
    )


@router.get("/exceptions", response_model=ExceptionCenterResponse)
def exception_center(
    company_id: uuid.UUID = Query(alias="companyId"),
    db: Session = Depends(get_db),
    current: tuple = Depends(get_current_user),
) -> ExceptionCenterResponse:
    user, _roles = current
    assert_company_access(
        db, user_id=user.id, resource="core.company", action="read", company_id=company_id
    )
    items = exception_service.list_exceptions(db, company_id=company_id)
    return ExceptionCenterResponse(
        exception_zero=not items,
        total=len(items),
        critical_count=sum(1 for i in items if i.severity == "critical"),
        exceptions=[
            ExceptionResponse(
                code=i.code,
                severity=i.severity,
                title=i.title,
                detail=i.detail,
                count=i.count,
                suggested_action=i.suggested_action,
                route=i.route,
            )
            for i in items
        ],
    )


@router.get("/cash-forecast", response_model=CashForecastResponse)
def cash_forecast(
    company_id: uuid.UUID = Query(alias="companyId"),
    db: Session = Depends(get_db),
    current: tuple = Depends(get_current_user),
) -> CashForecastResponse:
    user, _roles = current
    assert_company_access(
        db, user_id=user.id, resource="core.company", action="read", company_id=company_id
    )
    fc = cash_forecast_service.forecast(db, company_id=company_id)
    return CashForecastResponse(
        as_of=fc.as_of,
        currency_code=fc.currency_code,
        opening_balance=fc.opening_balance,
        weeks=[
            ForecastWeekResponse(
                week_index=w.week_index,
                week_start=w.week_start,
                week_end=w.week_end,
                inflows=w.inflows,
                outflows=w.outflows,
                net=w.net,
                projected_balance=w.projected_balance,
            )
            for w in fc.weeks
        ],
        min_projected_balance=fc.min_projected_balance,
        first_negative_week_index=fc.first_negative_week_index,
        has_liquidity_alert=fc.has_liquidity_alert,
    )


@router.get("/cash-flow-actual", response_model=CashFlowActualResponse)
def cash_flow_actual(
    company_id: uuid.UUID = Query(alias="companyId"),
    db: Session = Depends(get_db),
    current: tuple = Depends(get_current_user),
) -> CashFlowActualResponse:
    """Flujo de caja REALIZADO de las últimas 13 semanas (§12). Fuente
    autoritativa: el movimiento real de las cuentas de tesorería, clasificado
    por origen. Sin doble conteo — se lee la línea del asiento, no las tablas
    de origen en paralelo."""
    user, _roles = current
    assert_company_access(
        db, user_id=user.id, resource="core.company", action="read", company_id=company_id
    )
    cf = cash_flow_actual_service.actual(db, company_id=company_id)
    return CashFlowActualResponse(
        as_of=cf.as_of,
        currency_code=cf.currency_code,
        opening_balance=cf.opening_balance,
        closing_balance=cf.closing_balance,
        total_inflows=cf.total_inflows,
        total_outflows=cf.total_outflows,
        inflow_by_category=cf.inflow_by_category,
        outflow_by_category=cf.outflow_by_category,
        weeks=[
            ActualWeekResponse(
                week_index=w.week_index,
                week_start=w.week_start,
                week_end=w.week_end,
                inflows=w.inflows,
                outflows=w.outflows,
                net=w.net,
                closing_balance=w.closing_balance,
                by_category=w.by_category,
            )
            for w in cf.weeks
        ],
    )


@router.get("/ar-metrics", response_model=None)
def ar_metrics(
    company_id: uuid.UUID = Query(alias="companyId"),
    db: Session = Depends(get_db),
    current: tuple = Depends(get_current_user),
):
    user, _roles = current
    assert_company_access(
        db, user_id=user.id, resource="core.company", action="read", company_id=company_id
    )
    return financial_control_service.ar_metrics(db, company_id=company_id)
