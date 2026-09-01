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


def _contract(
    client, *, company_id, supplier_id, value="500000.00", number="CTR-2026-001", category="LABOR"
):
    r = client.post(
        "/api/procurement/suppliers/contracts",
        json={
            "companyId": company_id,
            "supplierId": supplier_id,
            "contractNumber": number,
            "contractCategory": category,
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


# --------------------------------------------------------------------------- #
# PR 2 — allocation vía el endpoint de pago AP + reversal                      #
# --------------------------------------------------------------------------- #

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
    assert r.json()["supplierContractId"] == contract_id
    client.post(f"/api/ap/supplier-invoices/{r.json()['id']}/approve")
    return r.json()


def test_contract_payment_allocation_via_ap_endpoint_and_reversal(client, db_session):
    login_admin(client)
    company = create_company(client)
    supplier = create_supplier(client, company_id=company["id"])
    contract = _contract(client, company_id=company["id"], supplier_id=supplier["id"])
    schedule = _monthly_plan(db_session, contract["id"])
    bank, expense, payable = _ap_setup(client, company, tag="70")

    invoice = _contract_invoice(
        client, company=company, supplier=supplier, contract_id=contract["id"],
        expense=expense, payable=payable, amount="50000.00", number="F-CTR-AUG",
    )
    aug = [
        s for s in cps.installment_summaries(db_session, schedule_id=schedule.id)
        if s.period_label == "Agosto 2026"
    ][0]

    pay = client.post(
        f"/api/ap/supplier-invoices/{invoice['id']}/payments",
        json={
            "treasuryAccountId": bank["id"], "amount": "50000.00", "paymentDate": "2026-09-03",
            "contractAllocations": [
                {"installmentId": str(aug.installment_id), "amountApplied": "50000.00"}
            ],
        },
    )
    assert pay.status_code == 201, pay.text
    payment_id = pay.json()["id"]

    db_session.expire_all()
    after = [
        s for s in cps.installment_summaries(db_session, schedule_id=schedule.id)
        if s.installment_id == aug.installment_id
    ][0]
    assert after.paid == Decimal("50000.00")
    assert after.status == "PAID"

    # Reversal del pago -> reabre la cuota y baja amount_paid.
    rev = client.post(
        f"/api/ap/supplier-payments/{payment_id}/reverse",
        json={"reason": "Pago duplicado"},
    )
    assert rev.status_code in (200, 201), rev.text

    db_session.expire_all()
    reopened = [
        s for s in cps.installment_summaries(db_session, schedule_id=schedule.id)
        if s.installment_id == aug.installment_id
    ][0]
    assert reopened.paid == Decimal("0.00")
    assert reopened.remaining == Decimal("50000.00")
    assert reopened.status != "PAID"

    invoice_after = client.get(f"/api/ap/supplier-invoices/{invoice['id']}").json()
    assert float(invoice_after["amountPaid"]) == 0.0


def test_contract_allocation_sum_must_equal_payment_amount(client, db_session):
    login_admin(client)
    company = create_company(client)
    supplier = create_supplier(client, company_id=company["id"])
    contract = _contract(client, company_id=company["id"], supplier_id=supplier["id"])
    schedule = _monthly_plan(db_session, contract["id"])
    bank, expense, payable = _ap_setup(client, company, tag="71")
    invoice = _contract_invoice(
        client, company=company, supplier=supplier, contract_id=contract["id"],
        expense=expense, payable=payable, amount="50000.00", number="F-CTR-X",
    )
    aug = cps.installment_summaries(db_session, schedule_id=schedule.id)[0]

    bad = client.post(
        f"/api/ap/supplier-invoices/{invoice['id']}/payments",
        json={
            "treasuryAccountId": bank["id"], "amount": "50000.00", "paymentDate": "2026-09-03",
            "contractAllocations": [
                {"installmentId": str(aug.installment_id), "amountApplied": "40000.00"}
            ],
        },
    )
    assert bad.status_code == 422, bad.text


def test_fifo_proposal_spreads_over_oldest_unpaid_first(client, db_session):
    login_admin(client)
    company = create_company(client)
    supplier = create_supplier(client, company_id=company["id"])
    contract = _contract(client, company_id=company["id"], supplier_id=supplier["id"])
    schedule = _monthly_plan(db_session, contract["id"])

    proposal = cps.propose_fifo(
        db_session, schedule_id=schedule.id, amount=Decimal("60000.00"), as_of=date(2026, 10, 1)
    )
    assert [p["period_label"] for p in proposal] == ["Agosto 2026", "Septiembre 2026"]
    assert proposal[0]["amount_applied"] == Decimal("50000.00")
    assert proposal[1]["amount_applied"] == Decimal("10000.00")


def test_invoice_rejects_contract_of_another_supplier(client, db_session):
    login_admin(client)
    company = create_company(client)
    supplier_a = create_supplier(client, company_id=company["id"], legal_name="Proveedor A")
    supplier_b = create_supplier(client, company_id=company["id"], legal_name="Proveedor B")
    contract = _contract(
        client, company_id=company["id"], supplier_id=supplier_a["id"], number="CTR-A"
    )
    _bank, expense, payable = _ap_setup(client, company, tag="72")

    r = client.post(
        "/api/ap/supplier-invoices",
        json={
            "companyId": company["id"], "supplierId": supplier_b["id"],
            "invoiceNumber": "F-WRONG", "scope": "GENERAL",
            "expenseAccountId": expense["id"], "payableAccountId": payable["id"],
            "currencyCode": "HNL", "amount": "1000.00", "invoiceDate": "2026-09-01",
            "dueDate": "2026-09-30", "supplierContractId": contract["id"],
        },
    )
    assert r.status_code == 422, r.text


# --------------------------------------------------------------------------- #
# PR 5 — comprobante contractual: historial acumulativo + totales en el PDF   #
# --------------------------------------------------------------------------- #

def test_contract_voucher_pdf_shows_accumulative_history_and_totals(client, db_session):
    login_admin(client)
    company = create_company(client)
    client.patch(
        f"/api/master-data/companies/{company['id']}/profile",
        json={
            "voucherApproverName": "CARLOS HUMBERTO LOPEZ",
            "addressLine1": "Boulevard Morazan, Edificio Nexora",
            "city": "Tegucigalpa",
            "fiscalId": "08019999123456",
        },
    )
    supplier = create_supplier(client, company_id=company["id"], legal_name="LESTER GEOVANY RIVAS ZEPEDA")
    contract = _contract(client, company_id=company["id"], supplier_id=supplier["id"])
    schedule = _monthly_plan(db_session, contract["id"])
    bank, expense, payable = _ap_setup(client, company, tag="80")

    summaries = cps.installment_summaries(db_session, schedule_id=schedule.id)
    aug = [s for s in summaries if s.period_label == "Agosto 2026"][0]
    sep = [s for s in summaries if s.period_label == "Septiembre 2026"][0]

    def _pay_contract(number, installment, amount, *, obs, ref):
        inv = _contract_invoice(
            client, company=company, supplier=supplier, contract_id=contract["id"],
            expense=expense, payable=payable, amount=amount, number=number,
        )
        r = client.post(
            f"/api/ap/supplier-invoices/{inv['id']}/payments",
            json={
                "treasuryAccountId": bank["id"], "amount": amount, "paymentDate": "2026-09-03",
                "contractAllocations": [
                    {"installmentId": str(installment.installment_id), "amountApplied": amount}
                ],
                "bankTransactionReference": ref,
                "paymentObservations": obs,
            },
        )
        assert r.status_code == 201, r.text
        return db_session.execute(
            select(SupplierPayment)
            .join(SupplierInvoice, SupplierPayment.supplier_invoice_id == SupplierInvoice.id)
            .where(SupplierInvoice.id == inv["id"])
        ).scalar_one()

    p_aug = _pay_contract("F-AUG", aug, "50000.00", obs="Mano de obra agosto 2026", ref="ATL-93829172")
    db_session.commit()

    voucher = client.get(
        f"/api/treasury/vouchers/{p_aug.accounting_document_id}"
        "?beneficiary=LESTER%20GEOVANY%20RIVAS%20ZEPEDA&paymentMethod=Efectivo"
    )
    assert voucher.status_code == 200, voucher.text
    text = voucher.content.decode("latin-1")
    assert "Pagos del contrato a la fecha" in text
    assert "Agosto 2026" in text
    assert "Septiembre 2026" not in text  # aún no ocurrió (§38)
    assert "CTR-2026-001" in text
    # §25: el comprobante resuelve la categoría del contrato en español.
    assert "ategor" in text  # "Categoría del contrato" (tolerante a codificación PDF)
    assert "Mano de obra" in text
    assert "Valor contractual" in text
    assert "Pago actual" in text
    assert "ATL-93829172" in text
    assert "Mano de obra agosto" in text
    assert "Boulevard Morazan" in text
    assert "08019999123456" in text
    assert str(p_aug.accounting_document_id) not in text  # sin UUID

    # Septiembre -> el voucher de septiembre incluye Ago + Sep, NUNCA octubre.
    p_sep = _pay_contract("F-SEP", sep, "50000.00", obs="Mano de obra septiembre", ref="ATL-99999")
    db_session.commit()
    voucher_sep = client.get(
        f"/api/treasury/vouchers/{p_sep.accounting_document_id}"
        "?beneficiary=LESTER%20GEOVANY%20RIVAS%20ZEPEDA&paymentMethod=Efectivo"
    )
    assert voucher_sep.status_code == 200, voucher_sep.text
    text_sep = voucher_sep.content.decode("latin-1")
    assert "Agosto 2026" in text_sep
    assert "Septiembre 2026" in text_sep
    assert "Octubre 2026" not in text_sep
    assert "Pagado anteriormente" in text_sep


def test_issued_voucher_keeps_old_company_data_after_master_data_changes(client, db_session):
    """§62 — emitir comprobante, luego cambiar la dirección/aprobador de la
    empresa; reimprimir el comprobante viejo debe conservar los datos viejos
    (lee del snapshot VoucherIssuance, no de master data en vivo)."""
    from app.models.voucher_issuance import VoucherIssuance

    login_admin(client)
    company = create_company(client)
    client.patch(
        f"/api/master-data/companies/{company['id']}/profile",
        json={
            "voucherApproverName": "CARLOS HUMBERTO LOPEZ",
            "addressLine1": "Boulevard Morazan, Edificio Nexora",
            "city": "Tegucigalpa",
            "fiscalId": "08019999123456",
        },
    )
    supplier = create_supplier(client, company_id=company["id"], legal_name="LESTER GEOVANY RIVAS ZEPEDA")
    contract = _contract(client, company_id=company["id"], supplier_id=supplier["id"])
    schedule = _monthly_plan(db_session, contract["id"])
    bank, expense, payable = _ap_setup(client, company, tag="81")

    aug = [s for s in cps.installment_summaries(db_session, schedule_id=schedule.id)
           if s.period_label == "Agosto 2026"][0]
    inv = _contract_invoice(
        client, company=company, supplier=supplier, contract_id=contract["id"],
        expense=expense, payable=payable, amount="50000.00", number="F-AUG",
    )
    r = client.post(
        f"/api/ap/supplier-invoices/{inv['id']}/payments",
        json={
            "treasuryAccountId": bank["id"], "amount": "50000.00", "paymentDate": "2026-09-03",
            "contractAllocations": [
                {"installmentId": str(aug.installment_id), "amountApplied": "50000.00"}
            ],
        },
    )
    assert r.status_code == 201, r.text
    payment = db_session.execute(
        select(SupplierPayment).join(
            SupplierInvoice, SupplierPayment.supplier_invoice_id == SupplierInvoice.id
        ).where(SupplierInvoice.id == inv["id"])
    ).scalar_one()
    db_session.commit()
    doc_id = payment.accounting_document_id

    url = (
        f"/api/treasury/vouchers/{doc_id}"
        "?beneficiary=LESTER%20GEOVANY%20RIVAS%20ZEPEDA&paymentMethod=Efectivo"
    )
    first = client.get(url)
    assert first.status_code == 200
    assert "Boulevard Morazan" in first.content.decode("latin-1")

    issuance_count = db_session.execute(
        select(VoucherIssuance).where(VoucherIssuance.accounting_document_id == doc_id)
    ).scalars().all()
    assert len(issuance_count) == 1

    # Master data cambia DESPUÉS de emitir.
    client.patch(
        f"/api/master-data/companies/{company['id']}/profile",
        json={
            "voucherApproverName": "OTRA PERSONA APROBADORA",
            "addressLine1": "Nueva Sede Comayaguela Kilometro 5",
            "city": "Comayaguela",
        },
    )
    db_session.commit()

    reprint = client.get(url)
    assert reprint.status_code == 200
    text = reprint.content.decode("latin-1")
    assert "Boulevard Morazan" in text          # dirección vieja conservada
    assert "Nueva Sede Comayaguela" not in text  # master data nueva NO aparece
    assert "OTRA PERSONA APROBADORA" not in text
    # sigue habiendo exactamente una fila de emisión
    assert len(db_session.execute(
        select(VoucherIssuance).where(VoucherIssuance.accounting_document_id == doc_id)
    ).scalars().all()) == 1
