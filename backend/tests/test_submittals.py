from app.models.permission import UserCompanyAccess
from tests.helpers import create_company, create_supplier, create_user_with_role, login_admin, login_as


def _create_project(client, *, company_id: str, name: str = "Torre Nexora", code: str = "PRJ-SUB-01") -> dict:
    response = client.post(
        "/api/projects",
        json={"companyId": company_id, "name": name, "code": code, "currencyCode": "HNL"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_contract(client, *, company_id: str, supplier_id: str, contract_number: str = "SC-001") -> dict:
    response = client.post(
        "/api/procurement/suppliers/contracts",
        json={
            "companyId": company_id,
            "supplierId": supplier_id,
            "contractNumber": contract_number,
            "value": "150000.00",
            "currencyCode": "HNL",
            "startDate": "2026-01-01",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_submittal(client, *, company_id: str, project_id: str, title: str = "Ficha técnica de acero de refuerzo", **extra) -> dict:
    payload = {
        "companyId": company_id,
        "projectId": project_id,
        "title": title,
        "submittedAt": "2026-03-01",
        **extra,
    }
    response = client.post("/api/submittals", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_submittal_requires_response_before_approval(client):
    """Comportamiento de aceptación de este task: aprobar un Submittal sin
    una respuesta de revisor registrada se rechaza."""
    login_admin(client)
    company = create_company(client)
    project = _create_project(client, company_id=company["id"])
    submittal = _create_submittal(client, company_id=company["id"], project_id=project["id"])
    assert submittal["status"] == "SUBMITTED"
    assert submittal["reviewerResponse"] is None

    decision_without_response = client.post(
        f"/api/submittals/{submittal['id']}/decision", json={"decision": "APPROVED"}
    )
    assert decision_without_response.status_code == 409, decision_without_response.text
    assert decision_without_response.json()["error"]["code"] == "NXR-SUBMITTAL-001"

    record_response = client.post(
        f"/api/submittals/{submittal['id']}/response",
        json={"response": "Cumple con la especificación ASTM A615."},
    )
    assert record_response.status_code == 200, record_response.text
    assert record_response.json()["status"] == "UNDER_REVIEW"
    assert record_response.json()["reviewerResponse"] == "Cumple con la especificación ASTM A615."

    decision = client.post(f"/api/submittals/{submittal['id']}/decision", json={"decision": "APPROVED"})
    assert decision.status_code == 200, decision.text
    assert decision.json()["status"] == "APPROVED"
    assert decision.json()["decidedAt"] is not None

    # Una vez con decisión final, no se puede volver a decidir.
    redecide = client.post(f"/api/submittals/{submittal['id']}/decision", json={"decision": "REJECTED"})
    assert redecide.status_code == 409, redecide.text
    assert redecide.json()["error"]["code"] == "NXR-SUBMITTAL-001"


def test_submittal_optional_supplier_and_contract_reference(client):
    login_admin(client)
    company = create_company(client)
    project = _create_project(client, company_id=company["id"])
    supplier = create_supplier(client, company_id=company["id"])
    contract = _create_contract(client, company_id=company["id"], supplier_id=supplier["id"])

    submittal = _create_submittal(
        client,
        company_id=company["id"],
        project_id=project["id"],
        supplierId=supplier["id"],
        contractId=contract["id"],
    )
    assert submittal["supplierId"] == supplier["id"]
    assert submittal["contractId"] == contract["id"]


def test_submittal_rejects_contract_from_another_company(client):
    login_admin(client)
    company_a = create_company(client, name="Constructora A")
    company_b = create_company(client, name="Constructora B")
    project_a = _create_project(client, company_id=company_a["id"], code="PRJ-A")
    supplier_b = create_supplier(client, company_id=company_b["id"])
    contract_b = _create_contract(client, company_id=company_b["id"], supplier_id=supplier_b["id"])

    response = client.post(
        "/api/submittals",
        json={
            "companyId": company_a["id"],
            "projectId": project_a["id"],
            "title": "Cruzado",
            "submittedAt": "2026-03-01",
            "contractId": contract_b["id"],
        },
    )
    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "NXR-FINANCIAL-001"


def test_company_access_blocks_cross_company_submittal(client, db_session):
    login_admin(client)
    company_a = create_company(client, name="Constructora A")
    company_b = create_company(client, name="Constructora B")
    project_a = _create_project(client, company_id=company_a["id"], code="PRJ-A")
    submittal_a = _create_submittal(client, company_id=company_a["id"], project_id=project_a["id"])

    user = create_user_with_role(db_session, email="pm-b-sub@nexora.group", role_name="Project Manager")
    db_session.add(UserCompanyAccess(user_id=user.id, company_id=company_b["id"]))
    db_session.commit()
    login_as(client, email="pm-b-sub@nexora.group")

    response = client.get(f"/api/submittals/{submittal_a['id']}")
    assert response.status_code == 403, response.text
    assert response.json()["error"]["code"] == "NXR-PERM-001"
