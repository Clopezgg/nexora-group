from decimal import Decimal

from app.models.permission import UserCompanyAccess
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
