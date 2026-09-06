from datetime import date, timedelta
from decimal import Decimal

from tests.helpers import (
    create_account,
    create_company,
    create_supplier,
    create_treasury_account,
    login_admin,
)


def _ap_setup(client):
    company = create_company(client)
    bank_gl = create_account(client, company_id=company["id"], code="1100", name="Bancos", account_type="ASSET")
    expense = create_account(client, company_id=company["id"], code="5200", name="Mat", account_type="EXPENSE")
    payable = create_account(client, company_id=company["id"], code="2100", name="CxP", account_type="LIABILITY")
    contributions = create_account(client, company_id=company["id"], code="3100", name="Aportes", account_type="EQUITY")
    bank = create_treasury_account(client, company_id=company["id"], gl_account_id=bank_gl["id"])
    supplier = create_supplier(client, company_id=company["id"], legal_name="Ferretería Norte")
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
    return company, expense, payable, supplier


def test_ap_payment_proposal_lists_due_and_overdue_invoices(client):
    login_admin(client)
    company, expense, payable, supplier = _ap_setup(client)

    def _invoice(number, days):
        inv = client.post(
            "/api/ap/supplier-invoices",
            json={
                "companyId": company["id"],
                "supplierId": supplier["id"],
                "invoiceNumber": number,
                "scope": "GENERAL",
                "expenseAccountId": expense["id"],
                "payableAccountId": payable["id"],
                "currencyCode": "HNL",
                "amount": "300.00",
                "taxAmount": "0.00",
                "invoiceDate": str(date.today()),
                "dueDate": str(date.today() + timedelta(days=days)),
            },
        ).json()
        client.post(f"/api/ap/supplier-invoices/{inv['id']}/approve")
        return inv

    _invoice("PP-OVERDUE", -5)   # vencida
    _invoice("PP-SOON", 7)       # dentro del horizonte
    _invoice("PP-LATER", 60)     # fuera del horizonte de 14 días

    body = client.get(f"/api/ap/payment-proposal?companyId={company['id']}&horizonDays=14").json()
    numbers = [i["invoiceNumber"] for i in body["items"]]
    assert "PP-OVERDUE" in numbers and "PP-SOON" in numbers
    assert "PP-LATER" not in numbers
    # Vencida primero.
    assert body["items"][0]["invoiceNumber"] == "PP-OVERDUE"
    assert body["items"][0]["overdue"] is True
    assert body["items"][0]["supplierName"] == "Ferretería Norte"
    assert Decimal(body["total"]) == Decimal("600.00")


def test_ap_aging_metrics_computes_aging_buckets(client):
    """ORDEN MAESTRA DE CIERRE FINAL DE PRODUCTO §19: no existía AP Aging
    (ar_metrics ya existía, su equivalente AP no)."""
    login_admin(client)
    company, expense, payable, supplier = _ap_setup(client)

    def _invoice(number, days, amount="1200.00"):
        inv = client.post(
            "/api/ap/supplier-invoices",
            json={
                "companyId": company["id"],
                "supplierId": supplier["id"],
                "invoiceNumber": number,
                "scope": "GENERAL",
                "expenseAccountId": expense["id"],
                "payableAccountId": payable["id"],
                "currencyCode": "HNL",
                "amount": amount,
                "taxAmount": "0.00",
                "invoiceDate": str(date.today()),
                "dueDate": str(date.today() + timedelta(days=days)),
            },
        ).json()
        client.post(f"/api/ap/supplier-invoices/{inv['id']}/approve")
        return inv

    _invoice("AGE-CURRENT", 5, amount="500.00")
    _invoice("AGE-1-30", -10, amount="700.00")
    _invoice("AGE-61-90", -75, amount="900.00")

    body = client.get(f"/api/financial-control/ap-metrics?companyId={company['id']}").json()
    assert Decimal(body["apOutstanding"]) == Decimal("2100.00")
    assert Decimal(body["aging"]["current"]) == Decimal("500.00")
    assert Decimal(body["aging"]["1_30"]) == Decimal("700.00")
    assert Decimal(body["aging"]["61_90"]) == Decimal("900.00")
    assert Decimal(body["aging"]["31_60"]) == Decimal("0")
    assert Decimal(body["aging"]["over_90"]) == Decimal("0")


def test_ar_dso_metrics_computes_dso_and_aging(client):
    login_admin(client)
    company = create_company(client)
    receivable = create_account(client, company_id=company["id"], code="1200", name="CxC", account_type="ASSET")
    revenue = create_account(client, company_id=company["id"], code="4100", name="Ingresos", account_type="REVENUE")
    from tests.helpers import create_user_with_role  # noqa: F401

    # Cliente.
    customer = client.post(
        "/api/crm/customers",
        json={"companyId": company["id"], "legalName": "Cliente DSO"},
    ).json()

    inv = client.post(
        "/api/ar/customer-invoices",
        json={
            "companyId": company["id"],
            "customerId": customer["id"],
            "invoiceNumber": "AR-DSO-1",
            "scope": "GENERAL",
            "revenueAccountId": revenue["id"],
            "receivableAccountId": receivable["id"],
            "currencyCode": "HNL",
            "amount": "9000.00",
            "invoiceDate": str(date.today() - timedelta(days=10)),
            "dueDate": str(date.today() - timedelta(days=3)),
        },
    )
    assert inv.status_code == 201, inv.text
    client.post(f"/api/ar/customer-invoices/{inv.json()['id']}/approve")

    body = client.get(f"/api/financial-control/ar-metrics?companyId={company['id']}").json()
    assert Decimal(body["arOutstanding"]) == Decimal("9000.00")
    assert Decimal(body["trailingCreditSales90d"]) == Decimal("9000.00")
    # DSO = 9000 / 9000 * 90 = 90.0
    assert Decimal(body["dso"]) == Decimal("90.0")
    # Vencida hace 3 días -> bucket 1_30.
    assert Decimal(body["aging"]["1_30"]) == Decimal("9000.00")
    assert Decimal(body["aging"]["current"]) == Decimal("0")
