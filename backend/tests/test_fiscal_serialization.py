"""Real PostgreSQL transactions serialize fiscal eligibility and closure."""

from datetime import date

import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.fiscal import FiscalPeriod, FiscalYear
from app.services.fiscal_service import transition_period_status
from app.services.posting_service import (
    _assert_fiscal_period_open,
    FiscalPeriodClosedError,
)


def _period(db):
    company = Company(name="Fiscal serialization")
    db.add(company)
    db.flush()
    year = FiscalYear(
        company_id=company.id,
        code="2026",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )
    db.add(year)
    db.flush()
    period = FiscalPeriod(
        company_id=company.id,
        fiscal_year_id=year.id,
        period_number=1,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
        status="OPEN",
    )
    db.add(period)
    db.commit()
    return company.id, period.id


def test_fiscal_gate_waits_for_closure_and_rechecks_committed_status(db_session):
    company_id, period_id = _period(db_session)
    with (
        Session(db_session.get_bind()) as closer,
        Session(db_session.get_bind()) as poster,
    ):
        # Preload OPEN to also prove identity-map refresh after the lock.
        stale = poster.get(FiscalPeriod, period_id)
        transition_period_status(closer, period_id=period_id, target_status="CLOSED")
        poster.execute(text("SET LOCAL lock_timeout = '150ms'"))
        with pytest.raises(OperationalError) as exc:
            _assert_fiscal_period_open(
                poster, company_id=company_id, as_of=date(2026, 1, 15)
            )
        assert exc.value.orig.sqlstate == "55P03"
        poster.rollback()
        closer.commit()
        with pytest.raises(FiscalPeriodClosedError):
            _assert_fiscal_period_open(
                poster, company_id=company_id, as_of=date(2026, 1, 15)
            )
        assert stale.status == "CLOSED"


def test_closure_waits_until_eligible_posting_transaction_finishes(db_session):
    company_id, period_id = _period(db_session)
    with (
        Session(db_session.get_bind()) as poster,
        Session(db_session.get_bind()) as closer,
    ):
        _assert_fiscal_period_open(
            poster, company_id=company_id, as_of=date(2026, 1, 15)
        )
        closer.execute(text("SET LOCAL lock_timeout = '150ms'"))
        with pytest.raises(OperationalError) as exc:
            transition_period_status(
                closer, period_id=period_id, target_status="CLOSED"
            )
        assert exc.value.orig.sqlstate == "55P03"
        closer.rollback()
        poster.commit()
        assert (
            transition_period_status(
                closer, period_id=period_id, target_status="CLOSED"
            ).status
            == "CLOSED"
        )
        closer.commit()


def test_stale_period_cannot_reopen_a_committed_hard_close(db_session):
    _, period_id = _period(db_session)
    with (
        Session(db_session.get_bind()) as stale_session,
        Session(db_session.get_bind()) as closer,
    ):
        stale = stale_session.get(FiscalPeriod, period_id)
        transition_period_status(closer, period_id=period_id, target_status="CLOSED")
        closer.commit()
        with pytest.raises(ValueError, match="Transición"):
            transition_period_status(
                stale_session, period_id=period_id, target_status="SOFT_CLOSED"
            )
        assert stale.status == "CLOSED"


def test_stale_hard_close_cannot_issue_a_second_closure_manifest(db_session):
    from app.services.closing_service import hard_close

    company_id, period_id = _period(db_session)
    with (
        Session(db_session.get_bind()) as stale_session,
        Session(db_session.get_bind()) as closer,
    ):
        stale = stale_session.get(FiscalPeriod, period_id)
        transition_period_status(closer, period_id=period_id, target_status="CLOSED")
        closer.commit()
        with pytest.raises(ValueError, match="ya está cerrado"):
            hard_close(
                stale_session,
                company_id=company_id,
                period_id=period_id,
                force=True,
                reason="Controlled test closure",
            )
        assert stale.status == "CLOSED"


def test_period_generation_serializes_before_checking_existing_periods(db_session):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    from sqlalchemy import func, select
    from app.services.fiscal_service import create_year, generate_monthly_periods

    company = Company(name="Calendar generation concurrency")
    db_session.add(company)
    db_session.flush()
    year = create_year(
        db_session, company_id=company.id, code="2026",
        start_date=date(2026, 1, 1), end_date=date(2026, 12, 31),
    )
    db_session.commit()
    year_id = year.id
    ready = Event()
    backend_pid = []

    def competing_generation():
        with Session(db_session.get_bind()) as second:
            backend_pid.append(second.scalar(text("SELECT pg_backend_pid()")))
            ready.set()
            try:
                generate_monthly_periods(second, fiscal_year_id=year_id)
                second.commit()
                return "unexpected duplicate"
            except ValueError as exc:
                second.rollback()
                return str(exc)

    with Session(db_session.get_bind()) as first, ThreadPoolExecutor(max_workers=1) as pool:
        assert len(generate_monthly_periods(first, fiscal_year_id=year_id)) == 12
        future = pool.submit(competing_generation)
        try:
            assert ready.wait(5)
            import time
            deadline = time.monotonic() + 5
            with db_session.get_bind().connect().execution_options(isolation_level="AUTOCOMMIT") as observer:
                while time.monotonic() < deadline:
                    if observer.scalar(text(
                        "SELECT wait_event_type = 'Lock' FROM pg_stat_activity WHERE pid = :pid"
                    ), {"pid": backend_pid[0]}):
                        break
                else:
                    pytest.fail("Competing generator never waited for the first transaction")
        finally:
            first.commit()
        assert "ya tiene períodos" in future.result(timeout=5)
    assert db_session.scalar(select(func.count()).select_from(FiscalPeriod)) == 12
