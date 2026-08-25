from app.models.permission import UserCompanyAccess
from tests.helpers import create_company, create_user_with_role, login_admin, login_as


def _create_project(client, *, company_id: str, name: str = "Torre Nexora", code: str = "PRJ-RFI-01") -> dict:
    response = client.post(
        "/api/projects",
        json={"companyId": company_id, "name": name, "code": code, "currencyCode": "HNL"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_rfi(client, *, company_id: str, project_id: str, subject: str = "Detalle de anclaje") -> dict:
    response = client.post(
        "/api/rfis",
        json={
            "companyId": company_id,
            "projectId": project_id,
            "subject": subject,
            "question": "¿Cuál es el detalle de anclaje especificado en el plano estructural E-05?",
            "responsible": "Ing. Residente",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_rfi_lifecycle_open_answer_close(client):
    login_admin(client)
    company = create_company(client)
    project = _create_project(client, company_id=company["id"])

    rfi = _create_rfi(client, company_id=company["id"], project_id=project["id"])
    assert rfi["status"] == "OPEN"
    assert rfi["response"] is None
    assert rfi["number"].startswith("RFI-")

    respond = client.post(f"/api/rfis/{rfi['id']}/respond", json={"response": "Ver detalle revisado E-05-R1."})
    assert respond.status_code == 200, respond.text
    assert respond.json()["status"] == "ANSWERED"
    assert respond.json()["response"] == "Ver detalle revisado E-05-R1."
    assert respond.json()["respondedAt"] is not None

    # Responder un RFI que ya no está OPEN se rechaza.
    respond_again = client.post(f"/api/rfis/{rfi['id']}/respond", json={"response": "Otra respuesta"})
    assert respond_again.status_code == 409, respond_again.text
    assert respond_again.json()["error"]["code"] == "NXR-RFI-001"

    close = client.post(f"/api/rfis/{rfi['id']}/close")
    assert close.status_code == 200, close.text
    assert close.json()["status"] == "CLOSED"

    close_again = client.post(f"/api/rfis/{rfi['id']}/close")
    assert close_again.status_code == 409, close_again.text
    assert close_again.json()["error"]["code"] == "NXR-RFI-001"


def test_rfi_number_sequence_is_company_scoped(client):
    """Dos compañías distintas pueden emitir cada una su primer RFI sin
    colisión de unique constraint -- numeración company-scoped vía
    NumberSequence (mismo patrón que la numeración de documentos de Track
    A/AP/AR/Procurement)."""
    login_admin(client)
    company_a = create_company(client, name="Constructora A")
    company_b = create_company(client, name="Constructora B")
    project_a = _create_project(client, company_id=company_a["id"], code="PRJ-A")
    project_b = _create_project(client, company_id=company_b["id"], code="PRJ-B")

    rfi_a = _create_rfi(client, company_id=company_a["id"], project_id=project_a["id"])
    rfi_b = _create_rfi(client, company_id=company_b["id"], project_id=project_b["id"])

    assert rfi_a["number"] == rfi_b["number"]
    assert rfi_a["id"] != rfi_b["id"]

    # Un segundo RFI de la misma compañía A avanza la secuencia (no colisiona
    # con el primero de A ni reutiliza el de B).
    rfi_a2 = _create_rfi(client, company_id=company_a["id"], project_id=project_a["id"], subject="Segundo RFI")
    assert rfi_a2["number"] != rfi_a["number"]


def test_company_access_blocks_cross_company_rfi(client, db_session):
    login_admin(client)
    company_a = create_company(client, name="Constructora A")
    company_b = create_company(client, name="Constructora B")
    project_a = _create_project(client, company_id=company_a["id"], code="PRJ-A")
    rfi_a = _create_rfi(client, company_id=company_a["id"], project_id=project_a["id"])

    user = create_user_with_role(db_session, email="pm-b-rfi@nexora.group", role_name="Project Manager")
    db_session.add(UserCompanyAccess(user_id=user.id, company_id=company_b["id"]))
    db_session.commit()
    login_as(client, email="pm-b-rfi@nexora.group")

    response = client.get(f"/api/rfis/{rfi_a['id']}")
    assert response.status_code == 403, response.text
    assert response.json()["error"]["code"] == "NXR-PERM-001"

    list_response = client.get(f"/api/rfis?companyId={company_a['id']}")
    assert list_response.status_code == 403, list_response.text


def test_rfi_create_rejects_project_from_another_company(client):
    login_admin(client)
    company_a = create_company(client, name="Constructora A")
    company_b = create_company(client, name="Constructora B")
    project_b = _create_project(client, company_id=company_b["id"], code="PRJ-B")

    response = client.post(
        "/api/rfis",
        json={
            "companyId": company_a["id"],
            "projectId": project_b["id"],
            "subject": "Cruzado",
            "question": "¿?",
        },
    )
    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "NXR-FINANCIAL-001"
