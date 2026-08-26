"""NXR-REQ-0058 (Supplier Performance). Real, controlled fixtures --
never fabricated metrics: every number the API returns is computed by
`reporting_service.supplier_performance` from real PO/GoodsReceipt/
ThreeWayMatchResult rows this test creates through the actual API
flows (RFQ -> quotation -> PO -> receipt -> match), the same as any
real user action would. The "not enough historical volume" gap that
kept this NOT_STARTED was about production data maturity, not about
whether the metric can be computed correctly -- these fixtures prove
it can, honestly, including reporting `None` (not 0% or 100%) with an
explicit sample size when there isn't enough data for a given
supplier/metric."""

from datetime import date, timedelta

from tests.helpers import create_company, create_user_with_role, login_admin, login_as


def _create_warehouse(client, *, company_id: str, code: str) -> dict:
    response = client.post(
        "/api/inventory/warehouses",
        json={"companyId": company_id, "code": code, "name": "Almacén Central"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_supplier(client, *, company_id: str, legal_name: str) -> dict:
    response = client.post(
        "/api/procurement/suppliers",
        json={"companyId": company_id, "legalName": legal_name},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _po_from_quotation(
    client, *, company_id: str, supplier_id: str, unit_price: str, delivery_days: int
) -> dict:
    rfq = client.post(
        "/api/procurement/rfqs", json={"companyId": company_id, "supplierIds": [supplier_id]}
    ).json()
    quotation = client.post(
        f"/api/procurement/rfqs/{rfq['id']}/quotations",
        json={
            "supplierId": supplier_id,
            "currencyCode": "HNL",
            "deliveryDays": delivery_days,
            "lines": [{"description": "Cemento tipo I", "quantity": "10.0000", "unitPrice": unit_price}],
        },
    ).json()
    po = client.post(
        "/api/procurement/purchase-orders/from-quotation",
        json={"companyId": company_id, "supplierQuotationId": quotation["id"]},
    ).json()
    assert po["supplierQuotationId"] == quotation["id"], po
    client.post(f"/api/procurement/purchase-orders/{po['id']}/approve")
    client.post(f"/api/procurement/purchase-orders/{po['id']}/send")
    return po


def _receive(client, *, po: dict, warehouse_id: str, received_at: str) -> None:
    response = client.post(
        "/api/procurement/goods-receipts",
        json={
            "purchaseOrderId": po["id"],
            "warehouseId": warehouse_id,
            "receivedAt": received_at,
            "lines": [{"purchaseOrderLineId": po["lines"][0]["id"], "quantityReceived": "10.0000"}],
        },
    )
    assert response.status_code == 201, response.text


def _match(client, *, po_id: str, amount: str, quantity: str = "10.0000") -> dict:
    response = client.post(
        "/api/procurement/three-way-match",
        json={"purchaseOrderId": po_id, "supplierInvoiceAmount": amount, "supplierInvoiceQuantity": quantity},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_supplier_performance_computes_real_metrics_from_real_fixtures(client):
    login_admin(client)
    company = create_company(client)
    warehouse = _create_warehouse(client, company_id=company["id"], code="ALM-PERF")

    good_supplier = _create_supplier(client, company_id=company["id"], legal_name="Buen Proveedor S.A.")
    bad_supplier = _create_supplier(client, company_id=company["id"], legal_name="Mal Proveedor S.A.")

    today = date.today()

    # Good supplier: two on-time deliveries, both MATCHED, same price both
    # times (price_variance should be 0, computed from a real 2-order
    # sample -- not "no data").
    po1 = _po_from_quotation(
        client, company_id=company["id"], supplier_id=good_supplier["id"],
        unit_price="10.0000", delivery_days=30,
    )
    _receive(client, po=po1, warehouse_id=warehouse["id"], received_at=today.isoformat())
    _match(client, po_id=po1["id"], amount="100.00")

    po2 = _po_from_quotation(
        client, company_id=company["id"], supplier_id=good_supplier["id"],
        unit_price="10.0000", delivery_days=30,
    )
    _receive(client, po=po2, warehouse_id=warehouse["id"], received_at=today.isoformat())
    _match(client, po_id=po2["id"], amount="100.00")

    # Bad supplier: one late delivery (delivery_days=1 but received 30 days
    # later), one price EXCEPTION on the 3-way match, and a second order at
    # a materially different price for the same item (real price variance).
    po3 = _po_from_quotation(
        client, company_id=company["id"], supplier_id=bad_supplier["id"],
        unit_price="10.0000", delivery_days=1,
    )
    _receive(client, po=po3, warehouse_id=warehouse["id"], received_at=(today + timedelta(days=30)).isoformat())
    _match(client, po_id=po3["id"], amount="500.00")  # far off ordered_amount (100.00) -> EXCEPTION

    po4 = _po_from_quotation(
        client, company_id=company["id"], supplier_id=bad_supplier["id"],
        unit_price="20.0000", delivery_days=1,
    )
    _receive(client, po=po4, warehouse_id=warehouse["id"], received_at=(today + timedelta(days=30)).isoformat())
    _match(client, po_id=po4["id"], amount="260.00")  # ordered_amount is 200.00 -> EXCEPTION

    response = client.get(f"/api/reports/supplier-performance?companyId={company['id']}")
    assert response.status_code == 200, response.text
    rows = {row["supplierLegalName"]: row for row in response.json()}

    good = rows["Buen Proveedor S.A."]
    assert good["purchaseOrderCount"] == 2
    assert good["onTimeDeliverySampleSize"] == 2
    assert float(good["onTimeDeliveryRate"]) == 100.0
    assert good["threeWayMatchSampleSize"] == 2
    assert float(good["threeWayMatchCleanRate"]) == 100.0
    assert good["priceVarianceSampleSize"] == 1  # one item compared across 2 orders
    assert float(good["priceVariancePct"]) == 0.0

    bad = rows["Mal Proveedor S.A."]
    assert bad["purchaseOrderCount"] == 2
    assert bad["onTimeDeliverySampleSize"] == 2
    assert float(bad["onTimeDeliveryRate"]) == 0.0
    assert bad["threeWayMatchSampleSize"] == 2
    assert float(bad["threeWayMatchCleanRate"]) == 0.0
    assert bad["priceVarianceSampleSize"] == 1
    assert float(bad["priceVariancePct"]) > 0.0  # 10.00 vs 20.00 for the same item


def test_supplier_performance_reports_none_not_zero_when_there_is_no_data(client):
    """The exact concern that blocked this row: a supplier with zero
    purchase orders must never show a fabricated 0% or 100% -- it must
    show null with sample_size 0, so nobody reads "no data" as "perfect"
    or "terrible" performance."""
    login_admin(client)
    company = create_company(client)
    _create_supplier(client, company_id=company["id"], legal_name="Proveedor Nuevo S.A.")

    response = client.get(f"/api/reports/supplier-performance?companyId={company['id']}")
    assert response.status_code == 200, response.text
    row = next(r for r in response.json() if r["supplierLegalName"] == "Proveedor Nuevo S.A.")
    assert row["purchaseOrderCount"] == 0
    assert row["onTimeDeliveryRate"] is None
    assert row["onTimeDeliverySampleSize"] == 0
    assert row["threeWayMatchCleanRate"] is None
    assert row["priceVariancePct"] is None


def test_supplier_performance_never_returns_another_companys_suppliers(client, db_session):
    from app.models.permission import UserCompanyAccess

    login_admin(client)
    company_a = create_company(client, name="Performance A")
    company_b = create_company(client, name="Performance B")
    _create_supplier(client, company_id=company_a["id"], legal_name="Proveedor A")

    user = create_user_with_role(
        db_session, email="perf-user@nexora.group", role_name="Procurement Manager"
    )
    db_session.add(UserCompanyAccess(user_id=user.id, company_id=company_b["id"]))
    db_session.commit()
    login_as(client, email="perf-user@nexora.group")

    response = client.get(f"/api/reports/supplier-performance?companyId={company_a['id']}")
    assert response.status_code == 403, response.text
    assert response.json()["error"]["code"] == "NXR-PERM-001"
