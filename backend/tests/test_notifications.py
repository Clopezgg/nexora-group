import uuid

from sqlalchemy import select

from app.models.notification import Notification
from app.models.permission import UserCompanyAccess
from app.models.user import User
from app.services import approval_service
from tests.conftest import BOOTSTRAP_ADMIN_EMAIL
from tests.helpers import create_company, create_user_with_role, login_admin


def _get_admin_user(db_session) -> User:
    return db_session.execute(select(User).where(User.email == BOOTSTRAP_ADMIN_EMAIL)).scalar_one()


def test_notification_starts_unread_and_can_be_marked_read(client, db_session):
    login_admin(client)
    admin_user = _get_admin_user(db_session)

    from app.services import notification_service

    # recipient_user_id es una FK real hacia users.id (ver
    # app/models/notification.py) -- se usa el admin de bootstrap real, no
    # un uuid4() al azar, porque la constraint de integridad referencial se
    # aplica de verdad contra Postgres (no es un mock).
    note = notification_service.notify(
        db_session,
        recipient_user_id=admin_user.id,
        type="approval.assigned",
        title="Nueva aprobación pendiente",
        body="Tienes una factura de proveedor esperando tu aprobación",
    )
    db_session.commit()
    assert note.read_at is None

    from app.services import notification_service as ns

    ns.mark_read(db_session, notification_id=note.id)
    db_session.commit()
    db_session.refresh(note)
    assert note.read_at is not None


def test_deciding_an_approval_request_notifies_the_requester(client, db_session):
    login_admin(client)
    company = create_company(client)
    admin_user = _get_admin_user(db_session)
    approver = create_user_with_role(
        db_session, email="approver-notify@nexora.group", role_name="Finance Manager"
    )
    db_session.add(UserCompanyAccess(user_id=approver.id, company_id=uuid.UUID(company["id"])))
    db_session.commit()

    request = approval_service.create_request(
        db_session,
        policy_id=None,
        entity_type="test.entity",
        entity_id=uuid.uuid4(),
        company_id=uuid.UUID(company["id"]),
        requested_by=admin_user.id,
        module="test",
    )
    db_session.commit()

    approval_service.decide(
        db_session, request_id=request.id, decided_by=approver.id, decision="APPROVED"
    )
    db_session.commit()

    notes = (
        db_session.execute(
            select(Notification).where(
                Notification.recipient_user_id == admin_user.id,
                Notification.type == "approval.decided",
            )
        )
        .scalars()
        .all()
    )
    assert len(notes) == 1


def test_user_cannot_mark_another_users_notification_as_read(client, db_session):
    from app.services import notification_service
    from tests.helpers import login_as

    login_admin(client)
    company = create_company(client)
    admin_user = _get_admin_user(db_session)
    other = create_user_with_role(
        db_session, email="other-notify@nexora.group", role_name="Finance Manager"
    )
    db_session.add(UserCompanyAccess(user_id=other.id, company_id=uuid.UUID(company["id"])))
    db_session.commit()

    note = notification_service.notify(
        db_session,
        recipient_user_id=admin_user.id,
        type="approval.assigned",
        title="Test",
        body="Test body",
    )
    db_session.commit()

    login_as(client, email="other-notify@nexora.group")
    response = client.post(f"/api/notifications/{note.id}/read")

    assert response.status_code == 403, response.text
    assert response.json()["error"]["code"] == "NXR-PERM-001"


def test_user_can_list_and_mark_own_notification_as_read(client, db_session):
    from app.services import notification_service

    login_admin(client)
    admin_user = _get_admin_user(db_session)

    note = notification_service.notify(
        db_session,
        recipient_user_id=admin_user.id,
        type="approval.assigned",
        title="Test propio",
        body="Test body",
    )
    db_session.commit()

    list_response = client.get("/api/notifications", params={"unreadOnly": "true"})
    assert list_response.status_code == 200, list_response.text
    ids = [row["id"] for row in list_response.json()]
    assert str(note.id) in ids

    read_response = client.post(f"/api/notifications/{note.id}/read")
    assert read_response.status_code == 200, read_response.text
    assert read_response.json()["readAt"] is not None
