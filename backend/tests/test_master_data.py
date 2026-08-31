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


def test_grouping_account_can_be_parent_for_same_type_child(client):
    login_admin(client)
    company = create_company(client)

    parent_response = client.post(
        "/api/master-data/accounts",
        json={
            "companyId": company["id"],
            "code": "1000",
            "name": "ACTIVOS",
            "accountType": "ASSET",
            "isPostable": False,
        },
    )
    assert parent_response.status_code == 201, parent_response.text
    parent = parent_response.json()
    assert parent["isPostable"] is False

    child_response = client.post(
        "/api/master-data/accounts",
        json={
            "companyId": company["id"],
            "code": "1101",
            "name": "Caja y efectivo",
            "accountType": "ASSET",
            "parentId": parent["id"],
            "isPostable": True,
        },
    )
    assert child_response.status_code == 201, child_response.text
    child = child_response.json()
    assert child["parentId"] == parent["id"]
    assert child["isPostable"] is True


def test_postable_account_cannot_be_used_as_parent(client):
    login_admin(client)
    company = create_company(client)

    parent = client.post(
        "/api/master-data/accounts",
        json={
            "companyId": company["id"],
            "code": "1100",
            "name": "Caja operativa",
            "accountType": "ASSET",
            "isPostable": True,
        },
    ).json()

    response = client.post(
        "/api/master-data/accounts",
        json={
            "companyId": company["id"],
            "code": "1101",
            "name": "Caja menor",
            "accountType": "ASSET",
            "parentId": parent["id"],
        },
    )

    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "NXR-FINANCIAL-001"
    assert "agrupadora" in response.json()["error"]["message"].lower()


def test_account_parent_and_child_must_have_same_type(client):
    login_admin(client)
    company = create_company(client)

    parent = client.post(
        "/api/master-data/accounts",
        json={
            "companyId": company["id"],
            "code": "1000",
            "name": "ACTIVOS",
            "accountType": "ASSET",
            "isPostable": False,
        },
    ).json()

    response = client.post(
        "/api/master-data/accounts",
        json={
            "companyId": company["id"],
            "code": "2101",
            "name": "Cuentas por pagar",
            "accountType": "LIABILITY",
            "parentId": parent["id"],
        },
    )

    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "NXR-FINANCIAL-001"
    assert "mismo tipo" in response.json()["error"]["message"].lower()


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
            "isPostable": False,
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


def test_company_voucher_payer_is_set_once_then_immutable(client, db_session):
    """Orden maestra Phase 2: el pagador de comprobantes se asigna una sola
    vez (mismo patrón que `code`); el aprobador es siempre editable."""
    login_admin(client)
    company = create_company(client)

    first = client.patch(
        f"/api/master-data/companies/{company['id']}",
        json={
            "voucherPayerName": "KAREN VANNESSA LOPEZ GONZALEZ",
            "voucherApproverName": "CARLOS HUMBERTO LOPEZ",
        },
    )
    assert first.status_code == 200, first.text
    assert first.json()["voucherPayerName"] == "KAREN VANNESSA LOPEZ GONZALEZ"
    assert first.json()["voucherApproverName"] == "CARLOS HUMBERTO LOPEZ"

    # Aprobador editable.
    edit_approver = client.patch(
        f"/api/master-data/companies/{company['id']}",
        json={"voucherApproverName": "OTRO APROBADOR"},
    )
    assert edit_approver.status_code == 200, edit_approver.text
    assert edit_approver.json()["voucherApproverName"] == "OTRO APROBADOR"
    assert edit_approver.json()["voucherPayerName"] == "KAREN VANNESSA LOPEZ GONZALEZ"

    # Pagador inmutable una vez fijado.
    change_payer = client.patch(
        f"/api/master-data/companies/{company['id']}",
        json={"voucherPayerName": "ALGUIEN MAS"},
    )
    assert change_payer.status_code == 409, change_payer.text

    # Reenviar el mismo valor no es un cambio -> permitido.
    same_payer = client.patch(
        f"/api/master-data/companies/{company['id']}",
        json={"voucherPayerName": "KAREN VANNESSA LOPEZ GONZALEZ"},
    )
    assert same_payer.status_code == 200, same_payer.text
