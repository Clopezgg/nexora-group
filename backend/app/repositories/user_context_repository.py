import uuid

from sqlalchemy.orm import Session

from app.models.user_context import UserContext


def get_or_create(db: Session, user_id: uuid.UUID) -> UserContext:
    context = db.get(UserContext, user_id)
    if context is None:
        context = UserContext(user_id=user_id, active_project_id=None)
        db.add(context)
        db.flush()
    return context


def set_active_project(
    db: Session, user_id: uuid.UUID, active_project_id: uuid.UUID | None
) -> UserContext:
    context = get_or_create(db, user_id)
    context.active_project_id = active_project_id
    db.flush()
    return context
