from app.models.accounting import AccountingDocument
from tests.helpers import create_account, create_company, login_admin


def test_manual_post_rejects_grouping_account(client, db_session):
    """Una cuenta agrupadora puede estructurar el catálogo, pero nunca
    recibir débitos/créditos directamente."""
    login_admin(client)
    company = create_company(client)

    grouping_response = client.post(
        "/api/master-data/accounts",
        json={
            "companyId": company["id"],
            "code": "1000",
            "name": "ACTIVOS",
            "accountType": "ASSET",
            "isPostable": False,
        },
    )
    assert grouping_response.status_code == 201, grouping_response.text
    grouping = grouping_response.json()

    credit = create_account(
        client,
        company_id=company["id"],
        code="2101",
        name="Cuentas por pagar",
        account_type="LIABILITY",
    )
    documents_before = db_session.query(AccountingDocument).count()

    response = client.post(
        "/api/accounting/journal-entries",
        json={
            "companyId": company["id"],
            "scope": "GENERAL",
            "currencyCode": "HNL",
            "description": "Intento inválido contra cuenta agrupadora",
            "lines": [
                {"accountId": grouping["id"], "debitAmount": "100.00"},
                {"accountId": credit["id"], "creditAmount": "100.00"},
            ],
        },
    )

    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "NXR-FINANCIAL-001"
    assert "agrupadora" in response.json()["error"]["message"].lower()
    assert db_session.query(AccountingDocument).count() == documents_before
