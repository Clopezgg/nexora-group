"""Contract Payment Control — API (orden maestra final §6, §17-§23)."""

from tests.helpers import create_company, create_supplier, login_admin


def _contract(client, company_id, supplier_id, *, value="500000.00", number="CTR-API-001"):
    r = client.post(
        "/api/procurement/suppliers/contracts",
        json={
            "companyId": company_id, "supplierId": supplier_id, "contractNumber": number,
            "value": value, "currencyCode": "HNL", "startDate": "2026-08-01",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def test_create_monthly_schedule_and_read_back(client):
    login_admin(client)
    company = create_company(client)
    supplier = create_supplier(client, company_id=company["id"])
    contract = _contract(client, company["id"], supplier["id"])

    # Sin plan todavía.
    assert client.get(f"/api/contract-payments/by-contract/{contract['id']}").status_code == 404

    created = client.post(
        "/api/contract-payments/schedules",
        json={
            "supplierContractId": contract["id"],
            "scheduleType": "MONTHLY",
            "regularMonths": 10,
            "dueDay": 1,
            "firstPeriod": "2026-08-01",
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert len(body["installments"]) == 10
    assert body["installments"][0]["periodLabel"] == "Agosto 2026"
    assert sum(float(i["scheduledAmount"]) for i in body["installments"]) == 500000.0

    got = client.get(f"/api/contract-payments/by-contract/{contract['id']}")
    assert got.status_code == 200
    assert got.json()["id"] == body["id"]

    listed = client.get(
        f"/api/contract-payments/schedules?companyId={company['id']}&contractId={contract['id']}"
    )
    assert listed.status_code == 200
    assert len(listed.json()) == 1


def test_legacy_monthly_amount_schedule_shape_is_rejected(client):
    """ORDEN MAESTRA §41: el generador legacy (startPeriod/months/monthlyAmount,
    vencimientos a fin de mes, anticipo ignorado) ya no existe. La única ruta
    mensual es el motor canónico (regularMonths + firstPeriod)."""
    login_admin(client)
    company = create_company(client)
    supplier = create_supplier(client, company_id=company["id"])
    contract = _contract(client, company["id"], supplier["id"], number="CTR-API-LEG")

    r = client.post(
        "/api/contract-payments/schedules",
        json={
            "supplierContractId": contract["id"], "scheduleType": "MONTHLY",
            "startPeriod": "2026-08-01", "months": 10, "monthlyAmount": "50000.00",
        },
    )
    assert r.status_code == 422, r.text


def test_schedule_over_contract_value_is_422(client):
    login_admin(client)
    company = create_company(client)
    supplier = create_supplier(client, company_id=company["id"])
    contract = _contract(client, company["id"], supplier["id"], value="100000.00", number="CTR-API-SM")

    r = client.post(
        "/api/contract-payments/schedules",
        json={
            "supplierContractId": contract["id"], "scheduleType": "CUSTOM",
            "installments": [
                {"periodYear": 2026, "periodMonth": 8, "dueDate": "2026-08-31", "scheduledAmount": "80000.00"},
                {"periodYear": 2026, "periodMonth": 9, "dueDate": "2026-09-30", "scheduledAmount": "80000.00"},
            ],
        },
    )
    assert r.status_code == 422, r.text


def test_summary_and_fifo_preview(client):
    login_admin(client)
    company = create_company(client)
    supplier = create_supplier(client, company_id=company["id"])
    contract = _contract(client, company["id"], supplier["id"], number="CTR-API-SUM")
    schedule = client.post(
        "/api/contract-payments/schedules",
        json={
            "supplierContractId": contract["id"], "scheduleType": "MONTHLY",
            "regularMonths": 10, "dueDay": 1, "firstPeriod": "2026-08-01",
        },
    ).json()

    summary = client.get(f"/api/contract-payments/schedules/{schedule['id']}/summary?asOf=2026-08-15")
    assert summary.status_code == 200, summary.text
    assert float(summary.json()["contractValue"]) == 500000.0
    assert float(summary.json()["paidAccumulated"]) == 0.0
    assert float(summary.json()["contractBalance"]) == 500000.0

    preview = client.post(
        f"/api/contract-payments/schedules/{schedule['id']}/fifo-preview",
        json={"amount": "60000.00", "asOf": "2026-10-01"},
    )
    assert preview.status_code == 200, preview.text
    rows = preview.json()
    assert [r["periodLabel"] for r in rows] == ["Agosto 2026", "Septiembre 2026"]
    assert float(rows[0]["amountApplied"]) == 50000.0
    assert float(rows[1]["amountApplied"]) == 10000.0
