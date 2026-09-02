"""Reconciliación end-to-end del ANTICIPO contractual (ORDEN MAESTRA §36/§37/§40).

Cadena completa: contrato 1,500,000 · anticipo 50,000 → factura de anticipo
(DRAFT → aprobada, débito a cuenta ASSET) → pago con asignación a la cuota
ADVANCE → reversión del pago. Se verifica que:

  * el dinero sale de Tesorería UNA sola vez y se restaura al revertir;
  * subledger ↔ GL cuadra en cada paso;
  * el anticipo NO es costo real del proyecto (débito ASSET);
  * el presupuesto reporta `advances`, no `accrued`;
  * la reversión reabre la cuota y restaura el saldo contractual.
"""

from decimal import Decimal

from app.models.company import Company
from app.services import contract_payment_service as cps
from tests.helpers import create_account, create_company, create_supplier, create_treasury_account, login_admin


def _bank_balance(client, company_id, treasury_account_id):
    accounts = client.get(f"/api/treasury/accounts?companyId={company_id}").json()
    return Decimal(next(a["balance"] for a in accounts if a["id"] == treasury_account_id))


def _all_reconciled(client, company_id):
    body = client.get(
        f"/api/accounting/reconciliation/subledger-gl?companyId={company_id}"
    ).json()
    return body["allReconciled"], body


def test_advance_full_chain_and_reversal_reconcile(client, db_session):
    login_admin(client)
    company = create_company(client, name="Anticipo Recon Co")
    supplier = create_supplier(client, company_id=company["id"], legal_name="Contratista Recon")

    advance_asset = create_account(
        client, company_id=company["id"], code="1610",
        name="Anticipos a contratistas", account_type="ASSET",
    )
    payable = create_account(
        client, company_id=company["id"], code="2110", name="CxP", account_type="LIABILITY",
    )
    expense_gl = create_account(
        client, company_id=company["id"], code="5101", name="Costo de obra", account_type="EXPENSE",
    )
    contrib = create_account(
        client, company_id=company["id"], code="3101", name="Aportes", account_type="EQUITY",
    )
    bank_gl = create_account(
        client, company_id=company["id"], code="1102", name="Banco", account_type="ASSET",
    )
    bank = create_treasury_account(client, company_id=company["id"], gl_account_id=bank_gl["id"])
    client.post(
        "/api/treasury/remittances",
        json={
            "companyId": company["id"], "treasuryAccountId": bank["id"],
            "counterAccountId": contrib["id"], "sender": "Fondeo", "currencyCode": "HNL",
            "originalAmount": "2000000.00", "remittanceDate": "2026-01-01",
        },
    )

    company_row = db_session.get(Company, company["id"])
    company_row.supplier_advance_account_id = advance_asset["id"]
    db_session.commit()

    project = client.post(
        "/api/projects",
        json={"companyId": company["id"], "name": "Obra Recon", "code": "PRJ-REC", "currencyCode": "HNL"},
    ).json()
    client.post(
        f"/api/projects/{project['id']}/budgets/baseline",
        json={"currencyCode": "HNL", "lines": [{"authorizedAmount": "2000000.00"}]},
    )

    contract = client.post(
        "/api/procurement/suppliers/contracts",
        json={
            "companyId": company["id"], "supplierId": supplier["id"], "projectId": project["id"],
            "contractNumber": "10101960", "value": "1500000.00", "currencyCode": "HNL",
            "startDate": "2026-08-01", "advanceAmount": "50000.00",
            "advanceDueDate": "2026-08-22", "retentionPercentage": "0",
        },
    ).json()
    schedule = client.post(
        "/api/contract-payments/schedules",
        json={
            "supplierContractId": contract["id"], "scheduleType": "MONTHLY",
            "regularMonths": 7, "dueDay": 1, "firstPeriod": "2026-09-01",
        },
    ).json()

    balance_before = _bank_balance(client, company["id"], bank["id"])
    assert balance_before == Decimal("2000000.00")

    # --- factura de anticipo: DRAFT, no autoaprobada (Codex / §14) ---
    adv = client.post(
        f"/api/contract-payments/schedules/{schedule['id']}/advance-invoice",
        json={"payableAccountId": payable["id"]},
    )
    assert adv.status_code == 201, adv.text
    invoice_id = adv.json()["invoiceId"]
    assert adv.json()["status"] == "DRAFT"

    client.post(f"/api/ap/supplier-invoices/{invoice_id}/approve")

    advance_inst = next(
        s for s in cps.installment_summaries(db_session, schedule_id=schedule["id"])
        if s.installment_kind == "ADVANCE"
    )
    pay = client.post(
        f"/api/ap/supplier-invoices/{invoice_id}/payments",
        json={
            "treasuryAccountId": bank["id"], "amount": "50000.00", "paymentDate": "2026-08-22",
            "contractAllocations": [
                {"installmentId": str(advance_inst.installment_id), "amountApplied": "50000.00"}
            ],
        },
    )
    assert pay.status_code == 201, pay.text
    payment_id = pay.json()["id"]

    # --- §37: efecto financiero correcto del anticipo ---
    assert _bank_balance(client, company["id"], bank["id"]) == Decimal("1950000.00")  # −50k exactamente 1 vez

    summary = client.get(f"/api/contract-payments/schedules/{schedule['id']}/summary").json()
    assert Decimal(summary["advancePaid"]) == Decimal("50000.00")
    assert Decimal(summary["advanceRemaining"]) == Decimal("0.00")
    assert Decimal(summary["paidAccumulated"]) == Decimal("50000.00")
    assert Decimal(summary["contractBalance"]) == Decimal("1450000.00")

    budget = client.get(f"/api/projects/{project['id']}/budgets/summary").json()
    assert Decimal(budget["accrued"]) == Decimal("0.00")       # el anticipo NO es costo
    assert Decimal(budget["advances"]) == Decimal("50000.00")  # se reporta como anticipo
    assert Decimal(budget["available"]) == Decimal("2000000.00")

    fin = client.get(f"/api/projects/{project['id']}/financial-summary").json()
    assert Decimal(fin["actualCost"]) == Decimal("0.00")  # débito ASSET, no EXPENSE

    ok, body = _all_reconciled(client, company["id"])
    assert ok, body

    # --- §40: reversión del pago ---
    rev = client.post(
        f"/api/ap/supplier-payments/{payment_id}/reverse",
        json={"reason": "Anticipo revertido por prueba de conciliación"},
    )
    assert rev.status_code in (200, 201), rev.text

    db_session.expire_all()
    reopened = next(
        s for s in cps.installment_summaries(db_session, schedule_id=schedule["id"])
        if s.installment_id == advance_inst.installment_id
    )
    assert reopened.paid == Decimal("0.00")
    assert reopened.remaining == Decimal("50000.00")
    assert reopened.status != "PAID"

    assert _bank_balance(client, company["id"], bank["id"]) == Decimal("2000000.00")  # dinero restaurado

    summary_after = client.get(f"/api/contract-payments/schedules/{schedule['id']}/summary").json()
    assert Decimal(summary_after["paidAccumulated"]) == Decimal("0.00")
    assert Decimal(summary_after["contractBalance"]) == Decimal("1500000.00")

    ok_after, body_after = _all_reconciled(client, company["id"])
    assert ok_after, body_after
