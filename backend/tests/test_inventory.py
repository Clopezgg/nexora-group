import uuid
from decimal import Decimal

from app.repositories import inventory_repository
from tests.helpers import create_company, login_admin


def _setup(client):
    company = create_company(client)
    item = client.post(
        "/api/inventory/items",
        json={"companyId": company["id"], "sku": "VAR-3-8", "name": "Varilla 3/8", "uom": "UND"},
    ).json()
    warehouse = client.post(
        "/api/inventory/warehouses",
        json={"companyId": company["id"], "code": "ALM-01", "name": "Almacén Central"},
    ).json()
    return company, item, warehouse


def test_receive_stock_sets_moving_average(client):
    login_admin(client)
    company, item, warehouse = _setup(client)

    first = client.post(
        "/api/inventory/stock/receive",
        json={"companyId": company["id"], "itemId": item["id"], "warehouseId": warehouse["id"],
              "quantity": "100.0000", "unitCost": "10.0000"},
    ).json()
    assert float(first["resultingQtyOnHand"]) == 100.0
    assert float(first["resultingAvgCost"]) == 10.0

    second = client.post(
        "/api/inventory/stock/receive",
        json={"companyId": company["id"], "itemId": item["id"], "warehouseId": warehouse["id"],
              "quantity": "50.0000", "unitCost": "16.0000"},
    ).json()
    # (100*10 + 50*16) / 150 = 12.0
    assert float(second["resultingQtyOnHand"]) == 150.0
    assert float(second["resultingAvgCost"]) == 12.0


def test_issue_to_project_reduces_warehouse_stock(client, db_session):
    """INV-INV-002. Fase 0/1 todavía no expone un endpoint de creación de
    Project (lo construye Track B en paralelo) -- se inserta directo vía
    ORM, que es lo único disponible hoy para tener un Project real."""
    login_admin(client)
    company, item, warehouse = _setup(client)

    from app.models.project import Project

    project = Project(company_id=company["id"], name="Torre Nexora II", status="ACTIVE")
    db_session.add(project)
    db_session.commit()

    client.post(
        "/api/inventory/stock/receive",
        json={"companyId": company["id"], "itemId": item["id"], "warehouseId": warehouse["id"],
              "quantity": "100.0000", "unitCost": "10.0000"},
    )

    issued = client.post(
        "/api/inventory/stock/issue-to-project",
        json={"companyId": company["id"], "itemId": item["id"], "warehouseId": warehouse["id"],
              "projectId": str(project.id), "quantity": "30.0000"},
    )
    assert issued.status_code == 201, issued.text
    assert float(issued.json()["resultingQtyOnHand"]) == 70.0
    assert issued.json()["projectId"] == str(project.id)

    position = client.get(
        "/api/inventory/stock/position", params={"item_id": item["id"], "warehouse_id": warehouse["id"]}
    ).json()
    assert float(position["quantityOnHand"]) == 70.0


def test_inventory_actuals_are_derived_from_project_issues(client, db_session):
    """Only posted project issues contribute actuals; transfers never do."""
    login_admin(client)
    company, item, warehouse = _setup(client)

    from app.models.project import Project

    project = Project(company_id=company["id"], name="Torre Nexora III", status="ACTIVE")
    db_session.add(project)
    db_session.commit()
    other_warehouse = client.post(
        "/api/inventory/warehouses",
        json={"companyId": company["id"], "code": "ALM-02", "name": "Almacén Secundario"},
    ).json()
    received = client.post(
        "/api/inventory/stock/receive",
        json={
            "companyId": company["id"],
            "itemId": item["id"],
            "warehouseId": warehouse["id"],
            "quantity": "10.0000",
            "unitCost": "10.0000",
        },
    )
    assert received.status_code == 201, received.text
    issue = client.post(
        "/api/inventory/stock/issue-to-project",
        json={
            "companyId": company["id"],
            "itemId": item["id"],
            "warehouseId": warehouse["id"],
            "projectId": str(project.id),
            "quantity": "8.0000",
        },
    )
    assert issue.status_code == 201, issue.text
    transfer = client.post(
        "/api/inventory/stock/transfer",
        json={
            "companyId": company["id"],
            "itemId": item["id"],
            "fromWarehouseId": warehouse["id"],
            "toWarehouseId": other_warehouse["id"],
            "quantity": "2.0000",
        },
    )
    assert transfer.status_code == 201, transfer.text

    actuals = inventory_repository.project_actuals_by_project(
        db_session, company_id=uuid.UUID(company["id"])
    )

    assert actuals == {project.id: Decimal("80.00")}


def test_issue_more_than_available_is_rejected(client):
    """INV-INV-001: no hay stock negativo silencioso."""
    login_admin(client)
    company, item, warehouse = _setup(client)
    client.post(
        "/api/inventory/stock/receive",
        json={"companyId": company["id"], "itemId": item["id"], "warehouseId": warehouse["id"],
              "quantity": "10.0000", "unitCost": "5.0000"},
    )
    other_warehouse = client.post(
        "/api/inventory/warehouses",
        json={"companyId": company["id"], "code": "ALM-02", "name": "Almacén Secundario"},
    ).json()
    response = client.post(
        "/api/inventory/stock/transfer",
        json={"companyId": company["id"], "itemId": item["id"],
              "fromWarehouseId": warehouse["id"], "toWarehouseId": other_warehouse["id"], "quantity": "999.0000"},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "NXR-INVENTORY-001"


def test_transfer_moves_stock_between_warehouses(client):
    login_admin(client)
    company, item, warehouse = _setup(client)
    other_warehouse = client.post(
        "/api/inventory/warehouses",
        json={"companyId": company["id"], "code": "ALM-02", "name": "Almacén Secundario"},
    ).json()
    client.post(
        "/api/inventory/stock/receive",
        json={"companyId": company["id"], "itemId": item["id"], "warehouseId": warehouse["id"],
              "quantity": "20.0000", "unitCost": "8.0000"},
    )

    response = client.post(
        "/api/inventory/stock/transfer",
        json={"companyId": company["id"], "itemId": item["id"],
              "fromWarehouseId": warehouse["id"], "toWarehouseId": other_warehouse["id"], "quantity": "5.0000"},
    )
    assert response.status_code == 201, response.text
    outgoing, incoming = response.json()
    assert float(outgoing["resultingQtyOnHand"]) == 15.0
    assert float(incoming["resultingQtyOnHand"]) == 5.0
    assert float(incoming["unitCost"]) == 8.0


def test_physical_count_creates_adjustment_for_variance(client):
    login_admin(client)
    company, item, warehouse = _setup(client)
    client.post(
        "/api/inventory/stock/receive",
        json={"companyId": company["id"], "itemId": item["id"], "warehouseId": warehouse["id"],
              "quantity": "50.0000", "unitCost": "4.0000"},
    )

    count = client.post(
        "/api/inventory/physical-counts",
        json={
            "companyId": company["id"],
            "warehouseId": warehouse["id"],
            "countDate": "2026-08-24",
            "lines": [{"itemId": item["id"], "expectedQuantity": "50.0000", "countedQuantity": "47.0000"}],
        },
    ).json()
    assert count["status"] == "COUNTED"

    approved = client.post(f"/api/inventory/physical-counts/{count['id']}/approve").json()
    assert approved["status"] == "APPROVED"

    position = client.get(
        "/api/inventory/stock/position", params={"item_id": item["id"], "warehouse_id": warehouse["id"]}
    ).json()
    assert float(position["quantityOnHand"]) == 47.0
