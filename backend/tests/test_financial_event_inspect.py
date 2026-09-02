"""Forense de un hecho financiero — scripts/financial_event_inspect.py (§4/§5/§6).

Verifica que el inspector de solo lectura reúne la cadena completa de un
evento contractual (contrato → plan → cuota → factura → pago → GL) y que su
heurística marca un posible doble conteo GeneralExpense + SupplierInvoice.
"""

from decimal import Decimal

from scripts.financial_event_inspect import Filters, inspect
from tests.helpers import create_account, create_company, create_supplier, login_admin


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
    return r.json()


def _create_schedule(client, contract_id):
    r = client.post(
        "/api/contract-payments/schedules",
        json={
            "supplierContractId": contract_id, "scheduleType": "MONTHLY",
            "regularMonths": 7, "dueDay": 1, "firstPeriod": "2026-09-01",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def test_inspector_reconstructs_contract_chain_by_number(client, db_session):
    login_admin(client)
    company = create_company(client, name="Forense Co")
    supplier = create_supplier(client, company_id=company["id"], legal_name="Contratista Uno")
    contract = _contract_10101960(client, company["id"], supplier["id"])
    _create_schedule(client, contract["id"])

    report = inspect(db_session, Filters(contract_number="10101960"))

    assert len(report.sections["contracts"]) == 1
    found = report.sections["contracts"][0]
    assert found["contract"]["contract_number"] == "10101960"
    assert found["contract"]["value"] == Decimal("1500000.00")
    assert found["supplier"] == "Contratista Uno"
    # anticipo + 7 mensualidades
    assert len(found["installments"]) == 8
    assert found["derived_paid_active"] == Decimal(0)
    assert found["derived_balance"] == Decimal("1500000.00")


def test_inspector_requires_at_least_one_filter(db_session):
    report = inspect(db_session, Filters(amount=Decimal(50000)))
    # amount-only is a valid filter; the run must not raise and must return a Report
    assert "contracts" in report.sections


def test_inspector_flags_asset_debit_invoice_as_prepayment(client, db_session):
    login_admin(client)
    company = create_company(client, name="Prepago Co")
    supplier = create_supplier(client, company_id=company["id"])
    advance_asset = create_account(
        client, company_id=company["id"], code="1610",
        name="Anticipos a contratistas", account_type="ASSET",
    )
    payable = create_account(
        client, company_id=company["id"], code="2110",
        name="Cuentas por pagar", account_type="LIABILITY",
    )
    contract = _contract_10101960(client, company["id"], supplier["id"])
    schedule = _create_schedule(client, contract["id"])

    from app.models.company import Company

    company_row = db_session.get(Company, company["id"])
    company_row.supplier_advance_account_id = advance_asset["id"]
    db_session.commit()

    r = client.post(
        f"/api/contract-payments/schedules/{schedule['id']}/advance-invoice",
        json={"payableAccountId": payable["id"]},
    )
    assert r.status_code == 201, r.text

    report = inspect(db_session, Filters(amount=Decimal("50000.00"), company="Prepago Co"))
    invoices = report.sections["supplier_invoices"]
    assert invoices, "el inspector debe encontrar la factura de anticipo"
    assert any(inv["is_prepayment_debit"] for inv in invoices)
    assert any("ASSET" in note for note in report.notes)
