from decimal import Decimal

from app.models.permission import UserCompanyAccess, UserProjectAccess
from tests.helpers import (
    create_account,
    create_company,
    create_user_with_role,
    login_admin,
    login_as,
)


def _create_project(client, *, company_id: str, name: str, code: str) -> dict:
    response = client.post(
        "/api/projects",
        json={
            "companyId": company_id,
            "name": name,
            "code": code,
            "currencyCode": "HNL",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_sales_contract(client, *, company_id: str, project_id: str) -> dict:
    lead = client.post(
        "/api/crm/leads",
        json={"companyId": company_id, "name": "Cliente KPI", "source": "REFERRAL"},
    )
    assert lead.status_code == 201, lead.text
    converted = client.post(f"/api/crm/leads/{lead.json()['id']}/convert")
    assert converted.status_code == 200, converted.text
    customer = converted.json()["customer"]
    opportunity = converted.json()["opportunity"]
    quotation = client.post(
        "/api/crm/quotations",
        json={
            "companyId": company_id,
            "opportunityId": opportunity["id"],
            "customerId": customer["id"],
            "projectId": project_id,
            "quotationNumber": "KPI-COT-001",
            "currencyCode": "HNL",
            "amount": "1000.00",
        },
    )
    assert quotation.status_code == 201, quotation.text
    accepted = client.post(f"/api/crm/quotations/{quotation.json()['id']}/accept")
    assert accepted.status_code == 200, accepted.text
    contract = client.post(
        f"/api/crm/quotations/{quotation.json()['id']}/convert",
        json={"contractNumber": "KPI-SC-001", "startDate": "2026-08-01"},
    )
    assert contract.status_code == 201, contract.text
    return contract.json()


def _post_project_journal(
    client,
    *,
    company_id: str,
    project_id: str,
    debit_account_id: str,
    credit_account_id: str,
    amount: str,
    description: str,
) -> dict:
    response = client.post(
        "/api/accounting/journal-entries",
        json={
            "companyId": company_id,
            "projectId": project_id,
            "scope": "PROJECT",
            "currencyCode": "HNL",
            "description": description,
            "lines": [
                {
                    "accountId": debit_account_id,
                    "projectId": project_id,
                    "debitAmount": amount,
                },
                {
                    "accountId": credit_account_id,
                    "projectId": project_id,
                    "creditAmount": amount,
                },
            ],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_project_financial_summary_uses_real_sources_and_nets_reversals(client):
    login_admin(client)
    company = create_company(client, name="KPI Financial Sources")
    project = _create_project(
        client,
        company_id=company["id"],
        name="Proyecto KPI",
        code="KPI-001",
    )
    _create_sales_contract(client, company_id=company["id"], project_id=project["id"])

    budget = client.post(
        f"/api/projects/{project['id']}/budgets/baseline",
        json={"currencyCode": "HNL", "lines": [{"authorizedAmount": "600.00"}]},
    )
    assert budget.status_code == 201, budget.text
    progress = client.post(
        f"/api/projects/{project['id']}/progress",
        json={
            "recordDate": "2026-08-29",
            "plannedPercent": "60.00",
            "actualPercent": "50.00",
        },
    )
    assert progress.status_code == 201, progress.text

    receivable = create_account(
        client,
        company_id=company["id"],
        code="1200",
        name="Cuentas por cobrar KPI",
        account_type="ASSET",
    )
    revenue = create_account(
        client,
        company_id=company["id"],
        code="4100",
        name="Ingresos KPI",
        account_type="REVENUE",
    )
    expense = create_account(
        client,
        company_id=company["id"],
        code="5100",
        name="Costo KPI",
        account_type="EXPENSE",
    )
    payable = create_account(
        client,
        company_id=company["id"],
        code="2100",
        name="Cuentas por pagar KPI",
        account_type="LIABILITY",
    )
    _post_project_journal(
        client,
        company_id=company["id"],
        project_id=project["id"],
        debit_account_id=receivable["id"],
        credit_account_id=revenue["id"],
        amount="400.00",
        description="Ingreso reconocido KPI",
    )
    cost = _post_project_journal(
        client,
        company_id=company["id"],
        project_id=project["id"],
        debit_account_id=expense["id"],
        credit_account_id=payable["id"],
        amount="250.00",
        description="Costo real KPI",
    )

    response = client.get(f"/api/projects/{project['id']}/financial-summary")
    assert response.status_code == 200, response.text
    summary = response.json()
    assert Decimal(summary["contractValue"]) == Decimal("1000.00")
    assert Decimal(summary["baselineBudget"]) == Decimal("600.00")
    assert Decimal(summary["currentBudget"]) == Decimal("600.00")
    assert Decimal(summary["recognizedRevenue"]) == Decimal("400.00")
    assert Decimal(summary["actualCost"]) == Decimal("250.00")
    assert Decimal(summary["expectedProfit"]) == Decimal("400.00")
    assert Decimal(summary["expectedMarginPercent"]) == Decimal("40.00")
    assert Decimal(summary["actualProfit"]) == Decimal("150.00")
    assert Decimal(summary["actualMarginPercent"]) == Decimal("37.500")
    assert Decimal(summary["progressPercent"]) == Decimal("50.00")
    assert Decimal(summary["bac"]) == Decimal("600.00")
    assert Decimal(summary["pv"]) == Decimal("360.00")
    assert Decimal(summary["ev"]) == Decimal("300.00")
    assert Decimal(summary["ac"]) == Decimal("250.00")

    reversal = client.post(
        f"/api/accounting/journal-entries/{cost['id']}/reverse",
        json={"reason": "Costo imputado por error"},
    )
    assert reversal.status_code == 200, reversal.text
    after_reversal = client.get(
        f"/api/projects/{project['id']}/financial-summary"
    ).json()
    assert Decimal(after_reversal["actualCost"]) == Decimal("0")
    assert Decimal(after_reversal["actualProfit"]) == Decimal("400.00")
    assert Decimal(after_reversal["ac"]) == Decimal("0")


def test_project_financial_summary_blocks_an_unassigned_project(client, db_session):
    login_admin(client)
    company = create_company(client, name="KPI Project Isolation")
    allowed = _create_project(
        client,
        company_id=company["id"],
        name="Proyecto KPI permitido",
        code="KPI-ALLOW",
    )
    denied = _create_project(
        client,
        company_id=company["id"],
        name="Proyecto KPI restringido",
        code="KPI-DENY",
    )
    manager = create_user_with_role(
        db_session,
        email="kpi-project-scope@nexora.group",
        role_name="Project Manager",
    )
    db_session.add(UserCompanyAccess(user_id=manager.id, company_id=company["id"]))
    db_session.add(UserProjectAccess(user_id=manager.id, project_id=allowed["id"]))
    db_session.commit()

    login_as(client, email="kpi-project-scope@nexora.group")
    response = client.get(f"/api/projects/{denied['id']}/financial-summary")

    assert response.status_code == 403, response.text
    assert response.json()["error"]["code"] == "NXR-PERM-001"
