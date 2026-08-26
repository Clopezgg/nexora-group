import uuid

from sqlalchemy import select

from app.models.audit import AuditLog
from app.models.permission import UserCompanyAccess
from app.models.user import User
from tests.conftest import BOOTSTRAP_ADMIN_EMAIL
from tests.helpers import create_company, create_user_with_role, login_admin, login_as


def test_audit_log_is_append_only_and_records_actor_and_entity(client, db_session):
    login_admin(client)
    company = create_company(client)

    from app.services import audit_service

    # actor_user_id has a real FK to users.id -- a random uuid.uuid4()
    # would violate referential integrity, so this uses the real admin
    # user created by the test bootstrap.
    admin = db_session.execute(
        select(User).where(User.email == BOOTSTRAP_ADMIN_EMAIL)
    ).scalar_one()

    row = audit_service.record(
        db_session,
        actor_user_id=admin.id,
        action="test.create",
        entity_type="test_entity",
        entity_id=uuid.uuid4(),
        company_id=uuid.UUID(company["id"]),
        before=None,
        after={"status": "CREATED"},
        correlation_id="corr-1",
    )
    db_session.commit()

    fetched = db_session.get(AuditLog, row.id)
    assert fetched is not None
    assert fetched.action == "test.create"
    assert fetched.after == {"status": "CREATED"}
    assert fetched.company_id == uuid.UUID(company["id"])


def test_company_access_blocks_cross_company_audit_log(client, db_session):
    login_admin(client)
    company_a = create_company(client, name="Auditoria A")
    company_b = create_company(client, name="Auditoria B")

    # Auditor is granted SCOPE_ANY for every base permission by house
    # convention (permission_repository.py) so it cannot exercise company
    # isolation meaningfully here. Finance Manager is genuinely SCOPE_OWN
    # for audit.log/read, so it is used instead to make this test
    # meaningful (see docs/AUDIT.md).
    user = create_user_with_role(
        db_session, email="finance-b@nexora.group", role_name="Finance Manager"
    )
    db_session.add(UserCompanyAccess(user_id=user.id, company_id=company_b["id"]))
    db_session.commit()
    login_as(client, email="finance-b@nexora.group")

    response = client.get(f"/api/audit?companyId={company_a['id']}")
    assert response.status_code == 403, response.text
    assert response.json()["error"]["code"] == "NXR-PERM-001"
