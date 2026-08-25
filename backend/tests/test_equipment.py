from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.equipment import FuelLog
from tests.helpers import create_company, login_admin


def _create_project(client, *, company_id: str, name: str = "Torre Nexora III") -> dict:
    response = client.post(
        "/api/projects",
        json={"companyId": company_id, "name": name, "code": "PRJ-EQ-001", "currencyCode": "HNL"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_equipment(client, *, company_id: str, name: str = "Retroexcavadora") -> dict:
    response = client.post(
        "/api/equipment",
        json={"companyId": company_id, "equipmentType": "EXCAVATOR", "name": name},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_project_fuel_log_requires_project_id(client):
    """Named behavior from the brief: PROJECT scope sin project_id viola el
    dominio (422) Y el constraint real de PostgreSQL."""
    login_admin(client)
    company = create_company(client)
    equipment = _create_equipment(client, company_id=company["id"])

    response = client.post(
        "/api/equipment/fuel-logs",
        json={
            "companyId": company["id"],
            "equipmentId": equipment["id"],
            "logDate": "2026-01-05",
            "quantity": "40.000",
            "unitCost": "95.5000",
            "scope": "PROJECT",
        },
    )
    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "NXR-ACCOUNTING-002"


def test_fuel_log_db_constraint_rejects_project_scope_without_project(db_session):
    """Mismo invariante, ahora a nivel de constraint REAL de PostgreSQL
    (ck_fuel_logs_operation_scope), sin pasar por el service layer."""
    from app.models.company import Company

    company = Company(name="Fuel Constraint Co")
    db_session.add(company)
    db_session.flush()

    bad_log = FuelLog(
        company_id=company.id,
        log_date="2026-01-05",
        quantity=Decimal("40.000"),
        unit_cost=Decimal("95.5000"),
        total_cost=Decimal("3820.00"),
        scope="PROJECT",
        project_id=None,
    )
    db_session.add(bad_log)
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


def test_fuel_log_total_cost_is_computed_server_side(client):
    login_admin(client)
    company = create_company(client)
    equipment = _create_equipment(client, company_id=company["id"])

    response = client.post(
        "/api/equipment/fuel-logs",
        json={
            "companyId": company["id"],
            "equipmentId": equipment["id"],
            "logDate": "2026-01-05",
            "quantity": "40.000",
            "unitCost": "95.5000",
            "scope": "GENERAL",
        },
    )
    assert response.status_code == 201, response.text
    assert response.json()["totalCost"] == "3820.00"


def test_project_fuel_log_accepted_with_project_id(client):
    login_admin(client)
    company = create_company(client)
    equipment = _create_equipment(client, company_id=company["id"])
    project = _create_project(client, company_id=company["id"])

    response = client.post(
        "/api/equipment/fuel-logs",
        json={
            "companyId": company["id"],
            "equipmentId": equipment["id"],
            "logDate": "2026-01-05",
            "quantity": "40.000",
            "unitCost": "95.5000",
            "scope": "PROJECT",
            "projectId": project["id"],
        },
    )
    assert response.status_code == 201, response.text


def test_closed_maintenance_order_is_immutable(client):
    """Named behavior from the brief: update after CLOSED is rejected and
    persisted values remain unchanged."""
    login_admin(client)
    company = create_company(client)
    equipment = _create_equipment(client, company_id=company["id"])

    created = client.post(
        f"/api/equipment/{equipment['id']}/maintenance-orders",
        json={"orderType": "CORRECTIVE", "openedAt": "2026-01-10", "description": "Cambio de aceite"},
    )
    assert created.status_code == 201, created.text
    order = created.json()

    closed = client.patch(
        f"/api/equipment/maintenance-orders/{order['id']}",
        json={"status": "CLOSED", "partsCost": "150.00", "laborCost": "75.00"},
    )
    assert closed.status_code == 200, closed.text
    closed_order = closed.json()
    assert closed_order["status"] == "CLOSED"
    assert closed_order["partsCost"] == "150.00"

    attempted_update = client.patch(
        f"/api/equipment/maintenance-orders/{order['id']}",
        json={"partsCost": "999.00", "description": "intento de fraude"},
    )
    assert attempted_update.status_code == 409, attempted_update.text
    assert attempted_update.json()["error"]["code"] == "NXR-EQUIPMENT-001"

    reread = client.get(f"/api/equipment/{equipment['id']}/maintenance-orders")
    assert reread.status_code == 200
    persisted = reread.json()[0]
    assert persisted["partsCost"] == "150.00"
    assert persisted["description"] == "Cambio de aceite"


def test_maintenance_order_creation_sets_equipment_under_maintenance(client):
    login_admin(client)
    company = create_company(client)
    equipment = _create_equipment(client, company_id=company["id"])

    client.post(
        f"/api/equipment/{equipment['id']}/maintenance-orders",
        json={"orderType": "PREVENTIVE", "openedAt": "2026-01-10"},
    )
    refreshed = client.get(f"/api/equipment/{equipment['id']}")
    assert refreshed.json()["status"] == "UNDER_MAINTENANCE"
