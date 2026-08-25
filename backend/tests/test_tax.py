from decimal import Decimal

from app.models.permission import UserCompanyAccess
from app.services import tax_service
from tests.helpers import create_company, create_user_with_role, login_admin, login_as


def test_creating_and_listing_tax_codes(client):
    """NXR-REQ-0006: TaxCode/TaxLine ya existían como modelo sin servicio
    de gestión ni API real."""
    login_admin(client)
    company = create_company(client)

    created = client.post(
        "/api/master-data/tax-codes",
        json={"companyId": company["id"], "code": "ISV-15", "name": "ISV 15%", "ratePercent": "15.00"},
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["code"] == "ISV-15"
    assert Decimal(body["ratePercent"]) == Decimal("15.00")

    listed = client.get(f"/api/master-data/tax-codes?companyId={company['id']}")
    assert listed.status_code == 200, listed.text
    assert [tc["id"] for tc in listed.json()] == [body["id"]]


def test_creating_a_duplicate_tax_code_is_rejected(client):
    login_admin(client)
    company = create_company(client)
    client.post(
        "/api/master-data/tax-codes",
        json={"companyId": company["id"], "code": "ISV-15", "name": "ISV 15%", "ratePercent": "15.00"},
    )

    duplicate = client.post(
        "/api/master-data/tax-codes",
        json={"companyId": company["id"], "code": "ISV-15", "name": "Otro nombre", "ratePercent": "12.00"},
    )
    assert duplicate.status_code == 409, duplicate.text
    assert duplicate.json()["error"]["code"] == "NXR-TAX-001"


def test_tax_code_rejects_a_rate_out_of_range(client):
    login_admin(client)
    company = create_company(client)

    response = client.post(
        "/api/master-data/tax-codes",
        json={"companyId": company["id"], "code": "BAD", "name": "Tasa inválida", "ratePercent": "150.00"},
    )
    assert response.status_code == 422, response.text


def test_tax_codes_never_leak_across_companies(client, db_session):
    login_admin(client)
    company_a = create_company(client, name="Tax A")
    company_b = create_company(client, name="Tax B")
    client.post(
        "/api/master-data/tax-codes",
        json={"companyId": company_a["id"], "code": "ISV-15", "name": "ISV 15%", "ratePercent": "15.00"},
    )

    user = create_user_with_role(db_session, email="tax-scoped@nexora.group", role_name="Finance Manager")
    db_session.add(UserCompanyAccess(user_id=user.id, company_id=company_b["id"]))
    db_session.commit()
    login_as(client, email="tax-scoped@nexora.group")

    response = client.get(f"/api/master-data/tax-codes?companyId={company_a['id']}")
    assert response.status_code == 403, response.text
    assert response.json()["error"]["code"] == "NXR-PERM-001"


def test_compute_tax_applies_rate_and_rounds_to_two_decimals():
    from app.models.tax import TaxCode

    tax_code = TaxCode(code="ISV-15", name="ISV 15%", rate_percent=Decimal("15.00"))

    result = tax_service.compute_tax(Decimal("1000.00"), tax_code)

    assert result == Decimal("150.00")
