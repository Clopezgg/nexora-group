from datetime import date, timedelta

from app.models.fiscal import FiscalPeriod, FiscalYear
from tests.helpers import (
    create_account,
    create_company,
    create_supplier,
    create_treasury_account,
    login_admin,
)


def _clean_company(client, db_session):
    """Compañía con período fiscal vigente y pagador de comprobantes fijado
    -> Exception Zero salvo lo que el test provoque."""
    company = create_company(client)
    today = date.today()
    year = FiscalYear(
        company_id=company["id"],
        code=str(today.year),
        start_date=date(today.year, 1, 1),
        end_date=date(today.year, 12, 31),
    )
    db_session.add(year)
    db_session.flush()
    db_session.add(
        FiscalPeriod(
            fiscal_year_id=year.id,
            company_id=company["id"],
            period_number=today.month,
            start_date=today - timedelta(days=10),
            end_date=today + timedelta(days=10),
            status="OPEN",
        )
    )
    db_session.commit()
    client.patch(
        f"/api/master-data/companies/{company['id']}",
        json={"voucherPayerName": "KAREN VANNESSA LOPEZ GONZALEZ"},
    )
    return company


def test_exception_zero_for_a_clean_company(client, db_session):
    login_admin(client)
    company = _clean_company(client, db_session)

    response = client.get(f"/api/financial-control/exceptions?companyId={company['id']}")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["exceptionZero"] is True
    assert body["total"] == 0
    assert body["exceptions"] == []


def test_exception_center_flags_duplicate_and_overdue_and_missing_period(client, db_session):
    login_admin(client)
    # Compañía SIN período fiscal ni pagador -> ya dos excepciones.
    company = create_company(client)
    expense = create_account(client, company_id=company["id"], code="5200", name="Mat", account_type="EXPENSE")
    payable = create_account(client, company_id=company["id"], code="2100", name="CxP", account_type="LIABILITY")
    supplier = create_supplier(client, company_id=company["id"])

    # Dos facturas con el mismo número para el mismo proveedor -> duplicado.
    for _ in range(2):
        inv = client.post(
            "/api/ap/supplier-invoices",
            json={
                "companyId": company["id"],
                "supplierId": supplier["id"],
                "invoiceNumber": "DUP-001",
                "scope": "GENERAL",
                "expenseAccountId": expense["id"],
                "payableAccountId": payable["id"],
                "currencyCode": "HNL",
                "amount": "100.00",
                "taxAmount": "0.00",
                "invoiceDate": "2026-01-05",
                "dueDate": str(date.today() - timedelta(days=30)),
            },
        )
        assert inv.status_code == 201, inv.text

    body = client.get(f"/api/financial-control/exceptions?companyId={company['id']}").json()
    codes = {e["code"] for e in body["exceptions"]}
    assert "DUPLICATE_SUPPLIER_INVOICE" in codes
    assert "FISCAL_PERIOD_MISSING" in codes
    assert "VOUCHER_PAYER_UNSET" in codes
    assert body["exceptionZero"] is False
    assert body["criticalCount"] >= 2

    dup = next(e for e in body["exceptions"] if e["code"] == "DUPLICATE_SUPPLIER_INVOICE")
    assert dup["route"] == "/finanzas/cuentas-por-pagar"
    assert dup["suggestedAction"]
