"""Perfil documental de compañía y proyecto (orden maestra final §29-§32)."""

from tests.helpers import create_company, login_admin


def test_company_document_profile_persists(client):
    login_admin(client)
    company = create_company(client)

    r = client.patch(
        f"/api/master-data/companies/{company["id"]}/profile",
        json={
            "legalName": "NEXORA GROUP S. de R.L.",
            "tradeName": "NEXORA GROUP",
            "fiscalId": "08019999123456",
            "addressLine1": "Boulevard Morazán, Edificio Nexora",
            "addressLine2": "Piso 4",
            "city": "Tegucigalpa",
            "stateDepartment": "Francisco Morazán",
            "country": "HN",
            "phone": "+504 2200-0000",
            "email": "admin@nexora.group",
            "voucherFooterText": "Documento generado por NEXORA GROUP.",
            "voucherPayerName": "KAREN VANNESSA LOPEZ GONZALEZ",
            "voucherApproverName": "CARLOS HUMBERTO LOPEZ",
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["tradeName"] == "NEXORA GROUP"
    assert body["addressLine1"] == "Boulevard Morazán, Edificio Nexora"
    assert body["city"] == "Tegucigalpa"
    assert body["phone"] == "+504 2200-0000"
    assert body["voucherFooterText"] == "Documento generado por NEXORA GROUP."

    again = client.get(f"/api/master-data/companies").json()
    row = next(c for c in again if c["id"] == company["id"])
    assert row["addressLine2"] == "Piso 4"
    assert row["stateDepartment"] == "Francisco Morazán"


def test_project_address_fields_persist(client):
    login_admin(client)
    company = create_company(client)

    created = client.post(
        "/api/projects",
        json={"companyId": company["id"], "name": "Residencia López", "code": "RL-01"},
    )
    assert created.status_code == 201, created.text
    project_id = created.json()["id"]

    updated = client.patch(
        f"/api/projects/{project_id}",
        json={
            "addressLine1": "Colonia Las Colinas, bloque M",
            "city": "Tegucigalpa",
            "stateDepartment": "Francisco Morazán",
            "country": "HN",
            "locationReference": "Frente al parque, portón negro",
        },
    )
    assert updated.status_code == 200, updated.text
    body = updated.json()
    assert body["addressLine1"] == "Colonia Las Colinas, bloque M"
    assert body["locationReference"] == "Frente al parque, portón negro"
    assert body["country"] == "HN"
