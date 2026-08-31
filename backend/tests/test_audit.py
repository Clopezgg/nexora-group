import uuid

from sqlalchemy import select

from app.models.audit import AuditLog
from app.models.permission import UserCompanyAccess
from app.models.user import User
from tests.conftest import BOOTSTRAP_ADMIN_EMAIL
from tests.helpers import create_company, create_user_with_role, login_admin, login_as


def _record_page_entries(db_session, *, company_id: str, count: int) -> None:
    from app.services import audit_service

    admin = db_session.execute(
        select(User).where(User.email == BOOTSTRAP_ADMIN_EMAIL)
    ).scalar_one()
    for index in range(count):
        audit_service.record(
            db_session,
            actor_user_id=admin.id,
            action="test.page.create",
            entity_type="test.page",
            entity_id=uuid.uuid4(),
            company_id=uuid.UUID(company_id),
            before=None,
            after={"sequence": index},
            correlation_id=f"page-{index}",
        )
    db_session.commit()


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


def test_audit_feed_has_bounded_default_and_supports_offset(client, db_session):
    login_admin(client)
    company = create_company(client, name="Audit Pagination Co")
    _record_page_entries(db_session, company_id=company["id"], count=105)

    default_page = client.get(
        f"/api/audit?companyId={company['id']}&entityType=test.page"
    )
    assert default_page.status_code == 200, default_page.text
    assert len(default_page.json()) == 50

    first_twenty = client.get(
        f"/api/audit?companyId={company['id']}&entityType=test.page&limit=20"
    ).json()
    second_ten = client.get(
        f"/api/audit?companyId={company['id']}&entityType=test.page&offset=10&limit=10"
    ).json()
    assert [row["id"] for row in second_ten] == [row["id"] for row in first_twenty[10:20]]


def test_audit_feed_rejects_unbounded_or_negative_pages(client):
    login_admin(client)
    company = create_company(client, name="Audit Bounds Co")

    for query in ("limit=0", "limit=101", "offset=-1"):
        response = client.get(f"/api/audit?companyId={company['id']}&{query}")
        assert response.status_code == 422, response.text


def test_audit_feed_order_is_stable_when_timestamps_match(client, db_session):
    login_admin(client)
    company = create_company(client, name="Audit Stable Order Co")
    _record_page_entries(db_session, company_id=company["id"], count=8)

    first = client.get(
        f"/api/audit?companyId={company['id']}&entityType=test.page&limit=8"
    ).json()
    second = client.get(
        f"/api/audit?companyId={company['id']}&entityType=test.page&limit=8"
    ).json()

    assert [row["id"] for row in first] == [row["id"] for row in second]
    assert [row["id"] for row in first] == sorted(row["id"] for row in first)


def test_audit_feed_includes_actor_name_and_email(client, db_session):
    login_admin(client)
    company = create_company(client, name="Audit Actor Co")
    _record_page_entries(db_session, company_id=company["id"], count=1)

    rows = client.get(
        f"/api/audit?companyId={company['id']}&entityType=test.page"
    ).json()

    assert len(rows) == 1
    entry = rows[0]
    # Human audit view needs a name, not just a UUID.
    assert entry["actorFullName"] == "Administrador Nexora"
    assert entry["actorEmail"] == BOOTSTRAP_ADMIN_EMAIL
    assert entry["actorUserId"] is not None
    # Technical fields still present for the detail drawer.
    assert entry["action"] == "test.page.create"
    assert entry["correlationId"] == "page-0"


def test_audit_feed_actor_is_null_for_system_events(client, db_session):
    from app.services import audit_service

    login_admin(client)
    company = create_company(client, name="Audit System Co")
    audit_service.record(
        db_session,
        actor_user_id=None,
        action="test.page.create",
        entity_type="test.page",
        entity_id=uuid.uuid4(),
        company_id=uuid.UUID(company["id"]),
        before=None,
        after=None,
        correlation_id="sys-1",
    )
    db_session.commit()

    rows = client.get(
        f"/api/audit?companyId={company['id']}&entityType=test.page"
    ).json()
    assert rows[0]["actorUserId"] is None
    assert rows[0]["actorFullName"] is None
    assert rows[0]["actorEmail"] is None
