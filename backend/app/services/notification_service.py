import uuid

from sqlalchemy.orm import Session

from app.models.notification import Notification
from app.repositories import notification_repository

"""Notifications (Track G / Platform, NXR-REQ-0091/0092). Servicio delgado
sobre `notification_repository` -- no importa `approval_service` ni ningún
otro servicio de dominio (evita import circular: son los servicios de
dominio, p.ej. `approval_service.decide`, los que importan y llaman a
`notify()`, nunca al revés)."""


def notify(
    db: Session,
    *,
    recipient_user_id: uuid.UUID,
    type: str,
    title: str,
    body: str,
    entity_type: str | None = None,
    entity_id: uuid.UUID | None = None,
) -> Notification:
    return notification_repository.create(
        db,
        recipient_user_id=recipient_user_id,
        type=type,
        title=title,
        body=body,
        entity_type=entity_type,
        entity_id=entity_id,
    )


def mark_read(db: Session, *, notification_id: uuid.UUID) -> Notification:
    return notification_repository.mark_read(db, notification_id=notification_id)
