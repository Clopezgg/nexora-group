from app.models.permission import UserCompanyAccess
from tests.helpers import (
    create_account,
    create_company,
    create_user_with_role,
    login_admin,
    login_as,
)


def test_viewer_cannot_create_company(client, db_session):
    create_user_with_role(db_session, email="viewer@nexora.group", role_name="Viewer")
    login_as(client, email="viewer@nexora.group")

    response = client.post("/api/master-data/companies", json={"name": "Otra Constructora"})
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "NXR-PERM-001"


def test_viewer_can_read_companies(client, db_session):
    login_admin(client)
    company = create_company(client, name="Constructora Visible")
    user = create_user_with_role(db_session, email="viewer2@nexora.group", role_name="Viewer")
    db_session.add(UserCompanyAccess(user_id=user.id, company_id=company["id"]))
    db_session.commit()
    login_as(client, email="viewer2@nexora.group")

    response = client.get("/api/master-data/companies")
    assert response.status_code == 200
    assert any(c["name"] == "Constructora Visible" for c in response.json())


def test_company_listing_excludes_companies_outside_own_scope(client, db_session):
    login_admin(client)
    company_a = create_company(client, name="Constructora A")
    create_company(client, name="Constructora B")
    user = create_user_with_role(db_session, email="procurement-scope@nexora.group", role_name="Procurement Manager")
    db_session.add(UserCompanyAccess(user_id=user.id, company_id=company_a["id"]))
    db_session.commit()

    login_as(client, email="procurement-scope@nexora.group")
    response = client.get("/api/master-data/companies")

    assert response.status_code == 200
    assert [company["id"] for company in response.json()] == [company_a["id"]]


def test_company_listing_includes_all_companies_for_any_scope(client):
    login_admin(client)
    company_a = create_company(client, name="Constructora A")
    company_b = create_company(client, name="Constructora B")

    response = client.get("/api/master-data/companies")

    assert response.status_code == 200
    assert {company["id"] for company in response.json()} == {company_a["id"], company_b["id"]}


def test_accountant_without_company_access_is_denied(client, db_session):
    """INV-COMP-001: Accountant tiene company_scope=OWN -- sin
    UserCompanyAccess explícito, no puede contabilizar en ninguna company."""
    login_admin(client)
    company = create_company(client, name="Constructora Aislada")
    debit_account = create_account(
        client, company_id=company["id"], code="1000", name="Caja", account_type="ASSET"
    )
    credit_account = create_account(
        client, company_id=company["id"], code="2000", name="CxP", account_type="LIABILITY"
    )

    create_user_with_role(db_session, email="accountant@nexora.group", role_name="Accountant")
    login_as(client, email="accountant@nexora.group")

    response = client.post(
        "/api/accounting/journal-entries",
        json={
            "companyId": company["id"],
            "scope": "GENERAL",
            "currencyCode": "HNL",
            "lines": [
                {"accountId": debit_account["id"], "debitAmount": "10.00"},
                {"accountId": credit_account["id"], "creditAmount": "10.00"},
            ],
        },
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "NXR-PERM-001"


def test_accountant_with_company_access_can_post(client, db_session):
    """Mismo escenario, pero con UserCompanyAccess otorgado explícitamente:
    debe poder contabilizar normalmente."""
    login_admin(client)
    company = create_company(client, name="Constructora Con Acceso")
    debit_account = create_account(
        client, company_id=company["id"], code="1000", name="Caja", account_type="ASSET"
    )
    credit_account = create_account(
        client, company_id=company["id"], code="2000", name="CxP", account_type="LIABILITY"
    )

    user = create_user_with_role(db_session, email="accountant2@nexora.group", role_name="Accountant")
    db_session.add(UserCompanyAccess(user_id=user.id, company_id=company["id"]))
    db_session.commit()

    login_as(client, email="accountant2@nexora.group")
    response = client.post(
        "/api/accounting/journal-entries",
        json={
            "companyId": company["id"],
            "scope": "GENERAL",
            "currencyCode": "HNL",
            "lines": [
                {"accountId": debit_account["id"], "debitAmount": "10.00"},
                {"accountId": credit_account["id"], "creditAmount": "10.00"},
            ],
        },
    )
    assert response.status_code == 201, response.text


def test_accountant_cannot_post_to_a_second_company_without_access(client, db_session):
    """INV-COMP-001: acceso a Company A no implica acceso a Company B."""
    login_admin(client)
    company_a = create_company(client, name="Constructora A")
    company_b = create_company(client, name="Constructora B")
    debit_b = create_account(
        client, company_id=company_b["id"], code="1000", name="Caja", account_type="ASSET"
    )
    credit_b = create_account(
        client, company_id=company_b["id"], code="2000", name="CxP", account_type="LIABILITY"
    )

    user = create_user_with_role(db_session, email="accountant3@nexora.group", role_name="Accountant")
    db_session.add(UserCompanyAccess(user_id=user.id, company_id=company_a["id"]))
    db_session.commit()

    login_as(client, email="accountant3@nexora.group")
    response = client.post(
        "/api/accounting/journal-entries",
        json={
            "companyId": company_b["id"],
            "scope": "GENERAL",
            "currencyCode": "HNL",
            "lines": [
                {"accountId": debit_b["id"], "debitAmount": "10.00"},
                {"accountId": credit_b["id"], "creditAmount": "10.00"},
            ],
        },
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "NXR-PERM-001"
