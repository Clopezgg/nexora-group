from app.models.permission import UserCompanyAccess
from app.models.user_context import UserContext
from tests.conftest import BOOTSTRAP_ADMIN_EMAIL, BOOTSTRAP_ADMIN_PASSWORD
from tests.helpers import create_company, create_user_with_role, login_as


def _login(client):
    client.post(
        "/api/auth/login",
        json={"email": BOOTSTRAP_ADMIN_EMAIL, "password": BOOTSTRAP_ADMIN_PASSWORD},
    )


def _create_project(client, *, company_id: str, code: str, name: str) -> dict:
    response = client.post(
        "/api/projects",
        json={
            "companyId": company_id,
            "name": name,
            "code": code,
            "currencyCode": "HNL",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_get_context_requires_auth(client):
    response = client.get("/api/context")
    assert response.status_code == 401


def test_get_context_defaults_to_no_active_project(client):
    _login(client)
    response = client.get("/api/context")
    assert response.status_code == 200
    assert response.json() == {"activeProjectId": None, "activeProjectName": None}


def test_get_context_does_not_create_context_row(client, db_session):
    _login(client)
    assert db_session.query(UserContext).count() == 0

    response = client.get("/api/context")

    assert response.status_code == 200
    assert response.json() == {"activeProjectId": None, "activeProjectName": None}
    assert db_session.query(UserContext).count() == 0


def test_set_context_with_unknown_project_returns_400(client):
    _login(client)
    response = client.put(
        "/api/context", json={"activeProjectId": "00000000-0000-0000-0000-000000000000"}
    )
    assert response.status_code == 400


def test_set_context_rejects_project_outside_user_company_scope(client, db_session):
    _login(client)
    company_a = create_company(client, name="Context Company A")
    company_b = create_company(client, name="Context Company B")
    project_b = _create_project(
        client,
        company_id=company_b["id"],
        code="CTX-B-001",
        name="Proyecto B privado",
    )

    user = create_user_with_role(
        db_session,
        email="context-isolated@nexora.group",
        role_name="Viewer",
    )
    db_session.add(UserCompanyAccess(user_id=user.id, company_id=company_a["id"]))
    db_session.commit()

    login_as(client, email="context-isolated@nexora.group")
    response = client.put(
        "/api/context",
        json={"activeProjectId": project_b["id"]},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "El proyecto seleccionado no existe o no está disponible."


def test_get_context_hides_stale_project_after_company_access_revoked(client, db_session):
    _login(client)
    company = create_company(client, name="Context Revocation Company")
    project = _create_project(
        client,
        company_id=company["id"],
        code="CTX-R-001",
        name="Proyecto revocado",
    )

    user = create_user_with_role(
        db_session,
        email="context-revoked@nexora.group",
        role_name="Viewer",
    )
    db_session.add(UserCompanyAccess(user_id=user.id, company_id=company["id"]))
    db_session.commit()

    login_as(client, email="context-revoked@nexora.group")
    selected = client.put("/api/context", json={"activeProjectId": project["id"]})
    assert selected.status_code == 200
    assert selected.json()["activeProjectId"] == project["id"]

    access = (
        db_session.query(UserCompanyAccess)
        .filter_by(user_id=user.id, company_id=company["id"])
        .one()
    )
    db_session.delete(access)
    db_session.commit()

    response = client.get("/api/context")
    assert response.status_code == 200
    assert response.json() == {"activeProjectId": None, "activeProjectName": None}
