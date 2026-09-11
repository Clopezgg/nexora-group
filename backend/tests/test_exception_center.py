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


def test_exception_center_flags_overdue_and_missing_period(client, db_session):
    login_admin(client)
    # Compañía SIN período fiscal ni pagador -> ya dos excepciones.
    company = create_company(client)
    expense = create_account(client, company_id=company["id"], code="5200", name="Mat", account_type="EXPENSE")
    payable = create_account(client, company_id=company["id"], code="2100", name="CxP", account_type="LIABILITY")
    supplier = create_supplier(client, company_id=company["id"])

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
    assert "FISCAL_PERIOD_MISSING" in codes
    assert "VOUCHER_PAYER_UNSET" in codes
    assert body["exceptionZero"] is False


def test_duplicate_supplier_invoice_number_fails_closed(client, db_session):
    login_admin(client)
    company = create_company(client)
    expense = create_account(client, company_id=company["id"], code="5200", name="Mat", account_type="EXPENSE")
    payable = create_account(client, company_id=company["id"], code="2100", name="CxP", account_type="LIABILITY")
    supplier = create_supplier(client, company_id=company["id"])

    payload = {
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
    }
    first = client.post("/api/ap/supplier-invoices", json=payload)
    assert first.status_code == 201, first.text
    # Un duplicado no cancelado se rechaza fail-closed por el índice parcial
    # uq_supplier_invoice_business_number (la fuente de verdad es PostgreSQL).
    duplicate = client.post("/api/ap/supplier-invoices", json=payload)
    assert duplicate.status_code == 422, duplicate.text
    assert duplicate.json()["error"]["code"] == "NXR-DATA-001"
