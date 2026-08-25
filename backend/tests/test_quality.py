import uuid

from app.models.permission import UserCompanyAccess
from app.repositories import user_repository
from tests.conftest import BOOTSTRAP_ADMIN_EMAIL
from tests.helpers import create_company, create_user_with_role, login_admin, login_as


def _create_project(client, *, company_id: str, name: str = "Torre Nexora Quality") -> dict:
    response = client.post(
        "/api/projects",
        json={"companyId": company_id, "name": name, "code": "PRJ-QA-001", "currencyCode": "HNL"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _admin_user_id(db_session) -> str:
    user = user_repository.get_by_email(db_session, BOOTSTRAP_ADMIN_EMAIL)
    assert user is not None
    return str(user.id)


def _create_non_conformance(client, *, project_id: str, responsible_user_id: str) -> dict:
    response = client.post(
        "/api/quality/non-conformances",
        json={
            "projectId": project_id,
            "description": "Recubrimiento de acero insuficiente",
            "responsibleUserId": responsible_user_id,
            "dueDate": "2026-03-10",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_quality_inspection_create_and_list(client):
    login_admin(client)
    company = create_company(client)
    project = _create_project(client, company_id=company["id"])

    created = client.post(
        "/api/quality/inspections",
        json={
            "projectId": project["id"],
            "inspectionType": "REBAR_PLACEMENT",
            "inspectionDate": "2026-03-01",
            "result": "PASS",
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["result"] == "PASS"

    listed = client.get(f"/api/quality/inspections?projectId={project['id']}")
    assert listed.status_code == 200, listed.text
    assert len(listed.json()) == 1


def test_non_conformance_requires_corrective_action_before_closure(client, db_session):
    """Named behavior from the brief: cerrar una NonConformance sin
    CorrectiveAction adjunta se rechaza (NXR-QUALITY-002)."""
    login_admin(client)
    company = create_company(client)
    project = _create_project(client, company_id=company["id"])
    admin_id = _admin_user_id(db_session)

    non_conformance = _create_non_conformance(
        client, project_id=project["id"], responsible_user_id=admin_id
    )

    rejected = client.post(f"/api/quality/non-conformances/{non_conformance['id']}/close")
    assert rejected.status_code == 409, rejected.text
    assert rejected.json()["error"]["code"] == "NXR-QUALITY-002"

    corrective_action = client.post(
        f"/api/quality/non-conformances/{non_conformance['id']}/corrective-actions",
        json={
            "description": "Reforzar recubrimiento antes de vaciado",
            "responsibleUserId": admin_id,
            "dueDate": "2026-03-05",
        },
    )
    assert corrective_action.status_code == 201, corrective_action.text

    closed = client.post(f"/api/quality/non-conformances/{non_conformance['id']}/close")
    assert closed.status_code == 200, closed.text
    assert closed.json()["status"] == "CLOSED"
    assert closed.json()["closedAt"] is not None

    reclosed = client.post(f"/api/quality/non-conformances/{non_conformance['id']}/close")
    assert reclosed.status_code == 409, reclosed.text
    assert reclosed.json()["error"]["code"] == "NXR-QUALITY-001"


def test_corrective_action_can_be_completed(client, db_session):
    login_admin(client)
    company = create_company(client)
    project = _create_project(client, company_id=company["id"])
    admin_id = _admin_user_id(db_session)

    non_conformance = _create_non_conformance(
        client, project_id=project["id"], responsible_user_id=admin_id
    )
    corrective_action = client.post(
        f"/api/quality/non-conformances/{non_conformance['id']}/corrective-actions",
        json={
            "description": "Reforzar recubrimiento antes de vaciado",
            "responsibleUserId": admin_id,
            "dueDate": "2026-03-05",
        },
    ).json()

    completed = client.post(f"/api/quality/corrective-actions/{corrective_action['id']}/complete")
    assert completed.status_code == 200, completed.text
    assert completed.json()["status"] == "COMPLETED"
    assert completed.json()["completedAt"] is not None


def test_company_access_blocks_cross_company_quality_resource(client, db_session):
    """Named behavior from the brief: a user scoped to company A gets 403
    for a company B QualityInspection ID."""
    login_admin(client)
    company_a = create_company(client, name="Constructora A")
    company_b = create_company(client, name="Constructora B")
    project_b = _create_project(client, company_id=company_b["id"], name="Torre B")

    inspection_b = client.post(
        "/api/quality/inspections",
        json={
            "projectId": project_b["id"],
            "inspectionType": "REBAR_PLACEMENT",
            "inspectionDate": "2026-03-01",
        },
    )
    assert inspection_b.status_code == 201, inspection_b.text

    user = create_user_with_role(db_session, email="pm-a@nexora.group", role_name="Project Manager")
    db_session.add(UserCompanyAccess(user_id=user.id, company_id=company_a["id"]))
    db_session.commit()
    login_as(client, email="pm-a@nexora.group")

    response = client.get(f"/api/quality/inspections/{inspection_b.json()['id']}")
    assert response.status_code == 403, response.text
    assert response.json()["error"]["code"] == "NXR-PERM-001"


def test_non_conformance_evidence_must_belong_to_same_company(client, db_session):
    from app.repositories import evidence_repository

    login_admin(client)
    company_a = create_company(client, name="Constructora A")
    company_b = create_company(client, name="Constructora B")
    project_a = _create_project(client, company_id=company_a["id"], name="Torre A")
    admin_id = _admin_user_id(db_session)

    evidence_b = evidence_repository.create_evidence(
        db_session,
        company_id=uuid.UUID(company_b["id"]),
        blob_key=f"{company_b['id']}/{uuid.uuid4()}-foto.jpg",
        original_filename="foto.jpg",
        mime_type="image/jpeg",
        size_bytes=1024,
        uploaded_by=uuid.UUID(admin_id),
    )
    db_session.commit()

    rejected = client.post(
        "/api/quality/non-conformances",
        json={
            "projectId": project_a["id"],
            "description": "Fisura en columna",
            "responsibleUserId": admin_id,
            "evidenceId": str(evidence_b.id),
        },
    )
    assert rejected.status_code == 422, rejected.text
    assert rejected.json()["error"]["code"] == "NXR-FINANCIAL-001"
