"""Contract Payment Control — reporting layer (orden maestra final §47/§50/§54).

Cubre: Libro contractual de pagos (JSON + CSV), la línea de conciliación
subledger contractual <-> GL, y el camino contractual del Transaction
Inspector (PAGO -> CUOTA -> PLAN -> CONTRATO).
"""

from datetime import date
from decimal import Decimal

from sqlalchemy import select

from app.models.ap import SupplierInvoice, SupplierPayment
from app.services import contract_payment_service as cps
from tests.helpers import (
    create_account,
    create_company,
    create_supplier,
    create_treasury_account,
    login_admin,
)


def _contract(client, *, company_id, supplier_id, value="500000.00", number="CTR-REP-001"):
    r = client.post(
        "/api/procurement/suppliers/contracts",
        json={
            "companyId": company_id, "supplierId": supplier_id, "contractNumber": number,
            "value": value, "currencyCode": "HNL", "startDate": "2026-08-01",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def _monthly_plan(db, contract_id):
    rows = cps.build_monthly_installments(
        start_period=date(2026, 8, 1), count=10,
        monthly_amount=Decimal("50000.00"), total_value=Decimal("500000.00"),
    )
    return cps.create_schedule(
        db, supplier_contract_id=contract_id, schedule_type="MONTHLY", installments=rows
    )


def _ap_setup(client, company, *, tag):
    bank_gl = create_account(client, company_id=company["id"], code=f"11{tag}", name="Bancos", account_type="ASSET")
    expense = create_account(client, company_id=company["id"], code=f"52{tag}", name="Obra", account_type="EXPENSE")
    payable = create_account(client, company_id=company["id"], code=f"21{tag}", name="CxP", account_type="LIABILITY")
    contrib = create_account(client, company_id=company["id"], code=f"31{tag}", name="Aportes", account_type="EQUITY")
    bank = create_treasury_account(client, company_id=company["id"], gl_account_id=bank_gl["id"])
    client.post(
        "/api/treasury/remittances",
        json={
            "companyId": company["id"], "treasuryAccountId": bank["id"],
            "counterAccountId": contrib["id"], "sender": "Fondeo", "currencyCode": "HNL",
            "originalAmount": "600000.00", "remittanceDate": "2026-01-01",
        },
    )
    return bank, expense, payable


def _contract_invoice(client, *, company, supplier, contract_id, expense, payable, amount, number):
    r = client.post(
        "/api/ap/supplier-invoices",
        json={
            "companyId": company["id"], "supplierId": supplier["id"],
            "invoiceNumber": number, "scope": "GENERAL",
            "expenseAccountId": expense["id"], "payableAccountId": payable["id"],
            "currencyCode": "HNL", "amount": str(amount), "invoiceDate": "2026-09-01",
            "dueDate": "2026-09-30", "supplierContractId": contract_id,
        },
    )
    assert r.status_code == 201, r.text
    client.post(f"/api/ap/supplier-invoices/{r.json()['id']}/approve")
    return r.json()


def _pay_august(client, db_session, company, supplier, contract, schedule, bank, expense, payable):
    inv = _contract_invoice(
        client, company=company, supplier=supplier, contract_id=contract["id"],
        expense=expense, payable=payable, amount="50000.00", number="F-REP-AUG",
    )
    aug = [s for s in cps.installment_summaries(db_session, schedule_id=schedule.id)
           if s.period_label == "Agosto 2026"][0]
    r = client.post(
        f"/api/ap/supplier-invoices/{inv['id']}/payments",
        json={
            "treasuryAccountId": bank["id"], "amount": "50000.00", "paymentDate": "2026-09-03",
            "contractAllocations": [
                {"installmentId": str(aug.installment_id), "amountApplied": "50000.00"}
            ],
            "bankTransactionReference": "ATL-778899",
        },
    )
    assert r.status_code == 201, r.text
    db_session.commit()
    return db_session.execute(
        select(SupplierPayment).join(
            SupplierInvoice, SupplierPayment.supplier_invoice_id == SupplierInvoice.id
        ).where(SupplierInvoice.id == inv["id"])
    ).scalar_one()


def test_contract_payment_ledger_json_reports_installments_and_allocations(client, db_session):
    login_admin(client)
    company = create_company(client)
    supplier = create_supplier(client, company_id=company["id"], legal_name="RIVAS ZEPEDA SA")
    contract = _contract(client, company_id=company["id"], supplier_id=supplier["id"])
    schedule = _monthly_plan(db_session, contract["id"])
    bank, expense, payable = _ap_setup(client, company, tag="90")
    _pay_august(client, db_session, company, supplier, contract, schedule, bank, expense, payable)

    r = client.get(f"/api/reports/contract-payment-ledger?companyId={company['id']}&asOf=2026-09-15")
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body["entries"]) == 1
    entry = body["entries"][0]
    assert entry["contractNumber"] == "CTR-REP-001"
    assert entry["supplierLegalName"] == "RIVAS ZEPEDA SA"
    assert Decimal(entry["contractValue"]) == Decimal("500000.00")
    assert Decimal(entry["paidAccumulated"]) == Decimal("50000.00")
    assert Decimal(entry["contractBalance"]) == Decimal("450000.00")
    assert len(entry["installments"]) == 10
    aug = [i for i in entry["installments"] if i["periodLabel"] == "Agosto 2026"][0]
    assert aug["status"] == "PAID"
    assert len(entry["allocations"]) == 1
    assert entry["allocations"][0]["bankTransactionReference"] == "ATL-778899"
    assert entry["allocations"][0]["reversed"] is False
    assert Decimal(body["totalContractBalance"]) == Decimal("450000.00")


def test_contract_payment_ledger_csv_export(client, db_session):
    login_admin(client)
    company = create_company(client)
    supplier = create_supplier(client, company_id=company["id"])
    contract = _contract(client, company_id=company["id"], supplier_id=supplier["id"])
    schedule = _monthly_plan(db_session, contract["id"])
    bank, expense, payable = _ap_setup(client, company, tag="91")
    _pay_august(client, db_session, company, supplier, contract, schedule, bank, expense, payable)

    r = client.get(
        f"/api/reports/contract-payment-ledger?companyId={company['id']}&format=csv&asOf=2026-09-15"
    )
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("text/csv")
    lines = r.text.strip().splitlines()
    assert lines[0].startswith("contract_number,supplier,currency")
    assert len(lines) == 11  # header + 10 cuotas
    assert any("Agosto 2026" in line and "PAID" in line for line in lines)


def test_reconciliation_includes_contract_subledger_line(client, db_session):
    login_admin(client)
    company = create_company(client)
    supplier = create_supplier(client, company_id=company["id"])
    contract = _contract(client, company_id=company["id"], supplier_id=supplier["id"])
    schedule = _monthly_plan(db_session, contract["id"])
    bank, expense, payable = _ap_setup(client, company, tag="92")
    _pay_august(client, db_session, company, supplier, contract, schedule, bank, expense, payable)

    r = client.get(f"/api/accounting/reconciliation/subledger-gl?companyId={company['id']}")
    assert r.status_code == 200, r.text
    body = r.json()
    contract_line = [ln for ln in body["lines"] if ln["subledger"] == "CONTRACT_PAYMENTS"][0]
    assert Decimal(contract_line["subledgerTotal"]) == Decimal("50000.00")
    assert Decimal(contract_line["glTotal"]) == Decimal("50000.00")
    assert contract_line["reconciled"] is True


def test_transaction_inspector_exposes_contract_path(client, db_session):
    login_admin(client)
    company = create_company(client)
    supplier = create_supplier(client, company_id=company["id"])
    contract = _contract(client, company_id=company["id"], supplier_id=supplier["id"])
    schedule = _monthly_plan(db_session, contract["id"])
    bank, expense, payable = _ap_setup(client, company, tag="93")
    payment = _pay_august(
        client, db_session, company, supplier, contract, schedule, bank, expense, payable
    )

    r = client.get(f"/api/accounting/journal-entries/{payment.accounting_document_id}/inspect")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["sourceEvent"]["kind"] == "SUPPLIER_PAYMENT"
    assert body["contract"] is not None
    assert body["contract"]["contractNumber"] == "CTR-REP-001"
    assert Decimal(str(body["contract"]["contractBalance"])) == Decimal("450000.00")
    assert len(body["contract"]["allocations"]) == 1
    assert body["contract"]["allocations"][0]["periodLabel"] == "Agosto 2026"
    assert body["contract"]["allocations"][0]["reversed"] is False
