"""Project Contract Payment Control — dominio (orden maestra final §59-§61).

Cubre: creación del plan mensual, bloqueo de plan > valor contractual, plan
duplicado, historial ACUMULATIVO (sólo hasta el período, nunca meses
futuros), pago parcial y completo por cuota, y bloqueo de sobrepago.
"""

from datetime import date
from decimal import Decimal

import pytest

from sqlalchemy import select

from app.domain.errors import OverpaymentError
from app.models.ap import SupplierInvoice, SupplierPayment
from app.services import contract_payment_service as cps
from app.services.contract_payment_service import (
    ContractScheduleExistsError,
    build_monthly_installments,
)
from tests.helpers import (
    create_account,
    create_company,
    create_supplier,
    create_treasury_account,
    login_admin,
)


def _contract(client, *, company_id, supplier_id, value="500000.00", number="CTR-2026-001"):
    r = client.post(
        "/api/procurement/suppliers/contracts",
        json={
            "companyId": company_id,
            "supplierId": supplier_id,
            "contractNumber": number,
            "value": value,
            "currencyCode": "HNL",
            "startDate": "2026-08-01",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def _monthly_plan(db, contract_id, *, count=10, monthly="50000.00", total="500000.00"):
    rows = build_monthly_installments(
        start_period=date(2026, 8, 1),
        count=count,
        monthly_amount=Decimal(monthly),
        total_value=Decimal(total),
    )
    return cps.create_schedule(
        db, supplier_contract_id=contract_id, schedule_type="MONTHLY", installments=rows
    )


def test_monthly_schedule_generation_and_totals(client, db_session):
    login_admin(client)
    company = create_company(client)
    supplier = create_supplier(client, company_id=company["id"])
    contract = _contract(client, company_id=company["id"], supplier_id=supplier["id"])

    schedule = _monthly_plan(db_session, contract["id"])
    summaries = cps.installment_summaries(db_session, schedule_id=schedule.id, as_of=date(2026, 8, 15))

    assert len(summaries) == 10
    assert sum(s.scheduled_amount for s in summaries) == Decimal("500000.00")
    assert summaries[0].period_label == "Agosto 2026"
    assert summaries[1].period_label == "Septiembre 2026"
    assert all(s.status in {"UPCOMING", "DUE", "OVERDUE"} for s in summaries)


def test_plan_over_contract_value_is_rejected(client, db_session):
    login_admin(client)
    company = create_company(client)
    supplier = create_supplier(client, company_id=company["id"])
    contract = _contract(client, company_id=company["id"], supplier_id=supplier["id"], value="100000.00")

    with pytest.raises(OverpaymentError):
        _monthly_plan(db_session, contract["id"], count=3, monthly="50000.00", total="150000.00")


def test_duplicate_schedule_is_rejected(client, db_session):
    login_admin(client)
    company = create_company(client)
    supplier = create_supplier(client, company_id=company["id"])
    contract = _contract(client, company_id=company["id"], supplier_id=supplier["id"])

    _monthly_plan(db_session, contract["id"])
    with pytest.raises(ContractScheduleExistsError):
        _monthly_plan(db_session, contract["id"])


def test_accumulative_history_never_shows_future_periods(client, db_session):
    login_admin(client)
    company = create_company(client)
    supplier = create_supplier(client, company_id=company["id"])
    contract = _contract(client, company_id=company["id"], supplier_id=supplier["id"])
    schedule = _monthly_plan(db_session, contract["id"])

    aug = cps.history_through(db_session, schedule_id=schedule.id, period_year=2026, period_month=8)
    assert [s.period_label for s in aug] == ["Agosto 2026"]

    sep = cps.history_through(db_session, schedule_id=schedule.id, period_year=2026, period_month=9)
    assert [s.period_label for s in sep] == ["Agosto 2026", "Septiembre 2026"]

    oct_ = cps.history_through(db_session, schedule_id=schedule.id, period_year=2026, period_month=10)
    assert [s.period_label for s in oct_] == ["Agosto 2026", "Septiembre 2026", "Octubre 2026"]
    # nunca noviembre/diciembre
    assert "Noviembre 2026" not in [s.period_label for s in oct_]


def _real_supplier_payment(client, db, *, company, supplier, amount, tag):
    """Crea un SupplierPayment REAL vía la API (contabiliza por el Posting
    Engine) y devuelve la fila. Sin fixtures inventadas."""
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
            "originalAmount": "200000.00", "remittanceDate": "2026-01-01",
        },
    )
    inv = client.post(
        "/api/ap/supplier-invoices",
        json={
            "companyId": company["id"], "supplierId": supplier["id"],
            "invoiceNumber": f"F-{amount}", "scope": "GENERAL",
            "expenseAccountId": expense["id"], "payableAccountId": payable["id"],
            "currencyCode": "HNL", "amount": str(amount), "invoiceDate": "2026-09-01",
            "dueDate": "2026-09-30",
        },
    ).json()
    client.post(f"/api/ap/supplier-invoices/{inv['id']}/approve")
    r = client.post(
        f"/api/ap/supplier-invoices/{inv['id']}/payments",
        json={"treasuryAccountId": bank["id"], "amount": str(amount), "paymentDate": "2026-09-03"},
    )
    assert r.status_code == 201, r.text
    return db.execute(
        select(SupplierPayment)
        .join(SupplierInvoice, SupplierPayment.supplier_invoice_id == SupplierInvoice.id)
        .where(SupplierInvoice.id == inv["id"])
    ).scalar_one()


def test_partial_then_full_installment_via_allocations(client, db_session):
    login_admin(client)
    company = create_company(client)
    supplier = create_supplier(client, company_id=company["id"])
    contract = _contract(client, company_id=company["id"], supplier_id=supplier["id"])
    schedule = _monthly_plan(db_session, contract["id"])
    sept = [
        s for s in cps.installment_summaries(db_session, schedule_id=schedule.id)
        if s.period_label == "Septiembre 2026"
    ][0]

    p1 = _real_supplier_payment(client, db_session, company=company, supplier=supplier, amount="30000.00", tag="09")
    cps.allocate_payment(
        db_session,
        supplier_payment_id=p1.id,
        allocations=[{"installment_id": sept.installment_id, "amount_applied": "30000.00"}],
    )
    after1 = [
        s for s in cps.installment_summaries(db_session, schedule_id=schedule.id)
        if s.installment_id == sept.installment_id
    ][0]
    assert after1.paid == Decimal("30000.00")
    assert after1.remaining == Decimal("20000.00")
    assert after1.status == "PARTIALLY_PAID"

    # Sobrepago sobre el saldo -> bloqueado.
    p2 = _real_supplier_payment(client, db_session, company=company, supplier=supplier, amount="20000.00", tag="19")
    with pytest.raises(OverpaymentError):
        cps.allocate_payment(
            db_session,
            supplier_payment_id=p2.id,
            allocations=[{"installment_id": sept.installment_id, "amount_applied": "25000.00"}],
        )

    cps.allocate_payment(
        db_session,
        supplier_payment_id=p2.id,
        allocations=[{"installment_id": sept.installment_id, "amount_applied": "20000.00"}],
    )
    after2 = [
        s for s in cps.installment_summaries(db_session, schedule_id=schedule.id)
        if s.installment_id == sept.installment_id
    ][0]
    assert after2.paid == Decimal("50000.00")
    assert after2.remaining == Decimal("0.00")
    assert after2.status == "PAID"

    summary = cps.contract_summary(db_session, schedule_id=schedule.id, as_of=date(2026, 9, 15))
    assert summary.paid_accumulated == Decimal("50000.00")
    assert summary.contract_balance == Decimal("450000.00")
