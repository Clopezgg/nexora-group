from app.models.accounting import AccountingDocument
from app.models.ap import SupplierPayment
from app.models.ar import CustomerReceipt
from app.models.permission import UserCompanyAccess
from app.models.cost_center import CostCenter
from app.models.project import Project
from tests.helpers import (
    create_account,
    create_company,
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

    invoice = client.post(
        "/api/ar/customer-invoices",
        json={
            "companyId": company["id"],
            "customerName": "Inversiones ABC",
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
    customer_invoice = client.post(
        "/api/ar/customer-invoices",
        json={
            "companyId": company["id"],
            "customerName": "Cliente persistido",
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
    invoice = client.post(
        "/api/ar/customer-invoices",
        json={
            "companyId": company["id"],
            "customerName": "Cliente idempotente",
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
