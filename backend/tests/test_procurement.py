import uuid
from decimal import Decimal

from app.models.permission import UserCompanyAccess
from app.models.project import Project
from app.repositories import procurement_repository
from tests.helpers import create_company, create_user_with_role, login_admin, login_as


def _create_supplier(client, *, company_id: str) -> dict:
    response = client.post(
        "/api/procurement/suppliers",
        json={"companyId": company_id, "legalName": "Proveedor de prueba S.A."},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_purchase_order(client, *, company_id: str, supplier_id: str, project_id: str | None) -> dict:
    response = client.post(
        "/api/procurement/purchase-orders",
        json={
            "companyId": company_id,
            "supplierId": supplier_id,
            "projectId": project_id,
            "currencyCode": "HNL",
            "lines": [{"description": "Material", "quantity": "1.0000", "unitPrice": "125.5000"}],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_commitments_are_derived_from_approved_purchase_orders(client, db_session):
    """Budget consumes documentary commitments, never draft POs or cash."""
    login_admin(client)
    company = create_company(client)
    project = Project(company_id=company["id"], name="Torre de prueba", status="ACTIVE")
    db_session.add(project)
    db_session.commit()
    supplier = _create_supplier(client, company_id=company["id"])

    draft = _create_purchase_order(
        client, company_id=company["id"], supplier_id=supplier["id"], project_id=str(project.id)
    )
    approved = _create_purchase_order(
        client, company_id=company["id"], supplier_id=supplier["id"], project_id=str(project.id)
    )
    response = client.post(f"/api/procurement/purchase-orders/{approved['id']}/approve")
    assert response.status_code == 200, response.text
    assert draft["status"] == "DRAFT"

    commitments = procurement_repository.project_commitments_by_project(
        db_session, company_id=uuid.UUID(company["id"])
    )

    assert commitments == {project.id: Decimal("125.50")}


def test_company_access_blocks_cross_company_procurement_resource(client, db_session):
    """A company-A Buyer cannot fetch a purchase order owned by company B."""
    login_admin(client)
    company_a = create_company(client, name="Constructora A")
    company_b = create_company(client, name="Constructora B")
    supplier_b = _create_supplier(client, company_id=company_b["id"])
    po_b = _create_purchase_order(
        client, company_id=company_b["id"], supplier_id=supplier_b["id"], project_id=None
    )
    buyer = create_user_with_role(db_session, email="buyer-isolated@nexora.group", role_name="Buyer")
    db_session.add(UserCompanyAccess(user_id=buyer.id, company_id=company_a["id"]))
    db_session.commit()

    login_as(client, email="buyer-isolated@nexora.group")
    response = client.get(f"/api/procurement/purchase-orders/{po_b['id']}")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "NXR-PERM-001"
