from app.models.accounting import AccountingDocument, AccountingSourceLink
from app.models.equipment import MaintenanceOrder
from tests.helpers import create_account, create_company, login_admin


def _create_project(client, company_id: str) -> dict:
    response = client.post(
        "/api/projects",
        json={
            "companyId": company_id,
            "name": "Proyecto recursos",
            "code": "RES-01",
            "currencyCode": "HNL",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _configure(client, company_id: str, source_type: str, expense_id: str, offset_id: str):
    response = client.put(
        f"/api/master-data/companies/{company_id}/resource-posting-configs/{source_type}",
        json={
            "sourceType": source_type,
            "expenseAccountId": expense_id,
            "offsetAccountId": offset_id,
            "active": True,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def _assert_source_document(db_session, *, source_type: str, source_id: str, document_type: str, project_id: str):
    links = db_session.query(AccountingSourceLink).filter_by(
        source_type=source_type,
        source_id=source_id,
    ).all()
    assert len(links) == 1
    document = db_session.get(AccountingDocument, links[0].accounting_document_id)
    assert document is not None
    assert document.document_type_code == document_type
    assert document.status == "POSTED"
    assert document.scope == "PROJECT"
    assert str(document.project_id) == project_id
    return document


def test_fuel_maintenance_and_labor_post_through_configured_engine(client, db_session):
    login_admin(client)
    company = create_company(client, name="Resource Posting Co")
    project = _create_project(client, company["id"])
    offset = create_account(
        client,
        company_id=company["id"],
        code="2190",
        name="Recursos por pagar",
        account_type="LIABILITY",
    )
    fuel_expense = create_account(
        client,
        company_id=company["id"],
        code="5110",
        name="Combustible",
        account_type="EXPENSE",
    )
    maintenance_expense = create_account(
        client,
        company_id=company["id"],
        code="5120",
        name="Mantenimiento",
        account_type="EXPENSE",
    )
    labor_expense = create_account(
        client,
        company_id=company["id"],
        code="5130",
        name="Mano de obra",
        account_type="EXPENSE",
    )
    _configure(client, company["id"], "FUEL", fuel_expense["id"], offset["id"])
    _configure(client, company["id"], "MAINTENANCE", maintenance_expense["id"], offset["id"])
    _configure(client, company["id"], "LABOR", labor_expense["id"], offset["id"])

    equipment_response = client.post(
        "/api/equipment",
        json={
            "companyId": company["id"],
            "projectId": project["id"],
            "name": "Mezcladora",
            "equipmentType": "MACHINERY",
        },
    )
    assert equipment_response.status_code == 201, equipment_response.text
    equipment = equipment_response.json()

    fuel_response = client.post(
        "/api/equipment/fuel-logs",
        json={
            "companyId": company["id"],
            "equipmentId": equipment["id"],
            "scope": "PROJECT",
            "projectId": project["id"],
            "logDate": "2026-08-29",
            "quantity": "20.00",
            "unitCost": "5.00",
        },
    )
    assert fuel_response.status_code == 201, fuel_response.text
    fuel = fuel_response.json()
    _assert_source_document(
        db_session,
        source_type="fuel_log",
        source_id=fuel["id"],
        document_type="FUE",
        project_id=project["id"],
    )

    maintenance_response = client.post(
        f"/api/equipment/{equipment['id']}/maintenance-orders",
        json={
            "orderType": "PREVENTIVE",
            "description": "Servicio preventivo",
            "openedAt": "2026-08-29",
        },
    )
    assert maintenance_response.status_code == 201, maintenance_response.text
    maintenance = maintenance_response.json()
    close_response = client.patch(
        f"/api/equipment/maintenance-orders/{maintenance['id']}",
        json={
            "status": "CLOSED",
            "partsCost": "80.00",
            "laborCost": "20.00",
            "downtimeHours": "2.00",
            "closedAt": "2026-08-29",
        },
    )
    assert close_response.status_code == 200, close_response.text
    _assert_source_document(
        db_session,
        source_type="maintenance_order",
        source_id=maintenance["id"],
        document_type="MNT",
        project_id=project["id"],
    )

    second_close = client.patch(
        f"/api/equipment/maintenance-orders/{maintenance['id']}",
        json={"status": "CLOSED", "partsCost": "80.00", "laborCost": "20.00"},
    )
    assert second_close.status_code == 409, second_close.text
    assert db_session.query(AccountingSourceLink).filter_by(
        source_type="maintenance_order", source_id=maintenance["id"]
    ).count() == 1
    assert db_session.get(MaintenanceOrder, maintenance["id"]).status == "CLOSED"

    worker_response = client.post(
        "/api/workforce/workers",
        json={
            "companyId": company["id"],
            "fullName": "Trabajador Posting",
            "standardHourlyRate": "100.00",
        },
    )
    assert worker_response.status_code == 201, worker_response.text
    worker = worker_response.json()
    time_response = client.post(
        "/api/workforce/time-entries",
        json={
            "companyId": company["id"],
            "workerId": worker["id"],
            "scope": "PROJECT",
            "projectId": project["id"],
            "workDate": "2026-08-29",
            "hoursWorked": "8.00",
            "hourlyRate": "100.00",
        },
    )
    assert time_response.status_code == 201, time_response.text
    entry = time_response.json()
    approve_response = client.post(
        f"/api/workforce/time-entries/{entry['id']}/approve",
        json={},
    )
    assert approve_response.status_code == 200, approve_response.text
    approved = approve_response.json()
    assert float(approved["laborCost"]) == 800.0
    _assert_source_document(
        db_session,
        source_type="time_entry",
        source_id=entry["id"],
        document_type="LAB",
        project_id=project["id"],
    )

    second_approve = client.post(
        f"/api/workforce/time-entries/{entry['id']}/approve",
        json={},
    )
    assert second_approve.status_code == 409, second_approve.text
    assert db_session.query(AccountingSourceLink).filter_by(
        source_type="time_entry", source_id=entry["id"]
    ).count() == 1


def test_resource_posting_fails_closed_without_company_mapping(client):
    login_admin(client)
    company = create_company(client, name="Resource Fail Closed Co")
    project = _create_project(client, company["id"])
    equipment_response = client.post(
        "/api/equipment",
        json={
            "companyId": company["id"],
            "projectId": project["id"],
            "name": "Retroexcavadora",
            "equipmentType": "MACHINERY",
        },
    )
    assert equipment_response.status_code == 201, equipment_response.text
    equipment = equipment_response.json()

    response = client.post(
        "/api/equipment/fuel-logs",
        json={
            "companyId": company["id"],
            "equipmentId": equipment["id"],
            "scope": "PROJECT",
            "projectId": project["id"],
            "logDate": "2026-08-29",
            "quantity": "10.00",
            "unitCost": "5.00",
        },
    )
    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "NXR-FINANCIAL-001"
