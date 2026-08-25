import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.domain.errors import NotAuthorizedError
from app.repositories import notification_repository
from app.schemas.notification import NotificationResponse

"""Notifications API (Track G / Platform, NXR-REQ-0092). A `Notification`
pertenece a `recipient_user_id`, no a una compañía -- por eso, a diferencia
de las demás rutas de este codebase, NO llama a `assert_company_access`;
la propiedad se verifica directo contra el usuario autenticado
(`current`), mismo patrón que un recurso "propio" del usuario."""

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationResponse])
def list_my_notifications(
    unread_only: bool = Query(default=False, alias="unreadOnly"),
    db: Session = Depends(get_db),
    current=Depends(get_current_user),
) -> list[NotificationResponse]:
    user, _roles = current
    rows = notification_repository.list_for_user(db, user_id=user.id, unread_only=unread_only)
    return [NotificationResponse.model_validate(r, from_attributes=True) for r in rows]


@router.post("/{notification_id}/read", response_model=NotificationResponse)
def mark_notification_read(
    notification_id: uuid.UUID,
    db: Session = Depends(get_db),
    current=Depends(get_current_user),
) -> NotificationResponse:
    user, _roles = current
    row = notification_repository.get(db, notification_id=notification_id)
    if row.recipient_user_id != user.id:
        raise NotAuthorizedError("No puede marcar como leída una notificación de otro usuario")
    updated = notification_repository.mark_read(db, notification_id=notification_id)
    db.commit()
    return NotificationResponse.model_validate(updated, from_attributes=True)
