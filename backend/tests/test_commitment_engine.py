"""Commitment Engine — no doble contar contrato + PO + factura (§18-§23)."""

from decimal import Decimal

from app.models.supplier import SupplierContract
from tests.helpers import create_account, create_company, create_supplier, create_treasury_account, login_admin
from tests.test_project_control import _create_project


def _active_contract(client, db_session, company_id, supplier_id, project_id, *, value="200000.00", number="CE-1"):
    contract = client.post(
        "/api/procurement/suppliers/contracts",
        json={
            "companyId": company_id, "supplierId": supplier_id, "projectId": project_id,
            "contractNumber": number, "value": value, "currencyCode": "HNL", "startDate": "2026-08-01",
        },
    ).json()
    row = db_session.get(SupplierContract, contract["id"])
    row.status = "ACTIVE"
    db_session.commit()
    return contract


def _po(client, company_id, supplier_id, project_id, unit_price, *, contract_id=None):
    body = {
        "companyId": company_id, "supplierId": supplier_id, "projectId": project_id,
        "currencyCode": "HNL",
        "lines": [{"description": "Ejecución", "quantity": "1.0000", "unitPrice": unit_price}],
    }
    if contract_id:
        body["supplierContractId"] = contract_id
    r = client.post("/api/procurement/purchase-orders", json=body)
    assert r.status_code == 201, r.text
    po = r.json()
    approve = client.post(f"/api/procurement/purchase-orders/{po['id']}/approve")
    assert approve.status_code == 200, approve.text
    return po


def test_po_under_contract_does_not_add_to_commitment(client, db_session):
    """ORDEN MAESTRA §20 — contrato 200k + PO ligada 100k => compromiso total
    200k, no 300k. La PO desglosa el compromiso contractual."""
    login_admin(client)
    company = create_company(client)
    project = _create_project(client, company_id=company["id"])
    supplier = create_supplier(client, company_id=company["id"])
    client.post(
        f"/api/projects/{project['id']}/budgets/baseline",
        json={"currencyCode": "HNL", "lines": [{"authorizedAmount": "1000000.00"}]},
    )
    contract = _active_contract(client, db_session, company["id"], supplier["id"], project["id"])
    _po(client, company["id"], supplier["id"], project["id"], "100000.00", contract_id=contract["id"])

    body = client.get(f"/api/projects/{project['id']}/budgets/summary").json()
    assert Decimal(body["committed"]) == Decimal("200000.00")
    assert Decimal(body["contractCommitment"]) == Decimal("200000.00")
    assert Decimal(body["poUnderContract"]) == Decimal("100000.00")
    assert Decimal(body["standalonePoCommitment"]) == Decimal("0")
    assert Decimal(body["openCommitment"]) == Decimal("200000.00")
    assert Decimal(body["available"]) == Decimal("800000.00")


def test_invoice_against_po_relieves_open_commitment_without_double_count(client, db_session):
    """§21/§22 — factura 50k contra la PO: open commitment 150k, devengado 50k,
    exposición 200k, disponible 800k. El pago posterior no vuelve a consumir."""
    login_admin(client)
    company = create_company(client)
    project = _create_project(client, company_id=company["id"])
    supplier = create_supplier(client, company_id=company["id"])
    client.post(
        f"/api/projects/{project['id']}/budgets/baseline",
        json={"currencyCode": "HNL", "lines": [{"authorizedAmount": "1000000.00"}]},
    )
    contract = _active_contract(client, db_session, company["id"], supplier["id"], project["id"], number="CE-2")
    po = _po(client, company["id"], supplier["id"], project["id"], "100000.00", contract_id=contract["id"])

    expense = create_account(client, company_id=company["id"], code="5101", name="Obra", account_type="EXPENSE")
    payable = create_account(client, company_id=company["id"], code="2101", name="CxP", account_type="LIABILITY")
    bank_gl = create_account(client, company_id=company["id"], code="1102", name="Banco", account_type="ASSET")
    bank = create_treasury_account(client, company_id=company["id"], gl_account_id=bank_gl["id"])
    contrib = create_account(client, company_id=company["id"], code="3101", name="Aportes", account_type="EQUITY")
    client.post("/api/treasury/remittances", json={
        "companyId": company["id"], "treasuryAccountId": bank["id"], "counterAccountId": contrib["id"],
        "sender": "Fondeo", "currencyCode": "HNL", "originalAmount": "500000.00", "remittanceDate": "2026-01-01",
    })

    inv = client.post("/api/ap/supplier-invoices", json={
        "companyId": company["id"], "supplierId": supplier["id"], "invoiceNumber": "F-CE-2",
        "scope": "PROJECT", "projectId": project["id"], "purchaseOrderId": po["id"],
        "expenseAccountId": expense["id"], "payableAccountId": payable["id"],
        "currencyCode": "HNL", "amount": "50000.00", "invoiceDate": "2026-09-01", "dueDate": "2026-09-30",
    })
    assert inv.status_code == 201, inv.text
    assert inv.json()["purchaseOrderId"] == po["id"]
    assert inv.json()["supplierContractId"] == contract["id"]  # heredado de la PO
    client.post(f"/api/ap/supplier-invoices/{inv.json()['id']}/approve")

    body = client.get(f"/api/projects/{project['id']}/budgets/summary").json()
    assert Decimal(body["committed"]) == Decimal("200000.00")
    assert Decimal(body["openCommitment"]) == Decimal("150000.00")
    assert Decimal(body["accrued"]) == Decimal("50000.00")
    assert Decimal(body["available"]) == Decimal("800000.00")

    client.post(f"/api/ap/supplier-invoices/{inv.json()['id']}/payments",
                json={"treasuryAccountId": bank["id"], "amount": "50000.00", "paymentDate": "2026-09-05"})
    after = client.get(f"/api/projects/{project['id']}/budgets/summary").json()
    assert Decimal(after["available"]) == Decimal("800000.00")
    assert Decimal(after["paid"]) == Decimal("50000.00")


def test_standalone_po_still_adds_commitment(client, db_session):
    login_admin(client)
    company = create_company(client)
    project = _create_project(client, company_id=company["id"])
    supplier = create_supplier(client, company_id=company["id"])
    client.post(f"/api/projects/{project['id']}/budgets/baseline",
                json={"currencyCode": "HNL", "lines": [{"authorizedAmount": "1000000.00"}]})
    contract = _active_contract(client, db_session, company["id"], supplier["id"], project["id"], number="CE-3")
    _po(client, company["id"], supplier["id"], project["id"], "100000.00", contract_id=contract["id"])
    _po(client, company["id"], supplier["id"], project["id"], "30000.00")  # sin contrato

    body = client.get(f"/api/projects/{project['id']}/budgets/summary").json()
    assert Decimal(body["standalonePoCommitment"]) == Decimal("30000.00")
    assert Decimal(body["committed"]) == Decimal("230000.00")
    assert Decimal(body["available"]) == Decimal("770000.00")


def test_po_linked_to_contract_of_another_supplier_is_rejected(client, db_session):
    login_admin(client)
    company = create_company(client)
    project = _create_project(client, company_id=company["id"])
    s1 = create_supplier(client, company_id=company["id"], legal_name="Uno")
    s2 = create_supplier(client, company_id=company["id"], legal_name="Dos")
    contract = _active_contract(client, db_session, company["id"], s1["id"], project["id"], number="CE-4")
    r = client.post("/api/procurement/purchase-orders", json={
        "companyId": company["id"], "supplierId": s2["id"], "projectId": project["id"],
        "supplierContractId": contract["id"], "currencyCode": "HNL",
        "lines": [{"description": "x", "quantity": "1.0000", "unitPrice": "1000.00"}],
    })
    assert r.status_code == 422, r.text


def test_project_without_baseline_reports_unbudgeted_exposure(client, db_session):
    """§26/§52 — sin baseline: available null, unbudgetedExposure = costo+compromiso abierto."""
    login_admin(client)
    company = create_company(client)
    project = _create_project(client, company_id=company["id"])
    supplier = create_supplier(client, company_id=company["id"])
    contract = _active_contract(client, db_session, company["id"], supplier["id"], project["id"], number="CE-5", value="120000.00")
    _po(client, company["id"], supplier["id"], project["id"], "40000.00", contract_id=contract["id"])

    fin = client.get(f"/api/projects/{project['id']}/financial-summary").json()
    assert fin["available"] is None
    assert Decimal(fin["unbudgetedExposure"]) == Decimal("120000.00")
    assert Decimal(fin["openCommitment"]) == Decimal("120000.00")
