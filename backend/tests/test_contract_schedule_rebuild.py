"""Contract Schedule Repair / Rebuild — preview + apply (ORDEN MAESTRA §9/§10).

Un plan legacy (vencimientos a fin de mes, sin anticipo) se corrige al motor
canónico: preview ANTES/DESPUÉS sin persistir, apply auditado y transaccional,
bloqueado si ya hay pagos aplicados.
"""

from decimal import Decimal

from app.services import contract_payment_service as cps
from tests.helpers import create_account, create_company, create_supplier, create_treasury_account, login_admin
from tests.test_contract_payment_control import _contract, _monthly_plan


def _rebuild_terms(**over):
    base = {
        "reason": "Corrección: el plan legacy ignoró el anticipo contractual",
        "regularMonths": 7,
        "dueDay": 1,
        "firstPeriod": "2026-09-01",
        "advanceAmount": "50000.00",
        "advanceDueDate": "2026-08-22",
        "retentionPercentage": "0",
    }
    base.update(over)
    return base


def test_rebuild_preview_shows_before_and_after_without_persisting(client, db_session):
    login_admin(client)
    company = create_company(client)
    supplier = create_supplier(client, company_id=company["id"])
    contract = _contract(
        client, company_id=company["id"], supplier_id=supplier["id"],
        value="1500000.00", number="CTR-RB-1",
    )
    schedule = _monthly_plan(
        db_session, contract["id"], count=7, monthly="214285.71", total="1500000.00"
    )

    preview = client.post(
        f"/api/contract-payments/schedules/{schedule.id}/rebuild/preview",
        json={k: v for k, v in _rebuild_terms().items() if k != "reason"},
    )
    assert preview.status_code == 200, preview.text
    body = preview.json()
    assert body["blocked"] is False
    # ANTES: 7 cuotas legacy, sin anticipo
    assert len(body["before"]["installments"]) == 7
    assert all(i["kind"] == "REGULAR" for i in body["before"]["installments"])
    # DESPUÉS: anticipo + 7 mensualidades, total exacto
    after = body["after"]["installments"]
    assert [i["kind"] for i in after] == ["ADVANCE"] + ["REGULAR"] * 7
    assert after[0]["scheduledAmount"] == "50000.00"
    assert after[0]["dueDate"] == "2026-08-22"
    assert [i["dueDate"] for i in after[1:]] == [
        "2026-09-01", "2026-10-01", "2026-11-01", "2026-12-01",
        "2027-01-01", "2027-02-01", "2027-03-01",
    ]
    assert body["after"]["totalScheduled"] == "1500000.00"

    # Nada se persistió.
    db_session.expire_all()
    still = cps.installment_summaries(db_session, schedule_id=schedule.id)
    assert len(still) == 7
    assert all(s.installment_kind == "REGULAR" for s in still)


def test_rebuild_apply_replaces_plan_with_canonical_engine_and_audits(client, db_session):
    login_admin(client)
    company = create_company(client)
    supplier = create_supplier(client, company_id=company["id"])
    contract = _contract(
        client, company_id=company["id"], supplier_id=supplier["id"],
        value="1500000.00", number="CTR-RB-2",
    )
    schedule = _monthly_plan(
        db_session, contract["id"], count=7, monthly="214285.71", total="1500000.00"
    )

    applied = client.post(
        f"/api/contract-payments/schedules/{schedule.id}/rebuild",
        json=_rebuild_terms(),
    )
    assert applied.status_code == 200, applied.text

    db_session.expire_all()
    summaries = cps.installment_summaries(db_session, schedule_id=schedule.id)
    assert [s.installment_kind for s in summaries] == ["ADVANCE"] + ["REGULAR"] * 7
    assert sum(s.scheduled_amount for s in summaries) == Decimal("1500000.00")
    advance = summaries[0]
    assert advance.scheduled_amount == Decimal("50000.00")
    assert advance.due_date.isoformat() == "2026-08-22"

    audit = client.get(
        f"/api/audit?companyId={company['id']}&entityType=contract.payment_schedule"
    ).json()
    entry = next(e for e in audit if e["action"] == "contract.payment_schedule.rebuild")
    assert entry["before"]["installments"]
    assert entry["after"]["reason"].startswith("Corrección")


def test_rebuild_requires_a_reason(client, db_session):
    login_admin(client)
    company = create_company(client)
    supplier = create_supplier(client, company_id=company["id"])
    contract = _contract(
        client, company_id=company["id"], supplier_id=supplier["id"],
        value="1500000.00", number="CTR-RB-3",
    )
    schedule = _monthly_plan(
        db_session, contract["id"], count=7, monthly="214285.71", total="1500000.00"
    )
    r = client.post(
        f"/api/contract-payments/schedules/{schedule.id}/rebuild",
        json=_rebuild_terms(reason="corto"),
    )
    assert r.status_code == 422, r.text


def test_rebuild_is_blocked_once_an_installment_has_an_active_payment(client, db_session):
    login_admin(client)
    company = create_company(client)
    supplier = create_supplier(client, company_id=company["id"])
    contract = _contract(
        client, company_id=company["id"], supplier_id=supplier["id"],
        value="1500000.00", number="CTR-RB-4",
    )
    schedule = _monthly_plan(
        db_session, contract["id"], count=7, monthly="214285.71", total="1500000.00"
    )
    bank_gl = create_account(client, company_id=company["id"], code="1102", name="Banco", account_type="ASSET")
    bank = create_treasury_account(client, company_id=company["id"], gl_account_id=bank_gl["id"])
    expense = create_account(client, company_id=company["id"], code="5101", name="Costo obra", account_type="EXPENSE")
    payable = create_account(client, company_id=company["id"], code="2101", name="CxP", account_type="LIABILITY")

    first = cps.installment_summaries(db_session, schedule_id=schedule.id)[0]
    invoice = client.post(
        "/api/ap/supplier-invoices",
        json={
            "companyId": company["id"], "supplierId": supplier["id"],
            "invoiceNumber": "F-RB-1", "scope": "GENERAL",
            "expenseAccountId": expense["id"], "payableAccountId": payable["id"],
            "currencyCode": "HNL", "amount": "214285.71", "invoiceDate": "2026-09-01",
            "dueDate": "2026-09-30", "supplierContractId": contract["id"],
        },
    ).json()
    client.post(f"/api/ap/supplier-invoices/{invoice['id']}/approve")
    pay = client.post(
        f"/api/ap/supplier-invoices/{invoice['id']}/payments",
        json={
            "treasuryAccountId": bank["id"], "amount": "214285.71", "paymentDate": "2026-09-03",
            "contractAllocations": [
                {"installmentId": str(first.installment_id), "amountApplied": "214285.71"}
            ],
        },
    )
    assert pay.status_code == 201, pay.text

    preview = client.post(
        f"/api/contract-payments/schedules/{schedule.id}/rebuild/preview",
        json={k: v for k, v in _rebuild_terms().items() if k != "reason"},
    )
    assert preview.status_code == 200, preview.text
    assert preview.json()["blocked"] is True

    applied = client.post(
        f"/api/contract-payments/schedules/{schedule.id}/rebuild",
        json=_rebuild_terms(),
    )
    assert applied.status_code == 409, applied.text
