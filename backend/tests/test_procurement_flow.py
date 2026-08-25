import uuid

from sqlalchemy import select

from app.models.audit import AuditLog
from app.models.permission import UserCompanyAccess
from tests.helpers import create_account, create_company, create_user_with_role, login_admin, login_as


def _create_item(client, *, company_id: str, sku: str = "CEM-001") -> dict:
    response = client.post(
        "/api/inventory/items",
        json={"companyId": company_id, "sku": sku, "name": "Cemento", "itemType": "MATERIAL", "uom": "SACO"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_warehouse(client, *, company_id: str, code: str = "ALM-01") -> dict:
    response = client.post(
        "/api/inventory/warehouses",
        json={"companyId": company_id, "code": code, "name": "Almacén Central"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_supplier(client, *, company_id: str) -> dict:
    response = client.post(
        "/api/procurement/suppliers",
        json={"companyId": company_id, "legalName": "Ferreteria Nexora S.A."},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_po(client, *, company_id: str, supplier_id: str, item_id: str) -> dict:
    response = client.post(
        "/api/procurement/purchase-orders",
        json={
            "companyId": company_id,
            "supplierId": supplier_id,
            "currencyCode": "HNL",
            "lines": [
                {"itemId": item_id, "description": "Cemento tipo I", "quantity": "100.0000", "unitPrice": "10.0000"}
            ],
        },
    )
    assert response.status_code == 201, response.text
    order = response.json()
    client.post(f"/api/procurement/purchase-orders/{order['id']}/approve")
    sent = client.post(f"/api/procurement/purchase-orders/{order['id']}/send")
    return sent.json()


def test_requisition_to_purchase_order_end_to_end(client):
    """PR -> approval -> RFQ -> quotation -> PO (orden maestra §44-49)."""
    login_admin(client)
    company = create_company(client)
    supplier = _create_supplier(client, company_id=company["id"])

    pr = client.post(
        "/api/procurement/requisitions",
        json={
            "companyId": company["id"],
            "justification": "Reposición de cemento para obra",
            "lines": [{"description": "Cemento tipo I", "quantity": "100.0000", "estimatedUnitCost": "9.5000"}],
        },
    ).json()
    assert pr["status"] == "SUBMITTED"

    approved = client.post(f"/api/procurement/requisitions/{pr['id']}/approve").json()
    assert approved["status"] == "APPROVED"

    rfq = client.post(
        "/api/procurement/rfqs",
        json={"companyId": company["id"], "purchaseRequisitionId": pr["id"], "supplierIds": [supplier["id"]]},
    ).json()
    assert rfq["rfqNumber"].startswith("RFQ-")

    quotation = client.post(
        f"/api/procurement/rfqs/{rfq['id']}/quotations",
        json={
            "supplierId": supplier["id"],
            "currencyCode": "HNL",
            "lines": [{"description": "Cemento tipo I", "quantity": "100.0000", "unitPrice": "10.0000"}],
        },
    ).json()
    assert float(quotation["total"]) == 1000.0

    po = client.post(
        "/api/procurement/purchase-orders/from-quotation",
        json={"companyId": company["id"], "supplierQuotationId": quotation["id"]},
    ).json()
    assert po["poNumber"].startswith("PO-")
    assert po["status"] == "DRAFT"
    assert float(po["lines"][0]["unitPrice"]) == 10.0

    approved_po = client.post(f"/api/procurement/purchase-orders/{po['id']}/approve").json()
    assert approved_po["status"] == "APPROVED"
    sent_po = client.post(f"/api/procurement/purchase-orders/{po['id']}/send").json()
    assert sent_po["status"] == "SENT"


def test_requisition_without_approval_cannot_skip_to_approved_twice(client):
    login_admin(client)
    company = create_company(client)
    pr = client.post(
        "/api/procurement/requisitions",
        json={"companyId": company["id"], "lines": [{"description": "Arena", "quantity": "5.0000"}]},
    ).json()
    client.post(f"/api/procurement/requisitions/{pr['id']}/approve")
    second = client.post(f"/api/procurement/requisitions/{pr['id']}/approve")
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "NXR-PROCUREMENT-001"


def test_goods_receipt_partial_then_full_updates_po_status_and_stock(client):
    """Recepción parcial (orden maestra §50) + impacto real en Stock Ledger."""
    login_admin(client)
    company = create_company(client)
    supplier = _create_supplier(client, company_id=company["id"])
    item = _create_item(client, company_id=company["id"])
    warehouse = _create_warehouse(client, company_id=company["id"])
    po = _create_po(client, company_id=company["id"], supplier_id=supplier["id"], item_id=item["id"])
    po_line_id = po["lines"][0]["id"]

    partial = client.post(
        "/api/procurement/goods-receipts",
        json={
            "purchaseOrderId": po["id"],
            "warehouseId": warehouse["id"],
            "receivedAt": "2026-08-24",
            "lines": [{"purchaseOrderLineId": po_line_id, "quantityReceived": "60.0000"}],
        },
    )
    assert partial.status_code == 201, partial.text
    assert partial.json()["receiptNumber"].startswith("GR-")

    po_after_partial = client.get(f"/api/procurement/purchase-orders/{po['id']}").json()
    assert po_after_partial["status"] == "PARTIALLY_RECEIVED"
    assert float(po_after_partial["lines"][0]["quantityReceived"]) == 60.0

    position = client.get(
        "/api/inventory/stock/position", params={"item_id": item["id"], "warehouse_id": warehouse["id"]}
    ).json()
    assert float(position["quantityOnHand"]) == 60.0
    assert float(position["averageCost"]) == 10.0

    full = client.post(
        "/api/procurement/goods-receipts",
        json={
            "purchaseOrderId": po["id"],
            "warehouseId": warehouse["id"],
            "receivedAt": "2026-08-25",
            "lines": [{"purchaseOrderLineId": po_line_id, "quantityReceived": "40.0000"}],
        },
    )
    assert full.status_code == 201, full.text

    po_after_full = client.get(f"/api/procurement/purchase-orders/{po['id']}").json()
    assert po_after_full["status"] == "RECEIVED"

    over_receive = client.post(
        "/api/procurement/goods-receipts",
        json={
            "purchaseOrderId": po["id"],
            "warehouseId": warehouse["id"],
            "receivedAt": "2026-08-26",
            "lines": [{"purchaseOrderLineId": po_line_id, "quantityReceived": "1.0000"}],
        },
    )
    assert over_receive.status_code == 409
    assert over_receive.json()["error"]["code"] == "NXR-PROCUREMENT-001"


def test_three_way_match_matched_and_exception(client):
    """INV-PROC-001: las diferencias fuera de tolerancia quedan registradas,
    nunca se descartan; el caso sin diferencia también queda registrado."""
    login_admin(client)
    company = create_company(client)
    supplier = _create_supplier(client, company_id=company["id"])
    item = _create_item(client, company_id=company["id"])
    warehouse = _create_warehouse(client, company_id=company["id"])
    po = _create_po(client, company_id=company["id"], supplier_id=supplier["id"], item_id=item["id"])
    po_line_id = po["lines"][0]["id"]

    client.post(
        "/api/procurement/goods-receipts",
        json={
            "purchaseOrderId": po["id"],
            "warehouseId": warehouse["id"],
            "receivedAt": "2026-08-24",
            "lines": [{"purchaseOrderLineId": po_line_id, "quantityReceived": "100.0000"}],
        },
    )

    matched = client.post(
        "/api/procurement/three-way-match",
        json={
            "purchaseOrderId": po["id"],
            "supplierInvoiceAmount": "1000.00",
            "supplierInvoiceQuantity": "100.0000",
        },
    ).json()
    assert matched["status"] == "MATCHED"
    assert matched["exceptions"] == []

    exception = client.post(
        "/api/procurement/three-way-match",
        json={
            "purchaseOrderId": po["id"],
            "supplierInvoiceAmount": "1500.00",
            "supplierInvoiceQuantity": "100.0000",
        },
    ).json()
    assert exception["status"] == "EXCEPTION"
    assert len(exception["exceptions"]) == 1
    assert exception["exceptions"][0]["type"] == "AMOUNT_MISMATCH"


def test_service_entry_records_progress(client):
    login_admin(client)
    company = create_company(client)
    supplier = _create_supplier(client, company_id=company["id"])
    item = _create_item(client, company_id=company["id"])
    po = _create_po(client, company_id=company["id"], supplier_id=supplier["id"], item_id=item["id"])

    entry = client.post(
        "/api/procurement/service-entries",
        json={
            "purchaseOrderId": po["id"],
            "periodStart": "2026-08-01",
            "periodEnd": "2026-08-31",
            "progressPercentage": "35.00",
            "acceptedValue": "350.00",
        },
    )
    assert entry.status_code == 201, entry.text
    assert entry.json()["entryNumber"].startswith("SEN-")


def test_approving_purchase_order_creates_audit_log_entry(client, db_session):
    login_admin(client)
    company = create_company(client)
    supplier = _create_supplier(client, company_id=company["id"])
    item = _create_item(client, company_id=company["id"])

    order = client.post(
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

    approved = client.post(f"/api/procurement/purchase-orders/{order['id']}/approve")
    assert approved.status_code == 200, approved.text

    rows = db_session.execute(
        select(AuditLog).where(
            AuditLog.entity_type == "procurement.purchase_order",
            AuditLog.entity_id == uuid.UUID(order["id"]),
        )
    ).scalars().all()
    assert len(rows) == 1
    assert rows[0].action == "procurement.purchase_order.approve"
    assert rows[0].after["status"] == "APPROVED"


def _submit_rfq_and_quotation(client, *, company_id: str, supplier_id: str):
    rfq = client.post(
        "/api/procurement/rfqs",
        json={"companyId": company_id, "supplierIds": [supplier_id]},
    ).json()
    quotation = client.post(
        f"/api/procurement/rfqs/{rfq['id']}/quotations",
        json={
            "supplierId": supplier_id,
            "currencyCode": "HNL",
            "lines": [{"description": "Cemento tipo I", "quantity": "10.0000", "unitPrice": "10.0000"}],
        },
    ).json()
    return rfq, quotation


def test_rfq_rejects_a_supplier_from_another_company(client):
    """INV-COMP-001: sin este guard una RFQ podía enviarse a un Supplier de
    otra compañía."""
    login_admin(client)
    company_a = create_company(client, name="RFQ A")
    company_b = create_company(client, name="RFQ B")
    foreign_supplier = _create_supplier(client, company_id=company_b["id"])

    response = client.post(
        "/api/procurement/rfqs",
        json={"companyId": company_a["id"], "supplierIds": [foreign_supplier["id"]]},
    )

    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "NXR-FINANCIAL-001"


def test_listing_rfqs_is_real_and_company_isolated(client, db_session):
    login_admin(client)
    company_a = create_company(client, name="RFQ List A")
    company_b = create_company(client, name="RFQ List B")
    supplier = _create_supplier(client, company_id=company_a["id"])
    rfq, _quotation = _submit_rfq_and_quotation(client, company_id=company_a["id"], supplier_id=supplier["id"])

    listed = client.get(f"/api/procurement/rfqs?company_id={company_a['id']}")
    assert listed.status_code == 200, listed.text
    assert [r["id"] for r in listed.json()] == [rfq["id"]]

    user = create_user_with_role(db_session, email="rfq-list@nexora.group", role_name="Procurement Manager")
    db_session.add(UserCompanyAccess(user_id=user.id, company_id=company_b["id"]))
    db_session.commit()
    login_as(client, email="rfq-list@nexora.group")

    response = client.get(f"/api/procurement/rfqs?company_id={company_a['id']}")
    assert response.status_code == 403, response.text
    assert response.json()["error"]["code"] == "NXR-PERM-001"


def test_submitting_quotation_requires_access_to_the_rfqs_company(client, db_session):
    login_admin(client)
    company_a = create_company(client, name="Quote Access A")
    company_b = create_company(client, name="Quote Access B")
    supplier_a = _create_supplier(client, company_id=company_a["id"])
    rfq = client.post(
        "/api/procurement/rfqs",
        json={"companyId": company_a["id"], "supplierIds": [supplier_a["id"]]},
    ).json()

    user = create_user_with_role(db_session, email="quote-access@nexora.group", role_name="Procurement Manager")
    db_session.add(UserCompanyAccess(user_id=user.id, company_id=company_b["id"]))
    db_session.commit()
    login_as(client, email="quote-access@nexora.group")

    response = client.post(
        f"/api/procurement/rfqs/{rfq['id']}/quotations",
        json={
            "supplierId": supplier_a["id"],
            "currencyCode": "HNL",
            "lines": [{"description": "Cemento tipo I", "quantity": "10.0000", "unitPrice": "10.0000"}],
        },
    )

    assert response.status_code == 403, response.text
    assert response.json()["error"]["code"] == "NXR-PERM-001"


def test_submitting_quotation_rejects_a_supplier_from_another_company(client):
    login_admin(client)
    company_a = create_company(client, name="Quote Supplier A")
    company_b = create_company(client, name="Quote Supplier B")
    supplier_a = _create_supplier(client, company_id=company_a["id"])
    foreign_supplier = _create_supplier(client, company_id=company_b["id"])
    rfq = client.post(
        "/api/procurement/rfqs",
        json={"companyId": company_a["id"], "supplierIds": [supplier_a["id"]]},
    ).json()

    response = client.post(
        f"/api/procurement/rfqs/{rfq['id']}/quotations",
        json={
            "supplierId": foreign_supplier["id"],
            "currencyCode": "HNL",
            "lines": [{"description": "Cemento tipo I", "quantity": "10.0000", "unitPrice": "10.0000"}],
        },
    )

    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "NXR-FINANCIAL-001"


def test_listing_quotations_requires_access_to_the_rfqs_company(client, db_session):
    """Antes de este fix, cualquier usuario con `procurement.quotation
    read` en CUALQUIER compañía podía leer las cotizaciones confidenciales
    de otra compañía adivinando/conociendo el rfq_id -- sin ningún
    `assert_company_access`."""
    login_admin(client)
    company_a = create_company(client, name="Quote Read A")
    company_b = create_company(client, name="Quote Read B")
    supplier_a = _create_supplier(client, company_id=company_a["id"])
    rfq, _quotation = _submit_rfq_and_quotation(client, company_id=company_a["id"], supplier_id=supplier_a["id"])

    user = create_user_with_role(db_session, email="quote-read@nexora.group", role_name="Procurement Manager")
    db_session.add(UserCompanyAccess(user_id=user.id, company_id=company_b["id"]))
    db_session.commit()
    login_as(client, email="quote-read@nexora.group")

    response = client.get(f"/api/procurement/rfqs/{rfq['id']}/quotations")
    assert response.status_code == 403, response.text
    assert response.json()["error"]["code"] == "NXR-PERM-001"


def test_creating_po_from_quotation_rejects_a_foreign_companys_quotation(client):
    """docs/PROCUREMENT.md deuda intencional: `PurchaseOrderFromQuotationRequest`
    confiaba en que el caller ya hizo Bid Comparison correctamente, sin
    validar que la cotización perteneciera a la company indicada."""
    login_admin(client)
    company_a = create_company(client, name="PO Quote A")
    company_b = create_company(client, name="PO Quote B")
    supplier_b = _create_supplier(client, company_id=company_b["id"])
    _rfq_b, quotation_b = _submit_rfq_and_quotation(
        client, company_id=company_b["id"], supplier_id=supplier_b["id"]
    )

    response = client.post(
        "/api/procurement/purchase-orders/from-quotation",
        json={"companyId": company_a["id"], "supplierQuotationId": quotation_b["id"]},
    )

    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "NXR-FINANCIAL-001"
