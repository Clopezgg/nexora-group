import pytest

from app.models.permission import UserCompanyAccess
from tests.helpers import create_company, create_user_with_role, login_admin, login_as


def test_updating_company_persists_legal_name_and_fiscal_id(client, db_session):
    login_admin(client)
    company = create_company(client)

    response = client.patch(
        f"/api/master-data/companies/{company['id']}",
        json={"legalName": "Constructora Actualizada S.A.", "fiscalId": "0801-1990-12345"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["legalName"] == "Constructora Actualizada S.A."

    refetch = client.get("/api/master-data/companies").json()
    updated = next(c for c in refetch if c["id"] == company["id"])
    assert updated["fiscalId"] == "0801-1990-12345"


def test_updating_company_does_not_touch_functional_currency(client, db_session):
    """El schema de update solo acepta legal_name/fiscal_id -- code y
    functional_currency_code nunca se aceptan en el PATCH (son inmutables
    post-creación, ver CLAUDE.md)."""
    login_admin(client)
    company = create_company(client, currency="USD")

    response = client.patch(
        f"/api/master-data/companies/{company['id']}",
        json={"legalName": "Constructora USD S.A."},
    )
    assert response.status_code == 200, response.text
    assert response.json()["functionalCurrencyCode"] == "USD"


def test_user_without_company_access_cannot_update_company(client, db_session):
    """INV-COMP-001: Finance Manager tiene core.company:update con
    company_scope=OWN -- sin UserCompanyAccess explícito a la company B, el
    PATCH se rechaza."""
    login_admin(client)
    company_a = create_company(client, name="Constructora A")
    company_b = create_company(client, name="Constructora B")

    user = create_user_with_role(db_session, email="finance-scope@nexora.group", role_name="Finance Manager")
    db_session.add(UserCompanyAccess(user_id=user.id, company_id=company_a["id"]))
    db_session.commit()

    login_as(client, email="finance-scope@nexora.group")

    response = client.patch(
        f"/api/master-data/companies/{company_b['id']}",
        json={"legalName": "Intento no autorizado S.A."},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "NXR-PERM-001"

    allowed = client.patch(
        f"/api/master-data/companies/{company_a['id']}",
        json={"legalName": "Constructora A Actualizada S.A."},
    )
    assert allowed.status_code == 200, allowed.text


def test_account_parent_must_belong_to_the_same_company(client):
    """INV-COMP-001: la jerarquía contable nunca puede enlazar catálogos
    pertenecientes a compañías distintas."""
    login_admin(client)
    company_a = create_company(client, name="Constructora A")
    company_b = create_company(client, name="Constructora B")

    parent_b = client.post(
        "/api/master-data/accounts",
        json={
            "companyId": company_b["id"],
            "code": "1100",
            "name": "Activo corriente B",
            "accountType": "ASSET",
        },
    ).json()

    response = client.post(
        "/api/master-data/accounts",
        json={
            "companyId": company_a["id"],
            "code": "1101",
            "name": "Cuentas por cobrar A",
            "accountType": "ASSET",
            "parentId": parent_b["id"],
        },
    )

    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "NXR-FINANCIAL-001"
    assert client.get(f"/api/master-data/accounts?companyId={company_a['id']}").json() == []


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("code", "   "),
        ("name", "   "),
        ("accountType", "NOT_A_REAL_ACCOUNT_TYPE"),
    ],
)
def test_account_create_rejects_invalid_domain_values_without_inserting(client, field, value):
    login_admin(client)
    company = create_company(client)
    payload = {
        "companyId": company["id"],
        "code": "1100",
        "name": "Activo corriente",
        "accountType": "ASSET",
    }
    payload[field] = value

    response = client.post("/api/master-data/accounts", json=payload)

    assert response.status_code == 422, response.text
    assert client.get(f"/api/master-data/accounts?companyId={company['id']}").json() == []
