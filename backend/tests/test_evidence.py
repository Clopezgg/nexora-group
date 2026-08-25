from app.models.permission import UserCompanyAccess
from tests.helpers import create_company, create_user_with_role, login_admin, login_as


def _upload(client, *, company_id: str, filename: str = "foto.jpg", content: bytes = b"contenido-real", mime: str = "image/jpeg", **extra_fields):
    data = {"companyId": company_id, **extra_fields}
    files = {"file": (filename, content, mime)}
    return client.post("/api/evidence", data=data, files=files)


def test_evidence_rejects_unsupported_mime_type(client):
    login_admin(client)
    company = create_company(client)

    response = _upload(
        client, company_id=company["id"], filename="instalador.exe", content=b"MZ...", mime="application/x-msdownload"
    )
    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "NXR-EVIDENCE-002"


def test_evidence_rejects_unsupported_zip_mime_type(client):
    login_admin(client)
    company = create_company(client)

    response = _upload(
        client, company_id=company["id"], filename="paquete.zip", content=b"PK\x03\x04", mime="application/zip"
    )
    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "NXR-EVIDENCE-002"


def test_evidence_rejects_oversized_file(client):
    login_admin(client)
    company = create_company(client)

    oversized_content = b"a" * (26 * 1024 * 1024)  # supera max_evidence_mb=25 por defecto
    response = _upload(client, company_id=company["id"], content=oversized_content)
    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "NXR-EVIDENCE-003"


def test_evidence_upload_without_storage_configured_returns_real_error(client):
    """EVIDENCE_BACKEND queda sin configurar en el entorno de pruebas
    (default 'none', ver app/core/config.py). Un archivo válido en MIME y
    tamaño debe fallar con un 503 real y un código de error claro -- nunca
    un 200 con una URL de blob fabricada."""
    login_admin(client)
    company = create_company(client)

    response = _upload(client, company_id=company["id"])
    assert response.status_code == 503, response.text
    assert response.json()["error"]["code"] == "NXR-EVIDENCE-001"


def test_evidence_upload_requires_company_access(client, db_session):
    login_admin(client)
    company_a = create_company(client, name="Constructora A")
    company_b = create_company(client, name="Constructora B")

    user = create_user_with_role(db_session, email="pm-b@nexora.group", role_name="Project Manager")
    db_session.add(UserCompanyAccess(user_id=user.id, company_id=company_b["id"]))
    db_session.commit()
    login_as(client, email="pm-b@nexora.group")

    response = _upload(client, company_id=company_a["id"])
    assert response.status_code == 403, response.text
    assert response.json()["error"]["code"] == "NXR-PERM-001"
