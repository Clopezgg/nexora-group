"""ORDEN MAESTRA §16/§17/§18 — el pago contractual es fail-closed.

Un contrato MONTHLY/CUSTOM (o con ContractPaymentSchedule) NO se puede pagar sin
asignar el pago a cuotas. Sólo un override con permiso propio + motivo lo salta.
"""

from datetime import date
from decimal import Decimal

from app.models.permission import UserCompanyAccess
from app.services import contract_payment_service as cps
from app.services.contract_payment_service import build_monthly_installments
from tests.helpers import (
    create_account,
    create_company,
    create_supplier,
    create_treasury_account,
    create_user_with_role,
    login_admin,
    login_as,
)


def _plan(db, contract_id):
    rows = build_monthly_installments(
        start_period=date(2026, 8, 1), count=10,
        monthly_amount=Decimal("50000.00"), total_value=Decimal("500000.00"),
    )
    return cps.create_schedule(
        db, supplier_contract_id=contract_id, schedule_type="MONTHLY", installments=rows
    )


def _contract(client, company_id, supplier_id, *, number, terms="MONTHLY"):
    r = client.post(
        "/api/procurement/suppliers/contracts",
        json={
            "companyId": company_id, "supplierId": supplier_id, "contractNumber": number,
            "value": "500000.00", "currencyCode": "HNL", "startDate": "2026-08-01",
            "paymentTermsType": terms,
        },
    )
    assert r.status_code == 201, r.text
    assert r.json()["paymentTermsType"] == terms
    return r.json()


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


def _invoice(client, company, supplier, contract_id, expense, payable, *, number):
    r = client.post(
        "/api/ap/supplier-invoices",
        json={
            "companyId": company["id"], "supplierId": supplier["id"], "invoiceNumber": number,
            "scope": "GENERAL", "expenseAccountId": expense["id"], "payableAccountId": payable["id"],
            "currencyCode": "HNL", "amount": "50000.00", "invoiceDate": "2026-09-01",
            "dueDate": "2026-09-30", "supplierContractId": contract_id,
        },
    )
    assert r.status_code == 201, r.text
    client.post(f"/api/ap/supplier-invoices/{r.json()['id']}/approve")
    return r.json()


def test_monthly_contract_payment_without_allocation_is_422(client, db_session):
    login_admin(client)
    company = create_company(client)
    supplier = create_supplier(client, company_id=company["id"])
    contract = _contract(client, company["id"], supplier["id"], number="CTR-FC-1")
    _plan(db_session, contract["id"])
    bank, expense, payable = _ap_setup(client, company, tag="80")
    invoice = _invoice(client, company, supplier, contract["id"], expense, payable, number="F-FC-1")

    bad = client.post(
        f"/api/ap/supplier-invoices/{invoice['id']}/payments",
        json={"treasuryAccountId": bank["id"], "amount": "50000.00", "paymentDate": "2026-09-03"},
    )
    assert bad.status_code == 422, bad.text
    assert "plan de pagos" in bad.text


def test_monthly_contract_without_schedule_cannot_be_paid(client, db_session):
    login_admin(client)
    company = create_company(client)
    supplier = create_supplier(client, company_id=company["id"])
    contract = _contract(client, company["id"], supplier["id"], number="CTR-FC-2")
    # sin plan
    bank, expense, payable = _ap_setup(client, company, tag="81")
    invoice = _invoice(client, company, supplier, contract["id"], expense, payable, number="F-FC-2")

    bad = client.post(
        f"/api/ap/supplier-invoices/{invoice['id']}/payments",
        json={
            "treasuryAccountId": bank["id"], "amount": "50000.00", "paymentDate": "2026-09-03",
            "contractOverrideReason": "Contrato mal configurado, se paga hoy",
        },
    )
    assert bad.status_code == 422, bad.text
    assert "plan de pagos" in bad.text


def test_override_requires_the_dedicated_permission(client, db_session):
    login_admin(client)
    company = create_company(client)
    supplier = create_supplier(client, company_id=company["id"])
    contract = _contract(client, company["id"], supplier["id"], number="CTR-FC-3")
    _plan(db_session, contract["id"])
    bank, expense, payable = _ap_setup(client, company, tag="82")
    invoice = _invoice(client, company, supplier, contract["id"], expense, payable, number="F-FC-3")

    clerk = create_user_with_role(
        db_session, email="tm-noverride@nexora.group", role_name="Treasury Manager"
    )
    db_session.add(UserCompanyAccess(user_id=clerk.id, company_id=company["id"]))
    db_session.commit()
    login_as(client, email="tm-noverride@nexora.group")

    denied = client.post(
        f"/api/ap/supplier-invoices/{invoice['id']}/payments",
        json={
            "treasuryAccountId": bank["id"], "amount": "50000.00", "paymentDate": "2026-09-03",
            "contractOverrideReason": "Excepcion autorizada por gerencia general",
        },
    )
    assert denied.status_code == 403, denied.text


def test_admin_override_with_reason_is_allowed_and_audited(client, db_session):
    login_admin(client)
    company = create_company(client)
    supplier = create_supplier(client, company_id=company["id"])
    contract = _contract(client, company["id"], supplier["id"], number="CTR-FC-4")
    _plan(db_session, contract["id"])
    bank, expense, payable = _ap_setup(client, company, tag="83")
    invoice = _invoice(client, company, supplier, contract["id"], expense, payable, number="F-FC-4")

    ok = client.post(
        f"/api/ap/supplier-invoices/{invoice['id']}/payments",
        json={
            "treasuryAccountId": bank["id"], "amount": "50000.00", "paymentDate": "2026-09-03",
            "contractOverrideReason": "Excepcion autorizada por gerencia general",
        },
    )
    assert ok.status_code == 201, ok.text
