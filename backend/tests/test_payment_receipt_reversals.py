from app.models.accounting import AccountingDocument
from app.models.ap import SupplierPayment
from app.models.ar import CustomerReceipt
from tests.helpers import (
    create_account,
    create_company,
    create_customer,
    create_supplier,
    create_treasury_account,
    login_admin,
)


def _funded_ap_context(client):
    company = create_company(client)
    bank_gl = create_account(
        client, company_id=company["id"], code="1100", name="Banco reversal", account_type="ASSET"
    )
    expense = create_account(
        client, company_id=company["id"], code="5100", name="Gasto reversal", account_type="EXPENSE"
    )
    payable = create_account(
        client, company_id=company["id"], code="2100", name="CxP reversal", account_type="LIABILITY"
    )
    equity = create_account(
        client, company_id=company["id"], code="3100", name="Capital reversal", account_type="EQUITY"
    )
    bank = create_treasury_account(client, company_id=company["id"], gl_account_id=bank_gl["id"])
    supplier = create_supplier(client, company_id=company["id"])
    funded = client.post(
        "/api/treasury/remittances",
        json={
            "companyId": company["id"],
            "treasuryAccountId": bank["id"],
            "counterAccountId": equity["id"],
            "sender": "Fondeo reversal",
            "currencyCode": "HNL",
            "originalAmount": "10000.00",
            "remittanceDate": "2026-08-01",
        },
    )
    assert funded.status_code == 201, funded.text
    return company, bank, expense, payable, supplier


def test_supplier_payment_reversal_preserves_original_and_restores_invoice(client, db_session):
    login_admin(client)
    company, bank, expense, payable, supplier = _funded_ap_context(client)
    invoice = client.post(
        "/api/ap/supplier-invoices",
        json={
            "companyId": company["id"],
            "supplierId": supplier["id"],
            "invoiceNumber": "REV-AP-001",
            "scope": "GENERAL",
            "expenseAccountId": expense["id"],
            "payableAccountId": payable["id"],
            "currencyCode": "HNL",
            "amount": "1000.00",
            "invoiceDate": "2026-08-02",
            "dueDate": "2026-09-02",
        },
    ).json()
    approved = client.post(f"/api/ap/supplier-invoices/{invoice['id']}/approve")
    assert approved.status_code == 200, approved.text
    payment_response = client.post(
        f"/api/ap/supplier-invoices/{invoice['id']}/payments",
        json={"treasuryAccountId": bank["id"], "amount": "1000.00", "paymentDate": "2026-08-03"},
    )
    assert payment_response.status_code == 201, payment_response.text
    payment = payment_response.json()

    reversal = client.post(
        f"/api/ap/supplier-payments/{payment['id']}/reverse",
        json={"reason": "Pago aplicado a cuenta bancaria equivocada"},
    )
    assert reversal.status_code == 200, reversal.text
    body = reversal.json()
    assert body["originalId"] == payment["id"]
    assert body["invoiceId"] == invoice["id"]
    assert body["invoiceStatus"] == "APPROVED"
    assert float(body["appliedAmountAfterReversal"]) == 0
    assert body["reversalAccountingDocumentId"] != body["originalAccountingDocumentId"]

    refreshed = client.get(f"/api/ap/supplier-invoices/{invoice['id']}").json()
    assert refreshed["status"] == "APPROVED"
    assert float(refreshed["amountPaid"]) == 0

    persisted_payment = db_session.get(SupplierPayment, payment["id"])
    assert persisted_payment is not None
    assert persisted_payment.accounting_document_id is not None
    assert persisted_payment.reversal_accounting_document_id is not None
    assert persisted_payment.reversed_at is not None
    assert persisted_payment.reversed_by_user_id is not None
    assert persisted_payment.reversal_reason == "Pago aplicado a cuenta bancaria equivocada"
    original_document = db_session.get(AccountingDocument, persisted_payment.accounting_document_id)
    reversal_document = db_session.get(AccountingDocument, persisted_payment.reversal_accounting_document_id)
    assert original_document is not None and original_document.status == "REVERSED"
    assert reversal_document is not None and reversal_document.status == "POSTED"
    assert reversal_document.document_type_code == "ANU"

    duplicate = client.post(
        f"/api/ap/supplier-payments/{payment['id']}/reverse",
        json={"reason": "Segundo intento no permitido"},
    )
    assert duplicate.status_code == 422, duplicate.text
    unchanged = client.get(f"/api/ap/supplier-invoices/{invoice['id']}").json()
    assert float(unchanged["amountPaid"]) == 0


def test_customer_receipt_reversal_preserves_original_and_restores_invoice(client, db_session):
    login_admin(client)
    company = create_company(client)
    bank_gl = create_account(
        client, company_id=company["id"], code="1110", name="Banco AR reversal", account_type="ASSET"
    )
    receivable = create_account(
        client, company_id=company["id"], code="1210", name="CxC reversal", account_type="ASSET"
    )
    revenue = create_account(
        client, company_id=company["id"], code="4110", name="Ingreso reversal", account_type="REVENUE"
    )
    bank = create_treasury_account(client, company_id=company["id"], gl_account_id=bank_gl["id"])
    customer = create_customer(client, company_id=company["id"], legal_name="Cliente Reversal")
    invoice = client.post(
        "/api/ar/customer-invoices",
        json={
            "companyId": company["id"],
            "customerId": customer["id"],
            "invoiceNumber": "REV-AR-001",
            "scope": "GENERAL",
            "revenueAccountId": revenue["id"],
            "receivableAccountId": receivable["id"],
            "currencyCode": "HNL",
            "amount": "2500.00",
            "invoiceDate": "2026-08-02",
            "dueDate": "2026-09-02",
        },
    ).json()
    approved = client.post(f"/api/ar/customer-invoices/{invoice['id']}/approve")
    assert approved.status_code == 200, approved.text
    receipt_response = client.post(
        f"/api/ar/customer-invoices/{invoice['id']}/receipts",
        json={"treasuryAccountId": bank["id"], "amount": "2500.00", "receiptDate": "2026-08-03"},
    )
    assert receipt_response.status_code == 201, receipt_response.text
    receipt = receipt_response.json()

    reversal = client.post(
        f"/api/ar/customer-receipts/{receipt['id']}/reverse",
        json={"reason": "Cobro aplicado al cliente equivocado"},
    )
    assert reversal.status_code == 200, reversal.text
    body = reversal.json()
    assert body["originalId"] == receipt["id"]
    assert body["invoiceStatus"] == "APPROVED"
    assert float(body["appliedAmountAfterReversal"]) == 0

    refreshed = client.get(f"/api/ar/customer-invoices/{invoice['id']}").json()
    assert refreshed["status"] == "APPROVED"
    assert float(refreshed["amountCollected"]) == 0

    persisted_receipt = db_session.get(CustomerReceipt, receipt["id"])
    assert persisted_receipt is not None
    assert persisted_receipt.reversal_accounting_document_id is not None
    assert persisted_receipt.reversed_at is not None
    assert persisted_receipt.reversed_by_user_id is not None
    assert persisted_receipt.reversal_reason == "Cobro aplicado al cliente equivocado"

    duplicate = client.post(
        f"/api/ar/customer-receipts/{receipt['id']}/reverse",
        json={"reason": "Segundo intento no permitido"},
    )
    assert duplicate.status_code == 422, duplicate.text
    unchanged = client.get(f"/api/ar/customer-invoices/{invoice['id']}").json()
    assert float(unchanged["amountCollected"]) == 0
