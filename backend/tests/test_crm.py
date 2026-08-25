from sqlalchemy import select

from app.models.crm import Customer, Opportunity, SalesContract
from app.models.permission import UserCompanyAccess
from tests.helpers import create_account, create_company, create_user_with_role, login_admin, login_as


def _create_lead(client, *, company_id: str, name: str = "Constructora Prospecto") -> dict:
    response = client.post(
        "/api/crm/leads",
        json={
            "companyId": company_id,
            "name": name,
            "contactName": "Juan Perez",
            "email": "juan@prospecto.com",
            "source": "REFERRAL",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_project(client, *, company_id: str, name: str = "Torre Nexora II") -> dict:
    response = client.post(
        "/api/projects",
        json={"companyId": company_id, "name": name, "code": "PRJ-CRM-01", "currencyCode": "HNL"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _convert_lead(client, lead_id: str) -> dict:
    response = client.post(f"/api/crm/leads/{lead_id}/convert")
    assert response.status_code == 200, response.text
    return response.json()


def _create_quotation(
    client,
    *,
    company_id: str,
    opportunity_id: str,
    customer_id: str,
    project_id: str | None = None,
    quotation_number: str = "COT-001",
    amount: str = "50000.00",
) -> dict:
    payload = {
        "companyId": company_id,
        "opportunityId": opportunity_id,
        "customerId": customer_id,
        "quotationNumber": quotation_number,
        "currencyCode": "HNL",
        "amount": amount,
    }
    if project_id:
        payload["projectId"] = project_id
    response = client.post("/api/crm/quotations", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def _setup_ar_accounts(client, company_id: str) -> tuple[dict, dict]:
    revenue = create_account(
        client, company_id=company_id, code="4100", name="Ingresos por servicios", account_type="REVENUE"
    )
    receivable = create_account(
        client, company_id=company_id, code="1200", name="Cuentas por cobrar", account_type="ASSET"
    )
    return revenue, receivable


def test_converting_lead_creates_customer_exactly_once_even_if_attempted_twice(client, db_session):
    login_admin(client)
    company = create_company(client)
    lead = _create_lead(client, company_id=company["id"])

    first = client.post(f"/api/crm/leads/{lead['id']}/convert")
    assert first.status_code == 200, first.text
    second = client.post(f"/api/crm/leads/{lead['id']}/convert")
    assert second.status_code == 200, second.text

    assert first.json()["customer"]["id"] == second.json()["customer"]["id"]

    customers = list(
        db_session.execute(select(Customer).where(Customer.company_id == company["id"])).scalars()
    )
    assert len(customers) == 1

    opportunities = list(
        db_session.execute(select(Opportunity).where(Opportunity.company_id == company["id"])).scalars()
    )
    assert len(opportunities) == 1


def test_only_accepted_quotation_converts_and_conversion_preserves_amount_company_customer_project(client):
    login_admin(client)
    company = create_company(client)
    project = _create_project(client, company_id=company["id"])
    lead = _create_lead(client, company_id=company["id"])
    converted = _convert_lead(client, lead["id"])
    customer = converted["customer"]
    opportunity = converted["opportunity"]

    quotation = _create_quotation(
        client,
        company_id=company["id"],
        opportunity_id=opportunity["id"],
        customer_id=customer["id"],
        project_id=project["id"],
        amount="75000.00",
    )
    assert quotation["status"] == "DRAFT"

    convert_payload = {"contractNumber": "SC-001", "startDate": "2026-02-01"}
    rejected_attempt = client.post(
        f"/api/crm/quotations/{quotation['id']}/convert", json=convert_payload
    )
    assert rejected_attempt.status_code == 409, rejected_attempt.text
    assert rejected_attempt.json()["error"]["code"] == "NXR-CRM-001"

    accept = client.post(f"/api/crm/quotations/{quotation['id']}/accept")
    assert accept.status_code == 200, accept.text
    assert accept.json()["status"] == "ACCEPTED"

    converted_contract = client.post(
        f"/api/crm/quotations/{quotation['id']}/convert", json=convert_payload
    )
    assert converted_contract.status_code == 201, converted_contract.text
    contract = converted_contract.json()
    assert contract["quotationId"] == quotation["id"]
    assert contract["companyId"] == company["id"]
    assert contract["customerId"] == customer["id"]
    assert contract["projectId"] == project["id"]
    assert float(contract["amount"]) == 75000.00
    assert contract["status"] == "ACTIVE"


def test_billing_sales_contract_creates_exactly_one_ar_invoice_and_no_treasury_movement(client, db_session):
    login_admin(client)
    company = create_company(client)
    revenue, receivable = _setup_ar_accounts(client, company["id"])
    lead = _create_lead(client, company_id=company["id"])
    converted = _convert_lead(client, lead["id"])
    customer = converted["customer"]
    opportunity = converted["opportunity"]

    quotation = _create_quotation(
        client, company_id=company["id"], opportunity_id=opportunity["id"], customer_id=customer["id"]
    )
    client.post(f"/api/crm/quotations/{quotation['id']}/accept")
    contract = client.post(
        f"/api/crm/quotations/{quotation['id']}/convert",
        json={"contractNumber": "SC-100", "startDate": "2026-02-01"},
    ).json()

    bill = client.post(
        f"/api/crm/sales-contracts/{contract['id']}/bill",
        json={
            "invoiceNumber": "CI-CRM-001",
            "invoiceDate": "2026-02-01",
            "dueDate": "2026-03-01",
            "revenueAccountId": revenue["id"],
            "receivableAccountId": receivable["id"],
        },
    )
    assert bill.status_code == 201, bill.text
    billed_contract = bill.json()
    assert billed_contract["status"] == "BILLED"
    assert billed_contract["customerInvoiceId"]

    invoices = client.get(f"/api/ar/customer-invoices?companyId={company['id']}").json()
    assert len(invoices) == 1
    assert invoices[0]["id"] == billed_contract["customerInvoiceId"]
    assert invoices[0]["customerId"] == customer["id"]
    assert float(invoices[0]["amount"]) == 50000.00

    treasury_state = client.get(f"/api/treasury/accounts?companyId={company['id']}").json()
    assert treasury_state == []

    second_bill_attempt = client.post(
        f"/api/crm/sales-contracts/{contract['id']}/bill",
        json={
            "invoiceNumber": "CI-CRM-002",
            "invoiceDate": "2026-02-01",
            "dueDate": "2026-03-01",
            "revenueAccountId": revenue["id"],
            "receivableAccountId": receivable["id"],
        },
    )
    assert second_bill_attempt.status_code == 409, second_bill_attempt.text
    assert second_bill_attempt.json()["error"]["code"] == "NXR-CRM-001"

    invoices_after_retry = client.get(f"/api/ar/customer-invoices?companyId={company['id']}").json()
    assert len(invoices_after_retry) == 1


def test_crm_resources_from_other_company_are_denied(client, db_session):
    login_admin(client)
    company_a = create_company(client, name="Constructora A")
    company_b = create_company(client, name="Constructora B")
    lead_a = _create_lead(client, company_id=company_a["id"])

    user = create_user_with_role(db_session, email="sales-b@nexora.group", role_name="Sales Manager")
    db_session.add(UserCompanyAccess(user_id=user.id, company_id=company_b["id"]))
    db_session.commit()
    login_as(client, email="sales-b@nexora.group")

    response = client.post(f"/api/crm/leads/{lead_a['id']}/convert")
    assert response.status_code == 403, response.text
    assert response.json()["error"]["code"] == "NXR-PERM-001"

    list_response = client.get(f"/api/crm/leads?companyId={company_a['id']}")
    assert list_response.status_code == 403, list_response.text
