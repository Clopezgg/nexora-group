from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.accounting import AccountingDocument, JournalLine
from app.models.asset import FixedAsset
from app.models.permission import UserCompanyAccess, UserProjectAccess
from tests.helpers import (
    create_account,
    create_company,
    create_supplier,
    create_user_with_role,
    login_admin,
    login_as,
)


def _setup_asset_company(client):
    company = create_company(client)
    expense = create_account(
        client, company_id=company["id"], code="5300", name="Depreciación", account_type="EXPENSE"
    )
    accumulated = create_account(
        client, company_id=company["id"], code="1590", name="Depreciación acumulada", account_type="ASSET"
    )
    return company, expense, accumulated


def _create_asset(client, *, company, expense, accumulated, cost="12000.00", useful_life=12, salvage="0.00"):
    response = client.post(
        "/api/assets",
        json={
            "companyId": company["id"],
            "category": "Maquinaria pesada",
            "name": "Excavadora CAT 320",
            "acquisitionDate": "2026-01-01",
            "cost": cost,
            "currencyCode": "HNL",
            "usefulLifeMonths": useful_life,
            "salvageValue": salvage,
            "scope": "GENERAL",
            "depreciationExpenseAccountId": expense["id"],
            "accumulatedDepreciationAccountId": accumulated["id"],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_generate_depreciation_entry_posts_balanced_dep_document(client):
    """Straight-line real: (12000 - 0) / 12 = 1000.00 por periodo, y el
    posting DEP resultante balancea débito=crédito (INV-ACC-001), nunca un
    monto inventado."""
    login_admin(client)
    company, expense, accumulated = _setup_asset_company(client)
    asset = _create_asset(client, company=company, expense=expense, accumulated=accumulated)

    response = client.post(
        f"/api/assets/{asset['id']}/depreciation-entries",
        json={"periodStart": "2026-01-01", "periodEnd": "2026-01-31"},
    )
    assert response.status_code == 201, response.text
    entry = response.json()
    assert entry["amount"] == "1000.00"
    assert entry["accountingDocumentId"] is not None

    document_id = entry["accountingDocumentId"]
    response = client.get(f"/api/assets/{asset['id']}/depreciation-entries")
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_approved_supplier_invoice_capitalizes_one_project_asset_through_gl(client, db_session):
    login_admin(client)
    company, depreciation_expense, accumulated = _setup_asset_company(client)
    project = client.post(
        "/api/projects",
        json={"companyId": company["id"], "name": "Proyecto activo", "code": "AST-PRJ"},
    ).json()
    supplier = create_supplier(client, company_id=company["id"])
    purchase_expense = create_account(
        client,
        company_id=company["id"],
        code="5200",
        name="Compra por capitalizar",
        account_type="EXPENSE",
    )
    payable = create_account(
        client,
        company_id=company["id"],
        code="2100",
        name="Proveedor por pagar",
        account_type="LIABILITY",
    )
    fixed_asset_account = create_account(
        client,
        company_id=company["id"],
        code="1500",
        name="Maquinaria",
        account_type="ASSET",
    )
    invoice = client.post(
        "/api/ap/supplier-invoices",
        json={
            "companyId": company["id"],
            "supplierId": supplier["id"],
            "invoiceNumber": "ASSET-AP-001",
            "scope": "PROJECT",
            "projectId": project["id"],
            "expenseAccountId": purchase_expense["id"],
            "payableAccountId": payable["id"],
            "currencyCode": "HNL",
            "amount": "12000.00",
            "taxAmount": "0.00",
            "invoiceDate": "2026-01-01",
            "dueDate": "2026-01-31",
        },
    )
    assert invoice.status_code == 201, invoice.text
    approved = client.post(f"/api/ap/supplier-invoices/{invoice.json()['id']}/approve")
    assert approved.status_code == 200, approved.text

    response = client.post(
        f"/api/assets/from-supplier-invoice/{invoice.json()['id']}",
        json={
            "category": "Maquinaria pesada",
            "name": "Excavadora capitalizada",
            "usefulLifeMonths": 12,
            "salvageValue": "0.00",
            "assetAccountId": fixed_asset_account["id"],
            "depreciationExpenseAccountId": depreciation_expense["id"],
            "accumulatedDepreciationAccountId": accumulated["id"],
        },
    )

    assert response.status_code == 201, response.text
    asset = response.json()
    assert asset["supplierInvoiceId"] == invoice.json()["id"]
    assert asset["projectId"] == project["id"]
    assert asset["scope"] == "PROJECT"
    assert Decimal(asset["cost"]) == Decimal("12000.00")
    assert asset["capitalizationDocumentId"] is not None

    document = db_session.get(
        AccountingDocument,
        asset["capitalizationDocumentId"],
    )
    assert document is not None
    assert document.document_type_code == "CAP"
    assert str(document.project_id) == project["id"]
    lines = db_session.execute(
        select(JournalLine).where(JournalLine.accounting_document_id == document.id)
    ).scalars().all()
    assert sum((line.debit_amount for line in lines), Decimal("0")) == Decimal("12000.00")
    assert sum((line.credit_amount for line in lines), Decimal("0")) == Decimal("12000.00")
    debit = next(line for line in lines if line.debit_amount > 0)
    credit = next(line for line in lines if line.credit_amount > 0)
    assert str(debit.account_id) == fixed_asset_account["id"]
    assert str(credit.account_id) == purchase_expense["id"]

    duplicate = client.post(
        f"/api/assets/from-supplier-invoice/{invoice.json()['id']}",
        json={
            "category": "Maquinaria pesada",
            "name": "Duplicado",
            "usefulLifeMonths": 12,
            "salvageValue": "0.00",
            "assetAccountId": fixed_asset_account["id"],
            "depreciationExpenseAccountId": depreciation_expense["id"],
            "accumulatedDepreciationAccountId": accumulated["id"],
        },
    )
    assert duplicate.status_code == 409, duplicate.text
    assert db_session.query(FixedAsset).count() == 1

    blocked_accrual_reversal = client.post(
        f"/api/accounting/journal-entries/{approved.json()['accrualDocumentId']}/reverse",
        json={"reason": "No debe dejar un activo sin origen contable"},
    )
    assert blocked_accrual_reversal.status_code == 409, blocked_accrual_reversal.text
    assert blocked_accrual_reversal.json()["error"]["code"] == "NXR-AP-001"

    capitalization_reversal = client.post(
        f"/api/accounting/journal-entries/{asset['capitalizationDocumentId']}/reverse",
        json={"reason": "Capitalización registrada por error"},
    )
    assert capitalization_reversal.status_code == 200, capitalization_reversal.text
    retired = client.get(f"/api/assets/{asset['id']}")
    assert retired.status_code == 200
    assert retired.json()["status"] == "RETIRED"
    assert retired.json()["supplierInvoiceId"] == invoice.json()["id"]

    accrual_reversal = client.post(
        f"/api/accounting/journal-entries/{approved.json()['accrualDocumentId']}/reverse",
        json={"reason": "Factura y capitalización anuladas formalmente"},
    )
    assert accrual_reversal.status_code == 200, accrual_reversal.text
    cancelled_invoice = client.get(f"/api/ap/supplier-invoices/{invoice.json()['id']}")
    assert cancelled_invoice.status_code == 200
    assert cancelled_invoice.json()["status"] == "CANCELLED"

    allowed_project = client.post(
        "/api/projects",
        json={"companyId": company["id"], "name": "Proyecto permitido", "code": "AST-OK"},
    ).json()
    scoped_finance = create_user_with_role(
        db_session,
        email="finance-project-isolation-assets@nexora.group",
        role_name="Finance Manager",
    )
    db_session.add_all(
        [
            UserCompanyAccess(user_id=scoped_finance.id, company_id=company["id"]),
            UserProjectAccess(user_id=scoped_finance.id, project_id=allowed_project["id"]),
        ]
    )
    db_session.commit()
    login_as(client, email="finance-project-isolation-assets@nexora.group")

    assert client.get(f"/api/assets/{asset['id']}").status_code == 403
    assert client.post(
        f"/api/assets/{asset['id']}/status", json={"status": "ACTIVE"}
    ).status_code == 403
    assert client.get(f"/api/assets/{asset['id']}/depreciation-entries").status_code == 403
    assert client.post(
        f"/api/assets/from-supplier-invoice/{invoice.json()['id']}",
        json={
            "category": "No autorizado",
            "name": "No autorizado",
            "usefulLifeMonths": 12,
            "salvageValue": "0.00",
            "assetAccountId": fixed_asset_account["id"],
            "depreciationExpenseAccountId": depreciation_expense["id"],
            "accumulatedDepreciationAccountId": accumulated["id"],
        },
    ).status_code == 403
    assert client.post(
        "/api/assets",
        json={
            "companyId": company["id"],
            "category": "No autorizado",
            "name": "Alta proyecto bloqueado",
            "acquisitionDate": "2026-01-01",
            "cost": "100.00",
            "currencyCode": "HNL",
            "usefulLifeMonths": 12,
            "salvageValue": "0.00",
            "scope": "PROJECT",
            "projectId": project["id"],
            "depreciationExpenseAccountId": depreciation_expense["id"],
            "accumulatedDepreciationAccountId": accumulated["id"],
        },
    ).status_code == 403
    visible = client.get(f"/api/assets?companyId={company['id']}")
    assert visible.status_code == 200
    assert all(row["id"] != asset["id"] for row in visible.json())


def test_depreciation_period_cannot_be_posted_twice(client, db_session):
    """RED behavior named in the brief: generar dos veces la depreciación
    del mismo asset+periodo se rechaza, y solo existe UN posting DEP."""
    login_admin(client)
    company, expense, accumulated = _setup_asset_company(client)
    asset = _create_asset(client, company=company, expense=expense, accumulated=accumulated)

    first = client.post(
        f"/api/assets/{asset['id']}/depreciation-entries",
        json={"periodStart": "2026-01-01", "periodEnd": "2026-01-31"},
    )
    assert first.status_code == 201, first.text

    second = client.post(
        f"/api/assets/{asset['id']}/depreciation-entries",
        json={"periodStart": "2026-01-01", "periodEnd": "2026-01-31"},
    )
    assert second.status_code == 409, second.text
    assert second.json()["error"]["code"] == "NXR-ASSET-002"

    dep_documents = db_session.execute(
        select(AccountingDocument).where(AccountingDocument.document_type_code == "DEP")
    ).scalars().all()
    assert len(dep_documents) == 1


def test_disposed_asset_cannot_be_depreciated(client):
    login_admin(client)
    company, expense, accumulated = _setup_asset_company(client)
    asset = _create_asset(client, company=company, expense=expense, accumulated=accumulated)

    disposed = client.post(f"/api/assets/{asset['id']}/status", json={"status": "DISPOSED"})
    assert disposed.status_code == 200, disposed.text

    response = client.post(
        f"/api/assets/{asset['id']}/depreciation-entries",
        json={"periodStart": "2026-01-01", "periodEnd": "2026-01-31"},
    )
    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "NXR-ASSET-001"


def test_disposed_asset_status_is_terminal(client):
    login_admin(client)
    company, expense, accumulated = _setup_asset_company(client)
    asset = _create_asset(client, company=company, expense=expense, accumulated=accumulated)

    disposed = client.post(f"/api/assets/{asset['id']}/status", json={"status": "DISPOSED"})
    assert disposed.status_code == 200

    reactivate = client.post(f"/api/assets/{asset['id']}/status", json={"status": "ACTIVE"})
    assert reactivate.status_code == 409, reactivate.text
    assert reactivate.json()["error"]["code"] == "NXR-ASSET-001"


def test_fixed_asset_rejects_non_positive_cost_at_db_constraint(db_session):
    """A nivel de constraint REAL de PostgreSQL, sin pasar por el service."""
    from app.models.company import Company
    from app.models.currency import Currency
    from app.models.chart_of_accounts import Account, ChartOfAccount

    db_session.add(Currency(code="HNL", name="Lempira hondureño", symbol="L"))
    company = Company(name="Constraint Test Co")
    db_session.add(company)
    db_session.flush()
    coa = ChartOfAccount(company_id=company.id, name="Catálogo")
    db_session.add(coa)
    db_session.flush()
    expense = Account(chart_of_account_id=coa.id, code="5300", name="Depreciación", account_type="EXPENSE")
    accumulated = Account(chart_of_account_id=coa.id, code="1590", name="Dep. acumulada", account_type="ASSET")
    db_session.add_all([expense, accumulated])
    db_session.flush()

    bad_asset = FixedAsset(
        company_id=company.id,
        category="Test",
        name="Activo inválido",
        acquisition_date="2026-01-01",
        cost=Decimal("-100.00"),
        currency_code="HNL",
        useful_life_months=12,
        salvage_value=Decimal("0"),
        scope="GENERAL",
        depreciation_expense_account_id=expense.id,
        accumulated_depreciation_account_id=accumulated.id,
    )
    db_session.add(bad_asset)
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


def test_fixed_asset_operation_scope_requires_project_id_for_project_scope(client):
    login_admin(client)
    company, expense, accumulated = _setup_asset_company(client)
    response = client.post(
        "/api/assets",
        json={
            "companyId": company["id"],
            "category": "Maquinaria",
            "name": "Grúa torre",
            "acquisitionDate": "2026-01-01",
            "cost": "5000.00",
            "currencyCode": "HNL",
            "usefulLifeMonths": 24,
            "salvageValue": "0.00",
            "scope": "PROJECT",
            "depreciationExpenseAccountId": expense["id"],
            "accumulatedDepreciationAccountId": accumulated["id"],
        },
    )
    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "NXR-ACCOUNTING-002"


def test_depreciation_entry_rejects_period_end_before_period_start(client):
    """Coordinator review finding #2: un periodEnd anterior a periodStart
    debe surgir como un 422 limpio de Pydantic, nunca como el 500 sin
    manejar del `IntegrityError` real de `ck_depreciation_entries_period_valid`."""
    login_admin(client)
    company, expense, accumulated = _setup_asset_company(client)
    asset = _create_asset(client, company=company, expense=expense, accumulated=accumulated)

    response = client.post(
        f"/api/assets/{asset['id']}/depreciation-entries",
        json={"periodStart": "2026-01-31", "periodEnd": "2026-01-01"},
    )

    assert response.status_code == 422, response.text
    assert response.status_code != 500
    body = response.json()
    # FastAPI's default Pydantic validation error shape (not our custom
    # NXR-* envelope, since this never reaches a domain service/exception
    # handler -- rejected at the request-schema boundary).
    assert "detail" in body
    assert any("periodEnd" in str(error) for error in body["detail"])

    # No DepreciationEntry/DEP posting was created from the rejected request.
    entries = client.get(f"/api/assets/{asset['id']}/depreciation-entries")
    assert entries.status_code == 200
    assert entries.json() == []


def test_company_access_blocks_cross_company_asset(client, db_session):
    """A company-A Finance Manager cannot read a FixedAsset owned by
    company B (INV-COMP-001) -- same shared `assert_company_access` every
    other track's resources use."""
    login_admin(client)
    company_b, expense_b, accumulated_b = _setup_asset_company(client)
    asset_b = _create_asset(client, company=company_b, expense=expense_b, accumulated=accumulated_b)

    company_a = create_company(client, name="Constructora A")
    finance_a = create_user_with_role(
        db_session, email="finance-a-assets@nexora.group", role_name="Finance Manager"
    )
    db_session.add(UserCompanyAccess(user_id=finance_a.id, company_id=company_a["id"]))
    db_session.commit()

    login_as(client, email="finance-a-assets@nexora.group")
    response = client.get(f"/api/assets/{asset_b['id']}")

    assert response.status_code == 403, response.text
    assert response.json()["error"]["code"] == "NXR-PERM-001"
