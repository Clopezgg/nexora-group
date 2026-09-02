import uuid
from decimal import Decimal

from sqlalchemy import select

from app.models.budget import Budget
from app.models.procurement import PurchaseOrder
from app.models.project import Project
from tests.helpers import create_account, create_company, create_treasury_account, login_admin

# Forbidden substrings for a money/balance column on Project -- INV-TRE-002:
# Project jamás posee efectivo. Ver docs/PROJECTS_WBS.md.
_FORBIDDEN_COLUMN_HINTS = ("balance", "cash", "saldo")


def test_project_has_no_money_column():
    """INV-TRE-002: Project no tiene ninguna columna que represente saldo de
    dinero. Introspección real del esquema, no una convención de nombres en
    el código de la app."""
    columns = {column.name for column in Project.__table__.columns}
    for column_name in columns:
        for hint in _FORBIDDEN_COLUMN_HINTS:
            assert hint not in column_name.lower(), (
                f"Project.{column_name} sugiere que el proyecto posee dinero (INV-TRE-002)"
            )


def _create_project(client, *, company_id: str, name: str = "Torre Nexora II") -> dict:
    response = client.post(
        "/api/projects",
        json={"companyId": company_id, "name": name, "code": "PRJ-001", "currencyCode": "HNL"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_supplier(client, *, company_id: str) -> dict:
    response = client.post(
        "/api/procurement/suppliers",
        json={"companyId": company_id, "legalName": "Proveedor integrado S.A."},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_purchase_order(
    client,
    *,
    company_id: str,
    supplier_id: str,
    project_id: str,
    unit_price: str,
    currency_code: str = "HNL",
) -> dict:
    response = client.post(
        "/api/procurement/purchase-orders",
        json={
            "companyId": company_id,
            "supplierId": supplier_id,
            "projectId": project_id,
            "currencyCode": currency_code,
            "lines": [
                {
                    "description": "Material comprometido",
                    "quantity": "1.0000",
                    "unitPrice": unit_price,
                }
            ],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_create_and_list_project(client):
    login_admin(client)
    company = create_company(client)
    project = _create_project(client, company_id=company["id"])
    assert project["status"] == "PLANNING"
    assert project["companyId"] == company["id"]

    listed = client.get("/api/projects", params={"company_id": company["id"]})
    assert listed.status_code == 200, listed.text
    assert any(p["id"] == project["id"] for p in listed.json())


def test_create_project_persists_location_at_creation_time(client):
    """ORDEN MAESTRA §17: la ubicación de la obra viaja de verdad en el alta,
    no sólo en la edición posterior."""
    login_admin(client)
    company = create_company(client)
    response = client.post(
        "/api/projects",
        json={
            "companyId": company["id"],
            "name": "Puente sobre el río",
            "currencyCode": "HNL",
            "addressLine1": "Km 12 carretera del norte",
            "city": "El Progreso",
            "stateDepartment": "Yoro",
            "country": "HN",
            "locationReference": "Frente a la subestación",
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["addressLine1"] == "Km 12 carretera del norte"
    assert body["city"] == "El Progreso"
    assert body["stateDepartment"] == "Yoro"
    assert body["country"] == "HN"
    assert body["locationReference"] == "Frente a la subestación"

    fetched = client.get(f"/api/projects/{body['id']}").json()
    assert fetched["city"] == "El Progreso"


def test_wbs_hierarchy(client):
    login_admin(client)
    company = create_company(client)
    project = _create_project(client, company_id=company["id"])

    root = client.post(
        f"/api/projects/{project['id']}/wbs", json={"code": "01", "name": "PRELIMINARES"}
    ).json()
    assert root["level"] == 0

    child = client.post(
        f"/api/projects/{project['id']}/wbs",
        json={"code": "01.01", "name": "TRAZO Y NIVELACIÓN", "parentId": root["id"]},
    ).json()
    assert child["level"] == 1
    assert child["parentId"] == root["id"]

    listed = client.get(f"/api/projects/{project['id']}/wbs").json()
    assert {node["id"] for node in listed} == {root["id"], child["id"]}


def test_budget_baseline_cannot_be_created_twice(client):
    """docs/BUDGET_CONTROLLING.md: BASELINE se crea una sola vez."""
    login_admin(client)
    company = create_company(client)
    project = _create_project(client, company_id=company["id"])

    first = client.post(
        f"/api/projects/{project['id']}/budgets/baseline",
        json={"currencyCode": "HNL", "lines": [{"authorizedAmount": "100000.00"}]},
    )
    assert first.status_code == 201, first.text

    second = client.post(
        f"/api/projects/{project['id']}/budgets/baseline",
        json={"currencyCode": "HNL", "lines": [{"authorizedAmount": "999999.00"}]},
    )
    assert second.status_code == 409, second.text
    assert second.json()["error"]["code"] == "NXR-BUDGET-001"

    summary = client.get(f"/api/projects/{project['id']}/budgets/summary").json()
    assert summary["authorized"] == "100000.00"


def test_budget_baseline_rejects_non_functional_currency_without_persisting(client, db_session):
    """Budget arithmetic must start in the company's functional currency until FX policy exists."""
    login_admin(client)
    company = create_company(client, currency="HNL")
    project = _create_project(client, company_id=company["id"])

    response = client.post(
        f"/api/projects/{project['id']}/budgets/baseline",
        json={"currencyCode": "USD", "lines": [{"authorizedAmount": "1000.00"}]},
    )

    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "NXR-BUDGET-002"
    persisted = list(
        db_session.execute(
            select(Budget).where(Budget.project_id == uuid.UUID(project["id"]))
        ).scalars()
    )
    assert persisted == []


def test_budget_summary_uses_only_approved_project_purchase_orders_as_commitments(client):
    """Breaking the Procurement -> Project Control seam must lose the real
    commitment or incorrectly include the draft PO."""
    login_admin(client)
    company = create_company(client)
    project = _create_project(client, company_id=company["id"])
    supplier = _create_supplier(client, company_id=company["id"])
    client.post(
        f"/api/projects/{project['id']}/budgets/baseline",
        json={"currencyCode": "HNL", "lines": [{"authorizedAmount": "1000.00"}]},
    )
    _create_purchase_order(
        client,
        company_id=company["id"],
        supplier_id=supplier["id"],
        project_id=project["id"],
        unit_price="900.00",
    )
    approved = _create_purchase_order(
        client,
        company_id=company["id"],
        supplier_id=supplier["id"],
        project_id=project["id"],
        unit_price="125.50",
    )
    approval = client.post(f"/api/procurement/purchase-orders/{approved['id']}/approve")
    assert approval.status_code == 200, approval.text

    summary = client.get(f"/api/projects/{project['id']}/budgets/summary")

    assert summary.status_code == 200, summary.text
    body = summary.json()
    assert Decimal(body["authorized"]) == Decimal("1000.00")
    assert Decimal(body["committed"]) == Decimal("125.50")
    assert Decimal(body["accrued"]) == Decimal("0")
    assert Decimal(body["paid"]) == Decimal("0")
    assert Decimal(body["available"]) == Decimal("874.50")


def test_budget_summary_includes_real_ap_accrued_and_paid_amounts(client, db_session):
    """NXR-REQ-0034/0035: accrued/paid were hardcoded Decimal("0") in
    budget_service.compute_summary -- real financial data can never be
    hardcoded (CLAUDE.md). A PROJECT-scoped AP invoice must feed both
    figures once it is actually approved (accrual posted) and paid."""
    login_admin(client)
    company = create_company(client)
    project = _create_project(client, company_id=company["id"])
    supplier = _create_supplier(client, company_id=company["id"])
    client.post(
        f"/api/projects/{project['id']}/budgets/baseline",
        json={"currencyCode": "HNL", "lines": [{"authorizedAmount": "1000.00"}]},
    )
    bank_gl = create_account(client, company_id=company["id"], code="1100", name="Bancos", account_type="ASSET")
    expense = create_account(
        client, company_id=company["id"], code="5200", name="Materiales", account_type="EXPENSE"
    )
    payable = create_account(
        client, company_id=company["id"], code="2100", name="Cuentas por pagar", account_type="LIABILITY"
    )
    contributions = create_account(
        client, company_id=company["id"], code="3100", name="Aportes", account_type="EQUITY"
    )
    bank = create_treasury_account(client, company_id=company["id"], gl_account_id=bank_gl["id"])
    client.post(
        "/api/treasury/remittances",
        json={
            "companyId": company["id"],
            "treasuryAccountId": bank["id"],
            "counterAccountId": contributions["id"],
            "sender": "Fondeo inicial",
            "currencyCode": "HNL",
            "originalAmount": "100000.00",
            "remittanceDate": "2026-01-01",
        },
    )

    invoice = client.post(
        "/api/ap/supplier-invoices",
        json={
            "companyId": company["id"],
            "supplierId": supplier["id"],
            "invoiceNumber": "PRJ-AP-1",
            "scope": "PROJECT",
            "projectId": project["id"],
            "expenseAccountId": expense["id"],
            "payableAccountId": payable["id"],
            "currencyCode": "HNL",
            "amount": "200.00",
            "invoiceDate": "2026-01-10",
            "dueDate": "2026-02-10",
        },
    ).json()

    summary_before_approval = client.get(f"/api/projects/{project['id']}/budgets/summary").json()
    assert Decimal(summary_before_approval["accrued"]) == Decimal("0")

    client.post(f"/api/ap/supplier-invoices/{invoice['id']}/approve")
    client.post(
        f"/api/ap/supplier-invoices/{invoice['id']}/payments",
        json={"treasuryAccountId": bank["id"], "amount": "80.00", "paymentDate": "2026-01-20"},
    )

    summary = client.get(f"/api/projects/{project['id']}/budgets/summary")
    assert summary.status_code == 200, summary.text
    body = summary.json()
    assert Decimal(body["accrued"]) == Decimal("200.00")
    assert Decimal(body["paid"]) == Decimal("80.00")
    assert Decimal(body["available"]) == Decimal("800.00")


def test_budget_summary_excludes_a_draft_ap_invoice_from_accrued(client, db_session):
    """A DRAFT invoice never posted its accrual -- it must not inflate the
    project's accrued figure."""
    login_admin(client)
    company = create_company(client)
    project = _create_project(client, company_id=company["id"])
    supplier = _create_supplier(client, company_id=company["id"])
    client.post(
        f"/api/projects/{project['id']}/budgets/baseline",
        json={"currencyCode": "HNL", "lines": [{"authorizedAmount": "1000.00"}]},
    )
    expense = create_account(
        client, company_id=company["id"], code="5300", name="Materiales", account_type="EXPENSE"
    )
    payable = create_account(
        client, company_id=company["id"], code="2200", name="Cuentas por pagar", account_type="LIABILITY"
    )
    client.post(
        "/api/ap/supplier-invoices",
        json={
            "companyId": company["id"],
            "supplierId": supplier["id"],
            "invoiceNumber": "PRJ-AP-2",
            "scope": "PROJECT",
            "projectId": project["id"],
            "expenseAccountId": expense["id"],
            "payableAccountId": payable["id"],
            "currencyCode": "HNL",
            "amount": "500.00",
            "invoiceDate": "2026-01-10",
            "dueDate": "2026-02-10",
        },
    )

    summary = client.get(f"/api/projects/{project['id']}/budgets/summary")

    assert summary.status_code == 200, summary.text
    body = summary.json()
    assert Decimal(body["accrued"]) == Decimal("0")
    assert Decimal(body["paid"]) == Decimal("0")
    assert Decimal(body["available"]) == Decimal("1000.00")


def test_budget_summary_excludes_an_advance_prepayment_invoice_from_accrued(client, db_session):
    """ORDEN MAESTRA §13/§15: a supplier invoice whose debit is an ASSET
    account (contractual advance / prepayment) is NOT project cost. It must
    not inflate `accrued` or shrink `available`; it surfaces as `advances`."""
    login_admin(client)
    company = create_company(client)
    project = _create_project(client, company_id=company["id"])
    supplier = _create_supplier(client, company_id=company["id"])
    client.post(
        f"/api/projects/{project['id']}/budgets/baseline",
        json={"currencyCode": "HNL", "lines": [{"authorizedAmount": "1000.00"}]},
    )
    advance_asset = create_account(
        client, company_id=company["id"], code="1610",
        name="Anticipos a contratistas", account_type="ASSET",
    )
    payable = create_account(
        client, company_id=company["id"], code="2400",
        name="Cuentas por pagar", account_type="LIABILITY",
    )
    invoice = client.post(
        "/api/ap/supplier-invoices",
        json={
            "companyId": company["id"],
            "supplierId": supplier["id"],
            "invoiceNumber": "PRJ-ADV-1",
            "scope": "PROJECT",
            "projectId": project["id"],
            "expenseAccountId": advance_asset["id"],
            "payableAccountId": payable["id"],
            "currencyCode": "HNL",
            "amount": "200.00",
            "invoiceDate": "2026-01-10",
            "dueDate": "2026-02-10",
        },
    ).json()
    client.post(f"/api/ap/supplier-invoices/{invoice['id']}/approve")

    body = client.get(f"/api/projects/{project['id']}/budgets/summary").json()
    assert Decimal(body["accrued"]) == Decimal("0")
    assert Decimal(body["advances"]) == Decimal("200.00")
    assert Decimal(body["available"]) == Decimal("1000.00")


def test_budget_summary_rejects_a_non_functional_currency_ap_accrual(client, db_session):
    login_admin(client)
    company = create_company(client, currency="HNL")
    project = _create_project(client, company_id=company["id"])
    supplier = _create_supplier(client, company_id=company["id"])
    client.post(
        f"/api/projects/{project['id']}/budgets/baseline",
        json={"currencyCode": "HNL", "lines": [{"authorizedAmount": "1000.00"}]},
    )
    expense = create_account(
        client, company_id=company["id"], code="5400", name="Materiales", account_type="EXPENSE"
    )
    payable = create_account(
        client, company_id=company["id"], code="2300", name="Cuentas por pagar", account_type="LIABILITY"
    )
    invoice = client.post(
        "/api/ap/supplier-invoices",
        json={
            "companyId": company["id"],
            "supplierId": supplier["id"],
            "invoiceNumber": "PRJ-AP-3",
            "scope": "PROJECT",
            "projectId": project["id"],
            "expenseAccountId": expense["id"],
            "payableAccountId": payable["id"],
            "currencyCode": "USD",
            "amount": "50.00",
            "invoiceDate": "2026-01-10",
            "dueDate": "2026-02-10",
        },
    ).json()
    client.post(f"/api/ap/supplier-invoices/{invoice['id']}/approve")

    summary = client.get(f"/api/projects/{project['id']}/budgets/summary")

    assert summary.status_code == 409, summary.text
    assert summary.json()["error"]["code"] == "NXR-BUDGET-002"


def test_project_purchase_order_approval_rejects_non_functional_currency(client, db_session):
    """A foreign-currency project PO must never enter commitments without an FX policy."""
    login_admin(client)
    company = create_company(client, currency="HNL")
    project = _create_project(client, company_id=company["id"])
    supplier = _create_supplier(client, company_id=company["id"])
    client.post(
        f"/api/projects/{project['id']}/budgets/baseline",
        json={"currencyCode": "HNL", "lines": [{"authorizedAmount": "1000.00"}]},
    )
    order = _create_purchase_order(
        client,
        company_id=company["id"],
        supplier_id=supplier["id"],
        project_id=project["id"],
        unit_price="100.00",
        currency_code="USD",
    )

    approval = client.post(f"/api/procurement/purchase-orders/{order['id']}/approve")

    assert approval.status_code == 409, approval.text
    assert approval.json()["error"]["code"] == "NXR-PROCUREMENT-002"
    assert db_session.get(PurchaseOrder, uuid.UUID(order["id"])).status == "DRAFT"
    summary = client.get(f"/api/projects/{project['id']}/budgets/summary")
    assert summary.status_code == 200, summary.text
    assert Decimal(summary.json()["committed"]) == Decimal("0")


def test_budget_summary_rejects_preexisting_non_functional_currency_commitment(client, db_session):
    """The aggregate must reject legacy approved foreign-currency POs, not sum nominal values."""
    login_admin(client)
    company = create_company(client, currency="HNL")
    project = _create_project(client, company_id=company["id"])
    supplier = _create_supplier(client, company_id=company["id"])
    client.post(
        f"/api/projects/{project['id']}/budgets/baseline",
        json={"currencyCode": "HNL", "lines": [{"authorizedAmount": "1000.00"}]},
    )
    order = _create_purchase_order(
        client,
        company_id=company["id"],
        supplier_id=supplier["id"],
        project_id=project["id"],
        unit_price="100.00",
        currency_code="USD",
    )
    persisted = db_session.get(PurchaseOrder, uuid.UUID(order["id"]))
    persisted.status = "APPROVED"
    db_session.commit()

    summary = client.get(f"/api/projects/{project['id']}/budgets/summary")

    assert summary.status_code == 409, summary.text
    assert summary.json()["error"]["code"] == "NXR-PROCUREMENT-002"


def test_foreign_currency_commitment_only_blocks_its_own_project_summary(client, db_session):
    """A legacy invalid PO for project A must not deny a valid project B summary."""
    login_admin(client)
    company = create_company(client, currency="HNL")
    project_a = _create_project(client, company_id=company["id"], name="Proyecto A")
    project_b = _create_project(client, company_id=company["id"], name="Proyecto B")
    supplier = _create_supplier(client, company_id=company["id"])
    for project in (project_a, project_b):
        baseline = client.post(
            f"/api/projects/{project['id']}/budgets/baseline",
            json={"currencyCode": "HNL", "lines": [{"authorizedAmount": "1000.00"}]},
        )
        assert baseline.status_code == 201, baseline.text

    invalid_a = _create_purchase_order(
        client,
        company_id=company["id"],
        supplier_id=supplier["id"],
        project_id=project_a["id"],
        unit_price="100.00",
        currency_code="USD",
    )
    persisted_a = db_session.get(PurchaseOrder, uuid.UUID(invalid_a["id"]))
    persisted_a.status = "APPROVED"
    db_session.commit()
    valid_b = _create_purchase_order(
        client,
        company_id=company["id"],
        supplier_id=supplier["id"],
        project_id=project_b["id"],
        unit_price="50.00",
    )
    approval_b = client.post(f"/api/procurement/purchase-orders/{valid_b['id']}/approve")
    assert approval_b.status_code == 200, approval_b.text

    summary_b = client.get(f"/api/projects/{project_b['id']}/budgets/summary")
    summary_a = client.get(f"/api/projects/{project_a['id']}/budgets/summary")

    assert summary_b.status_code == 200, summary_b.text
    assert Decimal(summary_b.json()["committed"]) == Decimal("50.00")
    assert Decimal(summary_b.json()["available"]) == Decimal("950.00")
    assert summary_a.status_code == 409, summary_a.text
    assert summary_a.json()["error"]["code"] == "NXR-PROCUREMENT-002"


def test_forecast_uses_project_inventory_issues_as_actual_cost_without_relabeling_cash(client):
    """A posted material issue is forecast AC, never an accrued or paid cash amount."""
    login_admin(client)
    company = create_company(client)
    project = _create_project(client, company_id=company["id"])
    client.post(
        f"/api/projects/{project['id']}/budgets/baseline",
        json={"currencyCode": "HNL", "lines": [{"authorizedAmount": "1000.00"}]},
    )
    item = client.post(
        "/api/inventory/items",
        json={"companyId": company["id"], "sku": "CEMENTO", "name": "Cemento", "uom": "BOL"},
    ).json()
    warehouse = client.post(
        "/api/inventory/warehouses",
        json={"companyId": company["id"], "code": "ALM-PC", "name": "Almacén de obra"},
    ).json()
    received = client.post(
        "/api/inventory/stock/receive",
        json={
            "companyId": company["id"],
            "itemId": item["id"],
            "warehouseId": warehouse["id"],
            "quantity": "10.0000",
            "unitCost": "10.0000",
        },
    )
    assert received.status_code == 201, received.text
    issued = client.post(
        "/api/inventory/stock/issue-to-project",
        json={
            "companyId": company["id"],
            "itemId": item["id"],
            "warehouseId": warehouse["id"],
            "projectId": project["id"],
            "quantity": "3.0000",
        },
    )
    assert issued.status_code == 201, issued.text

    summary = client.get(f"/api/projects/{project['id']}/budgets/summary").json()
    forecast = client.get(f"/api/projects/{project['id']}/forecast")

    assert summary["accrued"] == "0"
    assert summary["paid"] == "0"
    assert forecast.status_code == 200, forecast.text
    assert Decimal(forecast.json()["ac"]) == Decimal("30.00")
    assert forecast.json()["pv"] is None
    assert forecast.json()["ev"] is None


def test_change_order_approval_creates_revised_budget_without_touching_baseline(client):
    login_admin(client)
    company = create_company(client)
    project = _create_project(client, company_id=company["id"])

    baseline = client.post(
        f"/api/projects/{project['id']}/budgets/baseline",
        json={"currencyCode": "HNL", "lines": [{"authorizedAmount": "100000.00"}]},
    ).json()
    assert baseline["version"] == "BASELINE"
    assert baseline["status"] == "ACTIVE"

    change_order = client.post(
        f"/api/projects/{project['id']}/change-orders",
        json={"reason": "Ampliación de alcance por cambio de cliente", "budgetChangeAmount": "15000.00"},
    ).json()
    assert change_order["status"] == "DRAFT"

    submitted = client.post(f"/api/projects/change-orders/{change_order['id']}/submit")
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["status"] == "SUBMITTED"

    revised = client.post(f"/api/projects/change-orders/{change_order['id']}/approve")
    assert revised.status_code == 200, revised.text
    revised_body = revised.json()
    assert revised_body["version"] == "REVISED"
    assert revised_body["previousBudgetId"] == baseline["id"]

    summary = client.get(f"/api/projects/{project['id']}/budgets/summary").json()
    assert summary["authorized"] == "115000.00"

    # El BASELINE original nunca se toca: sigue existiendo con sus líneas
    # originales, solo cambia a SUPERSEDED como budget activo.
    budgets = client.get(f"/api/projects/{project['id']}/budgets/active").json()
    assert budgets["id"] != baseline["id"]


def test_change_order_cannot_be_approved_without_submit(client):
    login_admin(client)
    company = create_company(client)
    project = _create_project(client, company_id=company["id"])
    client.post(
        f"/api/projects/{project['id']}/budgets/baseline",
        json={"currencyCode": "HNL", "lines": [{"authorizedAmount": "50000.00"}]},
    )
    change_order = client.post(
        f"/api/projects/{project['id']}/change-orders",
        json={"reason": "x", "budgetChangeAmount": "1000.00"},
    ).json()

    response = client.post(f"/api/projects/change-orders/{change_order['id']}/approve")
    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "NXR-PROJECT-001"


def test_forecast_without_progress_returns_none_not_fake_values(client):
    """Orden maestra §42: solo mostrar valores calculables -- sin
    ProgressRecord, PV/EV/CPI/SPI/ETC/EAC/VAC deben ser null, nunca 0
    inventado."""
    login_admin(client)
    company = create_company(client)
    project = _create_project(client, company_id=company["id"])
    client.post(
        f"/api/projects/{project['id']}/budgets/baseline",
        json={"currencyCode": "HNL", "lines": [{"authorizedAmount": "200000.00"}]},
    )

    forecast = client.get(f"/api/projects/{project['id']}/forecast").json()
    assert forecast["bac"] == "200000.00"
    assert forecast["ac"] == "0"
    assert forecast["pv"] is None
    assert forecast["ev"] is None
    assert forecast["cpi"] is None


def test_forecast_with_progress_computes_pv_and_ev(client):
    login_admin(client)
    company = create_company(client)
    project = _create_project(client, company_id=company["id"])
    client.post(
        f"/api/projects/{project['id']}/budgets/baseline",
        json={"currencyCode": "HNL", "lines": [{"authorizedAmount": "200000.00"}]},
    )
    progress = client.post(
        f"/api/projects/{project['id']}/progress",
        json={"recordDate": "2026-08-24", "plannedPercent": "50.00", "actualPercent": "40.00"},
    )
    assert progress.status_code == 201, progress.text

    forecast = client.get(f"/api/projects/{project['id']}/forecast").json()
    assert Decimal(forecast["pv"]) == Decimal("100000.00")
    assert Decimal(forecast["ev"]) == Decimal("80000.00")
    # AC sigue en 0 porque AP/Track A no ha aterrizado -- CPI no es
    # calculable (división por cero evitada explícitamente), nunca falso.
    assert forecast["ac"] == "0"
    assert forecast["cpi"] is None


def test_progress_record_lists_in_order(client):
    login_admin(client)
    company = create_company(client)
    project = _create_project(client, company_id=company["id"])
    client.post(
        f"/api/projects/{project['id']}/progress",
        json={"recordDate": "2026-08-01", "plannedPercent": "10.00", "actualPercent": "8.00"},
    )
    client.post(
        f"/api/projects/{project['id']}/progress",
        json={"recordDate": "2026-08-15", "plannedPercent": "20.00", "actualPercent": "18.00"},
    )
    records = client.get(f"/api/projects/{project['id']}/progress").json()
    assert len(records) == 2
    assert records[0]["recordDate"] < records[1]["recordDate"]


def test_task_and_milestone_creation(client):
    login_admin(client)
    company = create_company(client)
    project = _create_project(client, company_id=company["id"])

    task = client.post(
        f"/api/projects/{project['id']}/tasks",
        json={"name": "Excavación de zapatas", "plannedStart": "2026-09-01", "plannedEnd": "2026-09-10"},
    )
    assert task.status_code == 201, task.text

    milestone = client.post(
        f"/api/projects/{project['id']}/milestones",
        json={"name": "Cierre de cimentación", "dueDate": "2026-10-01"},
    )
    assert milestone.status_code == 201, milestone.text

    tasks = client.get(f"/api/projects/{project['id']}/tasks").json()
    milestones = client.get(f"/api/projects/{project['id']}/milestones").json()
    assert len(tasks) == 1
    assert len(milestones) == 1


def test_company_isolation_on_projects(client, db_session):
    """INV-COMP-001 aplicado a project: un usuario sin acceso a la company
    de otro no puede leer sus proyectos."""
    from tests.helpers import create_user_with_role

    login_admin(client)
    company_a = create_company(client, name="Constructora A")
    _create_project(client, company_id=company_a["id"], name="Proyecto A")

    create_user_with_role(db_session, email="viewer@nexora.group", role_name="Viewer")
    login_response = client.post(
        "/api/auth/login", json={"email": "viewer@nexora.group", "password": "Passw0rd!23"}
    )
    assert login_response.status_code == 200, login_response.text

    response = client.get("/api/projects", params={"company_id": company_a["id"]})
    assert response.status_code == 403, response.text
