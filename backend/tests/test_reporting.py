import uuid
from decimal import Decimal

from app.models.permission import UserCompanyAccess
from tests.helpers import (
    create_account,
    create_company,
    create_treasury_account,
    create_user_with_role,
    login_admin,
    login_as,
)


def _classify_account(client, *, account_id: str, cash_flow_activity: str | None):
    response = client.patch(
        f"/api/master-data/accounts/{account_id}", json={"cashFlowActivity": cash_flow_activity}
    )
    assert response.status_code == 200, response.text
    return response.json()


def _create_project(client, *, company_id: str, name: str = "Reporte Torre I") -> dict:
    response = client.post(
        "/api/projects",
        json={"companyId": company_id, "name": name, "code": "RPT-001", "currencyCode": "HNL"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _post_journal(client, *, company_id: str, lines: list[dict]) -> dict:
    response = client.post(
        "/api/accounting/journal-entries",
        json={
            "companyId": company_id,
            "scope": "GENERAL",
            "currencyCode": "HNL",
            "lines": lines,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_trial_balance_debits_equal_credits_after_a_real_posting(client, db_session):
    login_admin(client)
    company = create_company(client)
    expense = create_account(client, company_id=company["id"], code="6000", name="Gastos", account_type="EXPENSE")
    cash = create_account(client, company_id=company["id"], code="1000", name="Caja", account_type="ASSET")

    posting = client.post(
        "/api/accounting/journal-entries",
        json={
            "companyId": company["id"],
            "scope": "GENERAL",
            "currencyCode": "HNL",
            "lines": [
                {"accountId": expense["id"], "debitAmount": "100.00"},
                {"accountId": cash["id"], "creditAmount": "100.00"},
            ],
        },
    )
    assert posting.status_code == 201, posting.text

    response = client.get(f"/api/reports/trial-balance?companyId={company['id']}")
    assert response.status_code == 200, response.text
    body = response.json()
    total_debit = sum(Decimal(row["debitBalance"]) for row in body["rows"])
    total_credit = sum(Decimal(row["creditBalance"]) for row in body["rows"])
    assert total_debit == total_credit == Decimal("100.00")
    assert Decimal(body["totalDebit"]) == Decimal("100.00")
    assert Decimal(body["totalCredit"]) == Decimal("100.00")

    expense_row = next(row for row in body["rows"] if row["accountCode"] == "6000")
    cash_row = next(row for row in body["rows"] if row["accountCode"] == "1000")
    assert Decimal(expense_row["debitBalance"]) == Decimal("100.00")
    assert Decimal(expense_row["creditBalance"]) == Decimal("0")
    assert Decimal(cash_row["debitBalance"]) == Decimal("0")
    assert Decimal(cash_row["creditBalance"]) == Decimal("100.00")


def test_trial_balance_shows_a_normally_credit_account_in_the_credit_column(client, db_session):
    """Regression test for the sign convention: account_balance() always
    returns debit-minus-credit regardless of account_type. A REVENUE
    account, which normally carries a credit balance, must still show up
    in the credit column of the trial balance (never flipped negative in
    the debit column, never coerced positive)."""
    login_admin(client)
    company = create_company(client)
    revenue = create_account(client, company_id=company["id"], code="4000", name="Ingresos", account_type="REVENUE")
    cash = create_account(client, company_id=company["id"], code="1000", name="Caja", account_type="ASSET")

    posting = client.post(
        "/api/accounting/journal-entries",
        json={
            "companyId": company["id"],
            "scope": "GENERAL",
            "currencyCode": "HNL",
            "lines": [
                {"accountId": cash["id"], "debitAmount": "250.00"},
                {"accountId": revenue["id"], "creditAmount": "250.00"},
            ],
        },
    )
    assert posting.status_code == 201, posting.text

    response = client.get(f"/api/reports/trial-balance?companyId={company['id']}")
    assert response.status_code == 200, response.text
    body = response.json()
    revenue_row = next(row for row in body["rows"] if row["accountCode"] == "4000")
    assert Decimal(revenue_row["debitBalance"]) == Decimal("0")
    assert Decimal(revenue_row["creditBalance"]) == Decimal("250.00")
    assert Decimal(body["totalDebit"]) == Decimal(body["totalCredit"]) == Decimal("250.00")


def test_trial_balance_never_returns_another_companys_accounts(client, db_session):
    login_admin(client)
    company_a = create_company(client, name="Balance A")
    company_b = create_company(client, name="Balance B")

    user = create_user_with_role(
        db_session, email="finance-trial@nexora.group", role_name="Finance Manager"
    )
    db_session.add(UserCompanyAccess(user_id=user.id, company_id=company_b["id"]))
    db_session.commit()
    login_as(client, email="finance-trial@nexora.group")

    response = client.get(f"/api/reports/trial-balance?companyId={company_a['id']}")
    assert response.status_code == 403, response.text
    assert response.json()["error"]["code"] == "NXR-PERM-001"


def test_budget_vs_actual_matches_budget_service_compute_summary(client, db_session):
    from app.services import budget_service

    login_admin(client)
    company = create_company(client)
    project = _create_project(client, company_id=company["id"])
    baseline = client.post(
        f"/api/projects/{project['id']}/budgets/baseline",
        json={"currencyCode": "HNL", "lines": [{"authorizedAmount": "1000.00"}]},
    )
    assert baseline.status_code == 201, baseline.text

    response = client.get(f"/api/reports/budget-vs-actual?projectId={project['id']}")
    assert response.status_code == 200, response.text
    body = response.json()

    trusted = budget_service.compute_summary(db_session, project_id=uuid.UUID(project["id"]))
    assert Decimal(body["authorized"]) == trusted.authorized
    assert Decimal(body["committed"]) == trusted.committed
    assert Decimal(body["accrued"]) == trusted.accrued
    assert Decimal(body["paid"]) == trusted.paid
    assert Decimal(body["available"]) == trusted.available


def test_budget_vs_actual_never_returns_another_companys_project(client, db_session):
    login_admin(client)
    company_a = create_company(client, name="Presupuesto A")
    company_b = create_company(client, name="Presupuesto B")
    project = _create_project(client, company_id=company_a["id"])

    user = create_user_with_role(
        db_session, email="finance-budget@nexora.group", role_name="Finance Manager"
    )
    db_session.add(UserCompanyAccess(user_id=user.id, company_id=company_b["id"]))
    db_session.commit()
    login_as(client, email="finance-budget@nexora.group")

    response = client.get(f"/api/reports/budget-vs-actual?projectId={project['id']}")
    assert response.status_code == 403, response.text
    assert response.json()["error"]["code"] == "NXR-PERM-001"


def test_balance_sheet_balances_with_current_earnings(client, db_session):
    """Catches omitted current earnings or the wrong natural sign for equity."""
    login_admin(client)
    company = create_company(client)
    cash = create_account(
        client, company_id=company["id"], code="1000", name="Caja", account_type="ASSET"
    )
    equity = create_account(
        client, company_id=company["id"], code="3000", name="Capital", account_type="EQUITY"
    )
    revenue = create_account(
        client, company_id=company["id"], code="4000", name="Ingresos", account_type="REVENUE"
    )
    _post_journal(
        client,
        company_id=company["id"],
        lines=[
            {"accountId": cash["id"], "debitAmount": "150.00"},
            {"accountId": equity["id"], "creditAmount": "100.00"},
            {"accountId": revenue["id"], "creditAmount": "50.00"},
        ],
    )

    response = client.get(f"/api/reports/balance-sheet?companyId={company['id']}")

    assert response.status_code == 200, response.text
    body = response.json()
    assert Decimal(body["totalAssets"]) == Decimal("150.00")
    assert Decimal(body["totalLiabilities"]) == Decimal("0.00")
    assert Decimal(body["totalEquity"]) == Decimal("100.00")
    assert Decimal(body["currentEarnings"]) == Decimal("50.00")
    assert Decimal(body["totalEquityIncludingEarnings"]) == Decimal("150.00")
    assert Decimal(body["totalLiabilitiesAndEquity"]) == Decimal("150.00")
    assert Decimal(body["equationDelta"]) == Decimal("0.00")


def test_income_statement_uses_natural_revenue_and_expense_signs(client, db_session):
    """Catches credit revenue or debit expense being reported with a negative sign."""
    login_admin(client)
    company = create_company(client)
    cash = create_account(
        client, company_id=company["id"], code="1000", name="Caja", account_type="ASSET"
    )
    revenue = create_account(
        client, company_id=company["id"], code="4000", name="Ingresos", account_type="REVENUE"
    )
    expense = create_account(
        client, company_id=company["id"], code="5000", name="Gastos", account_type="EXPENSE"
    )
    _post_journal(
        client,
        company_id=company["id"],
        lines=[
            {"accountId": cash["id"], "debitAmount": "100.00"},
            {"accountId": revenue["id"], "creditAmount": "100.00"},
        ],
    )
    _post_journal(
        client,
        company_id=company["id"],
        lines=[
            {"accountId": expense["id"], "debitAmount": "25.00"},
            {"accountId": cash["id"], "creditAmount": "25.00"},
        ],
    )

    response = client.get(f"/api/reports/income-statement?companyId={company['id']}")

    assert response.status_code == 200, response.text
    body = response.json()
    assert Decimal(body["totalRevenue"]) == Decimal("100.00")
    assert Decimal(body["totalExpenses"]) == Decimal("25.00")
    assert Decimal(body["netIncome"]) == Decimal("75.00")
    assert body["revenue"][0]["accountCode"] == "4000"
    assert body["expenses"][0]["accountCode"] == "5000"


def test_general_ledger_paginates_and_totals_full_filter(client, db_session):
    """Catches totals being computed from only the current page."""
    login_admin(client)
    company = create_company(client)
    cash = create_account(
        client, company_id=company["id"], code="1000", name="Caja", account_type="ASSET"
    )
    equity = create_account(
        client, company_id=company["id"], code="3000", name="Capital", account_type="EQUITY"
    )
    _post_journal(
        client,
        company_id=company["id"],
        lines=[
            {"accountId": cash["id"], "debitAmount": "100.00"},
            {"accountId": equity["id"], "creditAmount": "100.00"},
        ],
    )

    response = client.get(
        f"/api/reports/general-ledger?companyId={company['id']}&offset=0&limit=1"
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == 2
    assert body["offset"] == 0
    assert body["limit"] == 1
    assert len(body["rows"]) == 1
    assert Decimal(body["totalDebit"]) == Decimal("100.00")
    assert Decimal(body["totalCredit"]) == Decimal("100.00")


def test_balance_sheet_nets_a_reversed_document_to_zero(client, db_session):
    """A reversed document's original + reversal must cancel; the statement
    must include both (never exclude REVERSED) and never leave a residue."""
    login_admin(client)
    company = create_company(client)
    cash = create_account(
        client, company_id=company["id"], code="1000", name="Caja", account_type="ASSET"
    )
    equity = create_account(
        client, company_id=company["id"], code="3000", name="Capital", account_type="EQUITY"
    )
    posted = _post_journal(
        client,
        company_id=company["id"],
        lines=[
            {"accountId": cash["id"], "debitAmount": "80.00"},
            {"accountId": equity["id"], "creditAmount": "80.00"},
        ],
    )
    reversal = client.post(
        f"/api/accounting/journal-entries/{posted['id']}/reverse",
        json={"reason": "Error de captura"},
    )
    assert reversal.status_code == 200, reversal.text

    response = client.get(f"/api/reports/balance-sheet?companyId={company['id']}")

    assert response.status_code == 200, response.text
    body = response.json()
    assert Decimal(body["totalAssets"]) == Decimal("0.00")
    assert Decimal(body["totalEquity"]) == Decimal("0.00")
    assert Decimal(body["equationDelta"]) == Decimal("0.00")


def test_income_statement_rejects_date_from_after_date_to(client, db_session):
    login_admin(client)
    company = create_company(client)

    response = client.get(
        f"/api/reports/income-statement?companyId={company['id']}"
        "&dateFrom=2026-06-01&dateTo=2026-01-01"
    )

    assert response.status_code == 422, response.text


def test_general_ledger_account_filter_from_another_company_is_404(client, db_session):
    login_admin(client)
    company_a = create_company(client, name="Mayor A")
    company_b = create_company(client, name="Mayor B")
    foreign_account = create_account(
        client, company_id=company_b["id"], code="1000", name="Caja", account_type="ASSET"
    )

    response = client.get(
        f"/api/reports/general-ledger?companyId={company_a['id']}&accountId={foreign_account['id']}"
    )

    assert response.status_code == 404, response.text


def test_general_ledger_never_returns_another_companys_rows(client, db_session):
    login_admin(client)
    company_a = create_company(client, name="Mayor C")
    company_b = create_company(client, name="Mayor D")

    user = create_user_with_role(
        db_session, email="finance-gl@nexora.group", role_name="Finance Manager"
    )
    db_session.add(UserCompanyAccess(user_id=user.id, company_id=company_b["id"]))
    db_session.commit()
    login_as(client, email="finance-gl@nexora.group")

    response = client.get(f"/api/reports/general-ledger?companyId={company_a['id']}")
    assert response.status_code == 403, response.text
    assert response.json()["error"]["code"] == "NXR-PERM-001"


def test_balance_sheet_never_returns_another_companys_accounts(client, db_session):
    login_admin(client)
    company_a = create_company(client, name="Mayor E")
    company_b = create_company(client, name="Mayor F")

    user = create_user_with_role(
        db_session, email="finance-bs@nexora.group", role_name="Finance Manager"
    )
    db_session.add(UserCompanyAccess(user_id=user.id, company_id=company_b["id"]))
    db_session.commit()
    login_as(client, email="finance-bs@nexora.group")

    response = client.get(f"/api/reports/balance-sheet?companyId={company_a['id']}")
    assert response.status_code == 403, response.text
    assert response.json()["error"]["code"] == "NXR-PERM-001"


def test_income_statement_never_returns_another_companys_accounts(client, db_session):
    login_admin(client)
    company_a = create_company(client, name="Mayor G")
    company_b = create_company(client, name="Mayor H")

    user = create_user_with_role(
        db_session, email="finance-is@nexora.group", role_name="Finance Manager"
    )
    db_session.add(UserCompanyAccess(user_id=user.id, company_id=company_b["id"]))
    db_session.commit()
    login_as(client, email="finance-is@nexora.group")

    response = client.get(f"/api/reports/income-statement?companyId={company_a['id']}")
    assert response.status_code == 403, response.text
    assert response.json()["error"]["code"] == "NXR-PERM-001"


def test_cash_flow_classifies_a_remittance_as_financing_and_reconciles_net_change(client, db_session):
    """Método directo (NXR-REQ-0016/0093): una remesa CENTRAL (débito
    Banco, crédito Aportes de socios) clasificada FINANCING debe aparecer
    como entrada de efectivo bajo Financing, y net_change_in_cash debe
    coincidir exactamente con el monto real depositado en Treasury."""
    login_admin(client)
    company = create_company(client)
    bank_gl = create_account(client, company_id=company["id"], code="1100", name="Bancos", account_type="ASSET")
    contributions = create_account(
        client, company_id=company["id"], code="3100", name="Aportes de socios", account_type="EQUITY"
    )
    _classify_account(client, account_id=contributions["id"], cash_flow_activity="FINANCING")
    bank = create_treasury_account(client, company_id=company["id"], gl_account_id=bank_gl["id"])

    remittance = client.post(
        "/api/treasury/remittances",
        json={
            "companyId": company["id"],
            "treasuryAccountId": bank["id"],
            "counterAccountId": contributions["id"],
            "sender": "Socio fundador",
            "currencyCode": "HNL",
            "originalAmount": "10000.00",
            "remittanceDate": "2026-01-15",
        },
    )
    assert remittance.status_code == 201, remittance.text

    response = client.get(f"/api/reports/cash-flow?companyId={company['id']}")
    assert response.status_code == 200, response.text
    body = response.json()

    assert Decimal(body["totalFinancing"]) == Decimal("10000.00")
    assert Decimal(body["totalOperating"]) == Decimal("0")
    assert Decimal(body["totalInvesting"]) == Decimal("0")
    assert Decimal(body["totalUnclassified"]) == Decimal("0")
    assert Decimal(body["netChangeInCash"]) == Decimal("10000.00")
    assert len(body["financing"]) == 1
    assert body["financing"][0]["accountCode"] == "3100"


def test_cash_flow_general_expense_is_operating_when_classified(client, db_session):
    login_admin(client)
    company = create_company(client)
    bank_gl = create_account(client, company_id=company["id"], code="1100", name="Bancos", account_type="ASSET")
    contributions = create_account(
        client, company_id=company["id"], code="3100", name="Aportes de socios", account_type="EQUITY"
    )
    expense = create_account(
        client, company_id=company["id"], code="5100", name="Gastos administrativos", account_type="EXPENSE"
    )
    _classify_account(client, account_id=contributions["id"], cash_flow_activity="FINANCING")
    _classify_account(client, account_id=expense["id"], cash_flow_activity="OPERATING")
    bank = create_treasury_account(client, company_id=company["id"], gl_account_id=bank_gl["id"])

    client.post(
        "/api/treasury/remittances",
        json={
            "companyId": company["id"], "treasuryAccountId": bank["id"], "counterAccountId": contributions["id"],
            "sender": "Socio", "currencyCode": "HNL", "originalAmount": "5000.00", "remittanceDate": "2026-01-01",
        },
    )
    expense_response = client.post(
        "/api/treasury/general-expenses",
        json={
            "companyId": company["id"], "treasuryAccountId": bank["id"], "expenseAccountId": expense["id"],
            "category": "papeleria", "amount": "300.00", "currencyCode": "HNL", "expenseDate": "2026-01-02",
            "description": "Papelería",
        },
    )
    assert expense_response.status_code == 201, expense_response.text

    body = client.get(f"/api/reports/cash-flow?companyId={company['id']}").json()
    assert Decimal(body["totalOperating"]) == Decimal("-300.00")
    assert Decimal(body["totalFinancing"]) == Decimal("5000.00")
    assert Decimal(body["netChangeInCash"]) == Decimal("4700.00")
    # invariant: the classified buckets + unclassified must always
    # reconcile exactly to the real net change in cash (double-entry
    # conservation, not a coincidence of this fixture).
    reconciled = (
        Decimal(body["totalOperating"])
        + Decimal(body["totalInvesting"])
        + Decimal(body["totalFinancing"])
        + Decimal(body["totalUnclassified"])
    )
    assert reconciled == Decimal(body["netChangeInCash"])


def test_cash_flow_shows_unclassified_bucket_instead_of_hiding_or_guessing(client, db_session):
    """CLAUDE.md: no fabricar datos, no ocultar bugs -- una cuenta sin
    clasificar aparece explícitamente en `unclassified`, nunca se le
    asigna una actividad adivinada ni se omite del reporte."""
    login_admin(client)
    company = create_company(client)
    bank_gl = create_account(client, company_id=company["id"], code="1100", name="Bancos", account_type="ASSET")
    contributions = create_account(
        client, company_id=company["id"], code="3100", name="Aportes de socios", account_type="EQUITY"
    )
    bank = create_treasury_account(client, company_id=company["id"], gl_account_id=bank_gl["id"])

    client.post(
        "/api/treasury/remittances",
        json={
            "companyId": company["id"], "treasuryAccountId": bank["id"], "counterAccountId": contributions["id"],
            "sender": "Socio", "currencyCode": "HNL", "originalAmount": "2000.00", "remittanceDate": "2026-01-01",
        },
    )

    body = client.get(f"/api/reports/cash-flow?companyId={company['id']}").json()
    assert Decimal(body["totalFinancing"]) == Decimal("0")
    assert Decimal(body["totalUnclassified"]) == Decimal("2000.00")
    assert len(body["unclassified"]) == 1
    assert body["unclassified"][0]["accountCode"] == "3100"


def test_update_account_rejects_invalid_cash_flow_activity(client, db_session):
    login_admin(client)
    company = create_company(client)
    account = create_account(client, company_id=company["id"], code="3100", name="Aportes", account_type="EQUITY")

    response = client.patch(
        f"/api/master-data/accounts/{account['id']}", json={"cashFlowActivity": "NOT_A_REAL_ACTIVITY"}
    )
    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "NXR-ACCOUNTING-005"


def test_update_account_never_crosses_company(client, db_session):
    login_admin(client)
    company_a = create_company(client, name="Flujo A")
    company_b = create_company(client, name="Flujo B")
    account_b = create_account(
        client, company_id=company_b["id"], code="3100", name="Aportes", account_type="EQUITY"
    )

    user = create_user_with_role(
        db_session, email="finance-cf@nexora.group", role_name="Finance Manager"
    )
    db_session.add(UserCompanyAccess(user_id=user.id, company_id=company_a["id"]))
    db_session.commit()
    login_as(client, email="finance-cf@nexora.group")

    response = client.patch(
        f"/api/master-data/accounts/{account_b['id']}", json={"cashFlowActivity": "FINANCING"}
    )
    assert response.status_code == 403, response.text
    assert response.json()["error"]["code"] == "NXR-PERM-001"


def test_cash_flow_never_returns_another_companys_accounts(client, db_session):
    login_admin(client)
    company_a = create_company(client, name="Flujo C")
    company_b = create_company(client, name="Flujo D")

    user = create_user_with_role(
        db_session, email="finance-cf2@nexora.group", role_name="Finance Manager"
    )
    db_session.add(UserCompanyAccess(user_id=user.id, company_id=company_b["id"]))
    db_session.commit()
    login_as(client, email="finance-cf2@nexora.group")

    response = client.get(f"/api/reports/cash-flow?companyId={company_a['id']}")
    assert response.status_code == 403, response.text
    assert response.json()["error"]["code"] == "NXR-PERM-001"
