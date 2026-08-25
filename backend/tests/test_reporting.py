import uuid
from decimal import Decimal

from app.models.permission import UserCompanyAccess
from tests.helpers import create_account, create_company, create_user_with_role, login_admin, login_as


def _create_project(client, *, company_id: str, name: str = "Reporte Torre I") -> dict:
    response = client.post(
        "/api/projects",
        json={"companyId": company_id, "name": name, "code": "RPT-001", "currencyCode": "HNL"},
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
