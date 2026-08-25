from app.models.permission import UserCompanyAccess
from tests.helpers import create_company, create_user_with_role, login_admin, login_as


def _create_worker(client, *, company_id: str, name: str = "Juan Pérez") -> dict:
    response = client.post(
        "/api/workforce/workers",
        json={"companyId": company_id, "fullName": name, "standardHourlyRate": "125.50"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_labor_cost_equals_approved_rate_times_hours(client):
    """Named behavior from the brief: rate 125.50 x 8 approved hours records
    1004.00 project cost. `labor_cost` es SIEMPRE calculado en el servidor,
    nunca aceptado del cliente."""
    login_admin(client)
    company = create_company(client)
    worker = _create_worker(client, company_id=company["id"])

    submitted = client.post(
        "/api/workforce/time-entries",
        json={
            "companyId": company["id"],
            "workerId": worker["id"],
            "scope": "GENERAL",
            "workDate": "2026-01-10",
            "hoursWorked": "8.00",
            "hourlyRate": "125.50",
        },
    )
    assert submitted.status_code == 201, submitted.text
    entry = submitted.json()
    assert entry["status"] == "SUBMITTED"
    assert entry["laborCost"] is None

    approved = client.post(f"/api/workforce/time-entries/{entry['id']}/approve", json={})
    assert approved.status_code == 200, approved.text
    approved_entry = approved.json()
    assert approved_entry["status"] == "APPROVED"
    assert approved_entry["approvedHours"] == "8.00"
    assert approved_entry["laborCost"] == "1004.00"


def test_time_entry_labor_cost_uses_approved_hours_not_submitted_hours(client):
    """Si el aprobador ajusta las horas (p.ej. 8 reportadas, 6 aprobadas), el
    costo usa las horas APROBADAS, no las originalmente reportadas."""
    login_admin(client)
    company = create_company(client)
    worker = _create_worker(client, company_id=company["id"])

    submitted = client.post(
        "/api/workforce/time-entries",
        json={
            "companyId": company["id"],
            "workerId": worker["id"],
            "scope": "GENERAL",
            "workDate": "2026-01-10",
            "hoursWorked": "8.00",
            "hourlyRate": "125.50",
        },
    )
    entry = submitted.json()

    approved = client.post(
        f"/api/workforce/time-entries/{entry['id']}/approve", json={"approvedHours": "6.00"}
    )
    assert approved.status_code == 200, approved.text
    approved_entry = approved.json()
    assert approved_entry["approvedHours"] == "6.00"
    assert approved_entry["laborCost"] == "753.00"


def test_time_entry_cannot_be_approved_twice(client):
    login_admin(client)
    company = create_company(client)
    worker = _create_worker(client, company_id=company["id"])

    submitted = client.post(
        "/api/workforce/time-entries",
        json={
            "companyId": company["id"],
            "workerId": worker["id"],
            "scope": "GENERAL",
            "workDate": "2026-01-10",
            "hoursWorked": "8.00",
            "hourlyRate": "125.50",
        },
    )
    entry = submitted.json()
    first = client.post(f"/api/workforce/time-entries/{entry['id']}/approve", json={})
    assert first.status_code == 200

    second = client.post(f"/api/workforce/time-entries/{entry['id']}/approve", json={})
    assert second.status_code == 409, second.text
    assert second.json()["error"]["code"] == "NXR-WORKFORCE-001"


def test_project_time_entry_requires_project_id(client):
    login_admin(client)
    company = create_company(client)
    worker = _create_worker(client, company_id=company["id"])

    response = client.post(
        "/api/workforce/time-entries",
        json={
            "companyId": company["id"],
            "workerId": worker["id"],
            "scope": "PROJECT",
            "workDate": "2026-01-10",
            "hoursWorked": "8.00",
            "hourlyRate": "125.50",
        },
    )
    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "NXR-ACCOUNTING-002"


def test_company_access_blocks_cross_company_time_entry_approval(client, db_session):
    """A company-A Project Manager cannot approve a TimeEntry owned by
    company B (INV-COMP-001) -- same shared `assert_company_access` every
    other track's resources use."""
    login_admin(client)
    company_b = create_company(client, name="Constructora B")
    worker_b = _create_worker(client, company_id=company_b["id"])
    submitted = client.post(
        "/api/workforce/time-entries",
        json={
            "companyId": company_b["id"],
            "workerId": worker_b["id"],
            "scope": "GENERAL",
            "workDate": "2026-01-10",
            "hoursWorked": "8.00",
            "hourlyRate": "125.50",
        },
    ).json()

    company_a = create_company(client, name="Constructora A")
    pm_a = create_user_with_role(
        db_session, email="pm-a-workforce@nexora.group", role_name="Project Manager"
    )
    db_session.add(UserCompanyAccess(user_id=pm_a.id, company_id=company_a["id"]))
    db_session.commit()

    login_as(client, email="pm-a-workforce@nexora.group")
    response = client.post(f"/api/workforce/time-entries/{submitted['id']}/approve", json={})

    assert response.status_code == 403, response.text
    assert response.json()["error"]["code"] == "NXR-PERM-001"

    login_admin(client)
    persisted = client.get(f"/api/workforce/time-entries?companyId={company_b['id']}").json()[0]
    assert persisted["status"] == "SUBMITTED"
    assert persisted["laborCost"] is None


def _create_project(client, *, company_id: str, name: str = "Torre Cuadrillas") -> dict:
    response = client.post(
        "/api/projects",
        json={"companyId": company_id, "name": name, "code": "CRW-001", "currencyCode": "HNL"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_creating_a_crew_and_adding_members(client):
    """NXR-REQ-0074: `movement_type`-style minimal scope, mismo criterio
    que `Worker` ("cubre lo mínimo... no un módulo de RRHH completo")."""
    login_admin(client)
    company = create_company(client)
    project = _create_project(client, company_id=company["id"])
    worker_a = _create_worker(client, company_id=company["id"], name="Carlos López")
    worker_b = _create_worker(client, company_id=company["id"], name="Ana Martínez")

    crew = client.post(
        "/api/workforce/crews",
        json={"companyId": company["id"], "name": "Cuadrilla Estructuras", "projectId": project["id"]},
    )
    assert crew.status_code == 201, crew.text
    crew_body = crew.json()
    assert crew_body["name"] == "Cuadrilla Estructuras"
    assert crew_body["projectId"] == project["id"]
    assert crew_body["status"] == "ACTIVE"

    added_a = client.post(
        f"/api/workforce/crews/{crew_body['id']}/members", json={"workerId": worker_a["id"]}
    )
    assert added_a.status_code == 201, added_a.text
    added_b = client.post(
        f"/api/workforce/crews/{crew_body['id']}/members", json={"workerId": worker_b["id"]}
    )
    assert added_b.status_code == 201, added_b.text

    detail = client.get(f"/api/workforce/crews/{crew_body['id']}")
    assert detail.status_code == 200, detail.text
    member_names = {m["fullName"] for m in detail.json()["members"]}
    assert member_names == {"Carlos López", "Ana Martínez"}

    listed = client.get(f"/api/workforce/crews?companyId={company['id']}").json()
    assert [c["id"] for c in listed] == [crew_body["id"]]


def test_cannot_add_the_same_worker_to_a_crew_twice(client):
    login_admin(client)
    company = create_company(client)
    worker = _create_worker(client, company_id=company["id"])
    crew = client.post(
        "/api/workforce/crews", json={"companyId": company["id"], "name": "Cuadrilla Única"}
    ).json()

    first = client.post(f"/api/workforce/crews/{crew['id']}/members", json={"workerId": worker["id"]})
    assert first.status_code == 201, first.text

    second = client.post(f"/api/workforce/crews/{crew['id']}/members", json={"workerId": worker["id"]})
    assert second.status_code == 409, second.text
    assert second.json()["error"]["code"] == "NXR-WORKFORCE-002"


def test_removing_a_crew_member(client):
    login_admin(client)
    company = create_company(client)
    worker = _create_worker(client, company_id=company["id"])
    crew = client.post(
        "/api/workforce/crews", json={"companyId": company["id"], "name": "Cuadrilla Temporal"}
    ).json()
    client.post(f"/api/workforce/crews/{crew['id']}/members", json={"workerId": worker["id"]})

    removed = client.delete(f"/api/workforce/crews/{crew['id']}/members/{worker['id']}")
    assert removed.status_code == 204, removed.text

    detail = client.get(f"/api/workforce/crews/{crew['id']}").json()
    assert detail["members"] == []


def test_crew_never_returns_another_companys_data(client, db_session):
    login_admin(client)
    company_a = create_company(client, name="Cuadrillas A")
    company_b = create_company(client, name="Cuadrillas B")

    user = create_user_with_role(
        db_session, email="equipment-crew@nexora.group", role_name="Equipment Manager"
    )
    db_session.add(UserCompanyAccess(user_id=user.id, company_id=company_b["id"]))
    db_session.commit()
    login_as(client, email="equipment-crew@nexora.group")

    response = client.get(f"/api/workforce/crews?companyId={company_a['id']}")
    assert response.status_code == 403, response.text
    assert response.json()["error"]["code"] == "NXR-PERM-001"
