"""ORDEN MAESTRA — anticipo + plan de pagos + cuotas (§4, §16-§20, §50-§57).

Caso de aceptación: contrato tipo 10101960.
  valor 1,500,000 · anticipo 50,000 vence 22/08/2026 · retención 0 ·
  7 mensualidades el día 1, primera 01/09/2026.
  -> 6 × 207,142.85 + 1 × 207,142.90 + anticipo 50,000 = 1,500,000 EXACTO.
"""

from datetime import date
from decimal import Decimal

import pytest

from app.services import contract_payment_service as cps
from app.services.contract_payment_service import build_contract_plan
from tests.helpers import (
    create_account,
    create_company,
    create_supplier,
    create_treasury_account,
    login_admin,
)

_ADV = Decimal("50000.00")
_REG_6 = Decimal("207142.85")
_REG_LAST = Decimal("207142.90")


def test_build_contract_plan_is_exact_decimal_math():
    rows = build_contract_plan(
        contract_value=Decimal("1500000.00"),
        advance_amount=_ADV,
        advance_due_date=date(2026, 8, 22),
        retention_percentage=Decimal("0.00"),
        regular_months=7,
        due_day=1,
        first_period=date(2026, 9, 1),
    )
    advance = [r for r in rows if r["installment_kind"] == "ADVANCE"]
    regular = [r for r in rows if r["installment_kind"] == "REGULAR"]

    assert len(advance) == 1
    assert advance[0]["scheduled_amount"] == _ADV
    assert advance[0]["due_date"] == date(2026, 8, 22)

    assert len(regular) == 7
    assert [r["scheduled_amount"] for r in regular] == [_REG_6] * 6 + [_REG_LAST]
    assert [r["due_date"] for r in regular] == [
        date(2026, 9, 1), date(2026, 10, 1), date(2026, 11, 1), date(2026, 12, 1),
        date(2027, 1, 1), date(2027, 2, 1), date(2027, 3, 1),
    ]

    regular_total = sum((r["scheduled_amount"] for r in regular), Decimal("0"))
    assert regular_total == Decimal("1450000.00")
    assert advance[0]["scheduled_amount"] == Decimal("50000.00")
    assert regular_total + advance[0]["scheduled_amount"] == Decimal("1500000.00")
    # 6*207142.85 + 207142.90
    assert Decimal("6") * _REG_6 + _REG_LAST == Decimal("1450000.00")


def _contract_10101960(client, company_id, supplier_id):
    r = client.post(
        "/api/procurement/suppliers/contracts",
        json={
            "companyId": company_id, "supplierId": supplier_id,
            "contractNumber": "10101960", "value": "1500000.00", "currencyCode": "HNL",
            "startDate": "2026-08-01", "advanceAmount": "50000.00",
            "advanceDueDate": "2026-08-22", "retentionPercentage": "0",
        },
    )
    assert r.status_code == 201, r.text
    assert r.json()["advanceAmount"] == "50000.00"
    return r.json()


def _create_schedule(client, contract_id):
    return client.post(
        "/api/contract-payments/schedules",
        json={
            "supplierContractId": contract_id, "scheduleType": "MONTHLY",
            "regularMonths": 7, "dueDay": 1, "firstPeriod": "2026-09-01",
        },
    )


def test_api_schedule_has_advance_plus_7_regular_and_initial_state(client):
    login_admin(client)
    company = create_company(client, name="Anticipo Co")
    supplier = create_supplier(client, company_id=company["id"])
    contract = _contract_10101960(client, company["id"], supplier["id"])

    created = _create_schedule(client, contract["id"])
    assert created.status_code == 201, created.text
    body = created.json()
    inst = body["installments"]
    assert len(inst) == 8  # anticipo + 7

    advance = next(i for i in inst if i["installmentKind"] == "ADVANCE")
    regulars = [i for i in inst if i["installmentKind"] == "REGULAR"]
    assert advance["periodLabel"] == "Anticipo"
    assert advance["scheduledAmount"] == "50000.00"
    assert advance["dueDate"] == "2026-08-22"
    # Anticipo NO consume una de las 7 (§6).
    assert [r["regularNumber"] for r in regulars] == [1, 2, 3, 4, 5, 6, 7]
    assert all(r["regularCount"] == 7 for r in regulars)
    assert [r["scheduledAmount"] for r in regulars] == ["207142.85"] * 6 + ["207142.90"]
    assert sum(Decimal(i["scheduledAmount"]) for i in inst) == Decimal("1500000.00")
    assert all(i["paid"] == "0.00" for i in inst)

    schedule_id = body["id"]
    summary = client.get(
        f"/api/contract-payments/schedules/{schedule_id}/summary?asOf=2026-08-01"
    ).json()
    assert Decimal(summary["contractValue"]) == Decimal("1500000.00")
    assert Decimal(summary["advanceScheduled"]) == Decimal("50000.00")
    assert Decimal(summary["regularScheduled"]) == Decimal("1450000.00")
    assert Decimal(summary["totalContractualScheduled"]) == Decimal("1500000.00")
    assert Decimal(summary["advancePaid"]) == Decimal("0.00")
    assert Decimal(summary["advanceRemaining"]) == Decimal("50000.00")
    assert Decimal(summary["paidAccumulated"]) == Decimal("0.00")
    assert Decimal(summary["contractBalance"]) == Decimal("1500000.00")
    assert Decimal(summary["retentionOutstanding"]) == Decimal("0.00")
    # Antes de 22/08: próximo vencimiento = el anticipo.
    assert summary["nextDuePeriod"] == "Anticipo"


def test_due_day_31_uses_last_valid_day(client):
    login_admin(client)
    company = create_company(client, name="DueDay Co")
    supplier = create_supplier(client, company_id=company["id"])
    r = client.post(
        "/api/procurement/suppliers/contracts",
        json={
            "companyId": company["id"], "supplierId": supplier["id"],
            "contractNumber": "DD-31", "value": "300000.00", "currencyCode": "HNL",
            "startDate": "2026-01-01",
        },
    )
    contract = r.json()
    created = client.post(
        "/api/contract-payments/schedules",
        json={
            "supplierContractId": contract["id"], "scheduleType": "MONTHLY",
            "regularMonths": 3, "dueDay": 31, "firstPeriod": "2026-01-01",
        },
    )
    dues = [i["dueDate"] for i in created.json()["installments"]]
    assert dues == ["2026-01-31", "2026-02-28", "2026-03-31"]


def test_retention_5pct_gross_net_split(client):
    login_admin(client)
    company = create_company(client, name="Retention Co")
    supplier = create_supplier(client, company_id=company["id"])
    r = client.post(
        "/api/procurement/suppliers/contracts",
        json={
            "companyId": company["id"], "supplierId": supplier["id"],
            "contractNumber": "RET-5", "value": "100000.00", "currencyCode": "HNL",
            "startDate": "2026-01-01", "retentionPercentage": "5",
        },
    )
    contract = r.json()
    created = client.post(
        "/api/contract-payments/schedules",
        json={
            "supplierContractId": contract["id"], "scheduleType": "MONTHLY",
            "regularMonths": 2, "dueDay": 1, "firstPeriod": "2026-01-01",
        },
    )
    inst = created.json()["installments"]
    assert [i["scheduledAmount"] for i in inst] == ["50000.00", "50000.00"]
    assert [i["retentionAmount"] for i in inst] == ["2500.00", "2500.00"]
    assert [i["netDue"] for i in inst] == ["47500.00", "47500.00"]
    summary = client.get(
        f"/api/contract-payments/schedules/{created.json()['id']}/summary"
    ).json()
    assert Decimal(summary["retentionOutstanding"]) == Decimal("5000.00")


def _pay_setup(client, company, tag):
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
            "originalAmount": "2000000.00", "remittanceDate": "2026-01-01",
        },
    )
    return bank, expense, payable


def test_partial_payment_of_september(client, db_session):
    login_admin(client)
    company = create_company(client, name="Partial Co")
    supplier = create_supplier(client, company_id=company["id"])
    contract = _contract_10101960(client, company["id"], supplier["id"])
    schedule = _create_schedule(client, contract["id"]).json()
    bank, expense, payable = _pay_setup(client, company, "60")

    sept = next(
        s for s in cps.installment_summaries(db_session, schedule_id=schedule["id"])
        if s.installment_kind == "REGULAR" and s.regular_number == 1
    )
    invoice = client.post(
        "/api/ap/supplier-invoices",
        json={
            "companyId": company["id"], "supplierId": supplier["id"],
            "invoiceNumber": "F-SEP", "scope": "GENERAL",
            "expenseAccountId": expense["id"], "payableAccountId": payable["id"],
            "currencyCode": "HNL", "amount": "50000.00", "invoiceDate": "2026-09-01",
            "dueDate": "2026-09-30", "supplierContractId": contract["id"],
        },
    )
    assert invoice.status_code == 201, invoice.text
    client.post(f"/api/ap/supplier-invoices/{invoice.json()['id']}/approve")
    pay = client.post(
        f"/api/ap/supplier-invoices/{invoice.json()['id']}/payments",
        json={
            "treasuryAccountId": bank["id"], "amount": "50000.00", "paymentDate": "2026-09-03",
            "contractAllocations": [
                {"installmentId": str(sept.installment_id), "amountApplied": "50000.00"}
            ],
        },
    )
    assert pay.status_code == 201, pay.text

    db_session.expire_all()
    after = next(
        s for s in cps.installment_summaries(db_session, schedule_id=schedule["id"])
        if s.installment_id == sept.installment_id
    )
    assert after.scheduled_amount == _REG_6
    assert after.paid == Decimal("50000.00")
    assert after.remaining == Decimal("157142.85")
    assert after.status == "PARTIALLY_PAID"


def test_advance_payment_fail_closed_without_advance_account(client):
    login_admin(client)
    company = create_company(client, name="NoAdvAcct Co")
    supplier = create_supplier(client, company_id=company["id"])
    contract = _contract_10101960(client, company["id"], supplier["id"])
    schedule = _create_schedule(client, contract["id"]).json()
    _, _, payable = _pay_setup(client, company, "61")

    r = client.post(
        f"/api/contract-payments/schedules/{schedule['id']}/advance-invoice",
        json={"payableAccountId": payable["id"]},
    )
    assert r.status_code == 422, r.text
    assert "cuenta contable para anticipos" in r.text
