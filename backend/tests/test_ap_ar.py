import uuid
from decimal import Decimal

from app.models.accounting import AccountingDocument
from app.models.ap import SupplierPayment
from app.models.ar import CustomerReceipt
from app.models.permission import UserCompanyAccess
from app.models.cost_center import CostCenter
from app.models.project import Project
from tests.helpers import (
    create_account,
    create_company,
    create_customer,
    create_supplier,
    create_treasury_account,
    create_user_with_role,
    login_admin,
    login_as,
)


def _setup_ap(client):
    company = create_company(client)
    bank_gl = create_account(client, company_id=company["id"], code="1100", name="Bancos", account_type="ASSET")
    expense = create_account(
        client, company_id=company["id"], code="5200", name="Materiales", account_type="EXPENSE"
    )
    payable = create_account(
        client, company_id=company["id"], code="2100", name="Cuentas por pagar", account_type="LIABILITY"
    )
    contributions = create_account(
        client, company_id=company["id"], code="3100", name="Aportes", account_type="EQUITY"
    )
    bank = create_treasury_account(client, company_id=company["id"], gl_account_id=bank_gl["id"])
    supplier = create_supplier(client, company_id=company["id"])
    client.post(
        "/api/treasury/remittances",
        json={
            "companyId": company["id"],
            "treasuryAccountId": bank["id"],
            "counterAccountId": contributions["id"],
            "sender": "Fondeo inicial",
            "currencyCode": "HNL",
            "originalAmount": "100000.00",
            "remittanceDate": "2026-01-01",
        },
    )
    return company, bank, expense, payable, supplier


def test_supplier_invoice_full_lifecycle_draft_to_paid(client):
    """Orden maestra §34: DRAFT -> APPROVED -> PARTIALLY_PAID -> PAID."""
    login_admin(client)
    company, bank, expense, payable, supplier = _setup_ap(client)

    created = client.post(
        "/api/ap/supplier-invoices",
        json={
            "companyId": company["id"],
            "supplierId": supplier["id"],
            "invoiceNumber": "F-001",
            "scope": "GENERAL",
            "expenseAccountId": expense["id"],
            "payableAccountId": payable["id"],
            "currencyCode": "HNL",
            "amount": "1000.00",
            "taxAmount": "150.00",
            "invoiceDate": "2026-01-10",
            "dueDate": "2026-02-10",
        },
    )
    assert created.status_code == 201, created.text
    invoice = created.json()
    assert invoice["status"] == "DRAFT"
    assert invoice["supplierId"] == supplier["id"]

    approved = client.post(f"/api/ap/supplier-invoices/{invoice['id']}/approve")
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "APPROVED"
    assert approved.json()["accrualDocumentId"]

    partial_payment = client.post(
        f"/api/ap/supplier-invoices/{invoice['id']}/payments",
        json={"treasuryAccountId": bank["id"], "amount": "600.00", "paymentDate": "2026-01-20"},
    )
    assert partial_payment.status_code == 201, partial_payment.text

    after_partial = client.get(f"/api/ap/supplier-invoices/{invoice['id']}").json()
    assert after_partial["status"] == "PARTIALLY_PAID"
    assert float(after_partial["amountPaid"]) == 600.0

    final_payment = client.post(
        f"/api/ap/supplier-invoices/{invoice['id']}/payments",
        json={"treasuryAccountId": bank["id"], "amount": "550.00", "paymentDate": "2026-01-25"},
    )
    assert final_payment.status_code == 201, final_payment.text

    after_full = client.get(f"/api/ap/supplier-invoices/{invoice['id']}").json()
    assert after_full["status"] == "PAID"
    assert float(after_full["amountPaid"]) == 1150.0

    bank_state = next(
        a for a in client.get(f"/api/treasury/accounts?companyId={company['id']}").json()
        if a["id"] == bank["id"]
    )
    assert float(bank_state["balance"]) == 100000.0 - 1150.0


def test_supplier_payment_exceeding_balance_is_rejected(client):
    """Orden maestra §34: nunca se debe poder sobrepagar una factura."""
    login_admin(client)
    company, bank, expense, payable, supplier = _setup_ap(client)
    invoice = client.post(
        "/api/ap/supplier-invoices",
        json={
            "companyId": company["id"],
            "supplierId": supplier["id"],
            "invoiceNumber": "F-002",
            "scope": "GENERAL",
            "expenseAccountId": expense["id"],
            "payableAccountId": payable["id"],
            "currencyCode": "HNL",
            "amount": "200.00",
            "invoiceDate": "2026-01-10",
            "dueDate": "2026-02-10",
        },
    ).json()
    client.post(f"/api/ap/supplier-invoices/{invoice['id']}/approve")

    response = client.post(
        f"/api/ap/supplier-invoices/{invoice['id']}/payments",
        json={"treasuryAccountId": bank["id"], "amount": "999.00", "paymentDate": "2026-01-20"},
    )
    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "NXR-AP-002"


def test_customer_invoice_lifecycle_draft_to_collected(client):
    """Orden maestra §36."""
    login_admin(client)
    company = create_company(client)
    bank_gl = create_account(client, company_id=company["id"], code="1100", name="Bancos", account_type="ASSET")
    revenue = create_account(
        client, company_id=company["id"], code="4100", name="Ingresos por servicios", account_type="REVENUE"
    )
    receivable = create_account(
        client, company_id=company["id"], code="1200", name="Cuentas por cobrar", account_type="ASSET"
    )
    bank = create_treasury_account(client, company_id=company["id"], gl_account_id=bank_gl["id"])
    customer = create_customer(client, company_id=company["id"], legal_name="Inversiones ABC")

    invoice = client.post(
        "/api/ar/customer-invoices",
        json={
            "companyId": company["id"],
            "customerId": customer["id"],
            "invoiceNumber": "CI-001",
            "scope": "GENERAL",
            "revenueAccountId": revenue["id"],
            "receivableAccountId": receivable["id"],
            "currencyCode": "HNL",
            "amount": "3000.00",
            "invoiceDate": "2026-01-05",
            "dueDate": "2026-02-05",
        },
    ).json()

    approved = client.post(f"/api/ar/customer-invoices/{invoice['id']}/approve")
    assert approved.status_code == 200, approved.text

    receipt = client.post(
        f"/api/ar/customer-invoices/{invoice['id']}/receipts",
        json={"treasuryAccountId": bank["id"], "amount": "3000.00", "receiptDate": "2026-01-15"},
    )
    assert receipt.status_code == 201, receipt.text

    final = client.get(f"/api/ar/customer-invoices/{invoice['id']}").json()
    assert final["status"] == "COLLECTED"

    bank_state = next(
        a for a in client.get(f"/api/treasury/accounts?companyId={company['id']}").json()
        if a["id"] == bank["id"]
    )
    assert float(bank_state["balance"]) == 3000.0


def test_ap_resource_from_other_company_is_denied(client, db_session):
    login_admin(client)
    company_a, _bank, expense, payable, supplier = _setup_ap(client)
    company_b = create_company(client, name="Constructora B")
    invoice = client.post(
        "/api/ap/supplier-invoices",
        json={
            "companyId": company_a["id"],
            "supplierId": supplier["id"],
            "invoiceNumber": "A-SEC-1",
            "scope": "GENERAL",
            "expenseAccountId": expense["id"],
            "payableAccountId": payable["id"],
            "currencyCode": "HNL",
            "amount": "100.00",
            "invoiceDate": "2026-01-10",
            "dueDate": "2026-02-10",
        },
    ).json()

    user = create_user_with_role(
        db_session, email="finance-b@nexora.group", role_name="Finance Manager"
    )
    db_session.add(UserCompanyAccess(user_id=user.id, company_id=company_b["id"]))
    db_session.commit()
    login_as(client, email="finance-b@nexora.group")

    response = client.post(f"/api/ap/supplier-invoices/{invoice['id']}/approve")

    assert response.status_code == 403, response.text
    assert response.json()["error"]["code"] == "NXR-PERM-001"


def test_payment_account_company_must_match_invoice_company(client, db_session):
    login_admin(client)
    company_a, _bank_a, expense, payable, supplier = _setup_ap(client)
    company_b = create_company(client, name="Constructora con banco ajeno")
    bank_gl_b = create_account(
        client,
        company_id=company_b["id"],
        code="1100",
        name="Banco B",
        account_type="ASSET",
    )
    bank_b = create_treasury_account(
        client, company_id=company_b["id"], gl_account_id=bank_gl_b["id"]
    )
    invoice = client.post(
        "/api/ap/supplier-invoices",
        json={
            "companyId": company_a["id"],
            "supplierId": supplier["id"],
            "invoiceNumber": "A-COMP-1",
            "scope": "GENERAL",
            "expenseAccountId": expense["id"],
            "payableAccountId": payable["id"],
            "currencyCode": "HNL",
            "amount": "100.00",
            "invoiceDate": "2026-01-10",
            "dueDate": "2026-02-10",
        },
    ).json()
    client.post(f"/api/ap/supplier-invoices/{invoice['id']}/approve")
    documents_before = db_session.query(AccountingDocument).count()

    response = client.post(
        f"/api/ap/supplier-invoices/{invoice['id']}/payments",
        json={
            "treasuryAccountId": bank_b["id"],
            "amount": "100.00",
            "paymentDate": "2026-01-20",
        },
    )

    assert response.status_code == 422, response.text
    assert db_session.query(AccountingDocument).count() == documents_before
    assert db_session.query(SupplierPayment).count() == 0


def test_zero_and_negative_invoice_amounts_are_rejected_by_api(client):
    login_admin(client)
    company, _bank, expense, payable, supplier = _setup_ap(client)
    for index, amount in enumerate(("0", "-1"), start=1):
        response = client.post(
            "/api/ap/supplier-invoices",
            json={
                "companyId": company["id"],
                "supplierId": supplier["id"],
                "invoiceNumber": f"BAD-{index}",
                "scope": "GENERAL",
                "expenseAccountId": expense["id"],
                "payableAccountId": payable["id"],
                "currencyCode": "HNL",
                "amount": amount,
                "invoiceDate": "2026-01-10",
                "dueDate": "2026-02-10",
            },
        )
        assert response.status_code == 422, response.text


def test_supplier_and_customer_invoices_can_be_listed_from_database(client):
    login_admin(client)
    company, _bank, expense, payable, supplier = _setup_ap(client)
    revenue = create_account(
        client,
        company_id=company["id"],
        code="4100",
        name="Ingresos",
        account_type="REVENUE",
    )
    receivable = create_account(
        client,
        company_id=company["id"],
        code="1200",
        name="Cuentas por cobrar",
        account_type="ASSET",
    )
    supplier_invoice = client.post(
        "/api/ap/supplier-invoices",
        json={
            "companyId": company["id"],
            "supplierId": supplier["id"],
            "invoiceNumber": "PERSIST-AP",
            "scope": "GENERAL",
            "expenseAccountId": expense["id"],
            "payableAccountId": payable["id"],
            "currencyCode": "HNL",
            "amount": "10.00",
            "invoiceDate": "2026-01-10",
            "dueDate": "2026-02-10",
        },
    ).json()
    customer = create_customer(client, company_id=company["id"], legal_name="Cliente persistido")
    customer_invoice = client.post(
        "/api/ar/customer-invoices",
        json={
            "companyId": company["id"],
            "customerId": customer["id"],
            "invoiceNumber": "PERSIST-AR",
            "scope": "GENERAL",
            "revenueAccountId": revenue["id"],
            "receivableAccountId": receivable["id"],
            "currencyCode": "HNL",
            "amount": "20.00",
            "invoiceDate": "2026-01-10",
            "dueDate": "2026-02-10",
        },
    ).json()

    supplier_list = client.get(
        f"/api/ap/supplier-invoices?companyId={company['id']}"
    )
    customer_list = client.get(
        f"/api/ar/customer-invoices?companyId={company['id']}"
    )

    assert supplier_list.status_code == 200, supplier_list.text
    assert customer_list.status_code == 200, customer_list.text
    assert supplier_invoice["id"] in {item["id"] for item in supplier_list.json()}
    assert customer_invoice["id"] in {item["id"] for item in customer_list.json()}


def test_retrying_payment_with_same_idempotency_key_does_not_duplicate_posting(
    client, db_session
):
    login_admin(client)
    company, bank, expense, payable, supplier = _setup_ap(client)
    invoice = client.post(
        "/api/ap/supplier-invoices",
        json={
            "companyId": company["id"],
            "supplierId": supplier["id"],
            "invoiceNumber": "IDEM-PAY",
            "scope": "GENERAL",
            "expenseAccountId": expense["id"],
            "payableAccountId": payable["id"],
            "currencyCode": "HNL",
            "amount": "100.00",
            "invoiceDate": "2026-01-10",
            "dueDate": "2026-02-10",
        },
    ).json()
    client.post(f"/api/ap/supplier-invoices/{invoice['id']}/approve")
    payload = {
        "treasuryAccountId": bank["id"],
        "amount": "100.00",
        "paymentDate": "2026-01-20",
    }
    documents_before = db_session.query(AccountingDocument).count()

    first = client.post(
        f"/api/ap/supplier-invoices/{invoice['id']}/payments",
        json=payload,
        headers={"Idempotency-Key": "payment-retry-1"},
    )
    second = client.post(
        f"/api/ap/supplier-invoices/{invoice['id']}/payments",
        json=payload,
        headers={"Idempotency-Key": "payment-retry-1"},
    )

    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text
    assert first.json()["id"] == second.json()["id"]
    assert db_session.query(SupplierPayment).count() == 1
    assert db_session.query(AccountingDocument).count() == documents_before + 1


def test_retrying_receipt_with_same_idempotency_key_does_not_duplicate_posting(
    client, db_session
):
    login_admin(client)
    company = create_company(client)
    bank_gl = create_account(
        client, company_id=company["id"], code="1100", name="Banco", account_type="ASSET"
    )
    revenue = create_account(
        client, company_id=company["id"], code="4100", name="Ingresos", account_type="REVENUE"
    )
    receivable = create_account(
        client, company_id=company["id"], code="1200", name="CxC", account_type="ASSET"
    )
    bank = create_treasury_account(
        client, company_id=company["id"], gl_account_id=bank_gl["id"]
    )
    customer = create_customer(client, company_id=company["id"], legal_name="Cliente idempotente")
    invoice = client.post(
        "/api/ar/customer-invoices",
        json={
            "companyId": company["id"],
            "customerId": customer["id"],
            "invoiceNumber": "IDEM-REC",
            "scope": "GENERAL",
            "revenueAccountId": revenue["id"],
            "receivableAccountId": receivable["id"],
            "currencyCode": "HNL",
            "amount": "100.00",
            "invoiceDate": "2026-01-10",
            "dueDate": "2026-02-10",
        },
    ).json()
    client.post(f"/api/ar/customer-invoices/{invoice['id']}/approve")
    payload = {
        "treasuryAccountId": bank["id"],
        "amount": "100.00",
        "receiptDate": "2026-01-20",
    }
    documents_before = db_session.query(AccountingDocument).count()

    first = client.post(
        f"/api/ar/customer-invoices/{invoice['id']}/receipts",
        json=payload,
        headers={"Idempotency-Key": "receipt-retry-1"},
    )
    second = client.post(
        f"/api/ar/customer-invoices/{invoice['id']}/receipts",
        json=payload,
        headers={"Idempotency-Key": "receipt-retry-1"},
    )

    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text
    assert first.json()["id"] == second.json()["id"]
    assert db_session.query(CustomerReceipt).count() == 1
    assert db_session.query(AccountingDocument).count() == documents_before + 1


def test_supplier_invoice_project_and_cost_center_must_match_company(client, db_session):
    login_admin(client)
    company_a, _bank, expense, payable, supplier = _setup_ap(client)
    company_b = create_company(client, name="Compañía de dimensiones ajenas")
    project_b = Project(company_id=company_b["id"], name="Proyecto B")
    cost_center_b = CostCenter(company_id=company_b["id"], code="CC-B", name="Centro B")
    db_session.add_all([project_b, cost_center_b])
    db_session.commit()

    response = client.post(
        "/api/ap/supplier-invoices",
        json={
            "companyId": company_a["id"],
            "supplierId": supplier["id"],
            "invoiceNumber": "DIM-1",
            "scope": "PROJECT",
            "projectId": str(project_b.id),
            "costCenterId": str(cost_center_b.id),
            "expenseAccountId": expense["id"],
            "payableAccountId": payable["id"],
            "currencyCode": "HNL",
            "amount": "100.00",
            "invoiceDate": "2026-01-10",
            "dueDate": "2026-02-10",
        },
    )

    assert response.status_code == 422, response.text


def test_supplier_invoice_rejects_supplier_from_other_company(client):
    """Track A+C integration: `supplier_id` es una FK real a `Supplier`
    (Track C) -- debe validarse contra la company propietaria igual que
    cualquier otra FK financiera (INV-COMP-001)."""
    login_admin(client)
    company_a, _bank, expense, payable, _supplier_a = _setup_ap(client)
    company_b = create_company(client, name="Compañía de proveedor ajeno")
    supplier_b = create_supplier(client, company_id=company_b["id"], legal_name="Proveedor B")

    response = client.post(
        "/api/ap/supplier-invoices",
        json={
            "companyId": company_a["id"],
            "supplierId": supplier_b["id"],
            "invoiceNumber": "SUP-DIM-1",
            "scope": "GENERAL",
            "expenseAccountId": expense["id"],
            "payableAccountId": payable["id"],
            "currencyCode": "HNL",
            "amount": "100.00",
            "invoiceDate": "2026-01-10",
            "dueDate": "2026-02-10",
        },
    )

    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "NXR-FINANCIAL-001"


def test_approving_supplier_invoice_creates_audit_log_entry(client, db_session):
    login_admin(client)
    company, _bank, expense, payable, supplier = _setup_ap(client)
    invoice = client.post(
        "/api/ap/supplier-invoices",
        json={
            "companyId": company["id"],
            "supplierId": supplier["id"],
            "invoiceNumber": "A-AUD-1",
            "scope": "GENERAL",
            "expenseAccountId": expense["id"],
            "payableAccountId": payable["id"],
            "currencyCode": "HNL",
            "amount": "100.00",
            "invoiceDate": "2026-01-10",
            "dueDate": "2026-02-10",
        },
    ).json()

    client.post(f"/api/ap/supplier-invoices/{invoice['id']}/approve")

    from app.models.audit import AuditLog
    from sqlalchemy import select

    rows = db_session.execute(
        select(AuditLog).where(
            AuditLog.entity_type == "ap.supplier_invoice",
            AuditLog.entity_id == uuid.UUID(invoice["id"]),
        )
    ).scalars().all()
    assert len(rows) == 1
    assert rows[0].action == "ap.supplier_invoice.approve"
    assert rows[0].after["status"] == "APPROVED"


def test_paying_supplier_invoice_creates_audit_log_entry(client, db_session):
    login_admin(client)
    company, bank, expense, payable, supplier = _setup_ap(client)
    invoice = client.post(
        "/api/ap/supplier-invoices",
        json={
            "companyId": company["id"],
            "supplierId": supplier["id"],
            "invoiceNumber": "A-AUD-2",
            "scope": "GENERAL",
            "expenseAccountId": expense["id"],
            "payableAccountId": payable["id"],
            "currencyCode": "HNL",
            "amount": "100.00",
            "invoiceDate": "2026-01-10",
            "dueDate": "2026-02-10",
        },
    ).json()
    client.post(f"/api/ap/supplier-invoices/{invoice['id']}/approve")

    payment = client.post(
        f"/api/ap/supplier-invoices/{invoice['id']}/payments",
        json={"treasuryAccountId": bank["id"], "amount": "100.00", "paymentDate": "2026-01-20"},
    ).json()

    from app.models.audit import AuditLog
    from sqlalchemy import select

    rows = db_session.execute(
        select(AuditLog).where(
            AuditLog.entity_type == "ap.supplier_payment",
            AuditLog.entity_id == uuid.UUID(payment["id"]),
        )
    ).scalars().all()
    assert len(rows) == 1
    assert rows[0].action == "ap.supplier_payment.create"
    assert rows[0].after["amount"] == "100.00"


def _create_draft_invoice(client, *, company_id: str, expense_id: str, payable_id: str, supplier_id: str, number: str) -> dict:
    response = client.post(
        "/api/ap/supplier-invoices",
        json={
            "companyId": company_id,
            "supplierId": supplier_id,
            "invoiceNumber": number,
            "scope": "GENERAL",
            "expenseAccountId": expense_id,
            "payableAccountId": payable_id,
            "currencyCode": "HNL",
            "amount": "500.00",
            "invoiceDate": "2026-01-10",
            "dueDate": "2026-02-10",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_finance_manager(db_session, *, company_id: str, email: str):
    user = create_user_with_role(db_session, email=email, role_name="Finance Manager")
    db_session.add(UserCompanyAccess(user_id=user.id, company_id=company_id))
    db_session.commit()
    return user


def test_submitting_supplier_invoice_creates_a_real_approval_request(client, db_session):
    """DEFERRED-FINAL-016: `approval_service.create_request` must have a
    real production caller -- submitting an AP invoice for approval is
    that caller. This moves the invoice DRAFT -> REVIEW and the resulting
    ApprovalRequest must show up in the assigned approver's real inbox."""
    login_admin(client)
    company, _bank, expense, payable, supplier = _setup_ap(client)
    approver = _create_finance_manager(db_session, company_id=company["id"], email="approver-1@nexora.group")
    invoice = _create_draft_invoice(
        client, company_id=company["id"], expense_id=expense["id"], payable_id=payable["id"],
        supplier_id=supplier["id"], number="SUB-001",
    )

    response = client.post(
        f"/api/ap/supplier-invoices/{invoice['id']}/submit-for-approval",
        json={"assignedTo": str(approver.id)},
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "REVIEW"

    login_as(client, email="approver-1@nexora.group")
    inbox = client.get(f"/api/approvals?companyId={company['id']}")
    assert inbox.status_code == 200, inbox.text
    entries = [row for row in inbox.json() if row["entityId"] == invoice["id"]]
    assert len(entries) == 1
    assert entries[0]["entityType"] == "ap.supplier_invoice"
    assert entries[0]["module"] == "ap"
    assert entries[0]["status"] == "PENDING"
    assert Decimal(entries[0]["amount"]) == Decimal("500.00")


def test_deciding_the_approval_request_approves_the_invoice_via_the_real_adapter(client, db_session):
    """Exercises the previously-dead `ap_service.apply_approval_decision`
    adapter for real: the decision made through the Approval Inbox must
    actually post the accrual and move the invoice to APPROVED."""
    login_admin(client)
    company, _bank, expense, payable, supplier = _setup_ap(client)
    approver = _create_finance_manager(db_session, company_id=company["id"], email="approver-2@nexora.group")
    invoice = _create_draft_invoice(
        client, company_id=company["id"], expense_id=expense["id"], payable_id=payable["id"],
        supplier_id=supplier["id"], number="SUB-002",
    )
    client.post(
        f"/api/ap/supplier-invoices/{invoice['id']}/submit-for-approval",
        json={"assignedTo": str(approver.id)},
    )

    login_as(client, email="approver-2@nexora.group")
    inbox = client.get(f"/api/approvals?companyId={company['id']}").json()
    request_id = next(row["id"] for row in inbox if row["entityId"] == invoice["id"])

    decision = client.post(f"/api/approvals/{request_id}/decide", json={"decision": "APPROVED"})
    assert decision.status_code == 200, decision.text

    updated = client.get(f"/api/ap/supplier-invoices/{invoice['id']}")
    assert updated.status_code == 200, updated.text
    body = updated.json()
    assert body["status"] == "APPROVED"
    assert body["accrualDocumentId"] is not None


def test_deciding_the_approval_request_rejects_the_invoice_via_the_real_adapter(client, db_session):
    login_admin(client)
    company, _bank, expense, payable, supplier = _setup_ap(client)
    approver = _create_finance_manager(db_session, company_id=company["id"], email="approver-3@nexora.group")
    invoice = _create_draft_invoice(
        client, company_id=company["id"], expense_id=expense["id"], payable_id=payable["id"],
        supplier_id=supplier["id"], number="SUB-003",
    )
    client.post(
        f"/api/ap/supplier-invoices/{invoice['id']}/submit-for-approval",
        json={"assignedTo": str(approver.id)},
    )

    login_as(client, email="approver-3@nexora.group")
    inbox = client.get(f"/api/approvals?companyId={company['id']}").json()
    request_id = next(row["id"] for row in inbox if row["entityId"] == invoice["id"])

    decision = client.post(f"/api/approvals/{request_id}/decide", json={"decision": "REJECTED"})
    assert decision.status_code == 200, decision.text

    updated = client.get(f"/api/ap/supplier-invoices/{invoice['id']}").json()
    assert updated["status"] == "CANCELLED"


def test_submitter_cannot_decide_their_own_invoice_approval(client, db_session):
    """INV-SOD-001 / NXR-WORKFLOW-001: the same user cannot both submit and
    decide -- the submitter here is the bootstrap Administrator, who also
    holds `workflow.approval decide`, so the guard must be the service-level
    SegregationOfDutiesError, not merely a missing-permission 403."""
    login_admin(client)
    company, _bank, expense, payable, supplier = _setup_ap(client)
    invoice = _create_draft_invoice(
        client, company_id=company["id"], expense_id=expense["id"], payable_id=payable["id"],
        supplier_id=supplier["id"], number="SUB-004",
    )
    from app.models.user import User
    from sqlalchemy import select as sa_select
    from tests.conftest import BOOTSTRAP_ADMIN_EMAIL

    admin = db_session.execute(sa_select(User).where(User.email == BOOTSTRAP_ADMIN_EMAIL)).scalar_one()

    submit = client.post(
        f"/api/ap/supplier-invoices/{invoice['id']}/submit-for-approval",
        json={"assignedTo": str(admin.id)},
    )
    assert submit.status_code == 422, submit.text
    assert submit.json()["error"]["code"] == "NXR-FINANCIAL-001"


def test_cannot_submit_an_invoice_that_is_not_draft(client, db_session):
    login_admin(client)
    company, _bank, expense, payable, supplier = _setup_ap(client)
    approver = _create_finance_manager(db_session, company_id=company["id"], email="approver-5@nexora.group")
    invoice = _create_draft_invoice(
        client, company_id=company["id"], expense_id=expense["id"], payable_id=payable["id"],
        supplier_id=supplier["id"], number="SUB-005",
    )
    client.post(f"/api/ap/supplier-invoices/{invoice['id']}/approve")

    response = client.post(
        f"/api/ap/supplier-invoices/{invoice['id']}/submit-for-approval",
        json={"assignedTo": str(approver.id)},
    )
    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "NXR-AP-001"


def test_submit_rejects_an_approver_without_decide_permission(client, db_session):
    """An approver who cannot decide (no `workflow.approval decide`) would
    make the ApprovalRequest a dead end nobody can ever act on."""
    login_admin(client)
    company, _bank, expense, payable, supplier = _setup_ap(client)
    accountant = create_user_with_role(db_session, email="not-an-approver@nexora.group", role_name="Accountant")
    db_session.add(UserCompanyAccess(user_id=accountant.id, company_id=company["id"]))
    db_session.commit()
    invoice = _create_draft_invoice(
        client, company_id=company["id"], expense_id=expense["id"], payable_id=payable["id"],
        supplier_id=supplier["id"], number="SUB-006",
    )

    response = client.post(
        f"/api/ap/supplier-invoices/{invoice['id']}/submit-for-approval",
        json={"assignedTo": str(accountant.id)},
    )
    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "NXR-FINANCIAL-001"


def test_submit_for_approval_never_crosses_company(client, db_session):
    login_admin(client)
    company_a, _bank, expense, payable, supplier = _setup_ap(client)
    company_b = create_company(client, name="Aprobación B")
    invoice = _create_draft_invoice(
        client, company_id=company_a["id"], expense_id=expense["id"], payable_id=payable["id"],
        supplier_id=supplier["id"], number="SUB-007",
    )
    approver_b = _create_finance_manager(db_session, company_id=company_b["id"], email="approver-b@nexora.group")

    user = create_user_with_role(db_session, email="finance-sub@nexora.group", role_name="Finance Manager")
    db_session.add(UserCompanyAccess(user_id=user.id, company_id=company_b["id"]))
    db_session.commit()
    login_as(client, email="finance-sub@nexora.group")

    response = client.post(
        f"/api/ap/supplier-invoices/{invoice['id']}/submit-for-approval",
        json={"assignedTo": str(approver_b.id)},
    )
    assert response.status_code == 403, response.text
    assert response.json()["error"]["code"] == "NXR-PERM-001"
