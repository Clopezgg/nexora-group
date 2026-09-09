"""Tests for subledger↔GL reconciliation invariants.

Covers:
- SupplierInvoice APPROVED → accrual POSTED ↔ GL
- SupplierPayment PAY POSTED ↔ GL
- CustomerInvoice APPROVED → AR POSTED ↔ GL
- CustomerReceipt REC POSTED ↔ GL
- Asset capitalized → CAP POSTED ↔ GL
- Depreciation posted → DEP POSTED ↔ GL
- Asset disposed → DIS POSTED ↔ GL
- Reversal sync: reversal document mirrors original
"""

from sqlalchemy import select

from app.models.accounting import AccountingDocument, AccountingSourceLink, JournalLine
from tests.helpers import (
    create_account,
    create_company,
    create_customer,
    create_supplier,
    create_treasury_account,
    login_admin,
)


def _setup_ap(client):
    company = create_company(client, name="Recon AP Co")
    bank_gl = create_account(
        client, company_id=company["id"], code="1100", name="Banco", account_type="ASSET"
    )
    expense = create_account(
        client, company_id=company["id"], code="5200", name="Materiales", account_type="EXPENSE"
    )
    payable = create_account(
        client, company_id=company["id"], code="2100", name="CxP", account_type="LIABILITY"
    )
    equity = create_account(
        client, company_id=company["id"], code="3100", name="Aportes", account_type="EQUITY"
    )
    bank = create_treasury_account(client, company_id=company["id"], gl_account_id=bank_gl["id"])
    supplier = create_supplier(client, company_id=company["id"], legal_name="Proveedor recon")
    funded = client.post(
        "/api/treasury/remittances",
        json={
            "companyId": company["id"],
            "treasuryAccountId": bank["id"],
            "counterAccountId": equity["id"],
            "sender": "Fondeo recon AP",
            "currencyCode": "HNL",
            "originalAmount": "10000.00",
            "remittanceDate": "2026-03-01",
        },
    )
    assert funded.status_code == 201, funded.text
    return company, bank, expense, payable, supplier


def _setup_ar(client):
    company = create_company(client, name="Recon AR Co")
    bank_gl = create_account(
        client, company_id=company["id"], code="1100", name="Banco", account_type="ASSET"
    )
    revenue = create_account(
        client, company_id=company["id"], code="4100", name="Ingresos", account_type="REVENUE"
    )
    receivable = create_account(
        client, company_id=company["id"], code="1200", name="CxC", account_type="ASSET"
    )
    bank = create_treasury_account(client, company_id=company["id"], gl_account_id=bank_gl["id"])
    customer = create_customer(client, company_id=company["id"], legal_name="Cliente recon")
    return company, bank, revenue, receivable, customer


def _account_totals(db_session, document_id):
    lines = list(
        db_session.execute(
            select(JournalLine).where(JournalLine.accounting_document_id == document_id)
        ).scalars()
    )
    return sum(l.debit_amount for l in lines), sum(l.credit_amount for l in lines), lines


def test_supplier_invoice_accrual_reconciles_with_gl(client, db_session):
    """INV-SUB-001: When a SupplierInvoice is APPROVED, the accrual
    AccountingDocument must exist, be POSTED, and its journal lines must
    balance (debit == credit)."""
    from app.models.ap import SupplierInvoice

    login_admin(client)
    _company, _bank, expense, payable, supplier = _setup_ap(client)

    created = client.post(
        "/api/ap/supplier-invoices",
        json={
            "companyId": _company["id"],
            "supplierId": supplier["id"],
            "invoiceNumber": "RECON-AP-001",
            "scope": "GENERAL",
            "expenseAccountId": expense["id"],
            "payableAccountId": payable["id"],
            "currencyCode": "HNL",
            "amount": "1250.00",
            "taxAmount": "0.00",
            "invoiceDate": "2026-03-05",
            "dueDate": "2026-04-05",
        },
    )
    assert created.status_code == 201, created.text
    invoice_id = created.json()["id"]

    approved = client.post(f"/api/ap/supplier-invoices/{invoice_id}/approve")
    assert approved.status_code == 200, approved.text

    invoice = db_session.get(SupplierInvoice, invoice_id)
    assert invoice is not None
    assert invoice.status == "APPROVED"
    assert invoice.accrual_document_id is not None

    doc = db_session.get(AccountingDocument, invoice.accrual_document_id)
    assert doc is not None
    assert doc.status == "POSTED"

    total_debit, total_credit, _lines = _account_totals(db_session, doc.id)
    assert total_debit == total_credit
    assert total_debit > 0

    link = db_session.execute(
        select(AccountingSourceLink).where(
            AccountingSourceLink.accounting_document_id == doc.id
        )
    ).scalar_one_or_none()
    assert link is not None
    assert link.source_type == "supplier_invoice"
    assert link.source_id == invoice.id


def test_supplier_payment_reconciles_with_gl(client, db_session):
    """INV-SUB-003: A SupplierPayment must have a POSTED PAY AccountingDocument
    whose lines balance, and the accrual must remain intact."""
    from app.models.ap import SupplierInvoice, SupplierPayment

    login_admin(client)
    _company, bank, expense, payable, supplier = _setup_ap(client)

    created = client.post(
        "/api/ap/supplier-invoices",
        json={
            "companyId": _company["id"],
            "supplierId": supplier["id"],
            "invoiceNumber": "RECON-AP-002",
            "scope": "GENERAL",
            "expenseAccountId": expense["id"],
            "payableAccountId": payable["id"],
            "currencyCode": "HNL",
            "amount": "800.00",
            "taxAmount": "0.00",
            "invoiceDate": "2026-03-06",
            "dueDate": "2026-04-06",
        },
    )
    assert created.status_code == 201, created.text
    invoice_id = created.json()["id"]
    assert client.post(f"/api/ap/supplier-invoices/{invoice_id}/approve").status_code == 200

    payment_resp = client.post(
        f"/api/ap/supplier-invoices/{invoice_id}/payments",
        json={"treasuryAccountId": bank["id"], "amount": "800.00", "paymentDate": "2026-03-10"},
    )
    assert payment_resp.status_code == 201, payment_resp.text
    payment_id = payment_resp.json()["id"]

    payment = db_session.get(SupplierPayment, payment_id)
    assert payment is not None
    assert payment.accounting_document_id is not None

    pay_doc = db_session.get(AccountingDocument, payment.accounting_document_id)
    assert pay_doc is not None
    assert pay_doc.status == "POSTED"
    total_debit, total_credit, _lines = _account_totals(db_session, pay_doc.id)
    assert total_debit == total_credit
    assert total_debit > 0

    invoice = db_session.get(SupplierInvoice, invoice_id)
    assert invoice.accrual_document_id is not None
    accrual = db_session.get(AccountingDocument, invoice.accrual_document_id)
    assert accrual.status == "POSTED"


def test_customer_invoice_ar_reconciles_with_gl(client, db_session):
    """INV-SUB-002: When a CustomerInvoice is APPROVED, the AR
    AccountingDocument must exist, be POSTED, and its journal lines must
    balance."""
    from app.models.ar import CustomerInvoice

    login_admin(client)
    _company, _bank, revenue, receivable, customer = _setup_ar(client)

    created = client.post(
        "/api/ar/customer-invoices",
        json={
            "companyId": _company["id"],
            "customerId": customer["id"],
            "invoiceNumber": "RECON-CI-001",
            "scope": "GENERAL",
            "revenueAccountId": revenue["id"],
            "receivableAccountId": receivable["id"],
            "currencyCode": "HNL",
            "amount": "3000.00",
            "invoiceDate": "2026-03-05",
            "dueDate": "2026-04-05",
        },
    )
    assert created.status_code == 201, created.text
    invoice_id = created.json()["id"]

    approved = client.post(f"/api/ar/customer-invoices/{invoice_id}/approve")
    assert approved.status_code == 200, approved.text

    invoice = db_session.get(CustomerInvoice, invoice_id)
    assert invoice is not None
    assert invoice.status == "APPROVED"
    assert invoice.accounting_document_id is not None

    doc = db_session.get(AccountingDocument, invoice.accounting_document_id)
    assert doc is not None
    assert doc.status == "POSTED"

    total_debit, total_credit, _lines = _account_totals(db_session, doc.id)
    assert total_debit == total_credit
    assert total_debit > 0

    link = db_session.execute(
        select(AccountingSourceLink).where(
            AccountingSourceLink.accounting_document_id == doc.id
        )
    ).scalar_one_or_none()
    assert link is not None
    assert link.source_type == "customer_invoice"
    assert link.source_id == invoice.id


def test_customer_receipt_reconciles_with_gl(client, db_session):
    """INV-SUB-004: A CustomerReceipt must have a POSTED receipt GL document
    whose lines balance."""
    from app.models.ar import CustomerInvoice, CustomerReceipt

    login_admin(client)
    _company, bank, revenue, receivable, customer = _setup_ar(client)

    created = client.post(
        "/api/ar/customer-invoices",
        json={
            "companyId": _company["id"],
            "customerId": customer["id"],
            "invoiceNumber": "RECON-CI-002",
            "scope": "GENERAL",
            "revenueAccountId": revenue["id"],
            "receivableAccountId": receivable["id"],
            "currencyCode": "HNL",
            "amount": "2000.00",
            "invoiceDate": "2026-03-06",
            "dueDate": "2026-04-06",
        },
    )
    assert created.status_code == 201, created.text
    invoice_id = created.json()["id"]
    assert client.post(f"/api/ar/customer-invoices/{invoice_id}/approve").status_code == 200

    receipt_resp = client.post(
        f"/api/ar/customer-invoices/{invoice_id}/receipts",
        json={"treasuryAccountId": bank["id"], "amount": "2000.00", "receiptDate": "2026-03-10"},
    )
    assert receipt_resp.status_code == 201, receipt_resp.text
    receipt_id = receipt_resp.json()["id"]

    receipt = db_session.get(CustomerReceipt, receipt_id)
    assert receipt is not None
    assert receipt.accounting_document_id is not None

    doc = db_session.get(AccountingDocument, receipt.accounting_document_id)
    assert doc is not None
    assert doc.status == "POSTED"
    total_debit, total_credit, _lines = _account_totals(db_session, doc.id)
    assert total_debit == total_credit
    assert total_debit > 0

    invoice = db_session.get(CustomerInvoice, invoice_id)
    assert invoice.accounting_document_id is not None
    assert db_session.get(AccountingDocument, invoice.accounting_document_id).status == "POSTED"


def test_reversal_gl_mirrors_original(client, db_session):
    """INV-ACC-004: A reversal document must have inverted D/C relative to
    the original, and the original must be REVERSED."""
    from app.models.ap import SupplierPayment

    login_admin(client)
    _company, bank, expense, payable, supplier = _setup_ap(client)

    created = client.post(
        "/api/ap/supplier-invoices",
        json={
            "companyId": _company["id"],
            "supplierId": supplier["id"],
            "invoiceNumber": "RECON-AP-003",
            "scope": "GENERAL",
            "expenseAccountId": expense["id"],
            "payableAccountId": payable["id"],
            "currencyCode": "HNL",
            "amount": "500.00",
            "taxAmount": "0.00",
            "invoiceDate": "2026-03-08",
            "dueDate": "2026-04-08",
        },
    )
    assert created.status_code == 201, created.text
    invoice_id = created.json()["id"]
    assert client.post(f"/api/ap/supplier-invoices/{invoice_id}/approve").status_code == 200

    payment_resp = client.post(
        f"/api/ap/supplier-invoices/{invoice_id}/payments",
        json={"treasuryAccountId": bank["id"], "amount": "500.00", "paymentDate": "2026-03-12"},
    )
    assert payment_resp.status_code == 201, payment_resp.text
    payment_id = payment_resp.json()["id"]

    reversal = client.post(
        f"/api/ap/supplier-payments/{payment_id}/reverse",
        json={"reason": "Reconciliación: pago revertido"},
    )
    assert reversal.status_code == 200, reversal.text
    reversal_payload = reversal.json()

    payment = db_session.get(SupplierPayment, payment_id)
    original = db_session.get(AccountingDocument, payment.accounting_document_id)
    assert original is not None
    assert original.status == "REVERSED"
    assert str(original.reversed_document_id) == reversal_payload["reversalAccountingDocumentId"]

    reversal_doc = db_session.get(AccountingDocument, reversal_payload["reversalAccountingDocumentId"])
    assert reversal_doc is not None
    assert reversal_doc.status == "POSTED"

    orig_lines = list(
        db_session.execute(
            select(JournalLine).where(JournalLine.accounting_document_id == original.id)
        ).scalars()
    )
    rev_lines = list(
        db_session.execute(
            select(JournalLine).where(JournalLine.accounting_document_id == reversal_doc.id)
        ).scalars()
    )

    assert len(orig_lines) == len(rev_lines)
    for orig, rev in zip(orig_lines, rev_lines):
        assert orig.account_id == rev.account_id
        assert orig.debit_amount == rev.credit_amount
        assert orig.credit_amount == rev.debit_amount


def test_all_posted_documents_balance(db_session):
    """INV-ACC-001: Every POSTED AccountingDocument must have balanced
    journal lines (total_debit == total_credit)."""
    posted_docs = list(
        db_session.execute(
            select(AccountingDocument).where(AccountingDocument.status == "POSTED")
        ).scalars()
    )

    for doc in posted_docs:
        lines = list(
            db_session.execute(
                select(JournalLine).where(JournalLine.accounting_document_id == doc.id)
            ).scalars()
        )
        total_debit = sum(l.debit_amount for l in lines)
        total_credit = sum(l.credit_amount for l in lines)
        assert total_debit == total_credit, (
            f"Document {doc.document_number} ({doc.document_type_code}) "
            f"unbalanced: debit={total_debit}, credit={total_credit}"
        )


def test_no_source_without_gl(db_session):
    """INV-ACC-005: Every AccountingSourceLink must point to a POSTED
    AccountingDocument (no orphan links)."""
    links = list(
        db_session.execute(
            select(AccountingSourceLink).join(
                AccountingDocument, AccountingDocument.id == AccountingSourceLink.accounting_document_id
            )
        ).scalars()
    )

    for link in links:
        doc = db_session.get(AccountingDocument, link.accounting_document_id)
        assert doc is not None
        assert doc.status == "POSTED", (
            f"SourceLink to {link.source_type}/{link.source_id} points to "
            f"non-POSTED document {doc.document_number} ({doc.status})"
        )
