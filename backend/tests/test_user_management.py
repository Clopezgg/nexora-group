"""DEFERRED-FINAL-015: primera vez que existe una API real para crear
usuarios más allá del bootstrap Administrator inicial y para listar el
directorio de usuarios de una compañía. Confirmado como gap real por el
Critical Journey E2E, que tuvo que crear su segundo usuario (aprobador)
llamando directamente a las funciones de repositorio porque no existía
ningún endpoint."""

from app.models.permission import UserCompanyAccess
from tests.helpers import create_company, create_user_with_role, login_admin, login_as


def test_administrator_creates_a_user_and_grants_it_company_access(client, db_session):
    login_admin(client)
    company = create_company(client)

    response = client.post(
        "/api/master-data/users",
        json={
            "companyId": company["id"],
            "email": "nuevo@nexora.group",
            "fullName": "Nuevo Usuario",
            "password": "Passw0rd!23",
            "roleName": "Project Manager",
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["email"] == "nuevo@nexora.group"
    assert body["roles"] == ["Project Manager"]

    login_as(client, email="nuevo@nexora.group", password="Passw0rd!23")
    me = client.get("/api/auth/me")
    assert me.status_code == 200, me.text
    assert me.json()["email"] == "nuevo@nexora.group"


def test_create_user_rejects_duplicate_email(client, db_session):
    login_admin(client)
    company = create_company(client)
    payload = {
        "companyId": company["id"],
        "email": "dup@nexora.group",
        "fullName": "Usuario Uno",
        "password": "Passw0rd!23",
        "roleName": "Project Manager",
    }
    first = client.post("/api/master-data/users", json=payload)
    assert first.status_code == 201, first.text

    second = client.post("/api/master-data/users", json={**payload, "fullName": "Usuario Dos"})
    assert second.status_code == 409, second.text
    assert second.json()["error"]["code"] == "NXR-USER-001"


def test_create_user_rejects_unknown_role(client, db_session):
    login_admin(client)
    company = create_company(client)

    response = client.post(
        "/api/master-data/users",
        json={
            "companyId": company["id"],
            "email": "rol-invalido@nexora.group",
            "fullName": "Usuario",
            "password": "Passw0rd!23",
            "roleName": "Rol Que No Existe",
        },
    )
    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "NXR-USER-002"


def test_non_administrator_cannot_create_users(client, db_session):
    """core.user/create solo está en el grant automático de Administrator
    (_BASE_PERMISSIONS) -- ningún otro rol lo tiene explícito."""
    login_admin(client)
    company = create_company(client)
    pm = create_user_with_role(db_session, email="pm@nexora.group", role_name="Project Manager")
    db_session.add(UserCompanyAccess(user_id=pm.id, company_id=company["id"]))
    db_session.commit()
    login_as(client, email="pm@nexora.group")

    response = client.post(
        "/api/master-data/users",
        json={
            "companyId": company["id"],
            "email": "otro@nexora.group",
            "fullName": "Otro Usuario",
            "password": "Passw0rd!23",
            "roleName": "Project Manager",
        },
    )
    assert response.status_code == 403, response.text


def test_list_users_includes_explicit_access_and_administrators_only(client, db_session):
    """El directorio de una compañía incluye acceso explícito
    (UserCompanyAccess) y usuarios company-agnósticos de verdad
    (Administrator, vía `core.user`/`create` SCOPE_ANY). Un Project
    Manager de OTRA compañía no aparece solo porque su rol tenga
    SCOPE_ANY en lecturas puntuales (core.company/core.user read, para
    dashboards) -- eso no lo hace miembro real de esta compañía. Un
    Auditor tampoco: SCOPE_ANY en lecturas de todo el sistema, pero
    ninguna acción de escritura/asignación real -- no debe poder
    "pertenecer" a una compañía a la que nunca se le dio acceso
    explícito."""
    login_admin(client)
    company_a = create_company(client, name="Constructora A")
    company_b = create_company(client, name="Constructora B")

    explicit_user = create_user_with_role(
        db_session, email="explicito@nexora.group", role_name="Project Manager"
    )
    db_session.add(UserCompanyAccess(user_id=explicit_user.id, company_id=company_a["id"]))
    other_company_user = create_user_with_role(
        db_session, email="otra-compania@nexora.group", role_name="Project Manager"
    )
    db_session.add(UserCompanyAccess(user_id=other_company_user.id, company_id=company_b["id"]))
    auditor = create_user_with_role(db_session, email="auditor@nexora.group", role_name="Auditor")
    db_session.commit()

    response = client.get(f"/api/master-data/users?companyId={company_a['id']}")
    assert response.status_code == 200, response.text
    emails = {row["email"] for row in response.json()}

    assert "explicito@nexora.group" in emails
    assert "admin@nexora.group" in emails
    assert "otra-compania@nexora.group" not in emails
    assert "auditor@nexora.group" not in emails
