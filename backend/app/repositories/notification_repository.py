import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.notification import Notification


def create(db: Session, **kwargs) -> Notification:
    row = Notification(**kwargs)
    db.add(row)
    db.flush()
    return row


def get(db: Session, *, notification_id: uuid.UUID) -> Notification:
    row = db.get(Notification, notification_id)
    if row is None:
        raise ValueError(f"Notification {notification_id} no existe")
    return row


def list_for_user(
    db: Session, *, user_id: uuid.UUID, unread_only: bool = False
) -> list[Notification]:
    stmt = select(Notification).where(Notification.recipient_user_id == user_id)
    if unread_only:
        stmt = stmt.where(Notification.read_at.is_(None))
    stmt = stmt.order_by(Notification.created_at.desc())
    return list(db.execute(stmt).scalars())


def mark_read(db: Session, *, notification_id: uuid.UUID) -> Notification:
    row = get(db, notification_id=notification_id)
    row.read_at = datetime.now(timezone.utc)
    db.flush()
    return row
