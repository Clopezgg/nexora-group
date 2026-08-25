import uuid
from datetime import date

from sqlalchemy.exc import IntegrityError

from app.models.permission import UserCompanyAccess
from tests.helpers import create_company, create_user_with_role, login_admin, login_as


def _create_project(client, *, company_id: str, name: str = "Torre Nexora Site") -> dict:
    response = client.post(
        "/api/projects",
        json={"companyId": company_id, "name": name, "code": "PRJ-SITE-001", "currencyCode": "HNL"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _report_payload(project_id: str, **overrides) -> dict:
    payload = {
        "projectId": project_id,
        "reportDate": "2026-03-01",
        "weather": "SUNNY",
        "workforceSummary": "12 albañiles, 3 operadores",
        "activitiesPerformed": "Vaciado de losa nivel 2",
        "equipmentUsed": "Grúa torre, mezcladora",
        "materialsUsed": "Concreto 3000 PSI",
        "incidents": None,
        "observations": None,
    }
    payload.update(overrides)
    return payload


def test_daily_site_report_requires_project_id_at_domain_and_db_level(client, db_session):
    """Named behavior from the brief: a diferencia de la mayoría de recursos
    de Track D (Equipment/FuelLog: project_id OPCIONAL vía OperationScope),
    un DailySiteReport es inherentemente PROJECT-scoped -- se rechaza sin
    project_id tanto a nivel de dominio (API, 422) como de constraint real
    de PostgreSQL (NOT NULL)."""
    login_admin(client)

    # Nivel de dominio: el schema Pydantic exige projectId -- 422 real.
    response = client.post(
        "/api/site-reports",
        json={
            "reportDate": "2026-03-01",
            "activitiesPerformed": "Vaciado de losa nivel 2",
        },
    )
    assert response.status_code == 422, response.text

    # Nivel de DB: inserción directa del modelo sin project_id viola el NOT
    # NULL real de PostgreSQL, sin pasar por el service/API layer.
    from app.models.site_report import DailySiteReport
    from app.repositories import user_repository
    from tests.conftest import BOOTSTRAP_ADMIN_EMAIL

    admin = user_repository.get_by_email(db_session, BOOTSTRAP_ADMIN_EMAIL)
    assert admin is not None
    bad_report = DailySiteReport(
        project_id=None,
        report_date=date(2026, 3, 1),
        activities_performed="Sin proyecto",
        author_id=admin.id,
    )
    db_session.add(bad_report)
    try:
        db_session.flush()
        raised = False
    except IntegrityError:
        raised = True
    db_session.rollback()
    assert raised, "insertar un DailySiteReport sin project_id debió violar el NOT NULL real"


def test_daily_site_report_create_submit_approve_flow(client):
    login_admin(client)
    company = create_company(client)
    project = _create_project(client, company_id=company["id"])

    created = client.post("/api/site-reports", json=_report_payload(project["id"]))
    assert created.status_code == 201, created.text
    report = created.json()
    assert report["status"] == "DRAFT"
    assert report["projectId"] == project["id"]

    submitted = client.post(f"/api/site-reports/{report['id']}/submit")
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["status"] == "SUBMITTED"

    approved = client.post(f"/api/site-reports/{report['id']}/approve")
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "APPROVED"
    assert approved.json()["approvedById"] is not None

    # No se puede volver a aprobar un reporte ya decidido.
    reapproved = client.post(f"/api/site-reports/{report['id']}/approve")
    assert reapproved.status_code == 409, reapproved.text
    assert reapproved.json()["error"]["code"] == "NXR-SITE-001"


def test_daily_site_report_photo_attachment_rejects_cross_company_evidence(client, db_session):
    from app.repositories import evidence_repository, user_repository
    from tests.conftest import BOOTSTRAP_ADMIN_EMAIL

    login_admin(client)
    company_a = create_company(client, name="Constructora A")
    company_b = create_company(client, name="Constructora B")
    project_a = _create_project(client, company_id=company_a["id"], name="Torre A")

    created = client.post("/api/site-reports", json=_report_payload(project_a["id"]))
    assert created.status_code == 201, created.text
    report_id = created.json()["id"]

    admin = user_repository.get_by_email(db_session, BOOTSTRAP_ADMIN_EMAIL)
    evidence_b = evidence_repository.create_evidence(
        db_session,
        company_id=uuid.UUID(company_b["id"]),
        blob_key=f"{company_b['id']}/{uuid.uuid4()}-foto.jpg",
        original_filename="foto.jpg",
        mime_type="image/jpeg",
        size_bytes=1024,
        uploaded_by=admin.id,
    )
    db_session.commit()

    rejected = client.post(
        f"/api/site-reports/{report_id}/photos", json={"evidenceId": str(evidence_b.id)}
    )
    assert rejected.status_code == 422, rejected.text
    assert rejected.json()["error"]["code"] == "NXR-FINANCIAL-001"

    evidence_a = evidence_repository.create_evidence(
        db_session,
        company_id=uuid.UUID(company_a["id"]),
        blob_key=f"{company_a['id']}/{uuid.uuid4()}-foto.jpg",
        original_filename="foto.jpg",
        mime_type="image/jpeg",
        size_bytes=1024,
        uploaded_by=admin.id,
    )
    db_session.commit()
    accepted = client.post(
        f"/api/site-reports/{report_id}/photos", json={"evidenceId": str(evidence_a.id)}
    )
    assert accepted.status_code == 201, accepted.text

    refreshed = client.get(f"/api/site-reports/{report_id}")
    assert len(refreshed.json()["photos"]) == 1


def test_company_access_blocks_cross_company_site_report(client, db_session):
    login_admin(client)
    company_a = create_company(client, name="Constructora A")
    company_b = create_company(client, name="Constructora B")
    project_a = _create_project(client, company_id=company_a["id"], name="Torre A")

    created = client.post("/api/site-reports", json=_report_payload(project_a["id"]))
    assert created.status_code == 201, created.text
    report_id = created.json()["id"]

    user = create_user_with_role(db_session, email="pm-b@nexora.group", role_name="Project Manager")
    db_session.add(UserCompanyAccess(user_id=user.id, company_id=company_b["id"]))
    db_session.commit()
    login_as(client, email="pm-b@nexora.group")

    response = client.get(f"/api/site-reports/{report_id}")
    assert response.status_code == 403, response.text
    assert response.json()["error"]["code"] == "NXR-PERM-001"
