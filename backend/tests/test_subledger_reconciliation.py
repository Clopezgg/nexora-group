from tests.helpers import (
    create_account,
    create_company,
    create_supplier,
    create_treasury_account,
    login_admin,
)


def _finance_setup(client):
    company = create_company(client)
    cash_gl = create_account(client, company_id=company["id"], code="1100", name="Bancos", account_type="ASSET")
    expense = create_account(client, company_id=company["id"], code="5200", name="Materiales", account_type="EXPENSE")
    payable = create_account(client, company_id=company["id"], code="2100", name="CxP", account_type="LIABILITY")
    contributions = create_account(client, company_id=company["id"], code="3100", name="Aportes", account_type="EQUITY")
    bank = create_treasury_account(client, company_id=company["id"], gl_account_id=cash_gl["id"])
    supplier = create_supplier(client, company_id=company["id"])
    client.post(
        "/api/treasury/remittances",
        json={
            "companyId": company["id"],
            "treasuryAccountId": bank["id"],
            "counterAccountId": contributions["id"],
            "sender": "Fondeo",
            "currencyCode": "HNL",
            "originalAmount": "50000.00",
            "remittanceDate": "2026-01-01",
        },
    )
    return company, bank, expense, payable, supplier


def test_subledger_gl_reconciliation_matches_after_ap_accrual(client):
    """Orden maestra Phase 4: el subledger de AP debe cuadrar contra su
    cuenta de control en el GL. Un trial balance que cuadra no basta."""
    login_admin(client)
    company, _bank, expense, payable, supplier = _finance_setup(client)

    invoice = client.post(
        "/api/ap/supplier-invoices",
        json={
            "companyId": company["id"],
            "supplierId": supplier["id"],
            "invoiceNumber": "F-RECON-1",
            "scope": "GENERAL",
            "expenseAccountId": expense["id"],
            "payableAccountId": payable["id"],
            "currencyCode": "HNL",
            "amount": "1000.00",
            "taxAmount": "0.00",
            "invoiceDate": "2026-01-10",
            "dueDate": "2026-02-10",
        },
    ).json()
    client.post(f"/api/ap/supplier-invoices/{invoice['id']}/approve")

    response = client.get(
        f"/api/accounting/reconciliation/subledger-gl?companyId={company['id']}"
    )
    assert response.status_code == 200, response.text
    body = response.json()
    lines = {line["subledger"]: line for line in body["lines"]}

    assert set(lines) == {
        "TREASURY",
        "ACCOUNTS_PAYABLE",
        "ACCOUNTS_RECEIVABLE",
        "CONTRACT_PAYMENTS",
    }
    ap = lines["ACCOUNTS_PAYABLE"]
    assert float(ap["subledgerTotal"]) == 1000.0
    assert float(ap["glTotal"]) == 1000.0
    assert float(ap["difference"]) == 0.0
    assert ap["reconciled"] is True
    assert lines["TREASURY"]["reconciled"] is True
    assert body["allReconciled"] is True

    # Un pago parcial mantiene la conciliación (subledger y GL bajan juntos).
    client.post(
        f"/api/ap/supplier-invoices/{invoice['id']}/payments",
        json={"treasuryAccountId": _bank_id(client, company), "amount": "400.00", "paymentDate": "2026-01-20"},
    )
    after = client.get(
        f"/api/accounting/reconciliation/subledger-gl?companyId={company['id']}"
    ).json()
    ap_after = next(line for line in after["lines"] if line["subledger"] == "ACCOUNTS_PAYABLE")
    assert float(ap_after["subledgerTotal"]) == 600.0
    assert float(ap_after["glTotal"]) == 600.0
    assert ap_after["reconciled"] is True


def _bank_id(client, company):
    accounts = client.get(f"/api/treasury/accounts?companyId={company['id']}").json()
    return accounts[0]["id"]
