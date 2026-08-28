import calendar
import uuid
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.fiscal import FiscalPeriod, FiscalYear


_ALLOWED_PERIOD_TRANSITIONS: dict[str, set[str]] = {
    "OPEN": {"SOFT_CLOSED", "CLOSED"},
    "SOFT_CLOSED": {"OPEN", "CLOSED"},
    "CLOSED": set(),
}


def list_years(db: Session, *, company_id: uuid.UUID) -> list[FiscalYear]:
    stmt = (
        select(FiscalYear)
        .where(FiscalYear.company_id == company_id)
        .order_by(FiscalYear.start_date.desc())
    )
    return list(db.execute(stmt).scalars())


def list_periods(db: Session, *, company_id: uuid.UUID) -> list[FiscalPeriod]:
    stmt = (
        select(FiscalPeriod)
        .where(FiscalPeriod.company_id == company_id)
        .order_by(FiscalPeriod.start_date)
    )
    return list(db.execute(stmt).scalars())


def create_year(
    db: Session,
    *,
    company_id: uuid.UUID,
    code: str,
    start_date: date,
    end_date: date,
) -> FiscalYear:
    overlap_stmt = select(FiscalYear.id).where(
        FiscalYear.company_id == company_id,
        FiscalYear.start_date <= end_date,
        FiscalYear.end_date >= start_date,
    )
    if db.execute(overlap_stmt).scalar_one_or_none() is not None:
        raise ValueError("El año fiscal se superpone con otro año fiscal existente")
    year = FiscalYear(
        company_id=company_id,
        code=code.strip(),
        start_date=start_date,
        end_date=end_date,
    )
    db.add(year)
    db.flush()
    return year


def generate_monthly_periods(db: Session, *, fiscal_year_id: uuid.UUID) -> list[FiscalPeriod]:
    year = db.get(FiscalYear, fiscal_year_id)
    if year is None:
        raise ValueError("Año fiscal no encontrado")
    existing_stmt = select(FiscalPeriod.id).where(FiscalPeriod.fiscal_year_id == fiscal_year_id).limit(1)
    if db.execute(existing_stmt).scalar_one_or_none() is not None:
        raise ValueError("El año fiscal ya tiene períodos; no se regeneran automáticamente")

    periods: list[FiscalPeriod] = []
    cursor = year.start_date
    number = 1
    while cursor <= year.end_date:
        month_last_day = calendar.monthrange(cursor.year, cursor.month)[1]
        period_end = min(date(cursor.year, cursor.month, month_last_day), year.end_date)
        period = FiscalPeriod(
            fiscal_year_id=year.id,
            company_id=year.company_id,
            period_number=number,
            start_date=cursor,
            end_date=period_end,
            status="OPEN",
        )
        db.add(period)
        periods.append(period)
        cursor = period_end + timedelta(days=1)
        number += 1
    db.flush()
    return periods


def get_current_period(
    db: Session,
    *,
    company_id: uuid.UUID,
    on_date: date,
) -> tuple[FiscalYear | None, FiscalPeriod | None]:
    period_stmt = (
        select(FiscalPeriod)
        .where(
            FiscalPeriod.company_id == company_id,
            FiscalPeriod.start_date <= on_date,
            FiscalPeriod.end_date >= on_date,
        )
        .order_by(FiscalPeriod.start_date.desc())
        .limit(1)
    )
    period = db.execute(period_stmt).scalars().first()
    if period is None:
        return None, None
    return db.get(FiscalYear, period.fiscal_year_id), period


def transition_period_status(
    db: Session,
    *,
    period_id: uuid.UUID,
    target_status: str,
) -> FiscalPeriod:
    period = db.get(FiscalPeriod, period_id)
    if period is None:
        raise ValueError("Período fiscal no encontrado")
    if target_status == period.status:
        return period
    if target_status not in _ALLOWED_PERIOD_TRANSITIONS.get(period.status, set()):
        raise ValueError(f"Transición de período no permitida: {period.status} → {target_status}")
    period.status = target_status
    db.flush()
    return period
