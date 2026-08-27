from tests.helpers import create_account, create_company, create_treasury_account, login_admin


def _setup_financial_accounts(client):
    company = create_company(client)
    bank_gl = create_account(
        client, company_id=company["id"], code="1102", name="Banco Atlántida — HNL", account_type="ASSET"
    )
    bank = create_treasury_account(
        client, company_id=company["id"], gl_account_id=bank_gl["id"], name="Banco Atlántida HNL"
    )
    equity = create_account(
        client, company_id=company["id"], code="3101", name="Capital y aportaciones", account_type="EQUITY"
    )
    liability = create_account(
        client, company_id=company["id"], code="2201", name="Préstamos recibidos", account_type="LIABILITY"
    )
    revenue = create_account(
        client, company_id=company["id"], code="4201", name="Otros ingresos", account_type="REVENUE"
    )
    expense = create_account(
        client, company_id=company["id"], code="5101", name="Costos directos de construcción", account_type="EXPENSE"
    )
    return company, bank, equity, liability, revenue, expense


def test_remittance_origin_type_restricts_counter_account(client):
    login_admin(client)
    company, bank, equity, liability, revenue, expense = _setup_financial_accounts(client)

    valid_cases = [
        ("CAPITAL_CONTRIBUTION", equity["id"]),
        ("FINANCING", liability["id"]),
        ("OTHER_INCOME", revenue["id"]),
    ]
    for index, (origin_type, counter_account_id) in enumerate(valid_cases, start=1):
        response = client.post(
            "/api/treasury/remittances",
            json={
                "companyId": company["id"],
                "treasuryAccountId": bank["id"],
                "counterAccountId": counter_account_id,
                "originType": origin_type,
                "sender": f"Entrada válida {index}",
                "currencyCode": "HNL",
                "originalAmount": "100.00",
                "remittanceDate": "2026-08-27",
            },
        )
        assert response.status_code == 201, response.text

    invalid = client.post(
        "/api/treasury/remittances",
        json={
            "companyId": company["id"],
            "treasuryAccountId": bank["id"],
            "counterAccountId": expense["id"],
            "originType": "CAPITAL_CONTRIBUTION",
            "sender": "Entrada inválida",
            "currencyCode": "HNL",
            "originalAmount": "100.00",
            "remittanceDate": "2026-08-27",
        },
    )
    assert invalid.status_code == 422, invalid.text
    assert invalid.json()["error"]["code"] == "NXR-FINANCIAL-001"


def test_project_immediate_expense_posts_project_dimension(client):
    login_admin(client)
    company, bank, equity, _liability, _revenue, expense = _setup_financial_accounts(client)
    project_response = client.post(
        "/api/projects",
        json={
            "companyId": company["id"],
            "name": "Cerco Perimetral",
            "code": "PRJ-CERCO",
            "currencyCode": "HNL",
        },
    )
    assert project_response.status_code == 201, project_response.text
    project = project_response.json()

    funding = client.post(
        "/api/treasury/remittances",
        json={
            "companyId": company["id"],
            "treasuryAccountId": bank["id"],
            "counterAccountId": equity["id"],
            "originType": "CAPITAL_CONTRIBUTION",
            "sender": "Aporte inicial",
            "currencyCode": "HNL",
            "originalAmount": "5000.00",
            "remittanceDate": "2026-08-27",
        },
    )
    assert funding.status_code == 201, funding.text

    response = client.post(
        "/api/treasury/general-expenses",
        json={
            "companyId": company["id"],
            "treasuryAccountId": bank["id"],
            "expenseAccountId": expense["id"],
            "scope": "PROJECT",
            "projectId": project["id"],
            "category": "combustible",
            "amount": "750.00",
            "currencyCode": "HNL",
            "expenseDate": "2026-08-27",
            "description": "Gasolina para Cerco Perimetral",
        },
    )
    assert response.status_code == 201, response.text

    document = client.get(
        f"/api/accounting/journal-entries/{response.json()['accountingDocumentId']}"
    )
    assert document.status_code == 200, document.text
    body = document.json()
    assert body["scope"] == "PROJECT"
    assert body["projectId"] == project["id"]


def test_project_immediate_expense_requires_project_id(client):
    login_admin(client)
    company, bank, _equity, _liability, _revenue, expense = _setup_financial_accounts(client)
    response = client.post(
        "/api/treasury/general-expenses",
        json={
            "companyId": company["id"],
            "treasuryAccountId": bank["id"],
            "expenseAccountId": expense["id"],
            "scope": "PROJECT",
            "category": "combustible",
            "amount": "100.00",
            "currencyCode": "HNL",
            "expenseDate": "2026-08-27",
            "description": "Debe exigir proyecto",
        },
    )
    assert response.status_code == 422, response.text
