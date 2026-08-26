import uuid

from app.models.permission import UserCompanyAccess
from app.repositories import evidence_repository, user_repository
from tests.conftest import BOOTSTRAP_ADMIN_EMAIL
from tests.helpers import create_company, create_user_with_role, login_admin, login_as


def _admin_user_id(db_session) -> uuid.UUID:
    user = user_repository.get_by_email(db_session, BOOTSTRAP_ADMIN_EMAIL)
    assert user is not None
    return user.id


def _seed_evidence(db_session, *, company_id: str, filename: str = "plano-v1.pdf") -> str:
    """Inserta una fila Evidence directamente (sin pasar por el upload real a
    Azure Blob) para aislar las pruebas de Document/DocumentVersion del
    pipeline de subida -- ese pipeline tiene su propia cobertura dedicada en
    test_evidence.py."""
    evidence = evidence_repository.create_evidence(
        db_session,
        company_id=uuid.UUID(company_id),
        blob_key=f"{company_id}/{uuid.uuid4()}-{filename}",
        original_filename=filename,
        mime_type="application/pdf",
        size_bytes=2048,
        uploaded_by=_admin_user_id(db_session),
    )
    db_session.commit()
    return str(evidence.id)


def _create_document(client, *, company_id: str, evidence_id: str, title: str = "Plano estructural nivel 3") -> dict:
    response = client.post(
        "/api/documents",
        json={
            "companyId": company_id,
            "scope": "GENERAL",
            "category": "DRAWING",
            "title": title,
            "evidenceId": evidence_id,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_document_version_supersedes_previous_and_keeps_immutable_history(client, db_session):
    login_admin(client)
    company = create_company(client)
    evidence_v1 = _seed_evidence(db_session, company_id=company["id"])

    document = _create_document(client, company_id=company["id"], evidence_id=evidence_v1)
    assert document["currentVersion"]["versionNumber"] == 1
    assert document["currentVersion"]["status"] == "ACTIVE"
    assert document["currentVersion"]["evidenceId"] == evidence_v1

    evidence_v2 = _seed_evidence(db_session, company_id=company["id"], filename="plano-v2.pdf")
    new_version = client.post(
        f"/api/documents/{document['id']}/versions",
        json={"evidenceId": evidence_v2, "notes": "Corrección de cotas"},
    )
    assert new_version.status_code == 201, new_version.text
    assert new_version.json()["versionNumber"] == 2
    assert new_version.json()["status"] == "ACTIVE"

    # El Document expone el nuevo puntero de "versión actual"...
    refreshed = client.get(f"/api/documents/{document['id']}")
    assert refreshed.status_code == 200, refreshed.text
    assert refreshed.json()["currentVersion"]["versionNumber"] == 2
    assert refreshed.json()["currentVersion"]["evidenceId"] == evidence_v2

    # ...y la versión 1 sigue existiendo, inmutable, marcada SUPERSEDED --
    # nunca borrada ni sobrescrita.
    versions = client.get(f"/api/documents/{document['id']}/versions")
    assert versions.status_code == 200, versions.text
    by_number = {v["versionNumber"]: v for v in versions.json()}
    assert len(by_number) == 2
    assert by_number[1]["status"] == "SUPERSEDED"
    assert by_number[1]["evidenceId"] == evidence_v1
    assert by_number[2]["status"] == "ACTIVE"
    assert by_number[2]["evidenceId"] == evidence_v2


def test_company_access_blocks_cross_company_document(client, db_session):
    login_admin(client)
    company_a = create_company(client, name="Constructora A")
    company_b = create_company(client, name="Constructora B")
    evidence_a = _seed_evidence(db_session, company_id=company_a["id"])
    document_a = _create_document(client, company_id=company_a["id"], evidence_id=evidence_a)

    user = create_user_with_role(db_session, email="pm-b@nexora.group", role_name="Project Manager")
    db_session.add(UserCompanyAccess(user_id=user.id, company_id=company_b["id"]))
    db_session.commit()
    login_as(client, email="pm-b@nexora.group")

    response = client.get(f"/api/documents/{document_a['id']}")
    assert response.status_code == 403, response.text
    assert response.json()["error"]["code"] == "NXR-PERM-001"

    list_response = client.get(f"/api/documents?companyId={company_a['id']}")
    assert list_response.status_code == 403, list_response.text


def test_document_create_rejects_evidence_from_another_company(client, db_session):
    login_admin(client)
    company_a = create_company(client, name="Constructora A")
    company_b = create_company(client, name="Constructora B")
    evidence_b = _seed_evidence(db_session, company_id=company_b["id"])

    response = client.post(
        "/api/documents",
        json={
            "companyId": company_a["id"],
            "scope": "GENERAL",
            "category": "DRAWING",
            "title": "Plano cruzado",
            "evidenceId": evidence_b,
        },
    )
    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "NXR-FINANCIAL-001"


def test_progress_record_evidence_ref_is_a_real_evidence_fk(client, db_session):
    """NXR-REQ-0077/0078/0079: ProgressRecord.evidence_id es una FK real a
    evidence.id (ya no texto libre). Un evidence_id de otra compañía se
    rechaza ANTES de persistir el ProgressRecord."""
    login_admin(client)
    company_a = create_company(client, name="Constructora A")
    company_b = create_company(client, name="Constructora B")

    project = client.post(
        "/api/projects",
        json={"companyId": company_a["id"], "name": "Torre A", "code": "PRJ-DOC-01", "currencyCode": "HNL"},
    )
    assert project.status_code == 201, project.text
    project_id = project.json()["id"]

    evidence_own = _seed_evidence(db_session, company_id=company_a["id"], filename="avance-01.jpg")
    ok_response = client.post(
        f"/api/projects/{project_id}/progress",
        json={
            "recordDate": "2026-03-01",
            "plannedPercent": "10.00",
            "actualPercent": "8.00",
            "evidenceId": evidence_own,
        },
    )
    assert ok_response.status_code == 201, ok_response.text
    assert ok_response.json()["evidenceId"] == evidence_own

    evidence_other = _seed_evidence(db_session, company_id=company_b["id"], filename="avance-b.jpg")
    rejected = client.post(
        f"/api/projects/{project_id}/progress",
        json={
            "recordDate": "2026-03-02",
            "plannedPercent": "12.00",
            "actualPercent": "9.00",
            "evidenceId": evidence_other,
        },
    )
    assert rejected.status_code == 422, rejected.text
    assert rejected.json()["error"]["code"] == "NXR-FINANCIAL-001"

    records = client.get(f"/api/projects/{project_id}/progress").json()
    assert len(records) == 1
    assert records[0]["evidenceId"] == evidence_own
