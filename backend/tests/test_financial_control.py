from tests.helpers import (
    create_account,
    create_company,
    create_supplier,
    create_treasury_account,
    login_admin,
)


def _setup(client):
    company = create_company(client)
    cash_gl = create_account(
        client, company_id=company["id"], code="1110", name="Caja", account_type="ASSET"
    )
    contributions = create_account(
        client, company_id=company["id"], code="3100", name="Aportes", account_type="EQUITY"
    )
    cash = create_treasury_account(
        client, company_id=company["id"], gl_account_id=cash_gl["id"], name="Caja", kind="CASH"
    )
    client.post(
        "/api/treasury/remittances",
        json={
            "companyId": company["id"],
            "treasuryAccountId": cash["id"],
            "counterAccountId": contributions["id"],
            "sender": "Fondeo",
            "currencyCode": "HNL",
            "originalAmount": "5000.00",
            "remittanceDate": "2026-01-01",
        },
    )
    return company, cash


def test_daily_status_returns_actionable_kpis(client):
    login_admin(client)
    company, _cash = _setup(client)

    response = client.get(f"/api/financial-control/daily-status?companyId={company['id']}")
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["companyId"] == company["id"]
    assert body["currencyCode"] == "HNL"
    keys = {kpi["key"] for kpi in body["kpis"]}
    assert {
        "cash_position",
        "postings_today",
        "ap_due_today",
        "ap_overdue",
        "ar_due_today",
        "ar_overdue",
        "pending_approvals",
        "fiscal_period",
    } <= keys

    cash_kpi = next(k for k in body["kpis"] if k["key"] == "cash_position")
    assert cash_kpi["numeric"] == 5000.0
    assert cash_kpi["value"].startswith("L ")
    assert cash_kpi["route"] == "/finanzas/tesoreria"

    # Sin período fiscal configurado -> KPI crítico, no una cifra inventada.
    period_kpi = next(k for k in body["kpis"] if k["key"] == "fiscal_period")
    assert period_kpi["value"] == "No configurado"
    assert period_kpi["severity"] == "critical"


def test_daily_status_denies_company_without_access(client, db_session):
    from tests.helpers import create_user_with_role, login_as

    login_admin(client)
    company, _cash = _setup(client)

    create_user_with_role(
        db_session, email="outsider@nexora.group", role_name="Finance Manager"
    )
    login_as(client, email="outsider@nexora.group")
    denied = client.get(f"/api/financial-control/daily-status?companyId={company['id']}")
    assert denied.status_code in (403, 404), denied.text
