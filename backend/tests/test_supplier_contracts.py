from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models.permission import UserCompanyAccess
from app.models.supplier import Supplier, SupplierContract
from tests.helpers import create_company, create_supplier, create_user_with_role, login_admin, login_as


def _create_project(client, *, company_id: str, name: str = "Torre Contratos") -> dict:
    response = client.post(
        "/api/projects",
        json={"companyId": company_id, "name": name, "code": "SC-PRJ", "currencyCode": "HNL"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_contract(
    client,
    *,
    company_id: str,
    supplier_id: str,
    project_id: str | None = None,
    contract_number: str = "SC-001",
) -> dict:
    payload = {
        "companyId": company_id,
        "supplierId": supplier_id,
        "contractNumber": contract_number,
        "value": "150000.00",
        "currencyCode": "HNL",
        "startDate": "2026-01-01",
        "advancePercentage": "10.00",
        "retentionPercentage": "5.00",
    }
    if project_id is not None:
        payload["projectId"] = project_id
    return client.post("/api/procurement/suppliers/contracts", json=payload)


def test_creating_and_listing_supplier_contracts(client):
    """NXR-REQ-0059/0060: SupplierContract cubre tanto Supplier Contracts
    como Subcontracts (mismo modelo, sin campo distintivo -- ver la Ruling
    en docs/REQUIREMENTS_TRACEABILITY.md)."""
    login_admin(client)
    company = create_company(client)
    supplier = create_supplier(client, company_id=company["id"])
    project = _create_project(client, company_id=company["id"])

    created = _create_contract(
        client, company_id=company["id"], supplier_id=supplier["id"], project_id=project["id"]
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["contractNumber"] == "SC-001"
    assert Decimal(body["value"]) == Decimal("150000.00")
    assert Decimal(body["advancePercentage"]) == Decimal("10.00")
    assert Decimal(body["retentionPercentage"]) == Decimal("5.00")
    assert body["status"] == "DRAFT"
    assert body["projectId"] == project["id"]

    listed = client.get(f"/api/procurement/suppliers/contracts?company_id={company['id']}")
    assert listed.status_code == 200, listed.text
    assert [c["id"] for c in listed.json()] == [body["id"]]


def test_supplier_create_emits_safe_audit_snapshot(client):
    login_admin(client)
    company = create_company(client, name="Supplier Audit Co")

    response = client.post(
        "/api/procurement/suppliers",
        json={
            "companyId": company["id"],
            "legalName": "Proveedor Auditado",
            "classification": "CRITICAL",
            "bankingDetails": {"account": "SECRET-123", "bank": "Private Bank"},
        },
        headers={"X-Correlation-Id": "supplier-audit-001"},
    )
    assert response.status_code == 201, response.text
    supplier = response.json()

    entries = client.get(
        f"/api/audit?companyId={company['id']}&entityType=procurement.supplier"
    ).json()
    entry = next(item for item in entries if item["entityId"] == supplier["id"])
    assert entry["action"] == "procurement.supplier.create"
    assert entry["after"] == {
        "classification": "CRITICAL",
        "legalName": "Proveedor Auditado",
        "status": "ACTIVE",
        "tradeName": None,
    }
    assert "bankingDetails" not in entry["after"]
    assert "SECRET-123" not in str(entry)
    assert entry["correlationId"] == "supplier-audit-001"


def test_supplier_create_rolls_back_when_audit_fails(client, db_session, monkeypatch):
    login_admin(client)
    company = create_company(client, name="Supplier Rollback Co")

    def fail_record(*args, **kwargs):
        raise RuntimeError("audit unavailable")

    monkeypatch.setattr("app.api.routes.suppliers.audit_service.record", fail_record)

    with pytest.raises(RuntimeError, match="audit unavailable"):
        client.post(
            "/api/procurement/suppliers",
            json={"companyId": company["id"], "legalName": "Must Roll Back"},
        )

    db_session.expire_all()
    rows = db_session.execute(
        select(Supplier).where(Supplier.legal_name == "Must Roll Back")
    ).scalars().all()
    assert rows == []


def test_supplier_contract_create_emits_audit_entry(client):
    login_admin(client)
    company = create_company(client, name="Contract Audit Co")
    supplier = create_supplier(client, company_id=company["id"])
    project = _create_project(client, company_id=company["id"], name="Audit Contract Project")

    response = _create_contract(
        client,
        company_id=company["id"],
        supplier_id=supplier["id"],
        project_id=project["id"],
        contract_number="AUD-CON-001",
    )
    assert response.status_code == 201, response.text
    contract = response.json()

    entries = client.get(
        f"/api/audit?companyId={company['id']}&entityType=procurement.contract"
    ).json()
    entry = next(item for item in entries if item["entityId"] == contract["id"])
    assert entry["action"] == "procurement.contract.create"
    assert entry["projectId"] == project["id"]
    assert entry["after"] == {
        "contractNumber": "AUD-CON-001",
        "contractCategory": "OTHER",
        "currencyCode": "HNL",
        "status": "DRAFT",
        "supplierId": supplier["id"],
        "value": "150000.00",
    }


def test_supplier_contract_create_rolls_back_when_audit_fails(
    client, db_session, monkeypatch
):
    login_admin(client)
    company = create_company(client, name="Contract Rollback Co")
    supplier = create_supplier(client, company_id=company["id"])

    def fail_record(*args, **kwargs):
        raise RuntimeError("audit unavailable")

    monkeypatch.setattr("app.api.routes.suppliers.audit_service.record", fail_record)

    with pytest.raises(RuntimeError, match="audit unavailable"):
        _create_contract(
            client,
            company_id=company["id"],
            supplier_id=supplier["id"],
            contract_number="ROLLBACK-CON-001",
        )

    db_session.expire_all()
    rows = db_session.execute(
        select(SupplierContract).where(
            SupplierContract.contract_number == "ROLLBACK-CON-001"
        )
    ).scalars().all()
    assert rows == []


def test_supplier_contract_rejects_supplier_from_another_company(client):
    """INV-COMP-001: sin este guard, un contrato podría referenciar un
    Supplier de una company completamente distinta."""
    login_admin(client)
    company_a = create_company(client, name="Contratos A")
    company_b = create_company(client, name="Contratos B")
    foreign_supplier = create_supplier(client, company_id=company_b["id"], legal_name="Proveedor B")

    response = _create_contract(client, company_id=company_a["id"], supplier_id=foreign_supplier["id"])

    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "NXR-FINANCIAL-001"


def test_supplier_contract_rejects_project_from_another_company(client):
    login_admin(client)
    company_a = create_company(client, name="Contratos C")
    company_b = create_company(client, name="Contratos D")
    supplier = create_supplier(client, company_id=company_a["id"])
    foreign_project = _create_project(client, company_id=company_b["id"], name="Proyecto ajeno")

    response = _create_contract(
        client, company_id=company_a["id"], supplier_id=supplier["id"], project_id=foreign_project["id"]
    )

    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "NXR-FINANCIAL-001"


def test_supplier_contracts_never_leak_across_companies(client, db_session):
    login_admin(client)
    company_a = create_company(client, name="Contratos E")
    company_b = create_company(client, name="Contratos F")
    supplier_a = create_supplier(client, company_id=company_a["id"])
    _create_contract(client, company_id=company_a["id"], supplier_id=supplier_a["id"])

    user = create_user_with_role(
        db_session, email="proc-contracts@nexora.group", role_name="Procurement Manager"
    )
    db_session.add(UserCompanyAccess(user_id=user.id, company_id=company_b["id"]))
    db_session.commit()
    login_as(client, email="proc-contracts@nexora.group")

    response = client.get(f"/api/procurement/suppliers/contracts?company_id={company_a['id']}")
    assert response.status_code == 403, response.text
    assert response.json()["error"]["code"] == "NXR-PERM-001"


def test_contract_category_persists_and_filters(client):
    """ORDEN MAESTRA §13: contract_category (Mano de obra / Subcontrato / ...)."""
    login_admin(client)
    company = create_company(client, name="Categoria Co")
    supplier = create_supplier(client, company_id=company["id"])

    labor = _create_contract(
        client, company_id=company["id"], supplier_id=supplier["id"], contract_number="CAT-LAB"
    )
    assert labor.status_code == 201
    # Sin categoría explícita -> OTHER (dato existente conservado).
    assert labor.json()["contractCategory"] == "OTHER"

    payload = {
        "companyId": company["id"],
        "supplierId": supplier["id"],
        "contractNumber": "CAT-001",
        "contractCategory": "LABOR",
        "value": "250000.00",
        "currencyCode": "HNL",
        "startDate": "2026-01-01",
    }
    created = client.post("/api/procurement/suppliers/contracts", json=payload)
    assert created.status_code == 201, created.text
    assert created.json()["contractCategory"] == "LABOR"

    only_labor = client.get(
        f"/api/procurement/suppliers/contracts?company_id={company['id']}&category=LABOR"
    )
    assert only_labor.status_code == 200
    assert [c["contractNumber"] for c in only_labor.json()] == ["CAT-001"]


def test_contract_category_rejects_unknown_value(client):
    login_admin(client)
    company = create_company(client, name="Categoria Bad Co")
    supplier = create_supplier(client, company_id=company["id"])
    response = client.post(
        "/api/procurement/suppliers/contracts",
        json={
            "companyId": company["id"],
            "supplierId": supplier["id"],
            "contractNumber": "CAT-BAD",
            "contractCategory": "NOT_A_CATEGORY",
            "value": "1000.00",
            "currencyCode": "HNL",
            "startDate": "2026-01-01",
        },
    )
    assert response.status_code == 422, response.text


def test_contract_number_is_unique_per_company_not_globally(client):
    """ORDEN MAESTRA §15: dos compañías pueden tener su propio 'C-001'."""
    login_admin(client)
    company_a = create_company(client, name="Numero A")
    company_b = create_company(client, name="Numero B")
    supplier_a = create_supplier(client, company_id=company_a["id"])
    supplier_b = create_supplier(client, company_id=company_b["id"])

    first = _create_contract(
        client, company_id=company_a["id"], supplier_id=supplier_a["id"], contract_number="C-001"
    )
    assert first.status_code == 201, first.text

    # Otra compañía, mismo número -> permitido.
    other_company = _create_contract(
        client, company_id=company_b["id"], supplier_id=supplier_b["id"], contract_number="C-001"
    )
    assert other_company.status_code == 201, other_company.text

    # Misma compañía, número repetido -> rechazado con error de negocio, no 500.
    duplicate = _create_contract(
        client, company_id=company_a["id"], supplier_id=supplier_a["id"], contract_number="C-001"
    )
    assert duplicate.status_code == 422, duplicate.text
    assert duplicate.json()["error"]["code"] == "NXR-FINANCIAL-001"


def test_project_manager_user_id_links_a_real_user(client, db_session):
    """ORDEN MAESTRA §16: el responsable del proyecto es una FK a users."""
    login_admin(client)
    company = create_company(client, name="Manager FK Co")
    manager = create_user_with_role(
        db_session, email="site-manager@nexora.group", role_name="Project Manager"
    )
    db_session.commit()

    response = client.post(
        "/api/projects",
        json={
            "companyId": company["id"],
            "name": "Obra con responsable",
            "currencyCode": "HNL",
            "managerUserId": str(manager.id),
        },
    )
    assert response.status_code == 201, response.text
    assert response.json()["managerUserId"] == str(manager.id)


def test_project_manager_user_id_rejects_unknown_user(client):
    login_admin(client)
    company = create_company(client, name="Manager FK Bad Co")
    response = client.post(
        "/api/projects",
        json={
            "companyId": company["id"],
            "name": "Obra sin responsable válido",
            "currencyCode": "HNL",
            "managerUserId": "00000000-0000-0000-0000-000000000000",
        },
    )
    assert response.status_code == 422, response.text
