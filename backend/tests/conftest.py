import os
import re

# Isolate the test database per git worktree: running pytest concurrently in
# multiple worktrees (e.g. several tracks under active development at once)
# against one shared hardcoded database corrupts each other's schema mid-run
# (one worktree's Base.metadata doesn't know about another's tables, so
# drop_all/create_all races produce spurious FK/DependentObjectsStillExist
# errors that look like real test failures but aren't).
_worktree_slug = re.sub(
    r"[^a-z0-9]+", "_", os.path.basename(os.path.dirname(os.getcwd())).lower()
).strip("_") or "default"

_base_db_url = os.environ.get(
    "DATABASE_URL", "postgresql+psycopg://nexora:nexora@localhost:5432/nexora_test"
)
os.environ["DATABASE_URL"] = re.sub(
    r"/([^/]+)$", rf"/\1_{_worktree_slug}", _base_db_url
)
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
