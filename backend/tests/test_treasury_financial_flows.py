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


def _active_contract_with_schedule(client, db_session, company_id, *, amount="207142.85"):
    supplier = client.post(
        "/api/procurement/suppliers",
        json={"companyId": company_id, "legalName": "Contratista Guard"},
    ).json()
    project = client.post(
        "/api/projects",
        json={"companyId": company_id, "name": "Obra Guard", "code": "PRJ-GUARD", "currencyCode": "HNL"},
    ).json()
    contract = client.post(
        "/api/procurement/suppliers/contracts",
        json={
            "companyId": company_id, "supplierId": supplier["id"], "projectId": project["id"],
            "contractNumber": "GUARD-1", "value": "1500000.00", "currencyCode": "HNL",
            "startDate": "2026-08-01", "advanceAmount": "50000.00",
            "advanceDueDate": "2026-08-22", "retentionPercentage": "0",
        },
    ).json()
    client.post(
        "/api/contract-payments/schedules",
        json={
            "supplierContractId": contract["id"], "scheduleType": "MONTHLY",
            "regularMonths": 7, "dueDay": 1, "firstPeriod": "2026-09-01",
        },
    )
    from app.models.supplier import SupplierContract

    row = db_session.get(SupplierContract, contract["id"])
    row.status = "ACTIVE"
    db_session.commit()
    return project, contract


def test_project_general_expense_blocks_when_it_matches_an_open_contract_installment(client, db_session):
    """ORDEN MAESTRA §21 — el guard contractual: un gasto inmediato PROJECT por
    el importe de una cuota contractual abierta exige reconocimiento explícito."""
    login_admin(client)
    company, bank, equity, _liability, _revenue, expense = _setup_financial_accounts(client)
    project, _contract = _active_contract_with_schedule(client, db_session, company["id"])
    client.post(
        "/api/treasury/remittances",
        json={
            "companyId": company["id"], "treasuryAccountId": bank["id"], "counterAccountId": equity["id"],
            "originType": "CAPITAL_CONTRIBUTION", "sender": "Aporte", "currencyCode": "HNL",
            "originalAmount": "500000.00", "remittanceDate": "2026-08-27",
        },
    )
    payload = {
        "companyId": company["id"], "treasuryAccountId": bank["id"], "expenseAccountId": expense["id"],
        "scope": "PROJECT", "projectId": project["id"], "category": "subcontrato",
        "amount": "207142.85", "currencyCode": "HNL", "expenseDate": "2026-09-02",
        "description": "Pago mensualidad por fuera del contrato",
    }

    blocked = client.post("/api/treasury/general-expenses", json=payload)
    assert blocked.status_code == 409, blocked.text
    assert blocked.json()["error"]["code"] == "NXR-CONTRACT-GUARD-001"

    # Reconocimiento sin motivo -> 422
    no_reason = client.post(
        "/api/treasury/general-expenses",
        json={**payload, "acknowledgeContractualConflict": True},
    )
    assert no_reason.status_code == 422, no_reason.text

    # Reconocimiento con motivo -> se registra
    ok = client.post(
        "/api/treasury/general-expenses",
        json={
            **payload,
            "acknowledgeContractualConflict": True,
            "contractualConflictReason": "Compra puntual de materiales, no es la cuota del subcontrato",
        },
    )
    assert ok.status_code == 201, ok.text


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
