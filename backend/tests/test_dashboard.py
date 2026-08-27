from app.models.permission import UserCompanyAccess
from app.models.project import Project
from tests.conftest import BOOTSTRAP_ADMIN_EMAIL, BOOTSTRAP_ADMIN_PASSWORD
from tests.helpers import create_company, create_user_with_role, login_as


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
    assert body["treasuryBalance"] == 0.0
    assert body["periodIncome"] == 0.0
    assert body["periodExpense"] == 0.0
    assert body["activeProjects"] == 0
    assert body["pendingApprovals"] == 0
    assert body["overduePayables"] == 0
    assert body["overduePayablesAmount"] == 0.0
    assert body["receivablesOutstanding"] == 0.0
    assert len(body["cashFlow"]) == 6
    assert body["expensesByScope"] == []
    assert body["currency"] == "HNL"


def test_dashboard_active_projects_never_counts_another_companys_projects(client, db_session):
    """INV-COMP-001: `active_projects` no puede filtrarse cross-company --
    un usuario sin scope ANY solo debe ver el conteo real de las
    compañías a las que tiene acceso, nunca el agregado de toda la
    plataforma."""
    _login(client)
    company_a = create_company(client, name="Dashboard A")
    company_b = create_company(client, name="Dashboard B")
    db_session.add_all(
        [
            Project(company_id=company_a["id"], name="Proyecto A1", status="ACTIVE"),
            Project(company_id=company_a["id"], name="Proyecto A2", status="ACTIVE"),
            Project(company_id=company_b["id"], name="Proyecto B1", status="ACTIVE"),
        ]
    )
    db_session.commit()

    admin_summary = client.get("/api/dashboard/summary")
    assert admin_summary.status_code == 200, admin_summary.text
    assert admin_summary.json()["activeProjects"] == 3

    user = create_user_with_role(
        db_session, email="dashboard-scoped@nexora.group", role_name="Finance Manager"
    )
    db_session.add(UserCompanyAccess(user_id=user.id, company_id=company_a["id"]))
    db_session.commit()
    login_as(client, email="dashboard-scoped@nexora.group")

    scoped_summary = client.get("/api/dashboard/summary")
    assert scoped_summary.status_code == 200, scoped_summary.text
    assert scoped_summary.json()["activeProjects"] == 2
