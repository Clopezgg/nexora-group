from tests.helpers import create_company, login_admin


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
