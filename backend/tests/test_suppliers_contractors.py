"""CORRECTIVA §10-§20 / §29 — Proveedores y Contratistas.

Tipo de tercero (SUPPLIER/CONTRACTOR/BOTH), edición real, cambio de estado
(ACTIVE/INACTIVE/BLOCKED/ARCHIVED), soft-delete, y BLOCKED/ARCHIVED impide
nuevos contratos.
"""

from app.models.permission import UserCompanyAccess
from tests.helpers import (
    create_company,
    create_supplier,
    create_user_with_role,
    login_admin,
    login_as,
)


def _supplier(client, company_id, *, name="Lester Rivas", role="CONTRACTOR"):
    r = client.post(
        "/api/procurement/suppliers",
        json={"companyId": company_id, "legalName": name, "partyRole": role},
    )
    assert r.status_code == 201, r.text
    return r.json()


def test_create_contractor_with_party_role(client):
    login_admin(client)
    company = create_company(client, name="Terceros Co")
    s = _supplier(client, company["id"])
    assert s["partyRole"] == "CONTRACTOR"
    assert s["status"] == "ACTIVE"


def test_edit_supplier_master_data(client):
    login_admin(client)
    company = create_company(client, name="Edit Co")
    s = _supplier(client, company["id"], name="Constructora X", role="SUPPLIER")

    r = client.patch(
        f"/api/procurement/suppliers/{s['id']}",
        json={"tradeName": "Constructora X S. de R.L.", "email": "pagos@x.hn", "partyRole": "BOTH"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["tradeName"] == "Constructora X S. de R.L."
    assert body["email"] == "pagos@x.hn"
    assert body["partyRole"] == "BOTH"
    assert body["legalName"] == "Constructora X"  # no tocado

    audit = client.get(
        f"/api/audit?companyId={company['id']}&entityType=procurement.supplier"
    ).json()
    assert any(e["action"] == "procurement.supplier.update" for e in audit)


def test_supplier_status_transitions_and_soft_delete(client):
    login_admin(client)
    company = create_company(client, name="Status Co")
    s = _supplier(client, company["id"])

    assert client.post(f"/api/procurement/suppliers/{s['id']}/status", json={"status": "INACTIVE"}).json()["status"] == "INACTIVE"
    # BLOCKED requiere motivo.
    assert client.post(f"/api/procurement/suppliers/{s['id']}/status", json={"status": "BLOCKED"}).status_code == 422
    blocked = client.post(
        f"/api/procurement/suppliers/{s['id']}/status",
        json={"status": "BLOCKED", "reason": "Incumplimiento contractual reiterado"},
    )
    assert blocked.status_code == 200, blocked.text

    archived = client.post(
        f"/api/procurement/suppliers/{s['id']}/status",
        json={"status": "ARCHIVED", "reason": "Eliminado del catálogo de terceros"},
    )
    assert archived.status_code == 200
    assert archived.json()["status"] == "ARCHIVED"

    restored = client.post(
        f"/api/procurement/suppliers/{s['id']}/status",
        json={"status": "ACTIVE", "reason": "Se reincorpora tras resolver el litigio"},
    )
    assert restored.status_code == 200
    assert restored.json()["status"] == "ACTIVE"


def test_blocked_supplier_cannot_get_new_contract(client):
    login_admin(client)
    company = create_company(client, name="Blocked Contract Co")
    s = _supplier(client, company["id"])
    client.post(
        f"/api/procurement/suppliers/{s['id']}/status",
        json={"status": "BLOCKED", "reason": "Bloqueado por auditoría interna"},
    )
    r = client.post(
        "/api/procurement/suppliers/contracts",
        json={
            "companyId": company["id"], "supplierId": s["id"], "contractNumber": "CON-BLK-1",
            "value": "100000.00", "currencyCode": "HNL", "startDate": "2026-08-01",
        },
    )
    assert r.status_code == 409, r.text
    assert "bloqueado" in r.text


def test_supplier_edit_is_company_isolated(client, db_session):
    login_admin(client)
    company_a = create_company(client, name="ISO A")
    company_b = create_company(client, name="ISO B")
    s = create_supplier(client, company_id=company_a["id"])

    user = create_user_with_role(
        db_session, email="proc-b@nexora.group", role_name="Procurement Manager"
    )
    db_session.add(UserCompanyAccess(user_id=user.id, company_id=company_b["id"]))
    db_session.commit()
    login_as(client, email="proc-b@nexora.group")

    r = client.patch(f"/api/procurement/suppliers/{s['id']}", json={"email": "x@x.hn"})
    assert r.status_code in (403, 404), r.text
