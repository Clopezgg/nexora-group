"""ORDEN MAESTRA §9/§28/§29 — el costo contratado de EJECUCIÓN (SupplierContract
del proyecto) es un KPI distinto del compromiso por Órdenes de Compra
(`poCommitted`). Nunca se mezclan ni se renombra uno como el otro.
"""

from datetime import date
from decimal import Decimal

from app.services import contract_payment_service as cps
from app.services.contract_payment_service import build_monthly_installments
from tests.helpers import (
    create_account,
    create_company,
    create_supplier,
    create_treasury_account,
    login_admin,
)


def _project(client, company_id, *, code="EXC-001"):
    r = client.post(
        "/api/projects",
        json={"companyId": company_id, "name": f"Proyecto {code}", "code": code, "currencyCode": "HNL"},
    )
    assert r.status_code == 201, r.text
    return r.json()


def _contract(client, company_id, supplier_id, project_id, *, value, number):
    r = client.post(
        "/api/procurement/suppliers/contracts",
        json={
            "companyId": company_id,
            "supplierId": supplier_id,
            "projectId": project_id,
            "contractNumber": number,
            "contractCategory": "LABOR",
            "value": value,
            "currencyCode": "HNL",
            "startDate": "2026-08-01",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def test_execution_contract_value_is_independent_from_po_commitment(client, db_session):
    login_admin(client)
    company = create_company(client, name="Exec KPI Co")
    project = _project(client, company["id"])
    supplier = create_supplier(client, company_id=company["id"])

    _contract(
        client, company["id"], supplier["id"], project["id"],
        value="250000.00", number="CON-EXC-001",
    )

    summary = client.get(f"/api/projects/{project['id']}/financial-summary").json()
    # SupplierContract 250,000, sin PO -> costo contratado ejecución = 250,000,
    # PO comprometidas = 0.
    assert Decimal(summary["executionContractValue"]) == Decimal("250000.00")
    assert Decimal(summary["executionContractPaid"]) == Decimal("0.00")
    assert Decimal(summary["executionContractBalance"]) == Decimal("250000.00")
    assert Decimal(summary["poCommitted"]) == Decimal("0")


def test_execution_contract_paid_follows_non_reversed_allocations(client, db_session):
    login_admin(client)
    company = create_company(client, name="Exec KPI Paid Co")
    project = _project(client, company["id"], code="EXC-002")
    supplier = create_supplier(client, company_id=company["id"])
    contract = _contract(
        client, company["id"], supplier["id"], project["id"],
        value="250000.00", number="CON-EXC-002",
    )

    rows = build_monthly_installments(
        start_period=date(2026, 4, 1), count=5,
        monthly_amount=Decimal("50000.00"), total_value=Decimal("250000.00"),
    )
    schedule = cps.create_schedule(
        db_session, supplier_contract_id=contract["id"], schedule_type="MONTHLY", installments=rows
    )

    bank_gl = create_account(client, company_id=company["id"], code="1190", name="Bancos", account_type="ASSET")
    expense = create_account(client, company_id=company["id"], code="5290", name="Obra", account_type="EXPENSE")
    payable = create_account(client, company_id=company["id"], code="2190", name="CxP", account_type="LIABILITY")
    contrib = create_account(client, company_id=company["id"], code="3190", name="Aportes", account_type="EQUITY")
    bank = create_treasury_account(client, company_id=company["id"], gl_account_id=bank_gl["id"])
    client.post(
        "/api/treasury/remittances",
        json={
            "companyId": company["id"], "treasuryAccountId": bank["id"],
            "counterAccountId": contrib["id"], "sender": "Fondeo", "currencyCode": "HNL",
            "originalAmount": "300000.00", "remittanceDate": "2026-01-01",
        },
    )

    invoice = client.post(
        "/api/ap/supplier-invoices",
        json={
            "companyId": company["id"], "supplierId": supplier["id"],
            "invoiceNumber": "F-EXC-AUG", "scope": "PROJECT", "projectId": project["id"],
            "expenseAccountId": expense["id"], "payableAccountId": payable["id"],
            "currencyCode": "HNL", "amount": "50000.00", "invoiceDate": "2026-09-01",
            "dueDate": "2026-09-30", "supplierContractId": contract["id"],
        },
    )
    assert invoice.status_code == 201, invoice.text
    client.post(f"/api/ap/supplier-invoices/{invoice.json()['id']}/approve")

    aug = [
        s for s in cps.installment_summaries(db_session, schedule_id=schedule.id)
        if s.period_label == "Agosto 2026"
    ][0]
    pay = client.post(
        f"/api/ap/supplier-invoices/{invoice.json()['id']}/payments",
        json={
            "treasuryAccountId": bank["id"], "amount": "50000.00", "paymentDate": "2026-09-03",
            "contractAllocations": [
                {"installmentId": str(aug.installment_id), "amountApplied": "50000.00"}
            ],
        },
    )
    assert pay.status_code == 201, pay.text

    summary = client.get(f"/api/projects/{project['id']}/financial-summary").json()
    assert Decimal(summary["executionContractValue"]) == Decimal("250000.00")
    assert Decimal(summary["executionContractPaid"]) == Decimal("50000.00")
    assert Decimal(summary["executionContractBalance"]) == Decimal("200000.00")

    # Reversal -> el pagado contractual vuelve a 0.
    rev = client.post(
        f"/api/ap/supplier-payments/{pay.json()['id']}/reverse",
        json={"reason": "Pago duplicado"},
    )
    assert rev.status_code in (200, 201), rev.text
    summary_after = client.get(f"/api/projects/{project['id']}/financial-summary").json()
    assert Decimal(summary_after["executionContractPaid"]) == Decimal("0.00")
    assert Decimal(summary_after["executionContractBalance"]) == Decimal("250000.00")
