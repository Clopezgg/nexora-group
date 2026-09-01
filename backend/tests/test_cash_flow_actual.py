"""Flujo de Caja REAL — últimas 13 semanas (ORDEN MAESTRA — FIORI / CASH
FLOW / TREASURY DIRECTION, §12-§14, §20 bloque CASH).

- Una remesa de L100,000 aparece UNA sola vez en el flujo real (§12, sin
  doble conteo).
- Un aporte de capital y un financiamiento son ENTRADA de caja pero NO son
  ingreso contable (§13).
- El flujo real y el forecast son endpoints distintos (§4/§14).
"""

from decimal import Decimal

from tests.helpers import (
    create_account,
    create_company,
    create_treasury_account,
    login_admin,
)


def _company_with_bank(client):
    company = create_company(client)
    bank_gl = create_account(client, company_id=company["id"], code="1110", name="Banco", account_type="ASSET")
    bank = create_treasury_account(client, company_id=company["id"], gl_account_id=bank_gl["id"], name="Banco")
    return company, bank


def _remittance(client, company, bank, *, counter_id, origin_type, amount):
    r = client.post(
        "/api/treasury/remittances",
        json={
            "companyId": company["id"], "treasuryAccountId": bank["id"],
            "counterAccountId": counter_id, "originType": origin_type,
            "sender": "Aportante", "currencyCode": "HNL",
            "originalAmount": amount, "remittanceDate": "2026-08-20",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def test_remittance_appears_once_in_actual_cash_flow(client):
    login_admin(client)
    company, bank = _company_with_bank(client)
    equity = create_account(client, company_id=company["id"], code="3100", name="Aportes", account_type="EQUITY")
    _remittance(client, company, bank, counter_id=equity["id"], origin_type="CAPITAL_CONTRIBUTION", amount="100000.00")

    cf = client.get(f"/api/financial-control/cash-flow-actual?companyId={company['id']}")
    assert cf.status_code == 200, cf.text
    body = cf.json()

    # Contado UNA sola vez — no 200,000.
    assert Decimal(body["totalInflows"]) == Decimal("100000.00")
    assert Decimal(body["totalOutflows"]) == Decimal("0.00")
    assert Decimal(body["inflowByCategory"]["Aportes de capital"]) == Decimal("100000.00")
    assert len(body["weeks"]) == 13
    # El movimiento cae en la última semana (posted_at = ahora).
    assert Decimal(body["weeks"][-1]["inflows"]) == Decimal("100000.00")
    assert Decimal(body["weeks"][-1]["closingBalance"]) == Decimal("100000.00")
    # El saldo de cierre del flujo == saldo real de tesorería.
    assert Decimal(body["closingBalance"]) == Decimal("100000.00")


def test_capital_and_financing_are_cash_but_not_revenue(client):
    login_admin(client)
    company, bank = _company_with_bank(client)
    equity = create_account(client, company_id=company["id"], code="3100", name="Aportes", account_type="EQUITY")
    loan = create_account(client, company_id=company["id"], code="2300", name="Préstamo bancario", account_type="LIABILITY")

    _remittance(client, company, bank, counter_id=equity["id"], origin_type="CAPITAL_CONTRIBUTION", amount="100000.00")
    _remittance(client, company, bank, counter_id=loan["id"], origin_type="FINANCING", amount="200000.00")

    cf = client.get(f"/api/financial-control/cash-flow-actual?companyId={company['id']}").json()
    assert Decimal(cf["totalInflows"]) == Decimal("300000.00")
    assert Decimal(cf["inflowByCategory"]["Aportes de capital"]) == Decimal("100000.00")
    assert Decimal(cf["inflowByCategory"]["Financiamiento recibido"]) == Decimal("200000.00")

    # Contabilidad de devengo intacta: nada de esto es ingreso (§13).
    pnl = client.get(f"/api/reports/income-statement?companyId={company['id']}").json()
    assert Decimal(pnl["totalRevenue"]) == Decimal("0.00")
    assert Decimal(pnl["netIncome"]) == Decimal("0.00")


def test_supplier_payment_is_an_outflow_in_actual_cash_flow(client):
    login_admin(client)
    company, bank = _company_with_bank(client)
    equity = create_account(client, company_id=company["id"], code="3100", name="Aportes", account_type="EQUITY")
    _remittance(client, company, bank, counter_id=equity["id"], origin_type="CAPITAL_CONTRIBUTION", amount="50000.00")

    expense_gl = create_account(client, company_id=company["id"], code="5210", name="Servicios", account_type="EXPENSE")
    client.post(
        "/api/treasury/general-expenses",
        json={
            "companyId": company["id"], "treasuryAccountId": bank["id"],
            "expenseAccountId": expense_gl["id"], "category": "Luz", "amount": "3000.00",
            "currencyCode": "HNL", "expenseDate": "2026-08-25", "description": "Energía",
        },
    )

    cf = client.get(f"/api/financial-control/cash-flow-actual?companyId={company['id']}").json()
    assert Decimal(cf["totalInflows"]) == Decimal("50000.00")
    assert Decimal(cf["totalOutflows"]) == Decimal("3000.00")
    assert Decimal(cf["outflowByCategory"]["Gastos pagados"]) == Decimal("3000.00")
    assert Decimal(cf["closingBalance"]) == Decimal("47000.00")


def test_internal_transfer_is_not_a_cash_flow_movement(client):
    login_admin(client)
    company, bank_a = _company_with_bank(client)
    bank_b_gl = create_account(client, company_id=company["id"], code="1120", name="Banco B", account_type="ASSET")
    bank_b = create_treasury_account(client, company_id=company["id"], gl_account_id=bank_b_gl["id"], name="Banco B")
    equity = create_account(client, company_id=company["id"], code="3100", name="Aportes", account_type="EQUITY")
    _remittance(client, company, bank_a, counter_id=equity["id"], origin_type="CAPITAL_CONTRIBUTION", amount="20000.00")

    transfer = client.post(
        "/api/treasury/transfers",
        json={
            "companyId": company["id"], "sourceTreasuryAccountId": bank_a["id"],
            "destinationTreasuryAccountId": bank_b["id"], "amount": "5000.00",
            "currencyCode": "HNL", "transferDate": "2026-08-26",
        },
    )
    assert transfer.status_code == 201, transfer.text

    cf = client.get(f"/api/financial-control/cash-flow-actual?companyId={company['id']}").json()
    # La transferencia interna no mueve la caja consolidada — solo el aporte.
    assert Decimal(cf["totalInflows"]) == Decimal("20000.00")
    assert Decimal(cf["totalOutflows"]) == Decimal("0.00")
    assert Decimal(cf["closingBalance"]) == Decimal("20000.00")
