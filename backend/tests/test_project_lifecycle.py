"""CORRECTIVA §1-§9 / §28 — ciclo de vida del proyecto gobernado.

Grafo único de transiciones, ARCHIVED como soft-delete, reopen/restore con
motivo + permiso + audit, idempotencia de mismo-estado, filtros de listado.
"""

from sqlalchemy import select

from app.models.permission import (
    SCOPE_ANY,
    Permission,
    RolePermission,
    UserCompanyAccess,
    UserProjectAccess,
)
from app.models.role import Role
from tests.helpers import (
    create_company,
    create_user_with_role,
    login_admin,
    login_as,
)


def _project(client, company_id, *, name="Casa Residencial") -> dict:
    r = client.post(
        "/api/projects",
        json={"companyId": company_id, "name": name, "code": None, "currencyCode": "HNL"},
    )
    assert r.status_code == 201, r.text
    return r.json()


def _status(client, project_id, target, *, reason=None):
    body = {"status": target}
    if reason is not None:
        body["reason"] = reason
    return client.post(f"/api/projects/{project_id}/status", json=body)


def _revoke_role_permission(db_session, *, role_name: str, resource: str, action: str) -> None:
    grant = db_session.scalar(
        select(RolePermission)
        .join(Role, RolePermission.role_id == Role.id)
        .join(Permission, RolePermission.permission_id == Permission.id)
        .where(
            Role.name == role_name,
            Permission.resource == resource,
            Permission.action == action,
        )
    )
    assert grant is not None
    db_session.delete(grant)
    db_session.commit()


def test_full_lifecycle_planning_to_closed_and_reopen(client):
    login_admin(client)
    company = create_company(client, name="Lifecycle Co")
    p = _project(client, company["id"])
    assert p["status"] == "PLANNING"

    assert _status(client, p["id"], "ACTIVE").json()["status"] == "ACTIVE"
    assert _status(client, p["id"], "ON_HOLD").json()["status"] == "ON_HOLD"
    assert _status(client, p["id"], "ACTIVE").json()["status"] == "ACTIVE"

    completed = _status(client, p["id"], "COMPLETED").json()
    assert completed["status"] == "COMPLETED"
    assert completed["completedAt"] is not None
    assert completed["actualEnd"] is not None

    closed = _status(client, p["id"], "CLOSED").json()
    assert closed["status"] == "CLOSED"
    assert closed["closedAt"] is not None

    # Reabrir CLOSED es sensible: sin motivo -> 422.
    assert _status(client, p["id"], "ACTIVE").status_code == 422
    reopened = _status(client, p["id"], "ACTIVE", reason="Cerrado por error, la ejecución continúa")
    assert reopened.status_code == 200, reopened.text
    body = reopened.json()
    assert body["status"] == "ACTIVE"
    assert body["reopenedAt"] is not None
    # No se pierde cuándo se cerró originalmente (§8).
    assert body["closedAt"] is not None
    assert body["completedAt"] is not None


def test_same_status_is_idempotent_no_error(client):
    login_admin(client)
    company = create_company(client, name="Idempotent Co")
    p = _project(client, company["id"])
    _status(client, p["id"], "ACTIVE")
    _status(client, p["id"], "COMPLETED")
    r = _status(client, p["id"], "COMPLETED")
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "COMPLETED"
    r2 = client.post(f"/api/projects/{p['id']}/status", json={"status": "CLOSED"})
    assert r2.json()["status"] == "CLOSED"
    # CLOSED -> CLOSED nunca es un error técnico para el usuario.
    r3 = client.post(f"/api/projects/{p['id']}/status", json={"status": "CLOSED"})
    assert r3.status_code == 200, r3.text
    assert r3.json()["status"] == "CLOSED"


def test_archive_and_restore_keeps_prior_status(client):
    login_admin(client)
    company = create_company(client, name="Archive Co")
    p = _project(client, company["id"])
    _status(client, p["id"], "ACTIVE")
    _status(client, p["id"], "CANCELLED")

    archived = _status(client, p["id"], "ARCHIVED", reason="Proyecto descartado definitivamente")
    assert archived.status_code == 200, archived.text
    assert archived.json()["status"] == "ARCHIVED"
    assert archived.json()["archivedAt"] is not None

    lifecycle = client.get(f"/api/projects/{p['id']}/lifecycle").json()
    assert [t["status"] for t in lifecycle["allowedTransitions"]] == ["CANCELLED"]

    restored = _status(client, p["id"], "CANCELLED", reason="Se retoma la negociación con el cliente")
    assert restored.status_code == 200, restored.text
    assert restored.json()["status"] == "CANCELLED"
    assert restored.json()["archivedAt"] is None


def test_archived_hidden_from_default_list_but_filterable(client):
    login_admin(client)
    company = create_company(client, name="List Filter Co")
    keep = _project(client, company["id"], name="Vigente")
    gone = _project(client, company["id"], name="Archivado")
    _status(client, gone["id"], "ARCHIVED", reason="Eliminado por el administrador")

    default_list = client.get(f"/api/projects?company_id={company['id']}").json()
    names = {p["name"] for p in default_list}
    assert "Vigente" in names and "Archivado" not in names

    with_archived = client.get(
        f"/api/projects?company_id={company['id']}&includeArchived=true"
    ).json()
    assert {"Vigente", "Archivado"} <= {p["name"] for p in with_archived}

    only_archived = client.get(
        f"/api/projects?company_id={company['id']}&status=ARCHIVED"
    ).json()
    assert [p["name"] for p in only_archived] == ["Archivado"]
    assert keep  # noqa


def test_sensitive_transition_requires_lifecycle_permission(client, db_session):
    login_admin(client)
    company = create_company(client, name="RBAC Lifecycle Co")
    p = _project(client, company["id"])
    _status(client, p["id"], "ACTIVE")
    _status(client, p["id"], "COMPLETED")
    _status(client, p["id"], "CLOSED")

    pm = create_user_with_role(
        db_session, email="pm-no-lifecycle@nexora.group", role_name="Operations User"
    )
    db_session.add(UserCompanyAccess(user_id=pm.id, company_id=company["id"]))
    db_session.add(UserProjectAccess(user_id=pm.id, project_id=p["id"]))
    db_session.commit()

    login_as(client, email="pm-no-lifecycle@nexora.group")
    denied = _status(client, p["id"], "ACTIVE", reason="Intento de reapertura sin permiso")
    assert denied.status_code in (403, 422), denied.text


def test_normal_transition_requires_project_update_not_project_create(client, db_session):
    login_admin(client)
    company = create_company(client, name="Semantic lifecycle permission")
    project = _project(client, company["id"])
    manager = create_user_with_role(
        db_session, email="project-update@nexora.group", role_name="Project Manager"
    )
    db_session.add(UserCompanyAccess(user_id=manager.id, company_id=company["id"]))
    db_session.add(UserProjectAccess(user_id=manager.id, project_id=project["id"]))
    db_session.commit()

    login_as(client, email="project-update@nexora.group")
    allowed = _status(client, project["id"], "ACTIVE")
    assert allowed.status_code == 200, allowed.text

    _revoke_role_permission(
        db_session, role_name="Project Manager", resource="project", action="update"
    )
    denied = _status(client, project["id"], "ON_HOLD")
    assert denied.status_code == 403, denied.text


def test_sensitive_transition_still_requires_lifecycle_manage(client, db_session):
    login_admin(client)
    company = create_company(client, name="Sensitive lifecycle permission")
    project = _project(client, company["id"])
    assert _status(client, project["id"], "ACTIVE").status_code == 200
    assert _status(client, project["id"], "COMPLETED").status_code == 200
    assert _status(client, project["id"], "CLOSED").status_code == 200

    manager = create_user_with_role(
        db_session, email="project-no-lifecycle@nexora.group", role_name="Project Manager"
    )
    db_session.add(UserCompanyAccess(user_id=manager.id, company_id=company["id"]))
    db_session.add(UserProjectAccess(user_id=manager.id, project_id=project["id"]))
    db_session.commit()
    _revoke_role_permission(
        db_session, role_name="Project Manager", resource="project.lifecycle", action="manage"
    )

    login_as(client, email="project-no-lifecycle@nexora.group")
    denied = _status(client, project["id"], "ACTIVE", reason="Reapertura controlada")
    assert denied.status_code == 422, denied.text


def test_sensitive_transition_honors_lifecycle_project_scope(client, db_session):
    login_admin(client)
    company = create_company(client, name="Lifecycle project scope")
    assigned = _project(client, company["id"], name="Lifecycle assigned")
    unassigned = _project(client, company["id"], name="Lifecycle unassigned")
    for project in (assigned, unassigned):
        assert _status(client, project["id"], "ACTIVE").status_code == 200
        assert _status(client, project["id"], "COMPLETED").status_code == 200
        assert _status(client, project["id"], "CLOSED").status_code == 200

    manager = create_user_with_role(
        db_session, email="project-lifecycle-scope@nexora.group", role_name="Project Manager"
    )
    db_session.add(UserCompanyAccess(user_id=manager.id, company_id=company["id"]))
    db_session.add(UserProjectAccess(user_id=manager.id, project_id=assigned["id"]))
    db_session.commit()

    login_as(client, email="project-lifecycle-scope@nexora.group")
    allowed = _status(client, assigned["id"], "ACTIVE", reason="Reapertura autorizada")
    denied = _status(client, unassigned["id"], "ACTIVE", reason="Reapertura no autorizada")
    assert allowed.status_code == 200, allowed.text
    assert denied.status_code == 403, denied.text


def test_normal_transition_does_not_require_lifecycle_scope(client, db_session):
    login_admin(client)
    company = create_company(client, name="Normal lifecycle authority")
    project = _project(client, company["id"])
    manager = create_user_with_role(
        db_session, email="project-normal-authority@nexora.group", role_name="Project Manager"
    )
    role = db_session.scalar(select(Role).where(Role.name == "Project Manager"))
    assert role is not None
    update_grant = db_session.scalar(
        select(RolePermission)
        .join(Permission, RolePermission.permission_id == Permission.id)
        .where(
            RolePermission.role_id == role.id,
            Permission.resource == "project",
            Permission.action == "update",
        )
    )
    assert update_grant is not None
    update_grant.company_scope = SCOPE_ANY
    update_grant.project_scope = SCOPE_ANY
    db_session.commit()

    login_as(client, email="project-normal-authority@nexora.group")
    allowed = _status(client, project["id"], "ACTIVE")
    assert allowed.status_code == 200, allowed.text


def test_lifecycle_transition_preserves_company_isolation(client, db_session):
    login_admin(client)
    company_a = create_company(client, name="Lifecycle company A")
    company_b = create_company(client, name="Lifecycle company B")
    project_b = _project(client, company_b["id"])
    manager = create_user_with_role(
        db_session, email="project-company-scope@nexora.group", role_name="Project Manager"
    )
    db_session.add(UserCompanyAccess(user_id=manager.id, company_id=company_a["id"]))
    db_session.commit()

    login_as(client, email="project-company-scope@nexora.group")
    denied = _status(client, project_b["id"], "ACTIVE")
    assert denied.status_code == 403, denied.text


def test_invalid_transition_gives_readable_business_error(client):
    login_admin(client)
    company = create_company(client, name="Bad Transition Co")
    p = _project(client, company["id"])
    r = _status(client, p["id"], "CLOSED")
    assert r.status_code == 409, r.text
    assert "Planificación" in r.text
