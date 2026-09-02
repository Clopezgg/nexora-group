"""scripts/financial_reconciliation.py — preview / apply / blocked (§5/§6/§55)."""

from decimal import Decimal

import pytest

from app.services import contract_payment_service as cps
from scripts import financial_reconciliation as fr
from tests.helpers import create_account, create_company, create_supplier, create_treasury_account, login_admin
from tests.test_contract_payment_control import _contract, _monthly_plan


def _legacy_plan(client, db_session, *, number):
    company = create_company(client)
    supplier = create_supplier(client, company_id=company["id"])
    contract = _contract(
        client, company_id=company["id"], supplier_id=supplier["id"],
        value="1500000.00", number=number,
    )
    schedule = _monthly_plan(
        db_session, contract["id"], count=7, monthly="214285.71", total="1500000.00"
    )
    return company, supplier, contract, schedule


_TERMS = [
    "--contract-number", "",  # filled per test
    "--advance-amount", "50000.00",
    "--advance-due-date", "2026-08-22",
    "--retention", "0",
    "--regular-months", "7",
    "--due-day", "1",
    "--first-period", "2026-09",
]


def _args(number, mode, *extra):
    argv = ["--mode", mode, *_TERMS, *extra]
    argv[argv.index("--contract-number") + 1] = number
    return argv


def test_preview_does_not_persist(client, db_session, capsys):
    login_admin(client)
    _c, _s, _contract, schedule = _legacy_plan(client, db_session, number="REC-1")

    rc = fr.main(_args("REC-1", "preview"))
    assert rc == 0
    out = capsys.readouterr().out
    assert '"after"' in out
    assert '"totalScheduled": "1500000.00"' in out

    db_session.expire_all()
    still = cps.installment_summaries(db_session, schedule_id=schedule.id)
    assert len(still) == 7
    assert all(s.installment_kind == "REGULAR" for s in still)


def test_apply_requires_confirm_and_reason(client, db_session):
    login_admin(client)
    _legacy_plan(client, db_session, number="REC-2")
    with pytest.raises(SystemExit):
        fr.main(_args("REC-2", "apply"))
    with pytest.raises(SystemExit):
        fr.main(_args("REC-2", "apply", "--confirm", "APPLY", "--reason", "corto"))


def test_apply_rebuilds_canonically_and_audits(client, db_session):
    login_admin(client)
    company, _s, _contract, schedule = _legacy_plan(client, db_session, number="REC-3")

    rc = fr.main(
        _args(
            "REC-3", "apply",
            "--confirm", "APPLY",
            "--reason", "Plan legacy sin anticipo; correccion autorizada ORDEN MAESTRA",
        )
    )
    assert rc == 0

    db_session.expire_all()
    summaries = cps.installment_summaries(db_session, schedule_id=schedule.id)
    assert [s.installment_kind for s in summaries] == ["ADVANCE"] + ["REGULAR"] * 7
    assert summaries[0].scheduled_amount == Decimal("50000.00")
    assert summaries[0].due_date.isoformat() == "2026-08-22"
    assert sum(s.scheduled_amount for s in summaries) == Decimal("1500000.00")

    audit = client.get(
        f"/api/audit?companyId={company['id']}&entityType=contract.payment_schedule"
    ).json()
    assert any(e["action"] == "contract.payment_schedule.rebuild.maintenance" for e in audit)


def test_apply_is_blocked_when_installment_paid(client, db_session):
    login_admin(client)
    company, supplier, contract, schedule = _legacy_plan(client, db_session, number="REC-4")
    bank_gl = create_account(client, company_id=company["id"], code="1102", name="Banco", account_type="ASSET")
    bank = create_treasury_account(client, company_id=company["id"], gl_account_id=bank_gl["id"])
    expense = create_account(client, company_id=company["id"], code="5101", name="Obra", account_type="EXPENSE")
    payable = create_account(client, company_id=company["id"], code="2101", name="CxP", account_type="LIABILITY")
    first = cps.installment_summaries(db_session, schedule_id=schedule.id)[0]
    inv = client.post(
        "/api/ap/supplier-invoices",
        json={
            "companyId": company["id"], "supplierId": supplier["id"], "invoiceNumber": "F-REC-4",
            "scope": "GENERAL", "expenseAccountId": expense["id"], "payableAccountId": payable["id"],
            "currencyCode": "HNL", "amount": "214285.71", "invoiceDate": "2026-09-01",
            "dueDate": "2026-09-30", "supplierContractId": contract["id"],
        },
    ).json()
    client.post(f"/api/ap/supplier-invoices/{inv['id']}/approve")
    client.post(
        f"/api/ap/supplier-invoices/{inv['id']}/payments",
        json={
            "treasuryAccountId": bank["id"], "amount": "214285.71", "paymentDate": "2026-09-03",
            "contractAllocations": [{"installmentId": str(first.installment_id), "amountApplied": "214285.71"}],
        },
    )

    rc = fr.main(
        _args("REC-4", "apply", "--confirm", "APPLY", "--reason", "Intento de rebuild con pago aplicado")
    )
    assert rc == 3
