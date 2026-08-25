from sqlalchemy.exc import IntegrityError

from app.models.permission import UserCompanyAccess
from tests.helpers import create_company, create_user_with_role, login_admin, login_as


def _create_project(client, *, company_id: str, name: str = "Torre Nexora Safety") -> dict:
    response = client.post(
        "/api/projects",
        json={"companyId": company_id, "name": name, "code": "PRJ-SAF-001", "currencyCode": "HNL"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_safety_incident_severity_drives_required_fields(client, db_session):
    """Named behavior from the brief: a HIGH-severity incident without a
    responsible user assigned is rejected; a LOW-severity observation is
    not required to have one."""
    from app.repositories import user_repository
    from tests.conftest import BOOTSTRAP_ADMIN_EMAIL

    login_admin(client)
    company = create_company(client)
    project = _create_project(client, company_id=company["id"])

    rejected = client.post(
        "/api/safety/incidents",
        json={
            "projectId": project["id"],
            "incidentDate": "2026-03-01",
            "description": "Caída de altura en andamio",
            "severity": "HIGH",
        },
    )
    assert rejected.status_code == 422, rejected.text
    assert rejected.json()["error"]["code"] == "NXR-SAFETY-001"

    admin = user_repository.get_by_email(db_session, BOOTSTRAP_ADMIN_EMAIL)
    accepted = client.post(
        "/api/safety/incidents",
        json={
            "projectId": project["id"],
            "incidentDate": "2026-03-01",
            "description": "Caída de altura en andamio",
            "severity": "HIGH",
            "responsibleUserId": str(admin.id),
        },
    )
    assert accepted.status_code == 201, accepted.text
    assert accepted.json()["responsibleUserId"] == str(admin.id)

    low_observation = client.post(
        "/api/safety/observations",
        json={
            "projectId": project["id"],
            "observationDate": "2026-03-01",
            "category": "HOUSEKEEPING",
            "description": "Cables sueltos en pasillo",
            "severity": "LOW",
        },
    )
    assert low_observation.status_code == 201, low_observation.text
    assert low_observation.json()["responsibleUserId"] is None


def test_safety_incident_high_severity_db_constraint(db_session):
    """Mismo invariante (INV-SAFETY-001), ahora a nivel de constraint REAL de
    PostgreSQL (ck_safety_incidents_high_severity_requires_responsible), sin
    pasar por el service layer."""
    from datetime import date

    from app.models.company import Company
    from app.models.project import Project
    from app.models.safety import SafetyIncident

    company = Company(name="Safety Constraint Co")
    db_session.add(company)
    db_session.flush()
    project = Project(company_id=company.id, name="Obra Constraint", code="PRJ-SAF-DB")
    db_session.add(project)
    db_session.flush()

    bad_incident = SafetyIncident(
        project_id=project.id,
        incident_date=date(2026, 3, 1),
        description="Incidente sin responsable",
        severity="CRITICAL",
        responsible_user_id=None,
    )
    db_session.add(bad_incident)
    try:
        db_session.flush()
        raised = False
    except IntegrityError:
        raised = True
    db_session.rollback()
    assert raised, "un SafetyIncident CRITICAL sin responsible_user_id debió violar el CHECK real"


def test_safety_observation_and_incident_close_flow(client, db_session):
    from app.repositories import user_repository
    from tests.conftest import BOOTSTRAP_ADMIN_EMAIL

    login_admin(client)
    company = create_company(client)
    project = _create_project(client, company_id=company["id"])
    admin = user_repository.get_by_email(db_session, BOOTSTRAP_ADMIN_EMAIL)

    observation = client.post(
        "/api/safety/observations",
        json={
            "projectId": project["id"],
            "observationDate": "2026-03-01",
            "category": "PPE",
            "description": "Trabajador sin casco",
            "severity": "MEDIUM",
            "responsibleUserId": str(admin.id),
        },
    ).json()
    closed = client.post(f"/api/safety/observations/{observation['id']}/close")
    assert closed.status_code == 200, closed.text
    assert closed.json()["status"] == "CLOSED"

    reclosed = client.post(f"/api/safety/observations/{observation['id']}/close")
    assert reclosed.status_code == 409, reclosed.text
    assert reclosed.json()["error"]["code"] == "NXR-SAFETY-002"

    incident = client.post(
        "/api/safety/incidents",
        json={
            "projectId": project["id"],
            "incidentDate": "2026-03-01",
            "description": "Golpe menor",
            "severity": "LOW",
        },
    ).json()
    closed_incident = client.post(f"/api/safety/incidents/{incident['id']}/close")
    assert closed_incident.status_code == 200, closed_incident.text
    assert closed_incident.json()["status"] == "CLOSED"


def test_company_access_blocks_cross_company_safety_incident(client, db_session):
    login_admin(client)
    company_a = create_company(client, name="Constructora A")
    company_b = create_company(client, name="Constructora B")
    project_b = _create_project(client, company_id=company_b["id"], name="Torre B")

    incident_b = client.post(
        "/api/safety/incidents",
        json={
            "projectId": project_b["id"],
            "incidentDate": "2026-03-01",
            "description": "Golpe menor",
            "severity": "LOW",
        },
    )
    assert incident_b.status_code == 201, incident_b.text

    user = create_user_with_role(db_session, email="pm-a@nexora.group", role_name="Project Manager")
    db_session.add(UserCompanyAccess(user_id=user.id, company_id=company_a["id"]))
    db_session.commit()
    login_as(client, email="pm-a@nexora.group")

    response = client.get(f"/api/safety/incidents/{incident_b.json()['id']}")
    assert response.status_code == 403, response.text
    assert response.json()["error"]["code"] == "NXR-PERM-001"
