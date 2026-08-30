import uuid

from sqlalchemy import select

from app.models.evidence import Evidence
from app.models.user import User
from app.services import evidence_service
from tests.conftest import BOOTSTRAP_ADMIN_EMAIL
from tests.helpers import create_company, login_admin


PDF_CONTENT = b"%PDF-1.7\nprivate-evidence-content"


class FakeDownloader:
    def __init__(self, content: bytes):
        self.content = content

    def chunks(self):
        midpoint = max(1, len(self.content) // 2)
        return iter((self.content[:midpoint], self.content[midpoint:]))


class FakeContainerClient:
    def __init__(self, content: bytes):
        self.content = content
        self.downloaded: list[str] = []

    def download_blob(self, blob_key: str):
        self.downloaded.append(blob_key)
        return FakeDownloader(self.content)


def _seed_evidence(db_session, *, company_id: str) -> Evidence:
    admin = db_session.execute(
        select(User).where(User.email == BOOTSTRAP_ADMIN_EMAIL)
    ).scalar_one()
    row = Evidence(
        company_id=uuid.UUID(company_id),
        blob_key=f"{company_id}/private-document.pdf",
        original_filename="informe técnico.pdf",
        mime_type="application/pdf",
        size_bytes=len(PDF_CONTENT),
        uploaded_by=admin.id,
    )
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    return row


def test_evidence_download_streams_private_blob_with_safe_headers(client, db_session, monkeypatch):
    login_admin(client)
    company = create_company(client, name="Evidence Download Co")
    evidence = _seed_evidence(db_session, company_id=company["id"])
    container = FakeContainerClient(PDF_CONTENT)
    monkeypatch.setattr(
        evidence_service,
        "get_evidence_container_client",
        lambda settings: container,
    )

    response = client.get(f"/api/evidence/{evidence.id}/download")

    assert response.status_code == 200, response.text
    assert response.content == PDF_CONTENT
    assert response.headers["content-type"].startswith("application/pdf")
    assert response.headers["content-length"] == str(len(PDF_CONTENT))
    assert response.headers["content-encoding"] == "identity"
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert "attachment" in response.headers["content-disposition"]
    assert "filename*=UTF-8''informe%20t%C3%A9cnico.pdf" in response.headers["content-disposition"]
    assert container.downloaded == [evidence.blob_key]


def test_evidence_download_without_storage_returns_real_503(client, db_session):
    login_admin(client)
    company = create_company(client, name="Evidence Download Storage Missing Co")
    evidence = _seed_evidence(db_session, company_id=company["id"])

    response = client.get(f"/api/evidence/{evidence.id}/download")

    assert response.status_code == 503, response.text
    assert response.json()["error"]["code"] == "NXR-EVIDENCE-001"
