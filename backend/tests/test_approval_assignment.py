import uuid

from sqlalchemy import select

from app.models.permission import UserCompanyAccess
from app.models.user import User
from app.repositories import approval_repository
from app.services import approval_service
from tests.conftest import BOOTSTRAP_ADMIN_EMAIL
from tests.helpers import create_company, create_user_with_role, login_admin, login_as


def _admin(db_session) -> User:
    return db_session.execute(
        select(User).where(User.email == BOOTSTRAP_ADMIN_EMAIL)
    ).scalar_one()


def _finance_user(db_session, *, email: str, company_id: uuid.UUID) -> User:
    user = create_user_with_role(db_session, email=email, role_name="Finance Manager")
    db_session.add(UserCompanyAccess(user_id=user.id, company_id=company_id))
    db_session.commit()
    return user


def test_explicit_user_assignment_cannot_be_decided_by_another_approver(client, db_session):
    login_admin(client)
    company = create_company(client, name="Aprobaciones asignadas")
    company_id = uuid.UUID(company["id"])
    requester = _admin(db_session)
    assigned = _finance_user(
        db_session, email="assigned-approval@nexora.group", company_id=company_id
    )
    other = _finance_user(
        db_session, email="other-approval@nexora.group", company_id=company_id
    )

    request = approval_service.create_request(
        db_session,
        policy_id=None,
        entity_type="test.entity",
        entity_id=uuid.uuid4(),
        company_id=company_id,
        requested_by=requester.id,
        module="test",
        assigned_to=assigned.id,
    )
    db_session.commit()

    login_as(client, email=other.email)
    inbox = client.get(f"/api/approvals?companyId={company_id}")
    assert inbox.status_code == 200, inbox.text
    assert str(request.id) not in {row["id"] for row in inbox.json()}

    response = client.post(
        f"/api/approvals/{request.id}/decide", json={"decision": "APPROVED"}
    )
    assert response.status_code == 403, response.text
    assert response.json()["error"]["code"] == "NXR-PERM-001"

    db_session.expire_all()
    reloaded = approval_repository.get_for_update(db_session, request_id=request.id)
    assert reloaded.status == "PENDING"
    assert reloaded.decided_by is None

    login_as(client, email=assigned.email)
    assigned_inbox = client.get(f"/api/approvals?companyId={company_id}")
    assert assigned_inbox.status_code == 200, assigned_inbox.text
    assert str(request.id) in {row["id"] for row in assigned_inbox.json()}


def test_role_assignment_is_visible_and_decidable_only_by_matching_role(client, db_session):
    login_admin(client)
    company = create_company(client, name="Aprobaciones por rol")
    company_id = uuid.UUID(company["id"])
    requester = _admin(db_session)
    finance = _finance_user(
        db_session, email="role-finance@nexora.group", company_id=company_id
    )
    non_matching = create_user_with_role(
        db_session, email="role-auditor@nexora.group", role_name="Auditor"
    )
    db_session.add(UserCompanyAccess(user_id=non_matching.id, company_id=company_id))
    db_session.commit()

    request = approval_service.create_request(
        db_session,
        policy_id=None,
        entity_type="test.entity",
        entity_id=uuid.uuid4(),
        company_id=company_id,
        requested_by=requester.id,
        module="test",
        assigned_role="Finance Manager",
    )
    db_session.commit()

    login_as(client, email=non_matching.email)
    auditor_inbox = client.get(f"/api/approvals?companyId={company_id}")
    assert auditor_inbox.status_code == 200, auditor_inbox.text
    assert str(request.id) not in {row["id"] for row in auditor_inbox.json()}

    login_as(client, email=finance.email)
    finance_inbox = client.get(f"/api/approvals?companyId={company_id}")
    assert finance_inbox.status_code == 200, finance_inbox.text
    assert str(request.id) in {row["id"] for row in finance_inbox.json()}

    decision = client.post(
        f"/api/approvals/{request.id}/decide", json={"decision": "APPROVED"}
    )
    assert decision.status_code == 200, decision.text
    assert decision.json()["status"] == "APPROVED"


def test_missing_approval_request_returns_not_found(client, db_session):
    login_admin(client)
    response = client.post(
        f"/api/approvals/{uuid.uuid4()}/decide", json={"decision": "APPROVED"}
    )
    assert response.status_code == 404, response.text
    assert response.json()["error"]["code"] == "NXR-DATA-002"
