import uuid

from app.models.accounting import AccountingDocument
from app.models.audit import AuditLog
from app.models.cost_center import CostCenter
from app.models.project import Project
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


def _assert_financial_reference_rejected(client, db_session, payload):
    documents_before = db_session.query(AccountingDocument).count()

    response = client.post("/api/accounting/journal-entries", json=payload)

    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "NXR-FINANCIAL-001"
    assert db_session.query(AccountingDocument).count() == documents_before


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


def test_journal_rejects_document_project_from_another_company(client, db_session):
    login_admin(client)
    company_a, debit_a, credit_a = _setup_company_and_accounts(client)
    company_b = create_company(client, name="Foreign project company")
    project_b = Project(company_id=company_b["id"], name="Foreign project")
    db_session.add(project_b)
    db_session.commit()

    _assert_financial_reference_rejected(
        client,
        db_session,
        {
            "companyId": company_a["id"],
            "scope": "PROJECT",
            "projectId": str(project_b.id),
            "currencyCode": "HNL",
            "lines": [
                {"accountId": debit_a["id"], "debitAmount": "10.00"},
                {"accountId": credit_a["id"], "creditAmount": "10.00"},
            ],
        },
    )


def test_journal_rejects_line_account_from_another_company(client, db_session):
    login_admin(client)
    company_a, _debit_a, credit_a = _setup_company_and_accounts(client)
    company_b = create_company(client, name="Foreign account company")
    debit_b = create_account(
        client,
        company_id=company_b["id"],
        code="1000",
        name="Foreign cash",
        account_type="ASSET",
    )

    _assert_financial_reference_rejected(
        client,
        db_session,
        {
            "companyId": company_a["id"],
            "scope": "GENERAL",
            "currencyCode": "HNL",
            "lines": [
                {"accountId": debit_b["id"], "debitAmount": "10.00"},
                {"accountId": credit_a["id"], "creditAmount": "10.00"},
            ],
        },
    )


def test_journal_rejects_line_project_from_another_company(client, db_session):
    login_admin(client)
    company_a, debit_a, credit_a = _setup_company_and_accounts(client)
    company_b = create_company(client, name="Foreign line project company")
    project_b = Project(company_id=company_b["id"], name="Foreign line project")
    db_session.add(project_b)
    db_session.commit()

    _assert_financial_reference_rejected(
        client,
        db_session,
        {
            "companyId": company_a["id"],
            "scope": "GENERAL",
            "currencyCode": "HNL",
            "lines": [
                {
                    "accountId": debit_a["id"],
                    "debitAmount": "10.00",
                    "projectId": str(project_b.id),
                },
                {"accountId": credit_a["id"], "creditAmount": "10.00"},
            ],
        },
    )


def test_journal_rejects_line_cost_center_from_another_company(client, db_session):
    login_admin(client)
    company_a, debit_a, credit_a = _setup_company_and_accounts(client)
    company_b = create_company(client, name="Foreign cost center company")
    cost_center_b = CostCenter(
        company_id=company_b["id"], code="FOREIGN", name="Foreign cost center"
    )
    db_session.add(cost_center_b)
    db_session.commit()

    _assert_financial_reference_rejected(
        client,
        db_session,
        {
            "companyId": company_a["id"],
            "scope": "GENERAL",
            "currencyCode": "HNL",
            "lines": [
                {
                    "accountId": debit_a["id"],
                    "debitAmount": "10.00",
                    "costCenterId": str(cost_center_b.id),
                },
                {"accountId": credit_a["id"], "creditAmount": "10.00"},
            ],
        },
    )


def test_creating_journal_entry_creates_audit_log_entry(client, db_session):
    """Closes the General Ledger (manual entries) gap in docs/AUDIT.md's
    honest backlog -- same instrumentation pattern as AP approve/pay."""
    login_admin(client)
    company, debit_account, credit_account = _setup_company_and_accounts(client)

    response = client.post(
        "/api/accounting/journal-entries",
        json={
            "companyId": company["id"],
            "scope": "GENERAL",
            "currencyCode": "HNL",
            "description": "Asiento auditado",
            "lines": [
                {"accountId": debit_account["id"], "debitAmount": "10.00"},
                {"accountId": credit_account["id"], "creditAmount": "10.00"},
            ],
        },
    )
    assert response.status_code == 201, response.text
    document = response.json()

    rows = (
        db_session.query(AuditLog)
        .filter(
            AuditLog.entity_type == "accounting.journal_entry",
            AuditLog.entity_id == uuid.UUID(document["id"]),
        )
        .all()
    )
    assert len(rows) == 1
    assert rows[0].action == "accounting.journal_entry.create"
    assert rows[0].after["status"] == "POSTED"
    assert rows[0].after["documentNumber"] == document["documentNumber"]


def test_reversing_journal_entry_creates_audit_log_entry(client, db_session):
    login_admin(client)
    company, debit_account, credit_account = _setup_company_and_accounts(client)
    created = client.post(
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
    ).json()

    reversal = client.post(
        f"/api/accounting/journal-entries/{created['id']}/reverse",
        json={"reason": "Error de captura"},
    )
    assert reversal.status_code == 200, reversal.text

    rows = (
        db_session.query(AuditLog)
        .filter(
            AuditLog.entity_type == "accounting.journal_entry",
            AuditLog.entity_id == uuid.UUID(created["id"]),
            AuditLog.action == "accounting.journal_entry.reverse",
        )
        .all()
    )
    assert len(rows) == 1
    assert rows[0].before["status"] == "POSTED"
    assert rows[0].after["status"] == "REVERSED"
    assert rows[0].after["reversalDocumentId"] == reversal.json()["id"]
