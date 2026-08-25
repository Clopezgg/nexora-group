import os

os.environ["DATABASE_URL"] = "postgresql+psycopg://nexora@localhost:5432/nexora_tracka_test"
os.environ["BOOTSTRAP_ADMIN_EMAIL"] = "admin@nexora.group"
os.environ["BOOTSTRAP_ADMIN_PASSWORD"] = "NexoraAdmin123!"
os.environ["FRONTEND_URL"] = "http://localhost:5173"
os.environ["APP_ENV"] = "test"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.deps import get_db
from app.core.config import get_settings
from app.core.database import Base
from app.main import app

get_settings.cache_clear()

engine = create_engine(get_settings().database_url)
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


@pytest.fixture
def _clean_schema():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def db_session(_clean_schema):
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session):
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


BOOTSTRAP_ADMIN_EMAIL = os.environ["BOOTSTRAP_ADMIN_EMAIL"]
BOOTSTRAP_ADMIN_PASSWORD = os.environ["BOOTSTRAP_ADMIN_PASSWORD"]
