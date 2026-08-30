import uuid

import pytest

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


def test_journal_creation_rolls_back_when_audit_write_fails(client, db_session, monkeypatch):
    login_admin(client)
    company, debit_account, credit_account = _setup_company_and_accounts(client)

    def fail_record(*args, **kwargs):
        raise RuntimeError("audit unavailable")

    monkeypatch.setattr("app.api.routes.accounting.audit_service.record", fail_record)
    with pytest.raises(RuntimeError, match="audit unavailable"):
        client.post(
            "/api/accounting/journal-entries",
            json={
                "companyId": company["id"],
                "scope": "GENERAL",
                "currencyCode": "HNL",
                "description": "Must roll back with audit",
                "lines": [
                    {"accountId": debit_account["id"], "debitAmount": "10.00"},
                    {"accountId": credit_account["id"], "creditAmount": "10.00"},
                ],
            },
        )

    db_session.rollback()
    rows = (
        db_session.query(AccountingDocument)
        .filter(AccountingDocument.description == "Must roll back with audit")
        .all()
    )
    assert rows == []


def test_journal_reversal_rolls_back_when_audit_write_fails(client, db_session, monkeypatch):
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
    document_count = db_session.query(AccountingDocument).count()

    def fail_record(*args, **kwargs):
        raise RuntimeError("audit unavailable")

    monkeypatch.setattr("app.api.routes.accounting.audit_service.record", fail_record)
    with pytest.raises(RuntimeError, match="audit unavailable"):
        client.post(
            f"/api/accounting/journal-entries/{created['id']}/reverse",
            json={"reason": "Must roll back with audit"},
        )

    db_session.rollback()
    original = db_session.get(AccountingDocument, uuid.UUID(created["id"]))
    assert original is not None
    assert original.status == "POSTED"
    assert original.reversed_document_id is None
    assert db_session.query(AccountingDocument).count() == document_count


def _create_ap_setup(client):
    company = create_company(client)
    expense = create_account(client, company_id=company["id"], code="5100", name="Gastos", account_type="EXPENSE")
    payable = create_account(
        client, company_id=company["id"], code="2100", name="Cuentas por pagar", account_type="LIABILITY"
    )
    from tests.helpers import create_supplier

    supplier = create_supplier(client, company_id=company["id"])
    return company, expense, payable, supplier


def test_reversing_an_ap_accrual_cancels_the_invoice(client):
    """NXR-REQ-0025 (Corrections): revertir el accrual de una factura vía
    el endpoint genérico de reversal debe sincronizar el status de la
    factura -- de lo contrario queda APPROVED (pagable) apuntando a un
    documento contable ya REVERSED."""
    login_admin(client)
    company, expense, payable, supplier = _create_ap_setup(client)
    invoice = client.post(
        "/api/ap/supplier-invoices",
        json={
            "companyId": company["id"],
            "supplierId": supplier["id"],
            "invoiceNumber": "COR-001",
            "scope": "GENERAL",
            "expenseAccountId": expense["id"],
            "payableAccountId": payable["id"],
            "currencyCode": "HNL",
            "amount": "200.00",
            "invoiceDate": "2026-01-10",
            "dueDate": "2026-02-10",
        },
    ).json()
    approved = client.post(f"/api/ap/supplier-invoices/{invoice['id']}/approve").json()
    assert approved["status"] == "APPROVED"

    reversal = client.post(
        f"/api/accounting/journal-entries/{approved['accrualDocumentId']}/reverse",
        json={"reason": "Factura registrada por error"},
    )
    assert reversal.status_code == 200, reversal.text

    updated = client.get(f"/api/ap/supplier-invoices/{invoice['id']}").json()
    assert updated["status"] == "CANCELLED"


def test_reversing_a_paid_ap_accrual_is_rejected(client):
    """No se puede revertir el accrual de una factura que ya tiene pagos
    -- el dinero ya salió, revertir el accrual sin más dejaría el pago
    huérfano de su origen contable."""
    login_admin(client)
    company, expense, payable, supplier = _create_ap_setup(client)
    bank_gl = create_account(client, company_id=company["id"], code="1100", name="Bancos", account_type="ASSET")
    contributions = create_account(
        client, company_id=company["id"], code="3100", name="Aportes", account_type="EQUITY"
    )
    from tests.helpers import create_treasury_account

    bank = create_treasury_account(client, company_id=company["id"], gl_account_id=bank_gl["id"])
    client.post(
        "/api/treasury/remittances",
        json={
            "companyId": company["id"],
            "treasuryAccountId": bank["id"],
            "counterAccountId": contributions["id"],
            "sender": "Fondeo",
            "currencyCode": "HNL",
            "originalAmount": "10000.00",
            "remittanceDate": "2026-01-01",
        },
    )
    invoice = client.post(
        "/api/ap/supplier-invoices",
        json={
            "companyId": company["id"],
            "supplierId": supplier["id"],
            "invoiceNumber": "COR-002",
            "scope": "GENERAL",
            "expenseAccountId": expense["id"],
            "payableAccountId": payable["id"],
            "currencyCode": "HNL",
            "amount": "100.00",
            "invoiceDate": "2026-01-10",
            "dueDate": "2026-02-10",
        },
    ).json()
    approved = client.post(f"/api/ap/supplier-invoices/{invoice['id']}/approve").json()
    client.post(
        f"/api/ap/supplier-invoices/{invoice['id']}/payments",
        json={"treasuryAccountId": bank["id"], "amount": "100.00", "paymentDate": "2026-01-20"},
    )

    response = client.post(
        f"/api/accounting/journal-entries/{approved['accrualDocumentId']}/reverse",
        json={"reason": "Intento inválido"},
    )
    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "NXR-AP-001"

    unchanged = client.get(f"/api/ap/supplier-invoices/{invoice['id']}").json()
    assert unchanged["status"] == "PAID"


def test_reversing_an_ar_invoice_cancels_it(client):
    login_admin(client)
    company = create_company(client)
    revenue = create_account(
        client, company_id=company["id"], code="4100", name="Ingresos", account_type="REVENUE"
    )
    receivable = create_account(
        client, company_id=company["id"], code="1200", name="Cuentas por cobrar", account_type="ASSET"
    )
    from tests.helpers import create_customer

    customer = create_customer(client, company_id=company["id"], legal_name="Cliente reversal")
    invoice = client.post(
        "/api/ar/customer-invoices",
        json={
            "companyId": company["id"],
            "customerId": customer["id"],
            "invoiceNumber": "COR-AR-001",
            "scope": "GENERAL",
            "revenueAccountId": revenue["id"],
            "receivableAccountId": receivable["id"],
            "currencyCode": "HNL",
            "amount": "500.00",
            "invoiceDate": "2026-01-05",
            "dueDate": "2026-02-05",
        },
    ).json()
    approved = client.post(f"/api/ar/customer-invoices/{invoice['id']}/approve").json()
    assert approved["status"] == "APPROVED"

    reversal = client.post(
        f"/api/accounting/journal-entries/{approved['accountingDocumentId']}/reverse",
        json={"reason": "Factura duplicada"},
    )
    assert reversal.status_code == 200, reversal.text

    updated = client.get(f"/api/ar/customer-invoices/{invoice['id']}").json()
    assert updated["status"] == "CANCELLED"
