import hashlib
import uuid

import pytest
from azure.core.exceptions import (
    ClientAuthenticationError,
    HttpResponseError,
    ServiceRequestError,
)
from sqlalchemy import select

from app.domain.errors import EvidenceTooLargeError
from app.models.evidence import Evidence
from app.models.permission import UserCompanyAccess
from app.models.user import User
from app.services import evidence_service
from tests.conftest import BOOTSTRAP_ADMIN_EMAIL
from tests.helpers import create_company, create_user_with_role, login_admin, login_as


VALID_JPEG = b"\xff\xd8\xff\xe0JFIF\x00contenido-real"


def _upload(client, *, company_id: str, filename: str = "foto.jpg", content: bytes = VALID_JPEG, mime: str = "image/jpeg", **extra_fields):
    data = {"companyId": company_id, **extra_fields}
    files = {"file": (filename, content, mime)}
    return client.post("/api/evidence", data=data, files=files)


class FakeContainerClient:
    def __init__(self):
        self.uploaded: list[dict] = []
        self.deleted: list[str] = []

    def upload_blob(self, **kwargs):
        self.uploaded.append(kwargs)

    def delete_blob(self, blob_key: str):
        self.deleted.append(blob_key)


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


@pytest.mark.asyncio
async def test_stream_reader_stops_at_max_plus_one_without_consuming_more():
    class CountingUpload:
        def __init__(self):
            self.remaining = 100
            self.requested: list[int] = []
            self.returned = 0

        async def read(self, size: int) -> bytes:
            self.requested.append(size)
            amount = min(size, self.remaining)
            self.remaining -= amount
            self.returned += amount
            return b"x" * amount

    upload = CountingUpload()

    with pytest.raises(EvidenceTooLargeError):
        await evidence_service.read_bounded_upload(upload, max_bytes=10)

    assert upload.returned == 11
    assert upload.requested == [11]
    assert upload.remaining == 89


def test_evidence_rejects_content_that_does_not_match_allowed_mime(client, monkeypatch):
    login_admin(client)
    company = create_company(client, name="Evidence Signature Co")
    container = FakeContainerClient()
    monkeypatch.setattr(
        "app.services.evidence_service.get_evidence_container_client",
        lambda settings: container,
    )

    response = _upload(
        client,
        company_id=company["id"],
        filename="fake.pdf",
        content=b"this is not a pdf",
        mime="application/pdf",
    )

    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "NXR-EVIDENCE-002"
    assert container.uploaded == []


def test_evidence_normalizes_filename_before_blob_and_database(client, db_session, monkeypatch):
    login_admin(client)
    company = create_company(client, name="Evidence Filename Co")
    container = FakeContainerClient()
    monkeypatch.setattr(
        "app.services.evidence_service.get_evidence_container_client",
        lambda settings: container,
    )

    response = _upload(
        client,
        company_id=company["id"],
        filename="../private\\folder/\x00 informe.pdf",
        content=b"%PDF-1.7\nreal content",
        mime="application/pdf",
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["originalFilename"] == "informe.pdf"
    assert len(container.uploaded) == 1
    blob_key = container.uploaded[0]["name"]
    assert blob_key.startswith(f"{company['id']}/")
    assert blob_key.endswith("-informe.pdf")
    assert ".." not in blob_key
    assert "\\" not in blob_key
    assert "\x00" not in blob_key

    db_session.expire_all()
    row = db_session.execute(select(Evidence).where(Evidence.id == uuid.UUID(body["id"]))).scalar_one()
    assert row.original_filename == "informe.pdf"


def test_evidence_deletes_remote_blob_when_audit_fails(client, db_session, monkeypatch):
    login_admin(client)
    company = create_company(client, name="Evidence Compensation Co")
    container = FakeContainerClient()
    monkeypatch.setattr(
        "app.services.evidence_service.get_evidence_container_client",
        lambda settings: container,
    )

    def fail_record(*args, **kwargs):
        raise RuntimeError("audit unavailable")

    monkeypatch.setattr("app.api.routes.evidence.audit_service.record", fail_record)

    with pytest.raises(RuntimeError, match="audit unavailable"):
        _upload(client, company_id=company["id"])

    assert len(container.uploaded) == 1
    assert container.deleted == [container.uploaded[0]["name"]]
    db_session.expire_all()
    assert db_session.execute(select(Evidence)).scalars().all() == []


def test_evidence_deletes_remote_blob_when_database_persistence_fails(
    client, db_session, monkeypatch
):
    login_admin(client)
    company = create_company(client, name="Evidence Persistence Compensation Co")
    container = FakeContainerClient()
    monkeypatch.setattr(
        "app.services.evidence_service.get_evidence_container_client",
        lambda settings: container,
    )

    def fail_create(*args, **kwargs):
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(
        "app.services.evidence_service.evidence_repository.create_evidence",
        fail_create,
    )

    with pytest.raises(RuntimeError, match="database unavailable"):
        _upload(client, company_id=company["id"])

    assert len(container.uploaded) == 1
    assert container.deleted == [container.uploaded[0]["name"]]
    db_session.expire_all()
    assert db_session.execute(select(Evidence)).scalars().all() == []


def test_evidence_list_is_bounded_and_paginated(client, db_session):
    login_admin(client)
    company = create_company(client, name="Evidence Pagination Co")
    admin = db_session.execute(
        select(User).where(User.email == BOOTSTRAP_ADMIN_EMAIL)
    ).scalar_one()
    for index in range(55):
        db_session.add(
            Evidence(
                company_id=uuid.UUID(company["id"]),
                blob_key=f"{company['id']}/seed-{index}.pdf",
                original_filename=f"seed-{index}.pdf",
                mime_type="application/pdf",
                size_bytes=10,
                uploaded_by=admin.id,
            )
        )
    db_session.commit()

    default_page = client.get(f"/api/evidence?companyId={company['id']}")
    assert default_page.status_code == 200, default_page.text
    assert len(default_page.json()) == 50

    first_twenty = client.get(
        f"/api/evidence?companyId={company['id']}&limit=20"
    ).json()
    second_ten = client.get(
        f"/api/evidence?companyId={company['id']}&offset=10&limit=10"
    ).json()
    assert [row["id"] for row in second_ten] == [row["id"] for row in first_twenty[10:20]]

    for query in ("limit=0", "limit=101", "offset=-1"):
        response = client.get(f"/api/evidence?companyId={company['id']}&{query}")
        assert response.status_code == 422, response.text


# --- HEIC / HEIF (iOS Safari/iPhone) -----------------------------------------

HEIC_BYTES = b"\x00\x00\x00\x20ftypheic\x00\x00\x00\x00mif1heic" + b"\x00" * 24
HEIF_BYTES = b"\x00\x00\x00\x20ftypmif1\x00\x00\x00\x00mif1heic" + b"\x00" * 24


def test_evidence_accepts_heic_with_real_signature(client, db_session, monkeypatch):
    login_admin(client)
    company = create_company(client, name="Evidence HEIC Co")
    container = FakeContainerClient()
    monkeypatch.setattr(
        "app.services.evidence_service.get_evidence_container_client",
        lambda settings: container,
    )

    response = _upload(
        client,
        company_id=company["id"],
        filename="IMG_0001.HEIC",
        content=HEIC_BYTES,
        mime="image/heic",
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["mimeType"] == "image/heic"
    assert body["contentHash"] == hashlib.sha256(HEIC_BYTES).hexdigest()
    assert len(container.uploaded) == 1


def test_evidence_accepts_heif_when_ios_sends_empty_content_type(client, monkeypatch):
    login_admin(client)
    company = create_company(client, name="Evidence HEIF Co")
    container = FakeContainerClient()
    monkeypatch.setattr(
        "app.services.evidence_service.get_evidence_container_client",
        lambda settings: container,
    )

    # iOS a veces manda application/octet-stream para estas fotos.
    response = _upload(
        client,
        company_id=company["id"],
        filename="IMG_0002.heif",
        content=HEIF_BYTES,
        mime="application/octet-stream",
    )
    assert response.status_code == 201, response.text
    assert response.json()["mimeType"] == "image/heif"


def test_evidence_rejects_octet_stream_without_a_valid_signature(client, monkeypatch):
    login_admin(client)
    company = create_company(client, name="Evidence Octet Co")
    container = FakeContainerClient()
    monkeypatch.setattr(
        "app.services.evidence_service.get_evidence_container_client",
        lambda settings: container,
    )

    response = _upload(
        client,
        company_id=company["id"],
        filename="misterio.bin",
        content=b"\x00\x01\x02\x03not-a-real-image",
        mime="application/octet-stream",
    )
    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "NXR-EVIDENCE-002"
    assert container.uploaded == []


# --- Storage error classification ------------------------------------------


class _RaisingContainer:
    def __init__(self, exc: Exception):
        self.exc = exc

    def upload_blob(self, **kwargs):
        raise self.exc

    def delete_blob(self, blob_key: str):  # pragma: no cover
        pass


@pytest.mark.parametrize(
    ("exc", "expected_code"),
    [
        (ClientAuthenticationError("managed identity token failed"), "NXR-EVIDENCE-STORAGE-AUTH"),
        (ServiceRequestError("connection reset"), "NXR-EVIDENCE-STORAGE-TEMPORARY"),
    ],
)
def test_evidence_upload_classifies_storage_failures(client, monkeypatch, exc, expected_code):
    login_admin(client)
    company = create_company(client, name=f"Evidence Storage {expected_code}")
    monkeypatch.setattr(
        "app.services.evidence_service.get_evidence_container_client",
        lambda settings: _RaisingContainer(exc),
    )

    response = _upload(client, company_id=company["id"])
    assert response.status_code == 503, response.text
    body = response.json()["error"]
    assert body["code"] == expected_code
    # Nunca se filtra la causa raíz ni credenciales al cliente.
    assert "token" not in body["message"].lower()
    assert body["message"] == "No fue posible almacenar la evidencia. Intenta nuevamente."


def test_evidence_upload_maps_403_to_access_error(client, monkeypatch):
    login_admin(client)
    company = create_company(client, name="Evidence Storage 403 Co")
    forbidden = HttpResponseError("AuthorizationPermissionMismatch")
    forbidden.status_code = 403
    monkeypatch.setattr(
        "app.services.evidence_service.get_evidence_container_client",
        lambda settings: _RaisingContainer(forbidden),
    )

    response = _upload(client, company_id=company["id"])
    assert response.status_code == 503, response.text
    assert response.json()["error"]["code"] == "NXR-EVIDENCE-STORAGE-ACCESS"


def test_evidence_upload_persists_content_hash(client, db_session, monkeypatch):
    login_admin(client)
    company = create_company(client, name="Evidence Hash Co")
    container = FakeContainerClient()
    monkeypatch.setattr(
        "app.services.evidence_service.get_evidence_container_client",
        lambda settings: container,
    )

    content = b"%PDF-1.7\nintegridad"
    response = _upload(
        client,
        company_id=company["id"],
        filename="recibo.pdf",
        content=content,
        mime="application/pdf",
    )
    assert response.status_code == 201, response.text
    db_session.expire_all()
    row = db_session.execute(
        select(Evidence).where(Evidence.id == uuid.UUID(response.json()["id"]))
    ).scalar_one()
    assert row.content_hash == hashlib.sha256(content).hexdigest()
