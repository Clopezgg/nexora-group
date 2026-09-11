import uuid
from decimal import Decimal

from sqlalchemy import select

from app.models.audit import AuditLog
from app.models.permission import UserCompanyAccess
from tests.helpers import (
    create_account,
    create_company,
    create_supplier,
    create_treasury_account,
    create_user_with_role,
    login_admin,
    login_as,
)


def _setup_flow(client, *, suffix: str = "A", invoice_amount: str = "1000.00", tax_amount: str = "150.00") -> dict:
    company = create_company(client, name=f"Compañía TWM {suffix}")
    expense = create_account(
        client,
        company_id=company["id"],
        code=f"52{suffix}0",
        name="Compras",
        account_type="EXPENSE",
    )
    payable = create_account(
        client,
        company_id=company["id"],
        code=f"21{suffix}0",
        name="Proveedores",
        account_type="LIABILITY",
    )
    bank_gl = create_account(
        client,
        company_id=company["id"],
        code=f"11{suffix}0",
        name="Banco",
        account_type="ASSET",
    )
    bank = create_treasury_account(
        client,
        company_id=company["id"],
        gl_account_id=bank_gl["id"],
        name=f"Banco TWM {suffix}",
    )
    supplier = create_supplier(client, company_id=company["id"], legal_name=f"Proveedor TWM {suffix}")
    item_response = client.post(
        "/api/inventory/items",
        json={
            "companyId": company["id"],
            "sku": f"TWM-{suffix}",
            "name": "Material controlado",
            "itemType": "MATERIAL",
            "uom": "UN",
        },
    )
    assert item_response.status_code == 201, item_response.text
    item = item_response.json()
    warehouse_response = client.post(
        "/api/inventory/warehouses",
        json={"companyId": company["id"], "code": f"TWM-{suffix}", "name": "Almacén TWM"},
    )
    assert warehouse_response.status_code == 201, warehouse_response.text
    warehouse = warehouse_response.json()
    po_response = client.post(
        "/api/procurement/purchase-orders",
        json={
            "companyId": company["id"],
            "supplierId": supplier["id"],
            "currencyCode": "HNL",
            "lines": [
                {
                    "itemId": item["id"],
                    "description": "Material controlado",
                    "quantity": "100.0000",
                    "unitPrice": "10.0000",
                    "taxAmount": "150.00",
                }
            ],
        },
    )
    assert po_response.status_code == 201, po_response.text
    po = po_response.json()
    assert client.post(f"/api/procurement/purchase-orders/{po['id']}/approve").status_code == 200
    assert client.post(f"/api/procurement/purchase-orders/{po['id']}/send").status_code == 200
    receipt_response = client.post(
        "/api/procurement/goods-receipts",
        json={
            "purchaseOrderId": po["id"],
            "warehouseId": warehouse["id"],
            "receivedAt": "2026-08-24",
            "lines": [{"purchaseOrderLineId": po["lines"][0]["id"], "quantityReceived": "100.0000"}],
        },
    )
    assert receipt_response.status_code == 201, receipt_response.text
    invoice_response = client.post(
        "/api/ap/supplier-invoices",
        json={
            "companyId": company["id"],
            "supplierId": supplier["id"],
            "invoiceNumber": f"TWM-{suffix}-001",
            "scope": "GENERAL",
            "expenseAccountId": expense["id"],
            "payableAccountId": payable["id"],
            "currencyCode": "HNL",
            "amount": invoice_amount,
            "taxAmount": tax_amount,
            "invoiceDate": "2026-08-24",
            "dueDate": "2026-09-24",
            "purchaseOrderId": po["id"],
        },
    )
    assert invoice_response.status_code == 201, invoice_response.text
    invoice = invoice_response.json()
    approved = client.post(f"/api/ap/supplier-invoices/{invoice['id']}/approve")
    assert approved.status_code == 200, approved.text
    return {
        "company": company,
        "expense": expense,
        "payable": payable,
        "bank": bank,
        "supplier": supplier,
        "po": po,
        "invoice": invoice,
    }


def _match(client, flow: dict, *, quantity: str = "100.0000"):
    return client.post(
        "/api/procurement/three-way-match",
        json={
            "purchaseOrderId": flow["po"]["id"],
            "supplierInvoiceId": flow["invoice"]["id"],
            "supplierInvoiceQuantity": quantity,
        },
    )


def _pay(client, flow: dict):
    total = Decimal(flow["invoice"]["amount"]) + Decimal(flow["invoice"]["taxAmount"])
    return client.post(
        f"/api/ap/supplier-invoices/{flow['invoice']['id']}/payments",
        json={
            "treasuryAccountId": flow["bank"]["id"],
            "amount": str(total),
            "paymentDate": "2026-08-25",
            "paymentMethod": "OTHER",
        },
    )


def test_po_invoice_payment_is_blocked_without_three_way_match(client):
    login_admin(client)
    flow = _setup_flow(client)

    response = _pay(client, flow)

    assert response.status_code == 422, response.text
    assert "three-way match" in response.text.lower()


def test_matched_invoice_is_payable_and_invoice_total_includes_tax(client):
    login_admin(client)
    flow = _setup_flow(client)

    match = _match(client, flow)

    assert match.status_code == 201, match.text
    assert match.json()["status"] == "MATCHED"
    assert match.json()["supplierInvoiceId"] == flow["invoice"]["id"]
    assert match.json()["supplierInvoiceAmount"] == "1150.00"
    paid = _pay(client, flow)
    assert paid.status_code == 201, paid.text


def test_exception_blocks_payment_until_formal_override_and_audits_actor(client, db_session):
    login_admin(client)
    flow = _setup_flow(client, invoice_amount="1200.00", tax_amount="150.00")
    match_response = _match(client, flow)
    assert match_response.status_code == 201, match_response.text
    match = match_response.json()
    assert match["status"] == "EXCEPTION"

    blocked = _pay(client, flow)
    assert blocked.status_code == 422, blocked.text

    overridden = client.post(
        f"/api/procurement/three-way-match/{match['id']}/override",
        json={"reason": "Factura autorizada por variación contractual documentada"},
    )
    assert overridden.status_code == 200, overridden.text
    assert overridden.json()["overrideReason"]
    assert overridden.json()["overriddenByUserId"]
    assert overridden.json()["overriddenAt"]

    paid = _pay(client, flow)
    assert paid.status_code == 201, paid.text
    # The API contract above proves the persisted actor; the exact audit row
    # is asserted below without coupling to transaction ordering.
    rows = db_session.execute(
        select(AuditLog).where(AuditLog.action == "procurement.three_way_match.override")
    ).scalars().all()
    assert any(row.entity_id == uuid.UUID(match["id"]) for row in rows)


def test_exception_override_requires_dedicated_permission(client, db_session):
    login_admin(client)
    flow = _setup_flow(client, invoice_amount="1200.00", tax_amount="150.00")
    match = _match(client, flow).json()
    buyer = create_user_with_role(db_session, email="buyer-twm@nexora.group", role_name="Buyer")
    db_session.add(UserCompanyAccess(user_id=buyer.id, company_id=uuid.UUID(flow["company"]["id"])))
    db_session.commit()
    login_as(client, email="buyer-twm@nexora.group")

    response = client.post(
        f"/api/procurement/three-way-match/{match['id']}/override",
        json={"reason": "Intento de autorización sin permiso dedicado"},
    )

    assert response.status_code == 403, response.text


def test_three_way_match_rejects_wrong_invoice_supplier_company_and_currency(client):
    login_admin(client)
    flow = _setup_flow(client)

    other_po_response = client.post(
        "/api/procurement/purchase-orders",
        json={
            "companyId": flow["company"]["id"],
            "supplierId": flow["supplier"]["id"],
            "currencyCode": "HNL",
            "lines": [{"description": "Otra orden", "quantity": "1.0000", "unitPrice": "1150.0000"}],
        },
    )
    assert other_po_response.status_code == 201, other_po_response.text
    other_po = other_po_response.json()
    wrong_po_invoice = client.post(
        "/api/ap/supplier-invoices",
        json={
            "companyId": flow["company"]["id"],
            "supplierId": flow["supplier"]["id"],
            "invoiceNumber": "WRONG-PO",
            "scope": "GENERAL",
            "expenseAccountId": flow["expense"]["id"],
            "payableAccountId": flow["payable"]["id"],
            "currencyCode": "HNL",
            "amount": "1150.00",
            "invoiceDate": "2026-08-24",
            "dueDate": "2026-09-24",
            "purchaseOrderId": other_po["id"],
        },
    ).json()

    wrong_supplier = create_supplier(
        client,
        company_id=flow["company"]["id"],
        legal_name="Proveedor incorrecto",
    )
    wrong_supplier_invoice = client.post(
        "/api/ap/supplier-invoices",
        json={
            "companyId": flow["company"]["id"],
            "supplierId": wrong_supplier["id"],
            "invoiceNumber": "WRONG-SUPPLIER",
            "scope": "GENERAL",
            "expenseAccountId": flow["expense"]["id"],
            "payableAccountId": flow["payable"]["id"],
            "currencyCode": "HNL",
            "amount": "1150.00",
            "invoiceDate": "2026-08-24",
            "dueDate": "2026-09-24",
        },
    ).json()

    other_company = create_company(client, name="Otra compañía TWM")
    other_expense = create_account(
        client, company_id=other_company["id"], code="5299", name="Compras", account_type="EXPENSE"
    )
    other_payable = create_account(
        client, company_id=other_company["id"], code="2199", name="Proveedores", account_type="LIABILITY"
    )
    other_supplier = create_supplier(client, company_id=other_company["id"])
    wrong_company_invoice = client.post(
        "/api/ap/supplier-invoices",
        json={
            "companyId": other_company["id"],
            "supplierId": other_supplier["id"],
            "invoiceNumber": "WRONG-COMPANY",
            "scope": "GENERAL",
            "expenseAccountId": other_expense["id"],
            "payableAccountId": other_payable["id"],
            "currencyCode": "HNL",
            "amount": "1150.00",
            "invoiceDate": "2026-08-24",
            "dueDate": "2026-09-24",
        },
    ).json()

    wrong_currency_invoice = client.post(
        "/api/ap/supplier-invoices",
        json={
            "companyId": flow["company"]["id"],
            "supplierId": flow["supplier"]["id"],
            "invoiceNumber": "WRONG-CURRENCY",
            "scope": "GENERAL",
            "expenseAccountId": flow["expense"]["id"],
            "payableAccountId": flow["payable"]["id"],
            "currencyCode": "USD",
            "amount": "1150.00",
            "invoiceDate": "2026-08-24",
            "dueDate": "2026-09-24",
        },
    ).json()

    for invoice, expected_detail in (
        (wrong_po_invoice, "no corresponde"),
        (wrong_supplier_invoice, "proveedores distintos"),
        (wrong_company_invoice, "compañías distintas"),
        (wrong_currency_invoice, "moneda"),
    ):
        response = client.post(
            "/api/procurement/three-way-match",
            json={
                "purchaseOrderId": flow["po"]["id"],
                "supplierInvoiceId": invoice["id"],
                "supplierInvoiceQuantity": "100.0000",
            },
        )
        assert response.status_code == 422, response.text
        assert expected_detail in response.text.lower()
