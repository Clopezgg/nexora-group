from datetime import date, timedelta

from app.core.business_time import business_today
from app.models.permission import UserCompanyAccess, UserProjectAccess
from app.models.project import Project
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


def test_dashboard_summary_returns_real_zeroed_values_on_fresh_db(client):
    _login(client)
    response = client.get("/api/dashboard/summary")
    assert response.status_code == 200
    body = response.json()
    assert float(body["treasuryBalance"]) == 0.0
    assert float(body["periodIncome"]) == 0.0
    assert float(body["periodExpense"]) == 0.0
    assert body["activeProjects"] == 0
    assert body["pendingApprovals"] == 0
    assert body["overduePayables"] == 0
    assert float(body["overduePayablesAmount"]) == 0.0
    assert float(body["receivablesOutstanding"]) == 0.0
    assert len(body["cashFlow"]) == 6
    assert body["expensesByScope"] == []
    assert body["currency"] == "HNL"


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
        client, company_id=company["id"], code="3100", name="Aportes de socios", account_type="EQUITY"
    )
    bank = create_treasury_account(client, company_id=company["id"], gl_account_id=bank_gl["id"])
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

    body = client.get("/api/dashboard/summary").json()
    assert isinstance(body["treasuryBalance"], str), (
        f"treasuryBalance debe ser un string Decimal-safe, no float: {body['treasuryBalance']!r}"
    )
    assert body["treasuryBalance"] == "50000.00"


def test_dashboard_active_projects_never_counts_another_companys_projects(client, db_session):
    """INV-COMP-001: `active_projects` no puede filtrarse cross-company --
    un usuario sin scope ANY solo debe ver el conteo real de las
    compañías a las que tiene acceso, nunca el agregado de toda la
    plataforma."""
    _login(client)
    company_a = create_company(client, name="Dashboard A")
    company_b = create_company(client, name="Dashboard B")
    project_a1 = Project(company_id=company_a["id"], name="Proyecto A1", status="ACTIVE")
    project_a2 = Project(company_id=company_a["id"], name="Proyecto A2", status="ACTIVE")
    project_b1 = Project(company_id=company_b["id"], name="Proyecto B1", status="ACTIVE")
    db_session.add_all([project_a1, project_a2, project_b1])
    db_session.commit()

    admin_summary = client.get("/api/dashboard/summary")
    assert admin_summary.status_code == 200, admin_summary.text
    assert admin_summary.json()["activeProjects"] == 3

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

    scoped_summary = client.get("/api/dashboard/summary")
    assert scoped_summary.status_code == 200, scoped_summary.text
    assert scoped_summary.json()["activeProjects"] == 2


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
    expense = create_account(client, company_id=company["id"], code="5100", name="Gasto", account_type="EXPENSE")
    payable = create_account(client, company_id=company["id"], code="2100", name="Pasivo", account_type="LIABILITY")

    def _entry(eff_date, amount):
        r = client.post(
            "/api/accounting/journal-entries",
            json={
                "companyId": company["id"], "scope": "GENERAL", "currencyCode": "HNL",
                "effectiveDate": eff_date,
                "lines": [
                    {"accountId": expense["id"], "debitAmount": amount},
                    {"accountId": payable["id"], "creditAmount": amount},
                ],
            },
        )
        assert r.status_code == 201, r.text

    # El dashboard agrupa por fecha de negocio (America/Tegucigalpa); en CI
    # (UTC) ``date.today()`` adelanta el asiento un día entre las 18:00 y las
    # 23:59 de Honduras y lo saca del período económico actual.
    today = business_today()
    prev_month = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
    _entry(prev_month.isoformat(), "400.00")   # fuera del período económico actual
    _entry(today.isoformat(), "125.00")        # dentro

    body = client.get(f"/api/dashboard/summary?companyId={company['id']}").json()
    assert float(body["periodExpense"]) == 125.0


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
