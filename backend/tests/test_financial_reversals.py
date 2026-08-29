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


def _setup_ap(client):
    company = create_company(client, name="Reversal AP Co")
    bank_gl = create_account(client, company_id=company["id"], code="1100", name="Banco", account_type="ASSET")
    expense = create_account(client, company_id=company["id"], code="5100", name="Gasto", account_type="EXPENSE")
    payable = create_account(client, company_id=company["id"], code="2100", name="CxP", account_type="LIABILITY")
    equity = create_account(client, company_id=company["id"], code="3100", name="Aportes", account_type="EQUITY")
    bank = create_treasury_account(client, company_id=company["id"], gl_account_id=bank_gl["id"])
    supplier = create_supplier(client, company_id=company["id"], legal_name="Proveedor reversal")
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


def _setup_ar(client):
    company = create_company(client, name="Reversal AR Co")
    bank_gl = create_account(client, company_id=company["id"], code="1100", name="Banco", account_type="ASSET")
    revenue = create_account(client, company_id=company["id"], code="4100", name="Ingresos", account_type="REVENUE")
    receivable = create_account(client, company_id=company["id"], code="1200", name="CxC", account_type="ASSET")
    bank = create_treasury_account(client, company_id=company["id"], gl_account_id=bank_gl["id"])
    customer = create_customer(client, company_id=company["id"], legal_name="Cliente reversal")
    return company, bank, revenue, receivable, customer


def test_supplier_payment_reversal_preserves_original_and_metadata(client, db_session):
    login_admin(client)
    company, bank, expense, payable, supplier = _setup_ap(client)
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
            "dueDate": "2026-08-30",
        },
    )
    assert invoice.status_code == 201, invoice.text
    invoice = invoice.json()
    assert client.post(f"/api/ap/supplier-invoices/{invoice['id']}/approve").status_code == 200
    payment_response = client.post(
        f"/api/ap/supplier-invoices/{invoice['id']}/payments",
        json={"treasuryAccountId": bank["id"], "amount": "1000.00", "paymentDate": "2026-08-03"},
    )
    assert payment_response.status_code == 201, payment_response.text
    payment = payment_response.json()

    reversal = client.post(
        f"/api/ap/supplier-payments/{payment['id']}/reverse",
        json={"reason": "Pago aplicado a cuenta equivocada"},
    )
    assert reversal.status_code == 200, reversal.text
    reversal_payload = reversal.json()
    assert reversal_payload["originalId"] == payment["id"]
    assert reversal_payload["invoiceStatus"] == "APPROVED"
    assert float(reversal_payload["appliedAmountAfterReversal"]) == 0.0

    stored_payment = db_session.get(SupplierPayment, payment["id"])
    assert stored_payment is not None
    assert stored_payment.reversal_accounting_document_id is not None
    assert stored_payment.reversed_at is not None
    assert stored_payment.reversed_by_user_id is not None
    assert stored_payment.reversal_reason == "Pago aplicado a cuenta equivocada"
    assert str(stored_payment.reversal_accounting_document_id) == reversal_payload["reversalAccountingDocumentId"]

    original_document = db_session.get(AccountingDocument, payment["accountingDocumentId"])
    assert original_document is not None
    assert original_document.status == "REVERSED"
    assert str(original_document.reversed_document_id) == reversal_payload["reversalAccountingDocumentId"]

    listed = client.get(f"/api/ap/supplier-invoices/{invoice['id']}/payments")
    assert listed.status_code == 200, listed.text
    rows = listed.json()
    assert len(rows) == 1
    assert rows[0]["id"] == payment["id"]
    assert rows[0]["reversalAccountingDocumentId"] == reversal_payload["reversalAccountingDocumentId"]
    assert rows[0]["reversedAt"] is not None
    assert rows[0]["reversedByUserId"] is not None
    assert rows[0]["reversalReason"] == "Pago aplicado a cuenta equivocada"

    invoice_after = client.get(f"/api/ap/supplier-invoices/{invoice['id']}").json()
    assert invoice_after["status"] == "APPROVED"
    assert float(invoice_after["amountPaid"]) == 0.0
    assert db_session.query(SupplierPayment).count() == 1

    second = client.post(
        f"/api/ap/supplier-payments/{payment['id']}/reverse",
        json={"reason": "Segundo intento no permitido"},
    )
    assert second.status_code == 422, second.text


def test_customer_receipt_reversal_preserves_original_and_metadata(client, db_session):
    login_admin(client)
    company, bank, revenue, receivable, customer = _setup_ar(client)
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
            "amount": "1500.00",
            "invoiceDate": "2026-08-02",
            "dueDate": "2026-08-30",
        },
    )
    assert invoice.status_code == 201, invoice.text
    invoice = invoice.json()
    assert client.post(f"/api/ar/customer-invoices/{invoice['id']}/approve").status_code == 200
    receipt_response = client.post(
        f"/api/ar/customer-invoices/{invoice['id']}/receipts",
        json={"treasuryAccountId": bank["id"], "amount": "1500.00", "receiptDate": "2026-08-03"},
    )
    assert receipt_response.status_code == 201, receipt_response.text
    receipt = receipt_response.json()

    reversal = client.post(
        f"/api/ar/customer-receipts/{receipt['id']}/reverse",
        json={"reason": "Cobro aplicado al cliente incorrecto"},
    )
    assert reversal.status_code == 200, reversal.text
    reversal_payload = reversal.json()
    assert reversal_payload["originalId"] == receipt["id"]
    assert reversal_payload["invoiceStatus"] == "APPROVED"
    assert float(reversal_payload["appliedAmountAfterReversal"]) == 0.0

    stored_receipt = db_session.get(CustomerReceipt, receipt["id"])
    assert stored_receipt is not None
    assert stored_receipt.reversal_accounting_document_id is not None
    assert stored_receipt.reversed_at is not None
    assert stored_receipt.reversed_by_user_id is not None
    assert stored_receipt.reversal_reason == "Cobro aplicado al cliente incorrecto"
    assert str(stored_receipt.reversal_accounting_document_id) == reversal_payload["reversalAccountingDocumentId"]

    original_document = db_session.get(AccountingDocument, receipt["accountingDocumentId"])
    assert original_document is not None
    assert original_document.status == "REVERSED"
    assert str(original_document.reversed_document_id) == reversal_payload["reversalAccountingDocumentId"]

    listed = client.get(f"/api/ar/customer-invoices/{invoice['id']}/receipts")
    assert listed.status_code == 200, listed.text
    rows = listed.json()
    assert len(rows) == 1
    assert rows[0]["id"] == receipt["id"]
    assert rows[0]["reversalAccountingDocumentId"] == reversal_payload["reversalAccountingDocumentId"]
    assert rows[0]["reversedAt"] is not None
    assert rows[0]["reversedByUserId"] is not None
    assert rows[0]["reversalReason"] == "Cobro aplicado al cliente incorrecto"

    invoice_after = client.get(f"/api/ar/customer-invoices/{invoice['id']}").json()
    assert invoice_after["status"] == "APPROVED"
    assert float(invoice_after["amountCollected"]) == 0.0
    assert db_session.query(CustomerReceipt).count() == 1

    second = client.post(
        f"/api/ar/customer-receipts/{receipt['id']}/reverse",
        json={"reason": "Segundo intento no permitido"},
    )
    assert second.status_code == 422, second.text
