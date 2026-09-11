import uuid
from datetime import timedelta

import pytest
from pydantic import ValidationError

from app.core.business_time import business_today
from app.models.company import Company
from app.models.permission import UserCompanyAccess, UserProjectAccess
from app.models.project import Project
from app.schemas.dashboard import DashboardSummaryResponse
from tests.conftest import BOOTSTRAP_ADMIN_EMAIL, BOOTSTRAP_ADMIN_PASSWORD
from tests.helpers import (
    create_account,
    create_company,
    create_treasury_account,
    create_user_with_role,
    login_as,
)


def _login(client):
    client.post(
        "/api/auth/login",
        json={"email": BOOTSTRAP_ADMIN_EMAIL, "password": BOOTSTRAP_ADMIN_PASSWORD},
    )


def test_dashboard_summary_requires_auth(client):
    response = client.get("/api/dashboard/summary")
    assert response.status_code == 401


def test_dashboard_summary_requires_explicit_company_context(client):
    _login(client)

    response = client.get("/api/dashboard/summary")

    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "NXR-DASHBOARD-001"


def test_dashboard_schema_requires_explicit_currency():
    with pytest.raises(ValidationError):
        DashboardSummaryResponse(
            treasury_balance="0.00",
            period_income="0.00",
            period_expense="0.00",
            active_projects=0,
        )


def test_dashboard_unknown_company_is_not_found(client):
    _login(client)

    response = client.get(f"/api/dashboard/summary?companyId={uuid.uuid4()}")

    assert response.status_code == 404, response.text
    assert response.json()["error"]["code"] == "NXR-DATA-002"


def test_dashboard_company_without_functional_currency_fails_closed(client, db_session):
    _login(client)
    company = Company(name="Compañía sin moneda")
    db_session.add(company)
    db_session.commit()

    response = client.get(f"/api/dashboard/summary?companyId={company.id}")

    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "NXR-DASHBOARD-001"


def test_dashboard_money_fields_serialize_as_decimal_safe_strings_not_float(client):
    """CLAUDE.md §12/ORDEN MAESTRA: ninguna cifra financiera se serializa como
    float binario -- el resto del backend (p.ej. /api/treasury/accounts)
    devuelve Decimal como string JSON exacto. El dashboard debe seguir el
    mismo contrato, no truncar a float."""
    _login(client)
    company = create_company(client)
    bank_gl = create_account(
        client, company_id=company["id"], code="1100", name="Bancos", account_type="ASSET"
    )
    contributions = create_account(
        client,
        company_id=company["id"],
        code="3100",
        name="Aportes de socios",
        account_type="EQUITY",
    )
    bank = create_treasury_account(
        client, company_id=company["id"], gl_account_id=bank_gl["id"]
    )
    response = client.post(
        "/api/treasury/remittances",
        json={
            "companyId": company["id"],
            "treasuryAccountId": bank["id"],
            "counterAccountId": contributions["id"],
            "sender": "Constructora Matriz",
            "currencyCode": "HNL",
            "originalAmount": "50000.00",
            "remittanceDate": str(business_today()),
        },
    )
    assert response.status_code == 201, response.text

    dashboard = client.get(f"/api/dashboard/summary?companyId={company['id']}")
    assert dashboard.status_code == 200, dashboard.text
    body = dashboard.json()
    assert isinstance(body["treasuryBalance"], str), (
        f"treasuryBalance debe ser un string Decimal-safe, no float: {body['treasuryBalance']!r}"
    )
    assert body["treasuryBalance"] == "50000.00"


def test_company_dashboard_isolates_companies_and_functional_currencies(client):
    """Dos compañías visibles con monedas distintas nunca se mezclan ni heredan
    la moneda de la primera fila de `companies`."""
    _login(client)

    hnl_company = create_company(client, name="Nexora HNL", currency="HNL")
    hnl_bank_gl = create_account(
        client,
        company_id=hnl_company["id"],
        code="1100-HNL",
        name="Banco HNL",
        account_type="ASSET",
    )
    hnl_equity = create_account(
        client,
        company_id=hnl_company["id"],
        code="3100-HNL",
        name="Capital HNL",
        account_type="EQUITY",
    )
    hnl_bank = client.post(
        "/api/treasury/accounts",
        json={
            "companyId": hnl_company["id"],
            "name": "Banco HNL",
            "kind": "BANK",
            "currencyCode": "HNL",
            "glAccountId": hnl_bank_gl["id"],
        },
    )
    assert hnl_bank.status_code == 201, hnl_bank.text
    hnl_remittance = client.post(
        "/api/treasury/remittances",
        json={
            "companyId": hnl_company["id"],
            "treasuryAccountId": hnl_bank.json()["id"],
            "counterAccountId": hnl_equity["id"],
            "sender": "HNL owner",
            "currencyCode": "HNL",
            "originalAmount": "700.25",
            "remittanceDate": str(business_today()),
        },
    )
    assert hnl_remittance.status_code == 201, hnl_remittance.text

    usd_company = create_company(client, name="Nexora USD", currency="USD")
    usd_bank_gl = create_account(
        client,
        company_id=usd_company["id"],
        code="1100-USD",
        name="Banco USD",
        account_type="ASSET",
    )
    usd_equity = create_account(
        client,
        company_id=usd_company["id"],
        code="3100-USD",
        name="Capital USD",
        account_type="EQUITY",
    )
    usd_bank = client.post(
        "/api/treasury/accounts",
        json={
            "companyId": usd_company["id"],
            "name": "Banco USD",
            "kind": "BANK",
            "currencyCode": "USD",
            "glAccountId": usd_bank_gl["id"],
        },
    )
    assert usd_bank.status_code == 201, usd_bank.text
    usd_remittance = client.post(
        "/api/treasury/remittances",
        json={
            "companyId": usd_company["id"],
            "treasuryAccountId": usd_bank.json()["id"],
            "counterAccountId": usd_equity["id"],
            "sender": "USD owner",
            "currencyCode": "USD",
            "originalAmount": "125.50",
            "remittanceDate": str(business_today()),
        },
    )
    assert usd_remittance.status_code == 201, usd_remittance.text

    hnl_response = client.get(f"/api/dashboard/summary?companyId={hnl_company['id']}")
    usd_response = client.get(f"/api/dashboard/summary?companyId={usd_company['id']}")

    assert hnl_response.status_code == 200, hnl_response.text
    assert hnl_response.json()["currency"] == "HNL"
    assert hnl_response.json()["treasuryBalance"] == "700.25"

    assert usd_response.status_code == 200, usd_response.text
    assert usd_response.json()["currency"] == "USD"
    assert usd_response.json()["treasuryBalance"] == "125.50"


def test_dashboard_active_projects_never_counts_another_companys_projects(client, db_session):
    """INV-COMP-001: un dashboard con Company explícita solo cuenta proyectos
    visibles dentro de esa misma Company."""
    _login(client)
    company_a = create_company(client, name="Dashboard A")
    company_b = create_company(client, name="Dashboard B")
    project_a1 = Project(company_id=company_a["id"], name="Proyecto A1", status="ACTIVE")
    project_a2 = Project(company_id=company_a["id"], name="Proyecto A2", status="ACTIVE")
    project_b1 = Project(company_id=company_b["id"], name="Proyecto B1", status="ACTIVE")
    db_session.add_all([project_a1, project_a2, project_b1])
    db_session.commit()

    admin_a = client.get(f"/api/dashboard/summary?companyId={company_a['id']}")
    admin_b = client.get(f"/api/dashboard/summary?companyId={company_b['id']}")
    assert admin_a.status_code == 200, admin_a.text
    assert admin_b.status_code == 200, admin_b.text
    assert admin_a.json()["activeProjects"] == 2
    assert admin_b.json()["activeProjects"] == 1

    user = create_user_with_role(
        db_session, email="dashboard-scoped@nexora.group", role_name="Project Manager"
    )
    db_session.add(UserCompanyAccess(user_id=user.id, company_id=company_a["id"]))
    db_session.add_all(
        [
            UserProjectAccess(user_id=user.id, project_id=project_a1.id),
            UserProjectAccess(user_id=user.id, project_id=project_a2.id),
        ]
    )
    db_session.commit()
    login_as(client, email="dashboard-scoped@nexora.group")

    scoped_summary = client.get(f"/api/dashboard/summary?companyId={company_a['id']}")
    forbidden_summary = client.get(f"/api/dashboard/summary?companyId={company_b['id']}")
    assert scoped_summary.status_code == 200, scoped_summary.text
    assert scoped_summary.json()["activeProjects"] == 2
    assert forbidden_summary.status_code == 403, forbidden_summary.text


def test_dashboard_active_projects_respects_explicit_project_assignments(client, db_session):
    _login(client)
    company = create_company(client, name="Dashboard Project Scope")
    allowed = Project(company_id=company["id"], name="Proyecto permitido", status="ACTIVE")
    denied = Project(company_id=company["id"], name="Proyecto restringido", status="ACTIVE")
    db_session.add_all([allowed, denied])
    db_session.flush()
    user = create_user_with_role(
        db_session,
        email="dashboard-project-scope@nexora.group",
        role_name="Project Manager",
    )
    db_session.add(UserCompanyAccess(user_id=user.id, company_id=company["id"]))
    db_session.add(UserProjectAccess(user_id=user.id, project_id=allowed.id))
    db_session.commit()
    login_as(client, email="dashboard-project-scope@nexora.group")

    response = client.get(f"/api/dashboard/summary?companyId={company['id']}")

    assert response.status_code == 200, response.text
    assert response.json()["activeProjects"] == 1


def test_dashboard_period_metrics_group_by_effective_date_not_posted_at(client):
    """ORDEN MAESTRA §23/§28/§53 — un asiento con fecha económica en un mes
    anterior NO cuenta en el período económico actual, aunque se contabilice hoy."""
    _login(client)
    company = create_company(client, name="Dashboard EffDate")
    expense = create_account(
        client,
        company_id=company["id"],
        code="5100",
        name="Gasto",
        account_type="EXPENSE",
    )
    payable = create_account(
        client,
        company_id=company["id"],
        code="2100",
        name="Pasivo",
        account_type="LIABILITY",
    )

    def _entry(eff_date, amount):
        response = client.post(
            "/api/accounting/journal-entries",
            json={
                "companyId": company["id"],
                "scope": "GENERAL",
                "currencyCode": "HNL",
                "effectiveDate": eff_date,
                "lines": [
                    {"accountId": expense["id"], "debitAmount": amount},
                    {"accountId": payable["id"], "creditAmount": amount},
                ],
            },
        )
        assert response.status_code == 201, response.text

    today = business_today()
    prev_month = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
    _entry(prev_month.isoformat(), "400.00")
    _entry(today.isoformat(), "125.00")

    response = client.get(f"/api/dashboard/summary?companyId={company['id']}")
    assert response.status_code == 200, response.text
    assert float(response.json()["periodExpense"]) == 125.0


def test_dashboard_financial_totals_net_formal_reversals(client):
    _login(client)
    company = create_company(client, name="Dashboard Reversal")
    expense = create_account(
        client,
        company_id=company["id"],
        code="5100",
        name="Gasto dashboard",
        account_type="EXPENSE",
    )
    payable = create_account(
        client,
        company_id=company["id"],
        code="2100",
        name="Pasivo dashboard",
        account_type="LIABILITY",
    )
    journal = client.post(
        "/api/accounting/journal-entries",
        json={
            "companyId": company["id"],
            "scope": "GENERAL",
            "currencyCode": "HNL",
            "lines": [
                {"accountId": expense["id"], "debitAmount": "125.00"},
                {"accountId": payable["id"], "creditAmount": "125.00"},
            ],
        },
    )
    assert journal.status_code == 201, journal.text
    before = client.get(f"/api/dashboard/summary?companyId={company['id']}")
    assert before.status_code == 200, before.text
    assert float(before.json()["periodExpense"]) == 125.0

    reversal = client.post(
        f"/api/accounting/journal-entries/{journal.json()['id']}/reverse",
        json={"reason": "Gasto duplicado"},
    )
    assert reversal.status_code == 200, reversal.text
    after = client.get(f"/api/dashboard/summary?companyId={company['id']}")

    assert after.status_code == 200, after.text
    assert float(after.json()["periodExpense"]) == 0.0
