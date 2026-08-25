import uuid

import pytest

from app.repositories import evidence_repository, user_repository
from tests.conftest import BOOTSTRAP_ADMIN_EMAIL
from tests.helpers import create_account, create_company, create_customer, create_supplier, login_admin


def test_search_finds_project_by_name(client, db_session):
    login_admin(client)
    company = create_company(client)
    client.post(
        "/api/projects",
        json={"companyId": company["id"], "name": "Torre Reforma Norte"},
    )

    response = client.get(f"/api/search?companyId={company['id']}&q=Reforma")
    assert response.status_code == 200, response.text
    results = response.json()
    assert any(r["entityType"] == "project" and "Reforma" in r["label"] for r in results)


def test_search_finds_supplier_by_legal_name(client):
    login_admin(client)
    company = create_company(client)
    create_supplier(client, company_id=company["id"], legal_name="Ferreteria Alfa Unico")

    response = client.get(f"/api/search?companyId={company['id']}&q=Alfa")
    assert response.status_code == 200, response.text
    results = response.json()
    assert any(r["entityType"] == "supplier" and "Alfa" in r["label"] for r in results)


def test_search_finds_customer_by_legal_name(client):
    login_admin(client)
    company = create_company(client)
    create_customer(client, company_id=company["id"], legal_name="Inversiones Beta Unico")

    response = client.get(f"/api/search?companyId={company['id']}&q=Beta")
    assert response.status_code == 200, response.text
    results = response.json()
    assert any(r["entityType"] == "customer" and "Beta" in r["label"] for r in results)


def _setup_ap_accounts(client, *, company_id: str):
    expense = create_account(
        client, company_id=company_id, code="5200", name="Materiales", account_type="EXPENSE"
    )
    payable = create_account(
        client, company_id=company_id, code="2100", name="Cuentas por pagar", account_type="LIABILITY"
    )
    return expense, payable


def test_search_finds_supplier_invoice_by_invoice_number(client):
    login_admin(client)
    company = create_company(client)
    supplier = create_supplier(client, company_id=company["id"])
    expense, payable = _setup_ap_accounts(client, company_id=company["id"])

    client.post(
        "/api/ap/supplier-invoices",
        json={
            "companyId": company["id"],
            "supplierId": supplier["id"],
            "invoiceNumber": "SEARCH-F-001",
            "scope": "GENERAL",
            "expenseAccountId": expense["id"],
            "payableAccountId": payable["id"],
            "currencyCode": "HNL",
            "amount": "100.00",
            "invoiceDate": "2026-01-10",
            "dueDate": "2026-02-10",
        },
    )

    response = client.get(f"/api/search?companyId={company['id']}&q=SEARCH-F")
    assert response.status_code == 200, response.text
    results = response.json()
    assert any(
        r["entityType"] == "supplier_invoice" and "SEARCH-F-001" in r["label"] for r in results
    )


def test_search_finds_customer_invoice_by_invoice_number(client):
    login_admin(client)
    company = create_company(client)
    customer = create_customer(client, company_id=company["id"])
    revenue = create_account(
        client, company_id=company["id"], code="4100", name="Ingresos", account_type="REVENUE"
    )
    receivable = create_account(
        client, company_id=company["id"], code="1200", name="Cuentas por cobrar", account_type="ASSET"
    )

    client.post(
        "/api/ar/customer-invoices",
        json={
            "companyId": company["id"],
            "customerId": customer["id"],
            "invoiceNumber": "SEARCH-CI-001",
            "scope": "GENERAL",
            "revenueAccountId": revenue["id"],
            "receivableAccountId": receivable["id"],
            "currencyCode": "HNL",
            "amount": "100.00",
            "invoiceDate": "2026-01-10",
            "dueDate": "2026-02-10",
        },
    )

    response = client.get(f"/api/search?companyId={company['id']}&q=SEARCH-CI")
    assert response.status_code == 200, response.text
    results = response.json()
    assert any(
        r["entityType"] == "customer_invoice" and "SEARCH-CI-001" in r["label"] for r in results
    )


def test_search_finds_purchase_order_by_po_number(client):
    login_admin(client)
    company = create_company(client)
    supplier = create_supplier(client, company_id=company["id"])
    item = client.post(
        "/api/inventory/items",
        json={"companyId": company["id"], "sku": "CEM-SEARCH", "name": "Cemento", "itemType": "MATERIAL", "uom": "SACO"},
    ).json()

    po = client.post(
        "/api/procurement/purchase-orders",
        json={
            "companyId": company["id"],
            "supplierId": supplier["id"],
            "currencyCode": "HNL",
            "lines": [
                {"itemId": item["id"], "description": "Cemento tipo I", "quantity": "10.0000", "unitPrice": "10.0000"}
            ],
        },
    ).json()

    response = client.get(f"/api/search?companyId={company['id']}&q={po['poNumber'][:6]}")
    assert response.status_code == 200, response.text
    results = response.json()
    assert any(r["entityType"] == "purchase_order" and r["label"] == po["poNumber"] for r in results)


def _admin_user_id(db_session) -> uuid.UUID:
    user = user_repository.get_by_email(db_session, BOOTSTRAP_ADMIN_EMAIL)
    assert user is not None
    return user.id


def test_search_finds_document_by_title(client, db_session):
    login_admin(client)
    company = create_company(client)
    evidence = evidence_repository.create_evidence(
        db_session,
        company_id=uuid.UUID(company["id"]),
        blob_key=f"{company['id']}/{uuid.uuid4()}-plano.pdf",
        original_filename="plano.pdf",
        mime_type="application/pdf",
        size_bytes=1024,
        uploaded_by=_admin_user_id(db_session),
    )
    db_session.commit()

    client.post(
        "/api/documents",
        json={
            "companyId": company["id"],
            "scope": "GENERAL",
            "category": "DRAWING",
            "title": "Plano estructural Gamma Unico",
            "evidenceId": str(evidence.id),
        },
    )

    response = client.get(f"/api/search?companyId={company['id']}&q=Gamma")
    assert response.status_code == 200, response.text
    results = response.json()
    assert any(r["entityType"] == "document" and "Gamma" in r["label"] for r in results)


def test_search_finds_rfi_by_subject(client):
    login_admin(client)
    company = create_company(client)
    project = client.post(
        "/api/projects",
        json={"companyId": company["id"], "name": "Torre RFI Search", "code": "PRJ-SEARCH-RFI"},
    ).json()

    client.post(
        "/api/rfis",
        json={
            "companyId": company["id"],
            "projectId": project["id"],
            "subject": "Detalle de anclaje Delta Unico",
            "question": "¿Cuál es el detalle de anclaje?",
        },
    )

    response = client.get(f"/api/search?companyId={company['id']}&q=Delta")
    assert response.status_code == 200, response.text
    results = response.json()
    assert any(r["entityType"] == "rfi" and "Delta" in r["label"] for r in results)


def test_search_finds_fixed_asset_by_name(client):
    login_admin(client)
    company = create_company(client)
    expense = create_account(
        client, company_id=company["id"], code="5300", name="Depreciación", account_type="EXPENSE"
    )
    accumulated = create_account(
        client, company_id=company["id"], code="1590", name="Depreciación acumulada", account_type="ASSET"
    )

    client.post(
        "/api/assets",
        json={
            "companyId": company["id"],
            "category": "Maquinaria pesada",
            "name": "Excavadora Epsilon Unico",
            "acquisitionDate": "2026-01-01",
            "cost": "12000.00",
            "currencyCode": "HNL",
            "usefulLifeMonths": 12,
            "salvageValue": "0.00",
            "scope": "GENERAL",
            "depreciationExpenseAccountId": expense["id"],
            "accumulatedDepreciationAccountId": accumulated["id"],
        },
    )

    response = client.get(f"/api/search?companyId={company['id']}&q=Epsilon")
    assert response.status_code == 200, response.text
    results = response.json()
    assert any(r["entityType"] == "fixed_asset" and "Epsilon" in r["label"] for r in results)


def test_search_finds_equipment_by_name(client):
    login_admin(client)
    company = create_company(client)

    client.post(
        "/api/equipment",
        json={"companyId": company["id"], "equipmentType": "EXCAVATOR", "name": "Retroexcavadora Zeta Unico"},
    )

    response = client.get(f"/api/search?companyId={company['id']}&q=Zeta")
    assert response.status_code == 200, response.text
    results = response.json()
    assert any(r["entityType"] == "equipment" and "Zeta" in r["label"] for r in results)


def test_search_never_returns_another_companys_results(client, db_session):
    login_admin(client)
    company_a = create_company(client, name="Search A")
    company_b = create_company(client, name="Search B")
    client.post("/api/projects", json={"companyId": company_a["id"], "name": "Unico Alpha"})

    response = client.get(f"/api/search?companyId={company_b['id']}&q=Alpha")
    assert response.status_code == 200
    assert response.json() == []


# Company-isolation coverage beyond Project (code-review follow-up): all
# ten blocks in search_service.search() share the identical
# `Model.company_id == company_id` shape, but that's exactly the kind of
# thing a copy-paste error (e.g. filtering by a *joined* company_id, or
# dropping the filter) slips through in one specific block while every
# other test still passes. Project alone only proves the *simplest*
# shape (a model with no FK to another company-scoped entity). These
# five cases add the other two structurally distinct shapes actually
# used in search_service.py:
#   - plain company-scoped, no FK dependency: Supplier, Customer
#     (same shape as Project, but two more independent instances of it)
#   - company-scoped AND has a FK to *another* company-scoped entity
#     (Supplier/Customer) that a mistake could accidentally filter by
#     instead: SupplierInvoice (supplier_id), PurchaseOrder (supplier_id)
#   - company-scoped AND has a required FK to Project (another
#     company-scoped entity): RequestForInformation (project_id)
# This is 6/10 total (with the Project test above) -- not exhaustive,
# but every distinct query-construction pattern in search_service.py is
# now covered by at least one isolation case, which is what actually
# bounds the residual risk here (not the raw entity count).


def _isolated_supplier(client, company_id: str) -> tuple[str, str]:
    create_supplier(client, company_id=company_id, legal_name="IsoOnly Proveedor Uno")
    return "IsoOnly", "supplier"


def _isolated_customer(client, company_id: str) -> tuple[str, str]:
    create_customer(client, company_id=company_id, legal_name="IsoOnly Cliente Uno")
    return "IsoOnly", "customer"


def _isolated_supplier_invoice(client, company_id: str) -> tuple[str, str]:
    supplier = create_supplier(client, company_id=company_id)
    expense, payable = _setup_ap_accounts(client, company_id=company_id)
    client.post(
        "/api/ap/supplier-invoices",
        json={
            "companyId": company_id,
            "supplierId": supplier["id"],
            "invoiceNumber": "ISOONLY-INV-001",
            "scope": "GENERAL",
            "expenseAccountId": expense["id"],
            "payableAccountId": payable["id"],
            "currencyCode": "HNL",
            "amount": "100.00",
            "invoiceDate": "2026-01-10",
            "dueDate": "2026-02-10",
        },
    )
    return "ISOONLY-INV", "supplier_invoice"


def _isolated_purchase_order(client, company_id: str) -> tuple[str, str]:
    supplier = create_supplier(client, company_id=company_id)
    item = client.post(
        "/api/inventory/items",
        json={
            "companyId": company_id,
            "sku": "ISOONLY-SKU",
            "name": "Cemento aislado",
            "itemType": "MATERIAL",
            "uom": "SACO",
        },
    ).json()
    client.post(
        "/api/procurement/purchase-orders",
        json={
            "companyId": company_id,
            "supplierId": supplier["id"],
            "currencyCode": "HNL",
            "lines": [
                {
                    "itemId": item["id"],
                    "description": "Cemento tipo I",
                    "quantity": "10.0000",
                    "unitPrice": "10.0000",
                }
            ],
        },
    )
    # po_number is a real generated sequence value, not a literal we
    # control -- the isolation assertion below checks for zero results
    # from company_b instead of matching a fixed substring (see caller).
    return "", "purchase_order"


def _isolated_rfi(client, company_id: str) -> tuple[str, str]:
    project = client.post(
        "/api/projects", json={"companyId": company_id, "name": "Proyecto IsoOnly RFI"}
    ).json()
    client.post(
        "/api/rfis",
        json={
            "companyId": company_id,
            "projectId": project["id"],
            "subject": "IsoOnly Detalle de anclaje",
            "question": "¿Detalle de anclaje?",
        },
    )
    return "IsoOnly", "rfi"


_ISOLATION_CASES = [
    ("supplier", _isolated_supplier),
    ("customer", _isolated_customer),
    ("supplier_invoice", _isolated_supplier_invoice),
    ("purchase_order", _isolated_purchase_order),
    ("rfi", _isolated_rfi),
]


@pytest.mark.parametrize(
    "expected_entity_type, create_in_company", _ISOLATION_CASES, ids=[c[0] for c in _ISOLATION_CASES]
)
def test_search_isolation_across_representative_entity_types(
    client, expected_entity_type, create_in_company
):
    """Company A gets a real row of this entity type; company B searches
    for it and must never see it -- proves INV-COMP-001 holds for each
    structurally distinct query shape in search_service.py, not just the
    one Project happens to use."""
    login_admin(client)
    company_a = create_company(client, name=f"Iso A {expected_entity_type}")
    company_b = create_company(client, name=f"Iso B {expected_entity_type}")

    query_fragment, entity_type = create_in_company(client, company_a["id"])
    assert entity_type == expected_entity_type

    if entity_type == "purchase_order":
        # No stable literal substring to search for (po_number is
        # sequence-generated) -- assert the whole company_b search for a
        # generic term returns zero purchase_order rows instead.
        response = client.get(f"/api/search?companyId={company_b['id']}&q=PO-")
        assert response.status_code == 200, response.text
        assert not any(r["entityType"] == "purchase_order" for r in response.json())
        return

    response = client.get(f"/api/search?companyId={company_b['id']}&q={query_fragment}")
    assert response.status_code == 200, response.text
    assert response.json() == []
