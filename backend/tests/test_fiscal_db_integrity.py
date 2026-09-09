"""Fiscal identities and date ranges must survive bypassing service validation."""

from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.company import Company
from app.models.fiscal import FiscalPeriod, FiscalYear


def calendar(db):
    company = Company(name="Fiscal integrity")
    other = Company(name="Other fiscal company")
    db.add_all([company, other])
    db.flush()
    year = FiscalYear(
        company_id=company.id,
        code="2026",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )
    db.add(year)
    db.commit()
    return company, other, year


def test_period_cannot_reference_another_company_year(db_session):
    _, other, year = calendar(db_session)
    db_session.add(
        FiscalPeriod(
            company_id=other.id,
            fiscal_year_id=year.id,
            period_number=1,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()


@pytest.mark.parametrize(
    "start,end",
    [
        (date(2026, 12, 31), date(2027, 12, 31)),
        (date(2026, 2, 1), date(2026, 2, 28)),
    ],
)
def test_overlapping_year_is_rejected_by_database(db_session, start, end):
    company, _, _ = calendar(db_session)
    db_session.add(
        FiscalYear(company_id=company.id, code="OTHER", start_date=start, end_date=end)
    )
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_overlapping_period_is_rejected_by_database(db_session):
    company, _, year = calendar(db_session)
    db_session.add(
        FiscalPeriod(
            company_id=company.id,
            fiscal_year_id=year.id,
            period_number=1,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
        )
    )
    db_session.commit()
    db_session.add(
        FiscalPeriod(
            company_id=company.id,
            fiscal_year_id=year.id,
            period_number=2,
            start_date=date(2026, 1, 31),
            end_date=date(2026, 2, 28),
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_adjacent_periods_and_independent_company_calendars_are_valid(db_session):
    company, other, year = calendar(db_session)
    db_session.add(
        FiscalYear(
            company_id=other.id,
            code="2026",
            start_date=year.start_date,
            end_date=year.end_date,
        )
    )
    db_session.add_all(
        [
            FiscalPeriod(
                company_id=company.id,
                fiscal_year_id=year.id,
                period_number=1,
                start_date=date(2026, 1, 1),
                end_date=date(2026, 1, 31),
            ),
            FiscalPeriod(
                company_id=company.id,
                fiscal_year_id=year.id,
                period_number=2,
                start_date=date(2026, 2, 1),
                end_date=date(2026, 2, 28),
            ),
        ]
    )
    db_session.commit()


def test_concurrent_overlapping_years_have_one_winner(db_session):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from sqlalchemy import func, select
    from sqlalchemy.orm import Session

    company = Company(name="Concurrent fiscal calendar")
    db_session.add(company)
    db_session.commit()
    company_id = company.id
    engine = db_session.get_bind()
    barrier = Barrier(2)

    def insert(code):
        from app.services.fiscal_service import create_year

        with Session(engine) as session:
            barrier.wait(timeout=10)
            try:
                create_year(
                    session,
                    company_id=company_id,
                    code=code,
                    start_date=date(2026, 1, 1),
                    end_date=date(2026, 12, 31),
                )
                session.commit()
                return "created"
            except ValueError as exc:
                session.rollback()
                assert "superpone" in str(exc)
                return "overlap"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(insert, ["FIRST", "SECOND"]))
    assert sorted(results) == ["created", "overlap"]
    assert db_session.scalar(select(func.count()).select_from(FiscalYear)) == 1
