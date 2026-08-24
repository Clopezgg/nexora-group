import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.user import User


def get_by_email(db: Session, email: str) -> User | None:
    stmt = select(User).where(func.lower(User.email) == email.lower())
    return db.execute(stmt).scalar_one_or_none()


def get_by_id(db: Session, user_id: uuid.UUID) -> User | None:
    return db.get(User, user_id)


def count_users(db: Session) -> int:
    stmt = select(func.count()).select_from(User)
    return db.execute(stmt).scalar_one()


def create_user(db: Session, *, email: str, full_name: str, password_hash: str) -> User:
    user = User(email=email, full_name=full_name, password_hash=password_hash)
    db.add(user)
    db.flush()
    return user
