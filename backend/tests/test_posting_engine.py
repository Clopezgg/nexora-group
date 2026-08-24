from tests.helpers import create_account, create_company, login_admin


def _setup_company_and_accounts(client):
    company = create_company(client)
    debit_account = create_account(
        client, company_id=company["id"], code="1000", name="Caja", account_type="ASSET"
    )
    credit_account = create_account(
        client, company_id=company["id"], code="2000", name="Cuentas por pagar", account_type="LIABILITY"
    )
    return company, debit_account, credit_account


def test_balanced_journal_entry_is_posted_and_numbered(client):
    login_admin(client)
    company, debit_account, credit_account = _setup_company_and_accounts(client)

    response = client.post(
        "/api/accounting/journal-entries",
        json={
            "companyId": company["id"],
            "scope": "GENERAL",
            "currencyCode": "HNL",
            "description": "Compra de papelería administrativa",
            "lines": [
                {"accountId": debit_account["id"], "debitAmount": "100.00"},
                {"accountId": credit_account["id"], "creditAmount": "100.00"},
            ],
        },
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "POSTED"
    assert body["documentNumber"].startswith("JRN-")
    assert len(body["lines"]) == 2
    total_debit = sum(float(line["debitAmount"]) for line in body["lines"])
    total_credit = sum(float(line["creditAmount"]) for line in body["lines"])
    assert total_debit == total_credit == 100.0


def test_unbalanced_journal_entry_is_rejected(client):
    """INV-ACC-001."""
    login_admin(client)
    company, debit_account, credit_account = _setup_company_and_accounts(client)

    response = client.post(
        "/api/accounting/journal-entries",
        json={
            "companyId": company["id"],
            "scope": "GENERAL",
            "currencyCode": "HNL",
            "lines": [
                {"accountId": debit_account["id"], "debitAmount": "100.00"},
                {"accountId": credit_account["id"], "creditAmount": "50.00"},
            ],
        },
    )

    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "NXR-ACCOUNTING-001"


def test_project_scope_without_project_id_is_rejected(client):
    """INV-OPS-003."""
    login_admin(client)
    company, debit_account, credit_account = _setup_company_and_accounts(client)

    response = client.post(
        "/api/accounting/journal-entries",
        json={
            "companyId": company["id"],
            "scope": "PROJECT",
            "currencyCode": "HNL",
            "lines": [
                {"accountId": debit_account["id"], "debitAmount": "10.00"},
                {"accountId": credit_account["id"], "creditAmount": "10.00"},
            ],
        },
    )

    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "NXR-ACCOUNTING-002"


def test_general_scope_with_project_id_is_rejected(client):
    """INV-OPS-002."""
    login_admin(client)
    company, debit_account, credit_account = _setup_company_and_accounts(client)

    response = client.post(
        "/api/accounting/journal-entries",
        json={
            "companyId": company["id"],
            "scope": "GENERAL",
            "projectId": "00000000-0000-0000-0000-000000000001",
            "currencyCode": "HNL",
            "lines": [
                {"accountId": debit_account["id"], "debitAmount": "10.00"},
                {"accountId": credit_account["id"], "creditAmount": "10.00"},
            ],
        },
    )

    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "NXR-ACCOUNTING-002"


def test_reverse_preserves_original_and_swaps_debit_credit(client):
    """INV-ACC-002: el original nunca se muta, solo transiciona a REVERSED."""
    login_admin(client)
    company, debit_account, credit_account = _setup_company_and_accounts(client)

    created = client.post(
        "/api/accounting/journal-entries",
        json={
            "companyId": company["id"],
            "scope": "GENERAL",
            "currencyCode": "HNL",
            "lines": [
                {"accountId": debit_account["id"], "debitAmount": "75.00"},
                {"accountId": credit_account["id"], "creditAmount": "75.00"},
            ],
        },
    ).json()

    reversal = client.post(
        f"/api/accounting/journal-entries/{created['id']}/reverse",
        json={"reason": "Error de captura"},
    )
    assert reversal.status_code == 200, reversal.text
    reversal_body = reversal.json()
    assert reversal_body["documentNumber"].startswith("ANU-")
    reversal_lines = {line["accountId"]: line for line in reversal_body["lines"]}
    assert float(reversal_lines[debit_account["id"]]["creditAmount"]) == 75.0
    assert float(reversal_lines[credit_account["id"]]["debitAmount"]) == 75.0

    original = client.get(f"/api/accounting/journal-entries/{created['id']}").json()
    assert original["status"] == "REVERSED"
    # Las líneas originales no se tocaron.
    original_lines = {line["accountId"]: line for line in original["lines"]}
    assert float(original_lines[debit_account["id"]]["debitAmount"]) == 75.0
    assert float(original_lines[credit_account["id"]]["creditAmount"]) == 75.0


def test_reverse_of_already_reversed_document_is_rejected(client):
    login_admin(client)
    company, debit_account, credit_account = _setup_company_and_accounts(client)

    created = client.post(
        "/api/accounting/journal-entries",
        json={
            "companyId": company["id"],
            "scope": "GENERAL",
            "currencyCode": "HNL",
            "lines": [
                {"accountId": debit_account["id"], "debitAmount": "20.00"},
                {"accountId": credit_account["id"], "creditAmount": "20.00"},
            ],
        },
    ).json()
    client.post(f"/api/accounting/journal-entries/{created['id']}/reverse", json={"reason": "x"})

    second_reverse = client.post(
        f"/api/accounting/journal-entries/{created['id']}/reverse", json={"reason": "y"}
    )
    assert second_reverse.status_code == 409
    assert second_reverse.json()["error"]["code"] == "NXR-ACCOUNTING-004"
