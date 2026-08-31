from datetime import date, timedelta

from tests.helpers import (
    create_account,
    create_company,
    create_supplier,
    create_treasury_account,
    login_admin,
)


def _setup(client):
    company = create_company(client)
    bank_gl = create_account(client, company_id=company["id"], code="1100", name="Bancos", account_type="ASSET")
    expense = create_account(client, company_id=company["id"], code="5200", name="Materiales", account_type="EXPENSE")
    payable = create_account(client, company_id=company["id"], code="2100", name="CxP", account_type="LIABILITY")
    contributions = create_account(client, company_id=company["id"], code="3100", name="Aportes", account_type="EQUITY")
    bank = create_treasury_account(client, company_id=company["id"], gl_account_id=bank_gl["id"])
    supplier = create_supplier(client, company_id=company["id"])
    funding = client.post(
        "/api/treasury/remittances",
        json={
            "companyId": company["id"],
            "treasuryAccountId": bank["id"],
            "counterAccountId": contributions["id"],
            "sender": "Aportante Principal",
            "currencyCode": "HNL",
            "originalAmount": "10000.00",
            "remittanceDate": "2026-01-01",
        },
    ).json()
    return company, bank, expense, payable, supplier, funding["accountingDocumentId"]


def test_inspect_reveals_source_event_and_lines_for_a_remittance(client):
    login_admin(client)
    _company, _bank, _expense, _payable, _supplier, funding_doc = _setup(client)

    response = client.get(f"/api/accounting/journal-entries/{funding_doc}/inspect")
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["balanced"] is True
    assert body["sourceEvent"]["kind"] == "REMITTANCE"
    assert body["sourceEvent"]["reference"] == "Aportante Principal"
    codes = {line["accountCode"] for line in body["lines"]}
    assert "1100" in codes and "3100" in codes
    # Nombres de cuenta, no UUID.
    assert all(line["accountName"] for line in body["lines"])
    assert body["reversedByDocumentIds"] == []


def test_inspect_links_supplier_payment_to_its_invoice(client):
    login_admin(client)
    company, bank, expense, payable, supplier, _funding = _setup(client)
    invoice = client.post(
        "/api/ap/supplier-invoices",
        json={
            "companyId": company["id"],
            "supplierId": supplier["id"],
            "invoiceNumber": "F-INSPECT-1",
            "scope": "GENERAL",
            "expenseAccountId": expense["id"],
            "payableAccountId": payable["id"],
            "currencyCode": "HNL",
            "amount": "500.00",
            "taxAmount": "0.00",
            "invoiceDate": "2026-01-10",
            "dueDate": str(date.today() + timedelta(days=30)),
        },
    ).json()
    client.post(f"/api/ap/supplier-invoices/{invoice['id']}/approve")
    payment = client.post(
        f"/api/ap/supplier-invoices/{invoice['id']}/payments",
        json={"treasuryAccountId": bank["id"], "amount": "500.00", "paymentDate": "2026-01-15"},
    ).json()

    inspected = client.get(
        f"/api/accounting/journal-entries/{payment['accountingDocumentId']}/inspect"
    ).json()
    assert inspected["sourceEvent"]["kind"] == "SUPPLIER_PAYMENT"
    assert inspected["sourceEvent"]["reference"] == "F-INSPECT-1"


def test_inspect_shows_reversal_chain(client):
    login_admin(client)
    company, _bank, _expense, _payable, _supplier, funding_doc = _setup(client)

    reversal = client.post(
        f"/api/accounting/journal-entries/{funding_doc}/reverse",
        json={"reason": "Corrección de fondeo duplicado"},
    )
    assert reversal.status_code == 200, reversal.text
    reversal_id = reversal.json()["id"]

    original = client.get(f"/api/accounting/journal-entries/{funding_doc}/inspect").json()
    assert original["reversedByDocumentIds"] == [reversal_id]
    assert original["status"] == "REVERSED"
    assert "duplicado" in (original["reversalReason"] or "")

    rev = client.get(f"/api/accounting/journal-entries/{reversal_id}/inspect").json()
    assert rev["reversesDocumentId"] == funding_doc
    assert "duplicado" in (rev["reversalReason"] or "")
