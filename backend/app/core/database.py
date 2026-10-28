from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.database_url, pool_pre_ping=True,
    pool_size=settings.database_pool_size, max_overflow=settings.database_max_overflow,
    pool_timeout=30, pool_recycle=300,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


# Importar el paquete de modelos aquí (después de definir Base, antes de que
# nadie use Base.metadata) es lo que registra todas las tablas para
# Base.metadata.create_all (tests) y para Alembic autogenerate. Sin esto,
# un modelo nuevo que ningún repository/service importe todavía quedaría
# invisible para create_all/migraciones.
from app.models import *  # noqa: E402,F401


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
