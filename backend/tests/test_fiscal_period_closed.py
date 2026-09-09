from datetime import date, timedelta

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.fiscal import FiscalPeriod, FiscalYear
from app.services import posting_service
from tests.helpers import create_account, create_company, login_admin


def test_configured_year_without_periods_is_not_bootstrap(client, db_session):
    login_admin(client)
    company = create_company(client)
    db_session.add(FiscalYear(
        company_id=company["id"], code="2026",
        start_date=date(2026, 1, 1), end_date=date(2026, 12, 31),
    ))
    db_session.commit()
    with pytest.raises(posting_service.FiscalPeriodClosedError, match="gap"):
        posting_service._assert_fiscal_period_open(
            db_session, company_id=company["id"], as_of=date(2026, 6, 1),
        )


def test_closed_fiscal_period_blocks_posting(client, db_session):
    """INV-ACC-003."""
    login_admin(client)
    company = create_company(client)
    debit_account = create_account(
        client, company_id=company["id"], code="1000", name="Caja", account_type="ASSET"
    )
    credit_account = create_account(
        client, company_id=company["id"], code="2000", name="CxP", account_type="LIABILITY"
    )

    today = date.today()
    fiscal_year = FiscalYear(
        company_id=company["id"],
        code=str(today.year),
        start_date=date(today.year, 1, 1),
        end_date=date(today.year, 12, 31),
    )
    db_session.add(fiscal_year)
    db_session.flush()
    closed_period = FiscalPeriod(
        fiscal_year_id=fiscal_year.id,
        company_id=company["id"],
        period_number=today.month,
        start_date=today - timedelta(days=5),
        end_date=today + timedelta(days=5),
        status="CLOSED",
    )
    db_session.add(closed_period)
    db_session.commit()

    response = client.post(
        "/api/accounting/journal-entries",
        json={
            "companyId": company["id"],
            "scope": "GENERAL",
            "currencyCode": "HNL",
            "lines": [
                {"accountId": debit_account["id"], "debitAmount": "10.00"},
                {"accountId": credit_account["id"], "creditAmount": "10.00"},
            ],
        },
    )

    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "NXR-ACCOUNTING-003"


def test_open_fiscal_period_allows_posting(client, db_session):
    login_admin(client)
    company = create_company(client)
    debit_account = create_account(
        client, company_id=company["id"], code="1000", name="Caja", account_type="ASSET"
    )
    credit_account = create_account(
        client, company_id=company["id"], code="2000", name="CxP", account_type="LIABILITY"
    )

    today = date.today()
    fiscal_year = FiscalYear(
        company_id=company["id"],
        code=str(today.year),
        start_date=date(today.year, 1, 1),
        end_date=date(today.year, 12, 31),
    )
    db_session.add(fiscal_year)
    db_session.flush()
    open_period = FiscalPeriod(
        fiscal_year_id=fiscal_year.id,
        company_id=company["id"],
        period_number=today.month,
        start_date=today - timedelta(days=5),
        end_date=today + timedelta(days=5),
        status="OPEN",
    )
    db_session.add(open_period)
    db_session.commit()

    response = client.post(
        "/api/accounting/journal-entries",
        json={
            "companyId": company["id"],
            "scope": "GENERAL",
            "currencyCode": "HNL",
            "lines": [
                {"accountId": debit_account["id"], "debitAmount": "10.00"},
                {"accountId": credit_account["id"], "creditAmount": "10.00"},
            ],
        },
    )

    assert response.status_code == 201, response.text


def test_effective_date_in_closed_period_blocks_when_today_is_open(client, db_session):
    """Fiscal eligibility is determined by the economic date, never server today."""
    login_admin(client)
    company = create_company(client)
    debit = create_account(client, company_id=company["id"], code="1000", name="Caja", account_type="ASSET")
    credit = create_account(client, company_id=company["id"], code="2000", name="CxP", account_type="LIABILITY")
    year = FiscalYear(company_id=company["id"], code="2026", start_date=date(2026, 1, 1), end_date=date(2026, 12, 31))
    db_session.add(year)
    db_session.flush()
    db_session.add(FiscalPeriod(fiscal_year_id=year.id, company_id=company["id"], period_number=1, start_date=date(2026, 1, 1), end_date=date(2026, 1, 31), status="CLOSED"))
    db_session.commit()
    response = client.post("/api/accounting/journal-entries", json={"companyId": company["id"], "scope": "GENERAL", "currencyCode": "HNL", "effectiveDate": "2026-01-15", "lines": [{"accountId": debit["id"], "debitAmount": "10.00"}, {"accountId": credit["id"], "creditAmount": "10.00"}]})
    assert response.status_code == 409, response.text


def test_configured_calendar_gap_rejects_posting(client, db_session):
    login_admin(client)
    company = create_company(client)
    debit = create_account(client, company_id=company["id"], code="1000", name="Caja", account_type="ASSET")
    credit = create_account(client, company_id=company["id"], code="2000", name="CxP", account_type="LIABILITY")
    year = FiscalYear(company_id=company["id"], code="2026", start_date=date(2026, 1, 1), end_date=date(2026, 12, 31))
    db_session.add(year)
    db_session.flush()
    db_session.add(FiscalPeriod(fiscal_year_id=year.id, company_id=company["id"], period_number=1, start_date=date(2026, 1, 1), end_date=date(2026, 1, 31), status="OPEN"))
    db_session.commit()
    response = client.post("/api/accounting/journal-entries", json={"companyId": company["id"], "scope": "GENERAL", "currencyCode": "HNL", "effectiveDate": "2026-02-15", "lines": [{"accountId": debit["id"], "debitAmount": "10.00"}, {"accountId": credit["id"], "creditAmount": "10.00"}]})
    assert response.status_code == 409, response.text
    assert "gap" in response.text


def test_fiscal_period_check_uses_business_date_not_utc(client, db_session, monkeypatch):
    """INV-ACC-003 / timezone: at 23:00 in Honduras (05:00 UTC next day) a
    posting must be evaluated against the Honduras calendar day, not the UTC
    one. The CLOSED period covers only the Honduras 'today'."""
    login_admin(client)
    company = create_company(client)
    debit_account = create_account(
        client, company_id=company["id"], code="1000", name="Caja", account_type="ASSET"
    )
    credit_account = create_account(
        client, company_id=company["id"], code="2000", name="CxP", account_type="LIABILITY"
    )

    honduras_today = date(2026, 6, 15)
    utc_tomorrow = date(2026, 6, 16)
    monkeypatch.setattr(posting_service, "business_today", lambda: honduras_today)

    fiscal_year = FiscalYear(
        company_id=company["id"], code="2026",
        start_date=date(2026, 1, 1), end_date=date(2026, 12, 31),
    )
    db_session.add(fiscal_year)
    db_session.flush()
    db_session.add(
        FiscalPeriod(
            fiscal_year_id=fiscal_year.id, company_id=company["id"], period_number=6,
            start_date=honduras_today, end_date=honduras_today, status="CLOSED",
        )
    )
    db_session.add(
        FiscalPeriod(
            fiscal_year_id=fiscal_year.id, company_id=company["id"], period_number=7,
            start_date=utc_tomorrow, end_date=utc_tomorrow, status="OPEN",
        )
    )
    db_session.commit()

    response = client.post(
        "/api/accounting/journal-entries",
        json={
            "companyId": company["id"],
            "scope": "GENERAL",
            "currencyCode": "HNL",
            "lines": [
                {"accountId": debit_account["id"], "debitAmount": "10.00"},
                {"accountId": credit_account["id"], "creditAmount": "10.00"},
            ],
        },
    )

    # Must be blocked by the CLOSED Honduras-day period. Using the UTC date
    # would have hit the OPEN period and wrongly returned 201.
    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "NXR-ACCOUNTING-003"


def test_fiscal_year_rejects_an_inverted_date_range(db_session, client):
    """Fiscal calendars cannot persist an ambiguous year range."""
    login_admin(client)
    company = create_company(client)
    db_session.add(
        FiscalYear(
            company_id=company["id"],
            code="BAD-2026",
            start_date=date(2026, 12, 31),
            end_date=date(2026, 1, 1),
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_fiscal_period_rejects_an_inverted_date_range_and_invalid_status(db_session, client):
    """Hard fiscal period invariants are enforced by PostgreSQL, not the UI."""
    login_admin(client)
    company = create_company(client)
    year = FiscalYear(
        company_id=company["id"], code="2026", start_date=date(2026, 1, 1), end_date=date(2026, 12, 31)
    )
    db_session.add(year)
    db_session.flush()
    db_session.add(
        FiscalPeriod(
            fiscal_year_id=year.id,
            company_id=company["id"],
            period_number=1,
            start_date=date(2026, 2, 1),
            end_date=date(2026, 1, 1),
            status="INVALID",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()
