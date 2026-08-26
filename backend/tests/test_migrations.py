import os
import re
import shutil
import subprocess
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parents[1]
_worktree_slug = re.sub(
    r"[^a-z0-9]+", "_", os.path.basename(os.path.dirname(os.getcwd())).lower()
).strip("_") or "default"
_DB_NAME = f"nexora_migrations_test_{_worktree_slug}"
_PG_USER = "nexora"
_PG_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "nexora")
_PG_HOST = "localhost"
_PG_PORT = "5432"


_ALEMBIC_BIN = shutil.which("alembic") or str(_BACKEND_DIR / ".venv" / "bin" / "alembic")


def _pg_env() -> dict:
    return {**os.environ, "PGPASSWORD": _PG_PASSWORD, "PGHOST": _PG_HOST, "PGPORT": _PG_PORT, "PGUSER": _PG_USER}


def _run_alembic(*args: str) -> subprocess.CompletedProcess:
    env = {
        **os.environ,
        "DATABASE_URL": f"postgresql+psycopg://{_PG_USER}:{_PG_PASSWORD}@{_PG_HOST}:{_PG_PORT}/{_DB_NAME}",
        "BOOTSTRAP_ADMIN_EMAIL": "",
        "BOOTSTRAP_ADMIN_PASSWORD": "",
        "FRONTEND_URL": "http://localhost:5173",
        "APP_ENV": "test",
    }
    return subprocess.run(
        [str(_ALEMBIC_BIN), *args],
        cwd=_BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_fresh_install_then_full_downgrade_then_upgrade_roundtrip_succeeds():
    """NXR-REQ-0106 (Migrations): real evidence, not "alembic upgrade head
    aplicado" by itself. Found and fixed a real bug building this test:
    several migrations passed `None` as the constraint name to
    `create_foreign_key`/`create_unique_constraint`, which let PostgreSQL
    autogenerate an unpredictable name at CREATE time -- their own
    `downgrade()` then tried `drop_constraint(None, ...)`, which cannot
    resolve to any real constraint and always failed. Fixed by naming
    every such constraint explicitly at creation
    (131a6debf189/c622defc2308/f1075e290473/eaf5b6c0d061). This test
    would have caught it: fresh install -> head, full downgrade -> base,
    full upgrade -> head again, against a real dedicated PostgreSQL
    database (not `Base.metadata.create_all`, which every other test in
    this suite uses and which would never have exercised `downgrade()`
    or the real migration chain at all)."""
    subprocess.run(["dropdb", "--if-exists", _DB_NAME], check=True, env=_pg_env())
    subprocess.run(["createdb", _DB_NAME], check=True, env=_pg_env())
    try:
        upgrade_to_head = _run_alembic("upgrade", "head")
        assert upgrade_to_head.returncode == 0, upgrade_to_head.stderr

        downgrade_to_base = _run_alembic("downgrade", "base")
        assert downgrade_to_base.returncode == 0, downgrade_to_base.stderr

        upgrade_again = _run_alembic("upgrade", "head")
        assert upgrade_again.returncode == 0, upgrade_again.stderr

        current = _run_alembic("current")
        assert current.returncode == 0, current.stderr
        assert "(head)" in current.stdout
    finally:
        subprocess.run(["dropdb", "--if-exists", _DB_NAME], check=True, env=_pg_env())
