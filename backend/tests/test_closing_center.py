import uuid
from datetime import date, datetime, timedelta, timezone

import pytest

from app.models.accounting import AccountingDocument, JournalLine
from app.models.fiscal import FiscalPeriod, FiscalYear
from tests.helpers import create_account, create_company, login_admin


@pytest.mark.parametrize("within_period", [True, False])
def test_draft_close_guard_uses_economic_date(client, db_session, within_period):
    login_admin(client)
    company, period_id = _company_with_open_period(client, db_session)
    period = db_session.get(FiscalPeriod, uuid.UUID(period_id))
    draft = AccountingDocument(
        company_id=uuid.UUID(company["id"]),
        document_type_code="JRN",
        document_number="JRN-DRAFT-CLOSE",
        scope="GENERAL",
        currency_code="HNL",
        status="DRAFT",
        posted_at=None,
        effective_date=period.start_date
        if within_period
        else period.end_date + timedelta(days=1),
    )
    db_session.add(draft)
    db_session.commit()
    response = client.get(
        f"/api/accounting/closing/checklist?companyId={company['id']}&periodId={period_id}"
    )
    assert response.status_code == 200, response.text
    check = next(
        c for c in response.json()["checks"] if c["key"] == "no_draft_documents"
    )
    assert check["passed"] is not within_period
    closed = client.post(
        f"/api/accounting/closing/{period_id}/hard-close?companyId={company['id']}",
        json={},
    )
    assert closed.status_code == (409 if within_period else 200), closed.text


@pytest.mark.parametrize("within_period", [True, False])
def test_balance_close_guard_uses_economic_date(client, db_session, within_period):
    login_admin(client)
    company, period_id = _company_with_open_period(client, db_session)
    account = create_account(
        client,
        company_id=company["id"],
        code="9999",
        name="Closing tripwire",
        account_type="ASSET",
    )
    period = db_session.get(FiscalPeriod, uuid.UUID(period_id))
    inside, outside = period.start_date, period.end_date + timedelta(days=1)
    document = AccountingDocument(
        company_id=uuid.UUID(company["id"]),
        document_type_code="JRN",
        document_number="JRN-BALANCE-CLOSE",
        scope="GENERAL",
        currency_code="HNL",
        status="DRAFT",
        effective_date=inside if within_period else outside,
        posted_at=datetime.combine(
            outside if within_period else inside, datetime.min.time(), timezone.utc
        ),
    )
    db_session.add(document)
    db_session.flush()
    # Deliberately inconsistent fixture verifies the closing integrity tripwire.
    db_session.add(
        JournalLine(
            accounting_document_id=document.id,
            account_id=uuid.UUID(account["id"]),
            debit_amount=10,
            credit_amount=0,
        )
    )
    db_session.commit()
    response = client.get(
        f"/api/accounting/closing/checklist?companyId={company['id']}&periodId={period_id}"
    )
    assert response.status_code == 200, response.text
    check = next(c for c in response.json()["checks"] if c["key"] == "double_entry")
    assert check["passed"] is not within_period


def _company_with_open_period(client, db_session):
    company = create_company(client)
    debit_account = create_account(
        client, company_id=company["id"], code="1000", name="Caja", account_type="ASSET"
    )
    credit_account = create_account(
        client,
        company_id=company["id"],
        code="3000",
        name="Aportes",
        account_type="EQUITY",
    )
    today = date.today()
    year = FiscalYear(
        company_id=company["id"],
        code=str(today.year),
        start_date=date(today.year, 1, 1),
        end_date=date(today.year, 12, 31),
    )
    db_session.add(year)
    db_session.flush()
    period = FiscalPeriod(
        fiscal_year_id=year.id,
        company_id=company["id"],
        period_number=today.month,
        start_date=today - timedelta(days=10),
        end_date=today + timedelta(days=10),
        status="OPEN",
    )
    db_session.add(period)
    db_session.commit()

    # Un asiento manual balanceado dentro del período.
    client.post(
        "/api/accounting/journal-entries",
        json={
            "companyId": company["id"],
            "scope": "GENERAL",
            "currencyCode": "HNL",
            "lines": [
                {"accountId": debit_account["id"], "debitAmount": "100.00"},
                {"accountId": credit_account["id"], "creditAmount": "100.00"},
            ],
        },
    )
    return company, str(period.id)


def test_preclose_checklist_and_hard_close_flow(client, db_session):
    login_admin(client)
    company, period_id = _company_with_open_period(client, db_session)

    checklist = client.get(
        f"/api/accounting/closing/checklist?companyId={company['id']}&periodId={period_id}"
    )
    assert checklist.status_code == 200, checklist.text
    body = checklist.json()
    keys = {c["key"] for c in body["checks"]}
    assert {
        "period_state",
        "subledger_gl",
        "no_draft_documents",
        "double_entry",
        "bank_reconciliation",
    } == keys
    assert body["canHardClose"] is True
    assert all(c["passed"] for c in body["checks"] if c["blocking"])

    # Cierre duro -> manifiesto con el snapshot de checks.
    closed = client.post(
        f"/api/accounting/closing/{period_id}/hard-close?companyId={company['id']}",
        json={},
    )
    assert closed.status_code == 200, closed.text
    manifest = closed.json()
    assert manifest["forced"] is False
    assert len(manifest["checks"]) == 5

    # El período quedó CLOSED e inmutable.
    periods = client.get(f"/api/fiscal/periods?companyId={company['id']}").json()
    this_period = next(p for p in periods if p["id"] == period_id)
    assert this_period["status"] == "CLOSED"

    # Segundo cierre -> 422 (ya está cerrado).
    again = client.post(
        f"/api/accounting/closing/{period_id}/hard-close?companyId={company['id']}",
        json={},
    )
    assert again.status_code == 422, again.text

    # El checklist ahora reporta el check de estado como fallido y bloqueante.
    after = client.get(
        f"/api/accounting/closing/checklist?companyId={company['id']}&periodId={period_id}"
    ).json()
    state_check = next(c for c in after["checks"] if c["key"] == "period_state")
    assert state_check["passed"] is False
    assert after["canHardClose"] is False


def test_hard_close_force_requires_reason(client, db_session):
    login_admin(client)
    company, period_id = _company_with_open_period(client, db_session)
    forced_no_reason = client.post(
        f"/api/accounting/closing/{period_id}/hard-close?companyId={company['id']}",
        json={"force": True},
    )
    assert forced_no_reason.status_code == 422, forced_no_reason.text
    assert "motivo" in forced_no_reason.json()["detail"].lower()
