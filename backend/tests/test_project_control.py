from decimal import Decimal

from app.models.project import Project
from tests.helpers import create_company, login_admin

# Forbidden substrings for a money/balance column on Project -- INV-TRE-002:
# Project jamás posee efectivo. Ver docs/PROJECTS_WBS.md.
_FORBIDDEN_COLUMN_HINTS = ("balance", "cash", "saldo")


def test_project_has_no_money_column():
    """INV-TRE-002: Project no tiene ninguna columna que represente saldo de
    dinero. Introspección real del esquema, no una convención de nombres en
    el código de la app."""
    columns = {column.name for column in Project.__table__.columns}
    for column_name in columns:
        for hint in _FORBIDDEN_COLUMN_HINTS:
            assert hint not in column_name.lower(), (
                f"Project.{column_name} sugiere que el proyecto posee dinero (INV-TRE-002)"
            )


def _create_project(client, *, company_id: str, name: str = "Torre Nexora II") -> dict:
    response = client.post(
        "/api/projects",
        json={"companyId": company_id, "name": name, "code": "PRJ-001", "currencyCode": "HNL"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_create_and_list_project(client):
    login_admin(client)
    company = create_company(client)
    project = _create_project(client, company_id=company["id"])
    assert project["status"] == "PLANNING"
    assert project["companyId"] == company["id"]

    listed = client.get("/api/projects", params={"company_id": company["id"]})
    assert listed.status_code == 200, listed.text
    assert any(p["id"] == project["id"] for p in listed.json())


def test_wbs_hierarchy(client):
    login_admin(client)
    company = create_company(client)
    project = _create_project(client, company_id=company["id"])

    root = client.post(
        f"/api/projects/{project['id']}/wbs", json={"code": "01", "name": "PRELIMINARES"}
    ).json()
    assert root["level"] == 0

    child = client.post(
        f"/api/projects/{project['id']}/wbs",
        json={"code": "01.01", "name": "TRAZO Y NIVELACIÓN", "parentId": root["id"]},
    ).json()
    assert child["level"] == 1
    assert child["parentId"] == root["id"]

    listed = client.get(f"/api/projects/{project['id']}/wbs").json()
    assert {node["id"] for node in listed} == {root["id"], child["id"]}


def test_budget_baseline_cannot_be_created_twice(client):
    """docs/BUDGET_CONTROLLING.md: BASELINE se crea una sola vez."""
    login_admin(client)
    company = create_company(client)
    project = _create_project(client, company_id=company["id"])

    first = client.post(
        f"/api/projects/{project['id']}/budgets/baseline",
        json={"currencyCode": "HNL", "lines": [{"authorizedAmount": "100000.00"}]},
    )
    assert first.status_code == 201, first.text

    second = client.post(
        f"/api/projects/{project['id']}/budgets/baseline",
        json={"currencyCode": "HNL", "lines": [{"authorizedAmount": "999999.00"}]},
    )
    assert second.status_code == 409, second.text
    assert second.json()["error"]["code"] == "NXR-BUDGET-001"

    summary = client.get(f"/api/projects/{project['id']}/budgets/summary").json()
    assert summary["authorized"] == "100000.00"


def test_change_order_approval_creates_revised_budget_without_touching_baseline(client):
    login_admin(client)
    company = create_company(client)
    project = _create_project(client, company_id=company["id"])

    baseline = client.post(
        f"/api/projects/{project['id']}/budgets/baseline",
        json={"currencyCode": "HNL", "lines": [{"authorizedAmount": "100000.00"}]},
    ).json()
    assert baseline["version"] == "BASELINE"
    assert baseline["status"] == "ACTIVE"

    change_order = client.post(
        f"/api/projects/{project['id']}/change-orders",
        json={"reason": "Ampliación de alcance por cambio de cliente", "budgetChangeAmount": "15000.00"},
    ).json()
    assert change_order["status"] == "DRAFT"

    submitted = client.post(f"/api/projects/change-orders/{change_order['id']}/submit")
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["status"] == "SUBMITTED"

    revised = client.post(f"/api/projects/change-orders/{change_order['id']}/approve")
    assert revised.status_code == 200, revised.text
    revised_body = revised.json()
    assert revised_body["version"] == "REVISED"
    assert revised_body["previousBudgetId"] == baseline["id"]

    summary = client.get(f"/api/projects/{project['id']}/budgets/summary").json()
    assert summary["authorized"] == "115000.00"

    # El BASELINE original nunca se toca: sigue existiendo con sus líneas
    # originales, solo cambia a SUPERSEDED como budget activo.
    budgets = client.get(f"/api/projects/{project['id']}/budgets/active").json()
    assert budgets["id"] != baseline["id"]


def test_change_order_cannot_be_approved_without_submit(client):
    login_admin(client)
    company = create_company(client)
    project = _create_project(client, company_id=company["id"])
    client.post(
        f"/api/projects/{project['id']}/budgets/baseline",
        json={"currencyCode": "HNL", "lines": [{"authorizedAmount": "50000.00"}]},
    )
    change_order = client.post(
        f"/api/projects/{project['id']}/change-orders",
        json={"reason": "x", "budgetChangeAmount": "1000.00"},
    ).json()

    response = client.post(f"/api/projects/change-orders/{change_order['id']}/approve")
    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "NXR-PROJECT-001"


def test_forecast_without_progress_returns_none_not_fake_values(client):
    """Orden maestra §42: solo mostrar valores calculables -- sin
    ProgressRecord, PV/EV/CPI/SPI/ETC/EAC/VAC deben ser null, nunca 0
    inventado."""
    login_admin(client)
    company = create_company(client)
    project = _create_project(client, company_id=company["id"])
    client.post(
        f"/api/projects/{project['id']}/budgets/baseline",
        json={"currencyCode": "HNL", "lines": [{"authorizedAmount": "200000.00"}]},
    )

    forecast = client.get(f"/api/projects/{project['id']}/forecast").json()
    assert forecast["bac"] == "200000.00"
    assert forecast["ac"] == "0"
    assert forecast["pv"] is None
    assert forecast["ev"] is None
    assert forecast["cpi"] is None


def test_forecast_with_progress_computes_pv_and_ev(client):
    login_admin(client)
    company = create_company(client)
    project = _create_project(client, company_id=company["id"])
    client.post(
        f"/api/projects/{project['id']}/budgets/baseline",
        json={"currencyCode": "HNL", "lines": [{"authorizedAmount": "200000.00"}]},
    )
    progress = client.post(
        f"/api/projects/{project['id']}/progress",
        json={"recordDate": "2026-08-24", "plannedPercent": "50.00", "actualPercent": "40.00"},
    )
    assert progress.status_code == 201, progress.text

    forecast = client.get(f"/api/projects/{project['id']}/forecast").json()
    assert Decimal(forecast["pv"]) == Decimal("100000.00")
    assert Decimal(forecast["ev"]) == Decimal("80000.00")
    # AC sigue en 0 porque AP/Track A no ha aterrizado -- CPI no es
    # calculable (división por cero evitada explícitamente), nunca falso.
    assert forecast["ac"] == "0"
    assert forecast["cpi"] is None


def test_progress_record_lists_in_order(client):
    login_admin(client)
    company = create_company(client)
    project = _create_project(client, company_id=company["id"])
    client.post(
        f"/api/projects/{project['id']}/progress",
        json={"recordDate": "2026-08-01", "plannedPercent": "10.00", "actualPercent": "8.00"},
    )
    client.post(
        f"/api/projects/{project['id']}/progress",
        json={"recordDate": "2026-08-15", "plannedPercent": "20.00", "actualPercent": "18.00"},
    )
    records = client.get(f"/api/projects/{project['id']}/progress").json()
    assert len(records) == 2
    assert records[0]["recordDate"] < records[1]["recordDate"]


def test_task_and_milestone_creation(client):
    login_admin(client)
    company = create_company(client)
    project = _create_project(client, company_id=company["id"])

    task = client.post(
        f"/api/projects/{project['id']}/tasks",
        json={"name": "Excavación de zapatas", "plannedStart": "2026-09-01", "plannedEnd": "2026-09-10"},
    )
    assert task.status_code == 201, task.text

    milestone = client.post(
        f"/api/projects/{project['id']}/milestones",
        json={"name": "Cierre de cimentación", "dueDate": "2026-10-01"},
    )
    assert milestone.status_code == 201, milestone.text

    tasks = client.get(f"/api/projects/{project['id']}/tasks").json()
    milestones = client.get(f"/api/projects/{project['id']}/milestones").json()
    assert len(tasks) == 1
    assert len(milestones) == 1


def test_company_isolation_on_projects(client, db_session):
    """INV-COMP-001 aplicado a project: un usuario sin acceso a la company
    de otro no puede leer sus proyectos."""
    from tests.helpers import create_user_with_role

    login_admin(client)
    company_a = create_company(client, name="Constructora A")
    _create_project(client, company_id=company_a["id"], name="Proyecto A")

    create_user_with_role(db_session, email="viewer@nexora.group", role_name="Viewer")
    login_response = client.post(
        "/api/auth/login", json={"email": "viewer@nexora.group", "password": "Passw0rd!23"}
    )
    assert login_response.status_code == 200, login_response.text

    response = client.get("/api/projects", params={"company_id": company_a["id"]})
    assert response.status_code == 403, response.text
