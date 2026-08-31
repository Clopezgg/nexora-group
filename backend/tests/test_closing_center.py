from datetime import date, timedelta

from app.models.fiscal import FiscalPeriod, FiscalYear
from tests.helpers import create_account, create_company, login_admin


def _company_with_open_period(client, db_session):
    company = create_company(client)
    debit_account = create_account(
        client, company_id=company["id"], code="1000", name="Caja", account_type="ASSET"
    )
    credit_account = create_account(
        client, company_id=company["id"], code="3000", name="Aportes", account_type="EQUITY"
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
