from tests.helpers import create_account, create_company, create_supplier, login_admin


def _create_equipment(client, *, company_id: str, name: str) -> dict:
    response = client.post(
        "/api/equipment",
        json={"companyId": company_id, "equipmentType": "EXCAVATOR", "name": name},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_asset(client, *, company_id: str) -> dict:
    expense = create_account(
        client,
        company_id=company_id,
        code="EQ-DEP-EXP",
        name="Depreciación equipo",
        account_type="EXPENSE",
    )
    accumulated = create_account(
        client,
        company_id=company_id,
        code="EQ-DEP-ACC",
        name="Depreciación acumulada equipo",
        account_type="ASSET",
    )
    response = client.post(
        "/api/assets",
        json={
            "companyId": company_id,
            "category": "Maquinaria",
            "name": "Activo aislado",
            "acquisitionDate": "2026-01-01",
            "cost": "12000.00",
            "currencyCode": "HNL",
            "usefulLifeMonths": 12,
            "salvageValue": "0.00",
            "scope": "GENERAL",
            "depreciationExpenseAccountId": expense["id"],
            "accumulatedDepreciationAccountId": accumulated["id"],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_equipment_rejects_asset_owned_by_another_company(client):
    login_admin(client)
    company_a = create_company(client, name="Equipment Tenant A")
    company_b = create_company(client, name="Equipment Tenant B")
    asset_b = _create_asset(client, company_id=company_b["id"])

    response = client.post(
        "/api/equipment",
        json={
            "companyId": company_a["id"],
            "assetId": asset_b["id"],
            "equipmentType": "EXCAVATOR",
            "name": "Equipo con activo ajeno",
        },
    )

    assert response.status_code == 422, response.text
    assert "asset_id" in str(response.json()).lower()


def test_maintenance_order_rejects_supplier_owned_by_another_company(client):
    login_admin(client)
    company_a = create_company(client, name="Maintenance Tenant A")
    company_b = create_company(client, name="Maintenance Tenant B")
    equipment_a = _create_equipment(client, company_id=company_a["id"], name="Equipo A")
    supplier_b = create_supplier(client, company_id=company_b["id"], legal_name="Proveedor B")

    response = client.post(
        f"/api/equipment/{equipment_a['id']}/maintenance-orders",
        json={
            "orderType": "CORRECTIVE",
            "openedAt": "2026-01-10",
            "supplierId": supplier_b["id"],
        },
    )

    assert response.status_code == 422, response.text
    assert "supplier_id" in str(response.json()).lower()

    reread = client.get(f"/api/equipment/{equipment_a['id']}")
    assert reread.status_code == 200, reread.text
    assert reread.json()["status"] == "AVAILABLE"


def test_maintenance_order_rejects_plan_from_another_equipment(client):
    login_admin(client)
    company = create_company(client, name="Maintenance Plan Isolation")
    equipment_a = _create_equipment(client, company_id=company["id"], name="Equipo A")
    equipment_b = _create_equipment(client, company_id=company["id"], name="Equipo B")

    plan = client.post(
        f"/api/equipment/{equipment_b['id']}/maintenance-plans",
        json={
            "name": "Plan exclusivo B",
            "triggerType": "HOURS",
            "triggerValue": "100.00",
        },
    )
    assert plan.status_code == 201, plan.text

    response = client.post(
        f"/api/equipment/{equipment_a['id']}/maintenance-orders",
        json={
            "orderType": "PREVENTIVE",
            "openedAt": "2026-01-10",
            "planId": plan.json()["id"],
        },
    )

    assert response.status_code == 422, response.text
    assert "plan_id" in str(response.json()).lower()

    reread = client.get(f"/api/equipment/{equipment_a['id']}")
    assert reread.status_code == 200, reread.text
    assert reread.json()["status"] == "AVAILABLE"
