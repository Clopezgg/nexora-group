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
