from app.models.permission import UserCompanyAccess, UserProjectAccess
from tests.helpers import create_company, create_user_with_role, login_admin, login_as


def _create_project(client, company_id: str, name: str, code: str) -> dict:
    response = client.post(
        "/api/projects",
        json={"companyId": company_id, "name": name, "code": code, "currencyCode": "HNL"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_equipment(client, company_id: str, project_id: str, name: str) -> dict:
    response = client.post(
        "/api/equipment",
        json={
            "companyId": company_id,
            "projectId": project_id,
            "equipmentType": "EXCAVATOR",
            "name": name,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_project_scope_own_filters_lists_and_blocks_direct_access(client, db_session):
    login_admin(client)
    company = create_company(client, name="Project Scope Co")
    project_a = _create_project(client, company["id"], "Proyecto permitido", "PS-01")
    project_b = _create_project(client, company["id"], "Proyecto restringido", "PS-02")

    manager = create_user_with_role(
        db_session,
        email="project-scope@nexora.group",
        role_name="Project Manager",
    )
    db_session.add(UserCompanyAccess(user_id=manager.id, company_id=company["id"]))
    db_session.commit()

    grant = client.put(f"/api/access-management/users/{manager.id}/projects/{project_a['id']}")
    assert grant.status_code == 200, grant.text
    assigned = {row["id"] for row in grant.json()["projects"] if row["assigned"]}
    assert project_a["id"] in assigned
    assert project_b["id"] not in assigned

    login_as(client, email="project-scope@nexora.group")
    listing = client.get(f"/api/projects?company_id={company['id']}")
    assert listing.status_code == 200, listing.text
    assert [row["id"] for row in listing.json()] == [project_a["id"]]

    allowed = client.get(f"/api/projects/{project_a['id']}")
    assert allowed.status_code == 200, allowed.text

    denied = client.get(f"/api/projects/{project_b['id']}")
    assert denied.status_code == 403, denied.text


def test_project_creator_with_own_scope_is_auto_assigned(client, db_session):
    login_admin(client)
    company = create_company(client, name="Creator Scope Co")
    manager = create_user_with_role(
        db_session,
        email="project-creator@nexora.group",
        role_name="Project Manager",
    )
    db_session.add(UserCompanyAccess(user_id=manager.id, company_id=company["id"]))
    db_session.commit()

    login_as(client, email="project-creator@nexora.group")
    created = _create_project(client, company["id"], "Proyecto propio", "OWN-01")

    grant = db_session.query(UserProjectAccess).filter_by(
        user_id=manager.id,
        project_id=created["id"],
    ).one_or_none()
    assert grant is not None

    direct = client.get(f"/api/projects/{created['id']}")
    assert direct.status_code == 200, direct.text


def test_revoke_project_access_removes_visibility_without_deleting_project(client, db_session):
    login_admin(client)
    company = create_company(client, name="Revoke Scope Co")
    project = _create_project(client, company["id"], "Proyecto revocable", "RV-01")
    manager = create_user_with_role(
        db_session,
        email="project-revoke@nexora.group",
        role_name="Project Manager",
    )
    db_session.add(UserCompanyAccess(user_id=manager.id, company_id=company["id"]))
    db_session.commit()

    assert client.put(
        f"/api/access-management/users/{manager.id}/projects/{project['id']}"
    ).status_code == 200
    revoked = client.delete(
        f"/api/access-management/users/{manager.id}/projects/{project['id']}"
    )
    assert revoked.status_code == 200, revoked.text

    login_as(client, email="project-revoke@nexora.group")
    listing = client.get(f"/api/projects?company_id={company['id']}")
    assert listing.status_code == 200, listing.text
    assert listing.json() == []
    denied = client.get(f"/api/projects/{project['id']}")
    assert denied.status_code == 403, denied.text

    login_admin(client)
    still_exists = client.get(f"/api/projects/{project['id']}")
    assert still_exists.status_code == 200, still_exists.text


def test_project_assignment_requires_explicit_company_membership(client, db_session):
    login_admin(client)
    company = create_company(client, name="Membership Required Co")
    project = _create_project(client, company["id"], "Proyecto de compañía", "MC-01")
    auditor = create_user_with_role(
        db_session,
        email="auditor-project@nexora.group",
        role_name="Auditor",
    )

    response = client.put(
        f"/api/access-management/users/{auditor.id}/projects/{project['id']}"
    )
    assert response.status_code == 409, response.text
    assert "Asigna primero la compañía" in response.json()["detail"]


def test_project_scope_rejects_foreign_project_in_json_body_and_indirect_entity_id(client, db_session):
    login_admin(client)
    company = create_company(client, name="Equipment Isolation Co")
    project_a = _create_project(client, company["id"], "Proyecto equipos A", "EQ-A")
    project_b = _create_project(client, company["id"], "Proyecto equipos B", "EQ-B")
    equipment_a = _create_equipment(client, company["id"], project_a["id"], "Excavadora A")
    equipment_b = _create_equipment(client, company["id"], project_b["id"], "Excavadora B")

    manager = create_user_with_role(
        db_session,
        email="equipment-scope@nexora.group",
        role_name="Equipment Manager",
    )
    db_session.add(UserCompanyAccess(user_id=manager.id, company_id=company["id"]))
    db_session.add(UserProjectAccess(user_id=manager.id, project_id=project_a["id"]))
    db_session.commit()

    login_as(client, email="equipment-scope@nexora.group")

    listing = client.get(f"/api/equipment?companyId={company['id']}")
    assert listing.status_code == 200, listing.text
    assert {row["id"] for row in listing.json()} == {equipment_a["id"]}

    indirect_denied = client.get(f"/api/equipment/{equipment_b['id']}")
    assert indirect_denied.status_code == 403, indirect_denied.text

    body_denied = client.post(
        "/api/equipment",
        json={
            "companyId": company["id"],
            "projectId": project_b["id"],
            "equipmentType": "LOADER",
            "name": "Cargador no autorizado",
        },
    )
    assert body_denied.status_code == 403, body_denied.text

    body_allowed = client.post(
        "/api/equipment",
        json={
            "companyId": company["id"],
            "projectId": project_a["id"],
            "equipmentType": "LOADER",
            "name": "Cargador autorizado",
        },
    )
    assert body_allowed.status_code == 201, body_allowed.text


def test_project_scope_rejects_foreign_project_in_query_parameter(client, db_session):
    login_admin(client)
    company = create_company(client, name="Document Isolation Co")
    project_a = _create_project(client, company["id"], "Proyecto docs A", "DOC-A")
    project_b = _create_project(client, company["id"], "Proyecto docs B", "DOC-B")

    manager = create_user_with_role(
        db_session,
        email="document-scope@nexora.group",
        role_name="Project Manager",
    )
    db_session.add(UserCompanyAccess(user_id=manager.id, company_id=company["id"]))
    db_session.add(UserProjectAccess(user_id=manager.id, project_id=project_a["id"]))
    db_session.commit()

    login_as(client, email="document-scope@nexora.group")
    allowed = client.get(
        f"/api/documents?companyId={company['id']}&projectId={project_a['id']}"
    )
    assert allowed.status_code == 200, allowed.text

    denied = client.get(
        f"/api/documents?companyId={company['id']}&projectId={project_b['id']}"
    )
    assert denied.status_code == 403, denied.text
