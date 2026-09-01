import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.schemas.exceptions import ExceptionCenterResponse, ExceptionResponse
from app.schemas.financial_control import (
    ActualWeekResponse,
    CashFlowActualResponse,
    CashFlowMovementResponse,
    CashFlowPeriodResponse,
    CashFlowSeriesResponse,
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


@router.get("/cash-flow-actual/series", response_model=CashFlowSeriesResponse)
def cash_flow_actual_series(
    company_id: uuid.UUID = Query(alias="companyId"),
    date_from: date | None = Query(default=None, alias="from"),
    date_to: date | None = Query(default=None, alias="to"),
    granularity: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current: tuple = Depends(get_current_user),
) -> CashFlowSeriesResponse:
    """Flujo de caja REALIZADO sobre un rango de fechas REAL con granularidad
    Auto/Día/Semana/Mes (§10/§11). Sin obligar a interpretar S1..S13."""
    user, _roles = current
    assert_company_access(
        db, user_id=user.id, resource="core.company", action="read", company_id=company_id
    )
    s = cash_flow_actual_service.series(
        db, company_id=company_id, date_from=date_from, date_to=date_to, granularity=granularity
    )
    return CashFlowSeriesResponse(
        date_from=s.date_from,
        date_to=s.date_to,
        granularity=s.granularity,
        currency_code=s.currency_code,
        opening_balance=s.opening_balance,
        closing_balance=s.closing_balance,
        total_inflows=s.total_inflows,
        total_outflows=s.total_outflows,
        inflow_by_category=s.inflow_by_category,
        outflow_by_category=s.outflow_by_category,
        periods=[
            CashFlowPeriodResponse(
                index=p.index,
                period_start=p.period_start,
                period_end=p.period_end,
                label=p.label,
                inflows=p.inflows,
                outflows=p.outflows,
                net=p.net,
                closing_balance=p.closing_balance,
                movement_count=p.movement_count,
                by_category=p.by_category,
            )
            for p in s.periods
        ],
    )


@router.get("/cash-flow-actual/movements", response_model=list[CashFlowMovementResponse])
def cash_flow_actual_movements(
    company_id: uuid.UUID = Query(alias="companyId"),
    date_from: date = Query(alias="from"),
    date_to: date = Query(alias="to"),
    db: Session = Depends(get_db),
    current: tuple = Depends(get_current_user),
) -> list[CashFlowMovementResponse]:
    """Drill-down: los movimientos individuales de tesorería en el rango
    (click en una barra/punto del gráfico, §10/§11)."""
    user, _roles = current
    assert_company_access(
        db, user_id=user.id, resource="core.company", action="read", company_id=company_id
    )
    rows = cash_flow_actual_service.movements(
        db, company_id=company_id, date_from=date_from, date_to=date_to
    )
    return [
        CashFlowMovementResponse(
            document_id=m.document_id,
            document_number=m.document_number,
            effective_date=m.effective_date,
            direction=m.direction,
            category=m.category,
            amount=m.amount,
            concept=m.concept,
            counterparty=m.counterparty,
        )
        for m in rows
    ]


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
