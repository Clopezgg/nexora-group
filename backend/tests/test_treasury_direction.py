"""Treasury Direction + Payment Voucher OUTFLOW-only (ORDEN MAESTRA — FIORI /
CASH FLOW / TREASURY DIRECTION, §15-§20).

- Una remesa / cobro / aporte de capital / financiamiento es INFLOW.
- Una transferencia banco A -> banco B es INTERNAL_TRANSFER (net 0).
- Un pago a proveedor / gasto pagado es OUTFLOW.
- Solo OUTFLOW es elegible para Payment Voucher; el backend es fail-closed y
  el endpoint de candidatos nunca devuelve inflows.
"""

from decimal import Decimal

from app.models.accounting import AccountingDocument
from app.services import treasury_direction_service as tds
from tests.helpers import (
    create_account,
    create_company,
    create_supplier,
    create_treasury_account,
    login_admin,
)


def _company_with_two_banks(client):
    company = create_company(client)
    bank_a_gl = create_account(client, company_id=company["id"], code="1101", name="Banco A", account_type="ASSET")
    bank_b_gl = create_account(client, company_id=company["id"], code="1102", name="Banco B", account_type="ASSET")
    equity = create_account(client, company_id=company["id"], code="3100", name="Aportes", account_type="EQUITY")
    bank_a = create_treasury_account(client, company_id=company["id"], gl_account_id=bank_a_gl["id"], name="Banco A")
    bank_b = create_treasury_account(client, company_id=company["id"], gl_account_id=bank_b_gl["id"], name="Banco B")
    return company, bank_a, bank_b, equity


def _direction(db_session, doc_id):
    document = db_session.get(AccountingDocument, doc_id)
    return tds.classify(db_session, document)


def test_remittance_is_inflow_and_not_voucher_eligible(client, db_session):
    login_admin(client)
    company, bank_a, _bank_b, equity = _company_with_two_banks(client)
    doc_id = client.post(
        "/api/treasury/remittances",
        json={
            "companyId": company["id"], "treasuryAccountId": bank_a["id"],
            "counterAccountId": equity["id"], "sender": "Aportante",
            "currencyCode": "HNL", "originalAmount": "100000.00", "remittanceDate": "2026-01-01",
        },
    ).json()["accountingDocumentId"]

    d = _direction(db_session, doc_id)
    assert d.direction == "INFLOW"
    assert d.treasury_net == Decimal("100000.00")
    assert d.voucher_eligible is False

    blocked = client.get(
        f"/api/treasury/vouchers/{doc_id}?beneficiary=Aportante&paymentMethod=Efectivo"
    )
    assert blocked.status_code == 422, blocked.text
    assert blocked.json()["error"]["code"] == "NXR-VOUCHER-NOT-OUTFLOW"


def test_supplier_payment_is_outflow_and_voucher_eligible(client, db_session):
    login_admin(client)
    company, bank_a, _bank_b, equity = _company_with_two_banks(client)
    client.post(
        "/api/treasury/remittances",
        json={
            "companyId": company["id"], "treasuryAccountId": bank_a["id"],
            "counterAccountId": equity["id"], "sender": "Fondeo",
            "currencyCode": "HNL", "originalAmount": "50000.00", "remittanceDate": "2026-01-01",
        },
    )
    expense_gl = create_account(client, company_id=company["id"], code="5200", name="Obra", account_type="EXPENSE")
    payable_gl = create_account(client, company_id=company["id"], code="2100", name="CxP", account_type="LIABILITY")
    supplier = create_supplier(client, company_id=company["id"])
    invoice = client.post(
        "/api/ap/supplier-invoices",
        json={
            "companyId": company["id"], "supplierId": supplier["id"], "invoiceNumber": "F-1",
            "scope": "GENERAL", "expenseAccountId": expense_gl["id"], "payableAccountId": payable_gl["id"],
            "currencyCode": "HNL", "amount": "10000.00", "invoiceDate": "2026-01-05", "dueDate": "2026-02-05",
        },
    ).json()
    client.post(f"/api/ap/supplier-invoices/{invoice['id']}/approve")
    payment = client.post(
        f"/api/ap/supplier-invoices/{invoice['id']}/payments",
        json={"treasuryAccountId": bank_a["id"], "amount": "10000.00", "paymentDate": "2026-01-20"},
    )
    assert payment.status_code == 201, payment.text
    doc_id = payment.json()["accountingDocumentId"]

    d = _direction(db_session, doc_id)
    assert d.direction == "OUTFLOW"
    assert d.treasury_net == Decimal("-10000.00")
    assert d.voucher_eligible is True

    candidates = client.get(f"/api/treasury/voucher-candidates?companyId={company['id']}").json()
    assert doc_id in [c["id"] for c in candidates]
    assert all(c["treasuryDirection"] == "OUTFLOW" for c in candidates)


def test_internal_transfer_is_neither_inflow_nor_outflow(client, db_session):
    login_admin(client)
    company, bank_a, bank_b, equity = _company_with_two_banks(client)
    client.post(
        "/api/treasury/remittances",
        json={
            "companyId": company["id"], "treasuryAccountId": bank_a["id"],
            "counterAccountId": equity["id"], "sender": "Fondeo",
            "currencyCode": "HNL", "originalAmount": "20000.00", "remittanceDate": "2026-01-01",
        },
    )
    transfer = client.post(
        "/api/treasury/transfers",
        json={
            "companyId": company["id"], "sourceTreasuryAccountId": bank_a["id"],
            "destinationTreasuryAccountId": bank_b["id"], "amount": "5000.00",
            "currencyCode": "HNL", "transferDate": "2026-01-10",
        },
    )
    assert transfer.status_code == 201, transfer.text
    doc_id = transfer.json()["accountingDocumentId"]

    d = _direction(db_session, doc_id)
    assert d.direction == "INTERNAL_TRANSFER"
    assert d.treasury_net == Decimal("0.00")
    assert d.treasury_account_count == 2
    assert d.voucher_eligible is False

    blocked = client.get(
        f"/api/treasury/vouchers/{doc_id}?beneficiary=Interno&paymentMethod=Efectivo"
    )
    assert blocked.status_code == 422
    assert blocked.json()["error"]["code"] == "NXR-VOUCHER-NOT-OUTFLOW"


def test_voucher_candidates_excludes_inflows(client, db_session):
    login_admin(client)
    company, bank_a, _bank_b, equity = _company_with_two_banks(client)
    # Dos inflows (remesas) + un outflow (gasto).
    for i in range(2):
        client.post(
            "/api/treasury/remittances",
            json={
                "companyId": company["id"], "treasuryAccountId": bank_a["id"],
                "counterAccountId": equity["id"], "sender": f"Aporte {i}",
                "currencyCode": "HNL", "originalAmount": "10000.00", "remittanceDate": "2026-01-01",
            },
        )
    expense_gl = create_account(client, company_id=company["id"], code="5300", name="Servicios", account_type="EXPENSE")
    outflow_id = client.post(
        "/api/treasury/general-expenses",
        json={
            "companyId": company["id"], "treasuryAccountId": bank_a["id"],
            "expenseAccountId": expense_gl["id"], "category": "Luz", "amount": "1500.00",
            "currencyCode": "HNL", "expenseDate": "2026-01-12", "description": "Energía",
        },
    ).json()["accountingDocumentId"]

    candidates = client.get(f"/api/treasury/voucher-candidates?companyId={company['id']}").json()
    ids = [c["id"] for c in candidates]
    assert ids == [outflow_id]
