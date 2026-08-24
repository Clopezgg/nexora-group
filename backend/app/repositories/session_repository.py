import uuid
from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session as OrmSession

from app.models.session import Session as SessionModel


def create_session(
    db: OrmSession,
    *,
    user_id: uuid.UUID,
    token_hash: str,
    expires_at: datetime,
    user_agent: str | None,
) -> SessionModel:
    session = SessionModel(
        user_id=user_id, token_hash=token_hash, expires_at=expires_at, user_agent=user_agent
    )
    db.add(session)
    db.flush()
    return session


def get_valid_session(db: OrmSession, *, token_hash: str, now: datetime) -> SessionModel | None:
    stmt = select(SessionModel).where(
        SessionModel.token_hash == token_hash, SessionModel.expires_at > now
    )
    return db.execute(stmt).scalar_one_or_none()


def delete_session(db: OrmSession, *, token_hash: str) -> None:
    db.execute(delete(SessionModel).where(SessionModel.token_hash == token_hash))
