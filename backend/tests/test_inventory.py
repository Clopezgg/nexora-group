import uuid
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models.inventory import StockLedgerEntry
from app.models.permission import UserCompanyAccess
from app.repositories import inventory_repository
from app.services import inventory_service
from tests.helpers import create_company, create_supplier, create_user_with_role, login_admin, login_as


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


def _login_warehouse_manager_for_company(client, db_session, *, company_id: str, email: str) -> None:
    user = create_user_with_role(db_session, email=email, role_name="Warehouse Manager")
    db_session.add(UserCompanyAccess(user_id=user.id, company_id=company_id))
    db_session.commit()
    login_as(client, email=email)


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


def test_stock_receive_rejects_foreign_item_or_warehouse_without_ledger_entry(client, db_session):
    login_admin(client)
    company_a, item_a, warehouse_a = _setup(client)
    _company_b, item_b, warehouse_b = _setup(client)
    _login_warehouse_manager_for_company(
        client, db_session, company_id=company_a["id"], email="warehouse-foreign-resource@nexora.group"
    )

    foreign_item = client.post(
        "/api/inventory/stock/receive",
        json={
            "companyId": company_a["id"],
            "itemId": item_b["id"],
            "warehouseId": warehouse_a["id"],
            "quantity": "1.0000",
            "unitCost": "10.0000",
        },
    )
    foreign_warehouse = client.post(
        "/api/inventory/stock/receive",
        json={
            "companyId": company_a["id"],
            "itemId": item_a["id"],
            "warehouseId": warehouse_b["id"],
            "quantity": "1.0000",
            "unitCost": "10.0000",
        },
    )

    assert foreign_item.status_code == 403
    assert foreign_warehouse.status_code == 403
    assert list(db_session.execute(select(StockLedgerEntry)).scalars()) == []


def test_project_issue_rejects_foreign_project_without_ledger_entry(client, db_session):
    login_admin(client)
    company_a, item_a, warehouse_a = _setup(client)
    company_b = create_company(client, name="Constructora B")

    from app.models.project import Project

    foreign_project = Project(company_id=company_b["id"], name="Proyecto ajeno", status="ACTIVE")
    db_session.add(foreign_project)
    db_session.commit()
    received = client.post(
        "/api/inventory/stock/receive",
        json={
            "companyId": company_a["id"],
            "itemId": item_a["id"],
            "warehouseId": warehouse_a["id"],
            "quantity": "10.0000",
            "unitCost": "10.0000",
        },
    )
    assert received.status_code == 201, received.text
    _login_warehouse_manager_for_company(
        client, db_session, company_id=company_a["id"], email="warehouse-foreign-project@nexora.group"
    )

    response = client.post(
        "/api/inventory/stock/issue-to-project",
        json={
            "companyId": company_a["id"],
            "itemId": item_a["id"],
            "warehouseId": warehouse_a["id"],
            "projectId": str(foreign_project.id),
            "quantity": "1.0000",
        },
    )

    assert response.status_code == 403
    issues = list(
        db_session.execute(select(StockLedgerEntry).where(StockLedgerEntry.movement_type == "ISSUE")).scalars()
    )
    assert issues == []


def test_stock_position_does_not_leak_another_company(client, db_session):
    login_admin(client)
    company_a = create_company(client, name="Constructora A")
    _company_b, item_b, warehouse_b = _setup(client)
    received = client.post(
        "/api/inventory/stock/receive",
        json={
            "companyId": item_b["companyId"],
            "itemId": item_b["id"],
            "warehouseId": warehouse_b["id"],
            "quantity": "10.0000",
            "unitCost": "10.0000",
        },
    )
    assert received.status_code == 201, received.text
    _login_warehouse_manager_for_company(
        client, db_session, company_id=company_a["id"], email="warehouse-position@nexora.group"
    )

    response = client.get(
        "/api/inventory/stock/position",
        params={"item_id": item_b["id"], "warehouse_id": warehouse_b["id"]},
    )

    assert response.status_code == 403


def test_transfer_rolls_back_both_legs_when_the_incoming_leg_fails(client, db_session, monkeypatch):
    login_admin(client)
    company, item, source_warehouse = _setup(client)
    destination_warehouse = client.post(
        "/api/inventory/warehouses",
        json={"companyId": company["id"], "code": "ALM-02", "name": "Almacén Secundario"},
    ).json()
    received = client.post(
        "/api/inventory/stock/receive",
        json={
            "companyId": company["id"],
            "itemId": item["id"],
            "warehouseId": source_warehouse["id"],
            "quantity": "20.0000",
            "unitCost": "8.0000",
        },
    )
    assert received.status_code == 201, received.text
    original_append = inventory_repository.append_ledger_entry
    call_count = 0

    def fail_on_incoming_append(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise RuntimeError("injected incoming transfer failure")
        return original_append(*args, **kwargs)

    monkeypatch.setattr(inventory_repository, "append_ledger_entry", fail_on_incoming_append)

    with pytest.raises(RuntimeError, match="injected incoming transfer failure"):
        inventory_service.transfer_stock(
            db_session,
            company_id=uuid.UUID(company["id"]),
            item_id=uuid.UUID(item["id"]),
            from_warehouse_id=uuid.UUID(source_warehouse["id"]),
            to_warehouse_id=uuid.UUID(destination_warehouse["id"]),
            quantity=Decimal("5.0000"),
        )

    entries = list(
        db_session.execute(select(StockLedgerEntry).where(StockLedgerEntry.item_id == uuid.UUID(item["id"]))).scalars()
    )
    assert [entry.movement_type for entry in entries] == ["RECEIPT"]


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


def test_return_to_supplier_reduces_stock_and_tags_the_supplier(client):
    """NXR-REQ-0054: RETURN existía como movement_type sin service function
    ni endpoint (docs/INVENTORY.md deuda intencional)."""
    login_admin(client)
    company, item, warehouse = _setup(client)
    supplier = create_supplier(client, company_id=company["id"])
    client.post(
        "/api/inventory/stock/receive",
        json={"companyId": company["id"], "itemId": item["id"], "warehouseId": warehouse["id"],
              "quantity": "100.0000", "unitCost": "10.0000"},
    )

    returned = client.post(
        "/api/inventory/stock/return-to-supplier",
        json={
            "companyId": company["id"],
            "itemId": item["id"],
            "warehouseId": warehouse["id"],
            "supplierId": supplier["id"],
            "quantity": "15.0000",
            "notes": "Material defectuoso",
        },
    )

    assert returned.status_code == 201, returned.text
    body = returned.json()
    assert body["movementType"] == "RETURN"
    assert float(body["resultingQtyOnHand"]) == 85.0
    assert float(body["unitCost"]) == 10.0
    assert body["sourceType"] == "supplier_return"
    assert body["sourceId"] == supplier["id"]
    assert body["notes"] == "Material defectuoso"

    position = client.get(
        "/api/inventory/stock/position", params={"item_id": item["id"], "warehouse_id": warehouse["id"]}
    ).json()
    assert float(position["quantityOnHand"]) == 85.0


def test_return_to_supplier_more_than_available_is_rejected(client):
    login_admin(client)
    company, item, warehouse = _setup(client)
    supplier = create_supplier(client, company_id=company["id"])
    client.post(
        "/api/inventory/stock/receive",
        json={"companyId": company["id"], "itemId": item["id"], "warehouseId": warehouse["id"],
              "quantity": "10.0000", "unitCost": "5.0000"},
    )

    response = client.post(
        "/api/inventory/stock/return-to-supplier",
        json={
            "companyId": company["id"],
            "itemId": item["id"],
            "warehouseId": warehouse["id"],
            "supplierId": supplier["id"],
            "quantity": "999.0000",
        },
    )

    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "NXR-INVENTORY-001"


def test_return_to_supplier_rejects_a_supplier_from_another_company(client, db_session):
    login_admin(client)
    company, item, warehouse = _setup(client)
    company_b = create_company(client, name="Devoluciones B")
    foreign_supplier = create_supplier(client, company_id=company_b["id"], legal_name="Proveedor ajeno")
    client.post(
        "/api/inventory/stock/receive",
        json={"companyId": company["id"], "itemId": item["id"], "warehouseId": warehouse["id"],
              "quantity": "10.0000", "unitCost": "5.0000"},
    )

    response = client.post(
        "/api/inventory/stock/return-to-supplier",
        json={
            "companyId": company["id"],
            "itemId": item["id"],
            "warehouseId": warehouse["id"],
            "supplierId": foreign_supplier["id"],
            "quantity": "1.0000",
        },
    )

    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "NXR-FINANCIAL-001"


def test_physical_count_approval_requires_access_to_its_company(client, db_session):
    """INV-COMP-001: sin este guard cualquier usuario con
    `inventory.physical_count/approve` en SU compañía podía aprobar el
    conteo físico de otra compañía, generando ajustes de stock ajenos."""
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

    company_b = create_company(client, name="Foreign count company")
    _login_warehouse_manager_for_company(
        client, db_session, company_id=company_b["id"], email="foreign-count@nexora.group"
    )

    response = client.post(f"/api/inventory/physical-counts/{count['id']}/approve")
    assert response.status_code == 403, response.text
    assert response.json()["error"]["code"] == "NXR-PERM-001"
