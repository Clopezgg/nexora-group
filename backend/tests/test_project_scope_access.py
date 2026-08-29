import uuid
from datetime import date

from sqlalchemy import select

from app.models.evidence import Evidence
from app.models.permission import (
    SCOPE_ANY,
    SCOPE_NONE,
    SCOPE_OWN,
    Permission,
    RolePermission,
    UserCompanyAccess,
    UserProjectAccess,
)
from app.models.role import Role
from app.models.user import User
from tests.conftest import BOOTSTRAP_ADMIN_EMAIL
from tests.helpers import (
    create_company,
    create_supplier,
    create_user_with_role,
    login_admin,
    login_as,
)

VALID_JPEG = b"\xff\xd8\xff\xe0JFIF\x00evidence-project-scope"


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


def _seed_evidence(
    db_session,
    *,
    company_id: str,
    entity_type: str,
    entity_id: str,
    suffix: str,
) -> Evidence:
    admin = db_session.execute(
        select(User).where(User.email == BOOTSTRAP_ADMIN_EMAIL)
    ).scalar_one()
    row = Evidence(
        company_id=uuid.UUID(company_id),
        blob_key=f"{company_id}/scope-{suffix}.jpg",
        original_filename=f"scope-{suffix}.jpg",
        mime_type="image/jpeg",
        size_bytes=len(VALID_JPEG),
        uploaded_by=admin.id,
        category="PHOTO",
        entity_type=entity_type,
        entity_id=uuid.UUID(entity_id),
    )
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    return row


def _restrict_administrator_to_own_projects(db_session) -> None:
    grants = (
        db_session.query(RolePermission)
        .join(Role, Role.id == RolePermission.role_id)
        .join(Permission, Permission.id == RolePermission.permission_id)
        .filter(Role.name == "Administrator", RolePermission.project_scope != "NONE")
        .all()
    )
    assert grants
    for grant in grants:
        grant.project_scope = SCOPE_OWN
    db_session.commit()


def _set_role_project_read_scope(db_session, *, role_name: str, scope: str) -> None:
    grant = (
        db_session.query(RolePermission)
        .join(Role, Role.id == RolePermission.role_id)
        .join(Permission, Permission.id == RolePermission.permission_id)
        .filter(
            Role.name == role_name,
            Permission.resource == "project",
            Permission.action == "read",
        )
        .one()
    )
    grant.project_scope = scope
    db_session.commit()


def test_project_scope_any_lists_and_reads_without_assignment(client, db_session):
    login_admin(client)
    company = create_company(client, name="Project Scope Any Co")
    project = _create_project(client, company["id"], "Proyecto ANY", "ANY-01")
    manager = create_user_with_role(
        db_session,
        email="project-any@nexora.group",
        role_name="Project Manager",
    )
    db_session.add(UserCompanyAccess(user_id=manager.id, company_id=company["id"]))
    db_session.commit()
    _set_role_project_read_scope(db_session, role_name="Project Manager", scope=SCOPE_ANY)

    login_as(client, email="project-any@nexora.group")
    listing = client.get(f"/api/projects?company_id={company['id']}")
    assert listing.status_code == 200, listing.text
    assert project["id"] in {row["id"] for row in listing.json()}
    direct = client.get(f"/api/projects/{project['id']}")
    assert direct.status_code == 200, direct.text


def test_project_scope_none_filters_lists_and_blocks_direct_access(client, db_session):
    login_admin(client)
    company = create_company(client, name="Project Scope None Co")
    project = _create_project(client, company["id"], "Proyecto NONE", "NONE-01")
    manager = create_user_with_role(
        db_session,
        email="project-none@nexora.group",
        role_name="Project Manager",
    )
    db_session.add(UserCompanyAccess(user_id=manager.id, company_id=company["id"]))
    db_session.add(UserProjectAccess(user_id=manager.id, project_id=project["id"]))
    db_session.commit()
    _set_role_project_read_scope(db_session, role_name="Project Manager", scope=SCOPE_NONE)

    login_as(client, email="project-none@nexora.group")
    listing = client.get(f"/api/projects?company_id={company['id']}")
    assert listing.status_code == 200, listing.text
    assert listing.json() == []
    direct = client.get(f"/api/projects/{project['id']}")
    assert direct.status_code == 403, direct.text


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
    revoked = client.delete(f"/api/access-management/users/{manager.id}/projects/{project['id']}")
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

    response = client.put(f"/api/access-management/users/{auditor.id}/projects/{project['id']}")
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
    allowed = client.get(f"/api/documents?companyId={company['id']}&projectId={project_a['id']}")
    assert allowed.status_code == 200, allowed.text

    denied = client.get(f"/api/documents?companyId={company['id']}&projectId={project_b['id']}")
    assert denied.status_code == 403, denied.text


def test_project_scope_blocks_indirect_procurement_ids_in_path_and_nested_body(client, db_session):
    login_admin(client)
    company = create_company(client, name="Indirect Procurement Scope Co")
    project_a = _create_project(client, company["id"], "Proyecto permitido", "IND-A")
    project_b = _create_project(client, company["id"], "Proyecto restringido", "IND-B")
    supplier = create_supplier(client, company_id=company["id"])

    requisition = client.post(
        "/api/procurement/requisitions",
        json={
            "companyId": company["id"],
            "projectId": project_b["id"],
            "justification": "Compra restringida",
            "lines": [
                {
                    "description": "Material restringido",
                    "quantity": "1",
                    "estimatedUnitCost": "10",
                }
            ],
        },
    )
    assert requisition.status_code == 201, requisition.text
    requisition_id = requisition.json()["id"]

    rfq = client.post(
        "/api/procurement/rfqs",
        json={
            "companyId": company["id"],
            "purchaseRequisitionId": requisition_id,
            "supplierIds": [supplier["id"]],
        },
    )
    assert rfq.status_code == 201, rfq.text
    quotation = client.post(
        f"/api/procurement/rfqs/{rfq.json()['id']}/quotations",
        json={
            "supplierId": supplier["id"],
            "currencyCode": "HNL",
            "lines": [
                {
                    "description": "Material restringido",
                    "quantity": "1",
                    "unitPrice": "10",
                }
            ],
        },
    )
    assert quotation.status_code == 201, quotation.text

    scoped_admin = create_user_with_role(
        db_session,
        email="indirect-procurement@nexora.group",
        role_name="Administrator",
    )
    db_session.add(UserCompanyAccess(user_id=scoped_admin.id, company_id=company["id"]))
    db_session.add(UserProjectAccess(user_id=scoped_admin.id, project_id=project_a["id"]))
    db_session.commit()
    _restrict_administrator_to_own_projects(db_session)

    login_as(client, email="indirect-procurement@nexora.group")
    path_attack = client.post(f"/api/procurement/requisitions/{requisition_id}/approve")
    assert path_attack.status_code == 403, path_attack.text

    nested_body_attack = client.post(
        "/api/procurement/purchase-orders/from-quotation",
        json={
            "companyId": company["id"],
            "supplierQuotationId": quotation.json()["id"],
        },
    )
    assert nested_body_attack.status_code == 403, nested_body_attack.text


def test_project_scope_filters_and_blocks_multipart_evidence(client, db_session):
    login_admin(client)
    company = create_company(client, name="Multipart Evidence Scope Co")
    project_a = _create_project(client, company["id"], "Proyecto permitido", "EVD-A")
    project_b = _create_project(client, company["id"], "Proyecto restringido", "EVD-B")
    seeded = _seed_evidence(
        db_session,
        company_id=company["id"],
        entity_type="PROJECT",
        entity_id=project_b["id"],
        suffix="project",
    )

    scoped_admin = create_user_with_role(
        db_session,
        email="multipart-evidence@nexora.group",
        role_name="Administrator",
    )
    db_session.add(UserCompanyAccess(user_id=scoped_admin.id, company_id=company["id"]))
    db_session.add(UserProjectAccess(user_id=scoped_admin.id, project_id=project_a["id"]))
    db_session.commit()
    _restrict_administrator_to_own_projects(db_session)

    login_as(client, email="multipart-evidence@nexora.group")
    listing = client.get(f"/api/evidence?companyId={company['id']}")
    assert listing.status_code == 200, listing.text
    assert str(seeded.id) not in {row["id"] for row in listing.json()}

    direct_attack = client.get(f"/api/evidence/{seeded.id}")
    assert direct_attack.status_code == 403, direct_attack.text

    upload_attack = client.post(
        "/api/evidence",
        data={
            "companyId": company["id"],
            "entityType": "PROJECT",
            "entityId": project_b["id"],
        },
        files={"file": ("attack.jpg", VALID_JPEG, "image/jpeg")},
    )
    assert upload_attack.status_code == 403, upload_attack.text


def test_project_scope_resolves_daily_report_evidence_instead_of_treating_it_as_general(
    client, db_session
):
    login_admin(client)
    company = create_company(client, name="Daily Evidence Scope Co")
    project_a = _create_project(client, company["id"], "Proyecto permitido", "DAY-A")
    project_b = _create_project(client, company["id"], "Proyecto restringido", "DAY-B")

    report_response = client.post(
        "/api/site-reports",
        json={
            "projectId": project_b["id"],
            "reportDate": date.today().isoformat(),
            "weather": "Soleado",
            "activitiesPerformed": "Actividad restringida",
        },
    )
    assert report_response.status_code == 201, report_response.text
    report = report_response.json()
    seeded = _seed_evidence(
        db_session,
        company_id=company["id"],
        entity_type="DAILY_REPORT",
        entity_id=report["id"],
        suffix="daily-report",
    )

    scoped_admin = create_user_with_role(
        db_session,
        email="daily-evidence-scope@nexora.group",
        role_name="Administrator",
    )
    db_session.add(UserCompanyAccess(user_id=scoped_admin.id, company_id=company["id"]))
    db_session.add(UserProjectAccess(user_id=scoped_admin.id, project_id=project_a["id"]))
    db_session.commit()
    _restrict_administrator_to_own_projects(db_session)

    login_as(client, email="daily-evidence-scope@nexora.group")
    listing = client.get(f"/api/evidence?companyId={company['id']}")
    assert listing.status_code == 200, listing.text
    assert str(seeded.id) not in {row["id"] for row in listing.json()}

    direct_attack = client.get(f"/api/evidence/{seeded.id}")
    assert direct_attack.status_code == 403, direct_attack.text

    upload_attack = client.post(
        "/api/evidence",
        data={
            "companyId": company["id"],
            "entityType": "DAILY_REPORT",
            "entityId": report["id"],
            "category": "DAILY_REPORT",
        },
        files={"file": ("daily.jpg", VALID_JPEG, "image/jpeg")},
    )
    assert upload_attack.status_code == 403, upload_attack.text


def test_evidence_rejects_unknown_polymorphic_context_before_storage(client):
    login_admin(client)
    company = create_company(client, name="Unknown Evidence Context Co")
    response = client.post(
        "/api/evidence",
        data={
            "companyId": company["id"],
            "entityType": "UNKNOWN_EVENT",
            "entityId": str(uuid.uuid4()),
        },
        files={"file": ("unknown.jpg", VALID_JPEG, "image/jpeg")},
    )
    assert response.status_code == 422, response.text
    assert "no soportado" in response.json()["detail"]
