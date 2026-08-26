import uuid

import pytest
from sqlalchemy import select

from app.models.accounting import AccountingDocument
from app.models.audit import AuditLog
from app.models.treasury import (
    BankStatementLine,
    FundRestriction,
    GeneralExpense,
    ReconciliationMatch,
    TreasuryTransfer,
)
from app.models.permission import UserCompanyAccess
from tests.helpers import (
    create_account,
    create_company,
    create_treasury_account,
    create_user_with_role,
    login_admin,
    login_as,
)


def _setup(client):
    company = create_company(client)
    cash_gl = create_account(
        client, company_id=company["id"], code="1110", name="Caja", account_type="ASSET"
    )
    contributions = create_account(
        client, company_id=company["id"], code="3100", name="Aportes", account_type="EQUITY"
    )
    diff_account = create_account(
        client, company_id=company["id"], code="5900", name="Diferencia de caja", account_type="EXPENSE"
    )
    cash = create_treasury_account(
        client, company_id=company["id"], gl_account_id=cash_gl["id"], name="Caja Central", kind="CASH"
    )
    funding = client.post(
        "/api/treasury/remittances",
        json={
            "companyId": company["id"],
            "treasuryAccountId": cash["id"],
            "counterAccountId": contributions["id"],
            "sender": "Fondeo de caja",
            "currencyCode": "HNL",
            "originalAmount": "1000.00",
            "remittanceDate": "2026-01-01",
        },
    ).json()
    return company, cash, diff_account, contributions, funding["accountingDocumentId"]


def _create_statement_line(client, cash, *, amount: str, description: str = "Movimiento"):
    statement_id = client.post(
        "/api/treasury/bank-statements",
        json={
            "treasuryAccountId": cash["id"],
            "statementDate": "2026-01-31",
            "openingBalance": "0.00",
            "closingBalance": amount,
        },
    ).json()["id"]
    return client.post(
        f"/api/treasury/bank-statements/{statement_id}/lines",
        json={
            "lineDate": "2026-01-02",
            "description": description,
            "amount": amount,
        },
    ).json()


def test_cash_closing_with_shortage_posts_adjustment_and_reduces_balance(client):
    """Orden maestra §33: cash closing con diferencia negativa (faltante)."""
    login_admin(client)
    company, cash, diff_account, _contributions, _funding_doc = _setup(client)

    closing = client.post(
        "/api/treasury/cash-closings",
        json={
            "treasuryAccountId": cash["id"],
            "closingDate": "2026-01-31",
            "openingAmount": "1000.00",
            "expectedAmount": "1000.00",
            "countedAmount": "980.00",
        },
    ).json()
    assert float(closing["differenceAmount"]) == -20.0
    assert closing["status"] == "DRAFT"

    approved = client.post(
        f"/api/treasury/cash-closings/{closing['id']}/approve?companyId={company['id']}",
        json={"differenceAccountId": diff_account["id"]},
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "APPROVED"
    assert approved.json()["accountingDocumentId"]

    balance = next(
        a for a in client.get(f"/api/treasury/accounts?companyId={company['id']}").json()
        if a["id"] == cash["id"]
    )
    assert float(balance["balance"]) == 980.0


def test_cash_closing_without_difference_requires_no_account(client):
    login_admin(client)
    company, cash, _diff_account, _contributions, _funding_doc = _setup(client)

    closing = client.post(
        "/api/treasury/cash-closings",
        json={
            "treasuryAccountId": cash["id"],
            "closingDate": "2026-01-31",
            "openingAmount": "1000.00",
            "expectedAmount": "1000.00",
            "countedAmount": "1000.00",
        },
    ).json()

    approved = client.post(
        f"/api/treasury/cash-closings/{closing['id']}/approve?companyId={company['id']}", json={}
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["accountingDocumentId"] is None


def test_bank_reconciliation_manual_matching_lifecycle(client):
    """Orden maestra §32: UNMATCHED -> MATCHED / EXCLUDED, sin borrar
    destructivamente el statement histórico."""
    login_admin(client)
    _company, cash, _diff_account, _contributions, funding_doc = _setup(client)

    statement = client.post(
        "/api/treasury/bank-statements",
        json={
            "treasuryAccountId": cash["id"],
            "statementDate": "2026-01-31",
            "openingBalance": "0.00",
            "closingBalance": "1000.00",
        },
    )
    assert statement.status_code == 201, statement.text
    statement_id = statement.json()["id"]

    line = client.post(
        f"/api/treasury/bank-statements/{statement_id}/lines",
        json={"lineDate": "2026-01-01", "description": "Movimiento sin conciliar", "amount": "50.00"},
    )
    assert line.status_code == 201, line.text
    line_body = line.json()
    assert line_body["status"] == "UNMATCHED"

    excluded = client.post(f"/api/treasury/bank-statement-lines/{line_body['id']}/exclude")
    assert excluded.status_code == 200, excluded.text
    assert excluded.json()["status"] == "EXCLUDED"

    second_line = client.post(
        f"/api/treasury/bank-statements/{statement_id}/lines",
        json={"lineDate": "2026-01-02", "description": "Fondeo de caja", "amount": "1000.00"},
    ).json()
    assert second_line["status"] == "UNMATCHED"

    matched = client.post(
        f"/api/treasury/bank-statement-lines/{second_line['id']}/match",
        json={"accountingDocumentId": funding_doc, "matchedAmount": "1000.00"},
    )
    assert matched.status_code == 200, matched.text
    assert matched.json()["status"] == "MATCHED"


def test_fund_restriction_never_transfers_money_ownership_to_project(client):
    """Orden maestra §31: restricted != project-owned."""
    login_admin(client)
    company, cash, _diff_account, _contributions, _funding_doc = _setup(client)

    restriction = client.post(
        "/api/treasury/fund-restrictions",
        json={
            "treasuryAccountId": cash["id"],
            "amount": "300.00",
            "description": "Reservado para Proyecto Torre Nexora II",
        },
    )
    assert restriction.status_code == 201, restriction.text
    assert restriction.json()["restrictedForProjectId"] is None

    balance = next(
        a for a in client.get(f"/api/treasury/accounts?companyId={company['id']}").json()
        if a["id"] == cash["id"]
    )
    # La restricción NO reduce el saldo real de Treasury -- solo lo etiqueta.
    assert float(balance["balance"]) == 1000.0


def test_voucher_pdf_is_generated_for_a_remittance(client):
    """Orden maestra §71: comprobante PDF vectorial real, no captura."""
    login_admin(client)
    _company, _cash, _diff_account, _contributions, funding_doc = _setup(client)

    response = client.get(
        f"/api/treasury/vouchers/{funding_doc}"
        "?beneficiary=Constructora%20Nexora&payer=Aportante&paymentMethod=Transferencia"
    )
    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")


def test_reconciliation_uses_cumulative_matches_and_blocks_overmatch(client, db_session):
    login_admin(client)
    _company, cash, _diff_account, _contributions, funding_doc = _setup(client)
    statement_id = client.post(
        "/api/treasury/bank-statements",
        json={
            "treasuryAccountId": cash["id"],
            "statementDate": "2026-01-31",
            "openingBalance": "0.00",
            "closingBalance": "100.00",
        },
    ).json()["id"]
    line = client.post(
        f"/api/treasury/bank-statements/{statement_id}/lines",
        json={"lineDate": "2026-01-02", "description": "Fondeo parcial", "amount": "100.00"},
    ).json()

    first = client.post(
        f"/api/treasury/bank-statement-lines/{line['id']}/match",
        json={"accountingDocumentId": funding_doc, "matchedAmount": "40.00"},
    )
    second = client.post(
        f"/api/treasury/bank-statement-lines/{line['id']}/match",
        json={"accountingDocumentId": funding_doc, "matchedAmount": "60.00"},
    )
    overmatch = client.post(
        f"/api/treasury/bank-statement-lines/{line['id']}/match",
        json={"accountingDocumentId": funding_doc, "matchedAmount": "1.00"},
    )

    assert first.status_code == 200, first.text
    assert first.json()["status"] == "PARTIAL"
    assert second.status_code == 200, second.text
    assert second.json()["status"] == "MATCHED"
    assert overmatch.status_code == 422, overmatch.text
    assert db_session.query(ReconciliationMatch).count() == 2


def test_reconciliation_rejects_accounting_document_from_another_company(client):
    login_admin(client)
    _company_a, cash_a, _diff_a, _contributions_a, _funding_a = _setup(client)
    company_b = create_company(client, name="Compañía extranjera")
    debit_b = create_account(
        client, company_id=company_b["id"], code="1000", name="Activo B", account_type="ASSET"
    )
    credit_b = create_account(
        client, company_id=company_b["id"], code="3000", name="Capital B", account_type="EQUITY"
    )
    funding_b = client.post(
        "/api/accounting/journal-entries",
        json={
            "companyId": company_b["id"],
            "scope": "GENERAL",
            "currencyCode": "HNL",
            "lines": [
                {"accountId": debit_b["id"], "debitAmount": "50.00"},
                {"accountId": credit_b["id"], "creditAmount": "50.00"},
            ],
        },
    ).json()["id"]
    statement_id = client.post(
        "/api/treasury/bank-statements",
        json={
            "treasuryAccountId": cash_a["id"],
            "statementDate": "2026-01-31",
            "openingBalance": "0.00",
            "closingBalance": "50.00",
        },
    ).json()["id"]
    line = client.post(
        f"/api/treasury/bank-statements/{statement_id}/lines",
        json={"lineDate": "2026-01-02", "description": "Documento ajeno", "amount": "50.00"},
    ).json()

    response = client.post(
        f"/api/treasury/bank-statement-lines/{line['id']}/match",
        json={"accountingDocumentId": funding_b, "matchedAmount": "50.00"},
    )

    assert response.status_code == 422, response.text


def test_general_expense_retry_is_idempotent(client, db_session):
    login_admin(client)
    company, cash, diff_account, _contributions, _funding_doc = _setup(client)
    payload = {
        "companyId": company["id"],
        "treasuryAccountId": cash["id"],
        "expenseAccountId": diff_account["id"],
        "category": "ajuste",
        "amount": "25.00",
        "currencyCode": "HNL",
        "expenseDate": "2026-01-20",
        "description": "Gasto idempotente",
    }
    documents_before = db_session.query(AccountingDocument).count()

    first = client.post(
        "/api/treasury/general-expenses",
        json=payload,
        headers={"Idempotency-Key": "expense-retry-1"},
    )
    second = client.post(
        "/api/treasury/general-expenses",
        json=payload,
        headers={"Idempotency-Key": "expense-retry-1"},
    )

    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text
    assert first.json()["id"] == second.json()["id"]
    assert db_session.query(GeneralExpense).count() == 1
    assert db_session.query(AccountingDocument).count() == documents_before + 1
    assert (
        db_session.query(AuditLog)
        .filter(AuditLog.entity_type == "treasury.general_expense")
        .count()
        == 1
    )


def test_transfer_retry_is_idempotent_and_creates_one_audit_event(client, db_session):
    login_admin(client)
    company, cash, _diff_account, contributions, _funding_doc = _setup(client)
    bank_gl = create_account(
        client, company_id=company["id"], code="1100", name="Bancos", account_type="ASSET"
    )
    bank = create_treasury_account(
        client, company_id=company["id"], gl_account_id=bank_gl["id"]
    )
    client.post(
        "/api/treasury/remittances",
        json={
            "companyId": company["id"],
            "treasuryAccountId": bank["id"],
            "counterAccountId": contributions["id"],
            "sender": "Aporte",
            "currencyCode": "HNL",
            "originalAmount": "500.00",
            "remittanceDate": "2026-01-01",
        },
    )
    payload = {
        "companyId": company["id"],
        "sourceTreasuryAccountId": bank["id"],
        "destinationTreasuryAccountId": cash["id"],
        "amount": "100.00",
        "currencyCode": "HNL",
        "transferDate": "2026-01-05",
    }

    first = client.post(
        "/api/treasury/transfers",
        json=payload,
        headers={"Idempotency-Key": "transfer-retry-1"},
    )
    second = client.post(
        "/api/treasury/transfers",
        json=payload,
        headers={"Idempotency-Key": "transfer-retry-1"},
    )

    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text
    assert first.json()["id"] == second.json()["id"]
    assert db_session.query(TreasuryTransfer).count() == 1
    assert (
        db_session.query(AuditLog)
        .filter(AuditLog.entity_type == "treasury.transfer")
        .count()
        == 1
    )


def test_cash_closing_approval_retry_does_not_duplicate_adjustment(client, db_session):
    login_admin(client)
    company, cash, diff_account, _contributions, _funding_doc = _setup(client)
    closing = client.post(
        "/api/treasury/cash-closings",
        json={
            "treasuryAccountId": cash["id"],
            "closingDate": "2026-01-31",
            "openingAmount": "1000.00",
            "expectedAmount": "1000.00",
            "countedAmount": "990.00",
        },
    ).json()
    url = f"/api/treasury/cash-closings/{closing['id']}/approve?companyId={company['id']}"
    payload = {"differenceAccountId": diff_account["id"]}
    documents_before = db_session.query(AccountingDocument).count()

    first = client.post(url, json=payload, headers={"Idempotency-Key": "closing-retry-1"})
    second = client.post(url, json=payload, headers={"Idempotency-Key": "closing-retry-1"})

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert first.json()["accountingDocumentId"] == second.json()["accountingDocumentId"]
    assert db_session.query(AccountingDocument).count() == documents_before + 1


def test_nested_reconciliation_resource_from_other_company_is_denied(client, db_session):
    login_admin(client)
    _company_a, cash_a, _diff, _contributions, _funding = _setup(client)
    statement_id = client.post(
        "/api/treasury/bank-statements",
        json={
            "treasuryAccountId": cash_a["id"],
            "statementDate": "2026-01-31",
            "openingBalance": "0.00",
            "closingBalance": "10.00",
        },
    ).json()["id"]
    line = client.post(
        f"/api/treasury/bank-statements/{statement_id}/lines",
        json={"lineDate": "2026-01-02", "description": "Protegida", "amount": "10.00"},
    ).json()
    company_b = create_company(client, name="Compañía sin acceso a línea")
    user = create_user_with_role(
        db_session, email="treasury-b@nexora.group", role_name="Treasury Manager"
    )
    db_session.add(UserCompanyAccess(user_id=user.id, company_id=company_b["id"]))
    db_session.commit()
    login_as(client, email="treasury-b@nexora.group")

    response = client.post(f"/api/treasury/bank-statement-lines/{line['id']}/exclude")

    assert response.status_code == 403, response.text
    assert response.json()["error"]["code"] == "NXR-PERM-001"


def test_reconciliation_rejects_same_company_document_without_treasury_gl(client, db_session):
    login_admin(client)
    company, cash, diff_account, contributions, _funding_doc = _setup(client)
    unrelated_document = client.post(
        "/api/accounting/journal-entries",
        json={
            "companyId": company["id"],
            "scope": "GENERAL",
            "currencyCode": "HNL",
            "lines": [
                {"accountId": diff_account["id"], "debitAmount": "50.00"},
                {"accountId": contributions["id"], "creditAmount": "50.00"},
            ],
        },
    ).json()["id"]
    line = _create_statement_line(client, cash, amount="50.00")

    response = client.post(
        f"/api/treasury/bank-statement-lines/{line['id']}/match",
        json={"accountingDocumentId": unrelated_document, "matchedAmount": "50.00"},
    )

    assert response.status_code == 422, response.text
    assert db_session.query(ReconciliationMatch).count() == 0


def test_reconciliation_rejects_document_treasury_gl_with_wrong_sign(client, db_session):
    login_admin(client)
    _company, cash, _diff, _contributions, funding_doc = _setup(client)
    line = _create_statement_line(client, cash, amount="-100.00")

    response = client.post(
        f"/api/treasury/bank-statement-lines/{line['id']}/match",
        json={"accountingDocumentId": funding_doc, "matchedAmount": "100.00"},
    )

    assert response.status_code == 422, response.text
    assert db_session.query(ReconciliationMatch).count() == 0


def test_reconciliation_blocks_document_overallocation_across_statement_lines(
    client, db_session
):
    login_admin(client)
    _company, cash, _diff, _contributions, funding_doc = _setup(client)
    first_line = _create_statement_line(client, cash, amount="600.00", description="Part one")
    second_line = _create_statement_line(client, cash, amount="500.00", description="Part two")
    first = client.post(
        f"/api/treasury/bank-statement-lines/{first_line['id']}/match",
        json={"accountingDocumentId": funding_doc, "matchedAmount": "600.00"},
    )

    second = client.post(
        f"/api/treasury/bank-statement-lines/{second_line['id']}/match",
        json={"accountingDocumentId": funding_doc, "matchedAmount": "500.00"},
    )

    assert first.status_code == 200, first.text
    assert second.status_code == 422, second.text
    assert db_session.query(ReconciliationMatch).count() == 1


def test_reconciliation_rejects_matching_an_excluded_line(client, db_session):
    login_admin(client)
    _company, cash, _diff, _contributions, funding_doc = _setup(client)
    line = _create_statement_line(client, cash, amount="50.00")
    excluded = client.post(
        f"/api/treasury/bank-statement-lines/{line['id']}/exclude"
    )
    assert excluded.status_code == 200, excluded.text

    response = client.post(
        f"/api/treasury/bank-statement-lines/{line['id']}/match",
        json={"accountingDocumentId": funding_doc, "matchedAmount": "50.00"},
    )

    assert response.status_code == 422, response.text
    assert db_session.query(ReconciliationMatch).count() == 0


def test_reconciliation_rejects_excluding_a_line_with_match_history(client, db_session):
    login_admin(client)
    _company, cash, _diff, _contributions, funding_doc = _setup(client)
    line = _create_statement_line(client, cash, amount="100.00")
    partial = client.post(
        f"/api/treasury/bank-statement-lines/{line['id']}/match",
        json={"accountingDocumentId": funding_doc, "matchedAmount": "40.00"},
    )
    assert partial.status_code == 200, partial.text

    response = client.post(
        f"/api/treasury/bank-statement-lines/{line['id']}/exclude"
    )

    assert response.status_code == 422, response.text
    assert db_session.query(ReconciliationMatch).count() == 1
    assert response.json()["error"]["code"] == "NXR-FINANCIAL-001"


def test_approving_cash_closing_creates_audit_log_entry(client, db_session):
    login_admin(client)
    company, cash, diff_account, _contributions, _funding_doc = _setup(client)
    closing = client.post(
        "/api/treasury/cash-closings",
        json={
            "treasuryAccountId": cash["id"],
            "closingDate": "2026-01-31",
            "openingAmount": "1000.00",
            "expectedAmount": "1000.00",
            "countedAmount": "980.00",
        },
    ).json()

    approved = client.post(
        f"/api/treasury/cash-closings/{closing['id']}/approve?companyId={company['id']}",
        json={"differenceAccountId": diff_account["id"]},
    )
    assert approved.status_code == 200, approved.text

    rows = db_session.execute(
        select(AuditLog).where(
            AuditLog.entity_type == "treasury.cash_closing",
            AuditLog.entity_id == uuid.UUID(closing["id"]),
            AuditLog.action == "treasury.cash_closing.approve",
        )
    ).scalars().all()
    assert len(rows) == 1
    assert rows[0].after["status"] == "APPROVED"


def test_registering_remittance_creates_audit_log_entry(client, db_session):
    """Remittances have no separate approval step in this codebase (no
    status field, verified against app/models/treasury.py) -- so the
    auditable mutation for this entity is its creation, not an
    "approval" route that does not exist. See docs/AUDIT.md."""
    login_admin(client)
    company = create_company(client)
    cash_gl = create_account(
        client, company_id=company["id"], code="1110", name="Caja", account_type="ASSET"
    )
    contributions = create_account(
        client, company_id=company["id"], code="3100", name="Aportes", account_type="EQUITY"
    )
    cash = create_treasury_account(
        client, company_id=company["id"], gl_account_id=cash_gl["id"], name="Caja Central", kind="CASH"
    )

    remittance = client.post(
        "/api/treasury/remittances",
        json={
            "companyId": company["id"],
            "treasuryAccountId": cash["id"],
            "counterAccountId": contributions["id"],
            "sender": "Fondeo inicial",
            "currencyCode": "HNL",
            "originalAmount": "500.00",
            "remittanceDate": "2026-01-01",
        },
    ).json()

    rows = db_session.execute(
        select(AuditLog).where(
            AuditLog.entity_type == "treasury.remittance",
            AuditLog.entity_id == uuid.UUID(remittance["id"]),
        )
    ).scalars().all()
    assert len(rows) == 1
    assert rows[0].action == "treasury.remittance.create"
    assert rows[0].after["baseAmount"] == "500.00"


def test_registering_general_expense_creates_audit_log_entry(client, db_session):
    """docs/AUDIT.md backlog burn-down: Financial Core gap (General
    Expenses) closed."""
    login_admin(client)
    company, cash, diff_account, _contributions, _funding_doc = _setup(client)

    expense = client.post(
        "/api/treasury/general-expenses",
        json={
            "companyId": company["id"],
            "treasuryAccountId": cash["id"],
            "expenseAccountId": diff_account["id"],
            "category": "papeleria",
            "amount": "25.00",
            "currencyCode": "HNL",
            "expenseDate": "2026-01-20",
            "description": "Gasto de auditoria",
        },
    ).json()

    rows = db_session.execute(
        select(AuditLog).where(
            AuditLog.entity_type == "treasury.general_expense",
            AuditLog.entity_id == uuid.UUID(expense["id"]),
        )
    ).scalars().all()
    assert len(rows) == 1
    assert rows[0].action == "treasury.general_expense.create"
    assert rows[0].after["amount"] == "25.00"


def test_registering_transfer_creates_audit_log_entry(client, db_session):
    """docs/AUDIT.md backlog burn-down: Financial Core gap (Transfers)
    closed."""
    login_admin(client)
    company, cash, _diff_account, contributions, _funding_doc = _setup(client)
    bank_gl = create_account(
        client, company_id=company["id"], code="1100", name="Bancos", account_type="ASSET"
    )
    bank = create_treasury_account(client, company_id=company["id"], gl_account_id=bank_gl["id"])
    client.post(
        "/api/treasury/remittances",
        json={
            "companyId": company["id"],
            "treasuryAccountId": bank["id"],
            "counterAccountId": contributions["id"],
            "sender": "Aporte",
            "currencyCode": "HNL",
            "originalAmount": "500.00",
            "remittanceDate": "2026-01-01",
        },
    )

    transfer = client.post(
        "/api/treasury/transfers",
        json={
            "companyId": company["id"],
            "sourceTreasuryAccountId": bank["id"],
            "destinationTreasuryAccountId": cash["id"],
            "amount": "100.00",
            "currencyCode": "HNL",
            "transferDate": "2026-01-05",
        },
    ).json()

    rows = db_session.execute(
        select(AuditLog).where(
            AuditLog.entity_type == "treasury.transfer",
            AuditLog.entity_id == uuid.UUID(transfer["id"]),
        )
    ).scalars().all()
    assert len(rows) == 1
    assert rows[0].action == "treasury.transfer.create"
    assert rows[0].after["amount"] == "100.00"


def test_bank_reconciliation_match_and_exclude_create_audit_log_entries(client, db_session):
    """docs/AUDIT.md backlog burn-down: Financial Core gap (Bank
    Reconciliation match/exclude) closed."""
    login_admin(client)
    _company, cash, _diff_account, _contributions, funding_doc = _setup(client)

    statement_id = client.post(
        "/api/treasury/bank-statements",
        json={
            "treasuryAccountId": cash["id"],
            "statementDate": "2026-01-31",
            "openingBalance": "0.00",
            "closingBalance": "1000.00",
        },
    ).json()["id"]

    matched_line = client.post(
        f"/api/treasury/bank-statements/{statement_id}/lines",
        json={"lineDate": "2026-01-02", "description": "Fondeo de caja", "amount": "1000.00"},
    ).json()
    matched = client.post(
        f"/api/treasury/bank-statement-lines/{matched_line['id']}/match",
        json={"accountingDocumentId": funding_doc, "matchedAmount": "1000.00"},
    )
    assert matched.status_code == 200, matched.text

    excluded_line = client.post(
        f"/api/treasury/bank-statements/{statement_id}/lines",
        json={"lineDate": "2026-01-03", "description": "Sin conciliar", "amount": "50.00"},
    ).json()
    excluded = client.post(f"/api/treasury/bank-statement-lines/{excluded_line['id']}/exclude")
    assert excluded.status_code == 200, excluded.text

    match_rows = db_session.execute(
        select(AuditLog).where(
            AuditLog.entity_type == "treasury.bank_statement_line",
            AuditLog.entity_id == uuid.UUID(matched_line["id"]),
            AuditLog.action == "treasury.bank_reconciliation.match",
        )
    ).scalars().all()
    assert len(match_rows) == 1
    assert match_rows[0].after["status"] == "MATCHED"
    reconciliation_match = db_session.execute(
        select(ReconciliationMatch).where(
            ReconciliationMatch.bank_statement_line_id == uuid.UUID(matched_line["id"])
        )
    ).scalar_one()
    assert match_rows[0].after["accountingDocumentId"] == funding_doc
    assert match_rows[0].after["reconciliationMatchId"] == str(reconciliation_match.id)

    exclude_rows = db_session.execute(
        select(AuditLog).where(
            AuditLog.entity_type == "treasury.bank_statement_line",
            AuditLog.entity_id == uuid.UUID(excluded_line["id"]),
            AuditLog.action == "treasury.bank_reconciliation.exclude",
        )
    ).scalars().all()
    assert len(exclude_rows) == 1
    assert exclude_rows[0].after["status"] == "EXCLUDED"


def test_creating_fund_restriction_creates_audit_log_entry(client, db_session):
    """docs/AUDIT.md backlog burn-down: Financial Core gap (Fund
    Restrictions) closed."""
    login_admin(client)
    _company, cash, _diff_account, _contributions, _funding_doc = _setup(client)

    restriction = client.post(
        "/api/treasury/fund-restrictions",
        json={
            "treasuryAccountId": cash["id"],
            "amount": "300.00",
            "description": "Reservado para Proyecto Torre Nexora II",
        },
    ).json()

    rows = db_session.execute(
        select(AuditLog).where(
            AuditLog.entity_type == "treasury.fund_restriction",
            AuditLog.entity_id == uuid.UUID(restriction["id"]),
        )
    ).scalars().all()
    assert len(rows) == 1
    assert rows[0].action == "treasury.fund_restriction.create"
    assert rows[0].after["amount"] == "300.00"


def test_general_expense_rolls_back_when_audit_write_fails(client, db_session, monkeypatch):
    login_admin(client)
    company, cash, diff_account, _contributions, _funding_doc = _setup(client)
    documents_before = db_session.query(AccountingDocument).count()

    def fail_audit(*args, **kwargs):
        raise RuntimeError("audit unavailable")

    monkeypatch.setattr("app.api.routes.treasury.audit_service.record", fail_audit)

    with pytest.raises(RuntimeError, match="audit unavailable"):
        client.post(
            "/api/treasury/general-expenses",
            json={
                "companyId": company["id"],
                "treasuryAccountId": cash["id"],
                "expenseAccountId": diff_account["id"],
                "category": "papeleria",
                "amount": "25.00",
                "currencyCode": "HNL",
                "expenseDate": "2026-01-20",
                "description": "Debe revertirse con el audit",
            },
        )

    db_session.expire_all()
    assert db_session.query(GeneralExpense).count() == 0
    assert db_session.query(AccountingDocument).count() == documents_before


def test_transfer_rolls_back_when_audit_write_fails(client, db_session, monkeypatch):
    login_admin(client)
    company, cash, _diff_account, contributions, _funding_doc = _setup(client)
    bank_gl = create_account(
        client, company_id=company["id"], code="1100", name="Bancos", account_type="ASSET"
    )
    bank = create_treasury_account(
        client, company_id=company["id"], gl_account_id=bank_gl["id"]
    )
    client.post(
        "/api/treasury/remittances",
        json={
            "companyId": company["id"],
            "treasuryAccountId": bank["id"],
            "counterAccountId": contributions["id"],
            "sender": "Aporte",
            "currencyCode": "HNL",
            "originalAmount": "500.00",
            "remittanceDate": "2026-01-01",
        },
    )
    documents_before = db_session.query(AccountingDocument).count()

    def fail_audit(*args, **kwargs):
        raise RuntimeError("audit unavailable")

    monkeypatch.setattr("app.api.routes.treasury.audit_service.record", fail_audit)

    with pytest.raises(RuntimeError, match="audit unavailable"):
        client.post(
            "/api/treasury/transfers",
            json={
                "companyId": company["id"],
                "sourceTreasuryAccountId": bank["id"],
                "destinationTreasuryAccountId": cash["id"],
                "amount": "100.00",
                "currencyCode": "HNL",
                "transferDate": "2026-01-05",
            },
        )

    db_session.expire_all()
    assert db_session.query(TreasuryTransfer).count() == 0
    assert db_session.query(AccountingDocument).count() == documents_before


def test_reconciliation_match_rolls_back_when_audit_write_fails(
    client, db_session, monkeypatch
):
    login_admin(client)
    _company, cash, _diff_account, _contributions, funding_doc = _setup(client)
    line = _create_statement_line(client, cash, amount="1000.00")

    def fail_audit(*args, **kwargs):
        raise RuntimeError("audit unavailable")

    monkeypatch.setattr("app.api.routes.treasury.audit_service.record", fail_audit)

    with pytest.raises(RuntimeError, match="audit unavailable"):
        client.post(
            f"/api/treasury/bank-statement-lines/{line['id']}/match",
            json={"accountingDocumentId": funding_doc, "matchedAmount": "1000.00"},
        )

    db_session.expire_all()
    persisted_line = db_session.get(BankStatementLine, uuid.UUID(line["id"]))
    assert persisted_line.status == "UNMATCHED"
    assert db_session.query(ReconciliationMatch).count() == 0


def test_reconciliation_exclude_rolls_back_when_audit_write_fails(
    client, db_session, monkeypatch
):
    login_admin(client)
    _company, cash, _diff_account, _contributions, _funding_doc = _setup(client)
    line = _create_statement_line(client, cash, amount="50.00")

    def fail_audit(*args, **kwargs):
        raise RuntimeError("audit unavailable")

    monkeypatch.setattr("app.api.routes.treasury.audit_service.record", fail_audit)

    with pytest.raises(RuntimeError, match="audit unavailable"):
        client.post(f"/api/treasury/bank-statement-lines/{line['id']}/exclude")

    db_session.expire_all()
    persisted_line = db_session.get(BankStatementLine, uuid.UUID(line["id"]))
    assert persisted_line.status == "UNMATCHED"


def test_fund_restriction_rolls_back_when_audit_write_fails(
    client, db_session, monkeypatch
):
    login_admin(client)
    _company, cash, _diff_account, _contributions, _funding_doc = _setup(client)

    def fail_audit(*args, **kwargs):
        raise RuntimeError("audit unavailable")

    monkeypatch.setattr("app.api.routes.treasury.audit_service.record", fail_audit)

    with pytest.raises(RuntimeError, match="audit unavailable"):
        client.post(
            "/api/treasury/fund-restrictions",
            json={
                "treasuryAccountId": cash["id"],
                "amount": "300.00",
                "description": "Debe revertirse con el audit",
            },
        )

    db_session.expire_all()
    assert db_session.query(FundRestriction).count() == 0
