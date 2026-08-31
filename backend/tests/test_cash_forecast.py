from datetime import date, timedelta
from decimal import Decimal

from tests.helpers import (
    create_account,
    create_company,
    create_supplier,
    create_treasury_account,
    login_admin,
)


def _setup(client):
    company = create_company(client)
    bank_gl = create_account(client, company_id=company["id"], code="1100", name="Bancos", account_type="ASSET")
    expense = create_account(client, company_id=company["id"], code="5200", name="Mat", account_type="EXPENSE")
    payable = create_account(client, company_id=company["id"], code="2100", name="CxP", account_type="LIABILITY")
    contributions = create_account(client, company_id=company["id"], code="3100", name="Aportes", account_type="EQUITY")
    bank = create_treasury_account(client, company_id=company["id"], gl_account_id=bank_gl["id"])
    supplier = create_supplier(client, company_id=company["id"])
    client.post(
        "/api/treasury/remittances",
        json={
            "companyId": company["id"],
            "treasuryAccountId": bank["id"],
            "counterAccountId": contributions["id"],
            "sender": "Fondeo",
            "currencyCode": "HNL",
            "originalAmount": "1000.00",
            "remittanceDate": "2026-01-01",
        },
    )
    return company, bank, expense, payable, supplier


def test_cash_forecast_projects_13_weeks_and_flags_liquidity_shortfall(client):
    login_admin(client)
    company, _bank, expense, payable, supplier = _setup(client)

    # Un pago grande de proveedor que vence en ~2 semanas -> descubierto.
    invoice = client.post(
        "/api/ap/supplier-invoices",
        json={
            "companyId": company["id"],
            "supplierId": supplier["id"],
            "invoiceNumber": "F-CF-1",
            "scope": "GENERAL",
            "expenseAccountId": expense["id"],
            "payableAccountId": payable["id"],
            "currencyCode": "HNL",
            "amount": "5000.00",
            "taxAmount": "0.00",
            "invoiceDate": str(date.today()),
            "dueDate": str(date.today() + timedelta(days=14)),
        },
    ).json()
    client.post(f"/api/ap/supplier-invoices/{invoice['id']}/approve")

    response = client.get(f"/api/financial-control/cash-forecast?companyId={company['id']}")
    assert response.status_code == 200, response.text
    body = response.json()

    assert len(body["weeks"]) == 13
    assert Decimal(body["openingBalance"]) == Decimal("1000.00")
    assert body["hasLiquidityAlert"] is True
    # El descubierto ocurre en la semana 2 (día 14).
    assert body["firstNegativeWeekIndex"] == 2
    assert Decimal(body["minProjectedBalance"]) == Decimal("-4000.00")

    week2 = body["weeks"][2]
    assert Decimal(week2["outflows"]) == Decimal("5000.00")
    assert Decimal(week2["projectedBalance"]) == Decimal("-4000.00")


def test_cash_forecast_no_alert_when_balance_stays_positive(client):
    login_admin(client)
    company, _bank, _expense, _payable, _supplier = _setup(client)

    body = client.get(
        f"/api/financial-control/cash-forecast?companyId={company['id']}"
    ).json()
    assert body["hasLiquidityAlert"] is False
    assert body["firstNegativeWeekIndex"] is None
    assert all(Decimal(w["projectedBalance"]) == Decimal("1000.00") for w in body["weeks"])
