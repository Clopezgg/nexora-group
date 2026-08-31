from decimal import Decimal

from tests.helpers import create_account, create_company, login_admin
from tests.test_project_financial_summary import (
    _create_project,
    _create_sales_contract,
    _post_project_journal,
)


def test_project_financial_cockpit_computes_eac_etc_cpi_and_margin(client):
    login_admin(client)
    company = create_company(client, name="Cockpit Co")
    project = _create_project(
        client, company_id=company["id"], name="Torre Cockpit", code="CKP-001"
    )
    # Ingreso por contrato: 1000.00
    _create_sales_contract(client, company_id=company["id"], project_id=project["id"])

    # BAC = 600.00
    assert (
        client.post(
            f"/api/projects/{project['id']}/budgets/baseline",
            json={"currencyCode": "HNL", "lines": [{"authorizedAmount": "600.00"}]},
        ).status_code
        == 201
    )
    # Avance físico 50%
    assert (
        client.post(
            f"/api/projects/{project['id']}/progress",
            json={"recordDate": "2026-08-29", "plannedPercent": "60.00", "actualPercent": "50.00"},
        ).status_code
        == 201
    )
    # Costo real por el GL: gasto de 200 imputado al proyecto.
    expense = create_account(
        client, company_id=company["id"], code="5100", name="Costo obra", account_type="EXPENSE"
    )
    cash = create_account(
        client, company_id=company["id"], code="1100", name="Bancos", account_type="ASSET"
    )
    _post_project_journal(
        client,
        company_id=company["id"],
        project_id=project["id"],
        debit_account_id=expense["id"],
        credit_account_id=cash["id"],
        amount="200.00",
        description="Costo de obra imputado",
    )

    response = client.get(f"/api/projects/{project['id']}/financial-cockpit")
    assert response.status_code == 200, response.text
    body = response.json()

    assert Decimal(body["budgetAtCompletion"]) == Decimal("600.00")
    assert Decimal(body["actualCost"]) == Decimal("200.00")
    assert Decimal(body["percentComplete"]) == Decimal("50.00")
    assert Decimal(body["earnedValue"]) == Decimal("300.00")
    assert Decimal(body["costPerformanceIndex"]) == Decimal("1.5000")
    assert Decimal(body["estimateToComplete"]) == Decimal("200.00")
    assert Decimal(body["estimateAtCompletion"]) == Decimal("400.00")
    assert Decimal(body["varianceAtCompletion"]) == Decimal("200.00")
    assert Decimal(body["contractRevenue"]) == Decimal("1000.00")
    assert Decimal(body["projectedMargin"]) == Decimal("600.00")
    assert Decimal(body["projectedMarginPct"]) == Decimal("60.00")


def test_project_cockpit_without_budget_or_progress_is_fail_closed(client):
    login_admin(client)
    company = create_company(client, name="Cockpit Empty Co")
    project = _create_project(
        client, company_id=company["id"], name="Sin datos", code="CKP-002"
    )

    body = client.get(f"/api/projects/{project['id']}/financial-cockpit").json()
    assert Decimal(body["budgetAtCompletion"]) == Decimal("0")
    # Sin BAC ni avance -> los derivados quedan en None, no en cifras inventadas.
    assert body["earnedValue"] is None
    assert body["estimateAtCompletion"] is None
    assert body["projectedMargin"] is None
