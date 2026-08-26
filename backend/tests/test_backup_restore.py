"""NXR-REQ-0109 (Backup/Restore). Real evidence, not "documented but
never run": pg_dump a real seeded database, drop/recreate a separate
target database, pg_restore into it, then verify the restored data is
byte-for-byte the same business reality (not just "the tables exist") --
same company name, same accounting balances reconciling (SUM(debit) ==
SUM(credit)), same migration head. Every step shells out to the real
scripts/db_backup.sh and scripts/db_restore.sh -- this test is also
their only real exercise, so a regression in either script fails here
first, not in an actual disaster."""

import json
import os
import re
import subprocess
from decimal import Decimal
from pathlib import Path

from sqlalchemy import create_engine, text

from app.security.passwords import verify_password

_BACKEND_DIR = Path(__file__).resolve().parents[1]
_REPO_ROOT = _BACKEND_DIR.parent
_worktree_slug = re.sub(
    r"[^a-z0-9]+", "_", os.path.basename(os.path.dirname(os.getcwd())).lower()
).strip("_") or "default"
_SOURCE_DB = f"nexora_backup_source_{_worktree_slug}"
_TARGET_DB = f"nexora_backup_target_{_worktree_slug}"
_DUMP_PATH = _BACKEND_DIR / f".backup_restore_test_{_worktree_slug}.dump"


def _run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=120, **kwargs)


def _alembic_env(db_name: str) -> dict:
    return {
        **os.environ,
        "DATABASE_URL": f"postgresql+psycopg://nexora@localhost:5432/{db_name}",
        "BOOTSTRAP_ADMIN_EMAIL": "",
        "BOOTSTRAP_ADMIN_PASSWORD": "",
        "FRONTEND_URL": "http://localhost:5173",
        "APP_ENV": "test",
    }


def _trial_balance(engine) -> tuple[Decimal, Decimal]:
    with engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT COALESCE(SUM(debit_amount), 0), COALESCE(SUM(credit_amount), 0) "
                "FROM journal_lines"
            )
        ).one()
        return Decimal(row[0]), Decimal(row[1])


def test_real_pg_dump_backup_then_pg_restore_reproduces_the_same_financial_reality():
    for db_name in (_SOURCE_DB, _TARGET_DB):
        subprocess.run(["dropdb", "--if-exists", db_name], check=True)
    _DUMP_PATH.unlink(missing_ok=True)

    try:
        subprocess.run(["createdb", _SOURCE_DB], check=True)
        upgrade = _run(
            [str(_BACKEND_DIR / ".venv" / "bin" / "alembic"), "upgrade", "head"],
            cwd=_BACKEND_DIR, env=_alembic_env(_SOURCE_DB),
        )
        assert upgrade.returncode == 0, upgrade.stderr

        seed = _run(
            [str(_BACKEND_DIR / ".venv" / "bin" / "python"), "-m", "tests._seed_backup_restore_fixture"],
            cwd=_BACKEND_DIR, env=_alembic_env(_SOURCE_DB),
        )
        assert seed.returncode == 0, seed.stderr
        seeded = json.loads(seed.stdout.strip().splitlines()[-1])

        source_engine = create_engine(f"postgresql+psycopg://nexora@localhost:5432/{_SOURCE_DB}")
        source_debit, source_credit = _trial_balance(source_engine)
        assert source_debit == source_credit == Decimal(seeded["remittanceAmount"])
        source_engine.dispose()

        # Real backup, via the real script -- not a Python re-implementation.
        backup = _run(
            ["bash", str(_REPO_ROOT / "scripts" / "db_backup.sh"), _SOURCE_DB, str(_DUMP_PATH)]
        )
        assert backup.returncode == 0, backup.stderr
        assert _DUMP_PATH.exists() and _DUMP_PATH.stat().st_size > 0

        # Real restore into a SEPARATE, freshly created target database --
        # never restoring onto a live DB (see script docstring).
        restore = _run(
            ["bash", str(_REPO_ROOT / "scripts" / "db_restore.sh"), str(_DUMP_PATH), _TARGET_DB]
        )
        assert restore.returncode == 0, restore.stderr

        target_engine = create_engine(f"postgresql+psycopg://nexora@localhost:5432/{_TARGET_DB}")

        # 1. Migration head survived the round trip.
        current = _run(
            [str(_BACKEND_DIR / ".venv" / "bin" / "alembic"), "current"],
            cwd=_BACKEND_DIR, env=_alembic_env(_TARGET_DB),
        )
        assert current.returncode == 0, current.stderr
        assert "(head)" in current.stdout

        # 2. The exact company created before the backup is present.
        with target_engine.connect() as conn:
            company_row = conn.execute(
                text("SELECT name FROM companies WHERE id = :id"),
                {"id": seeded["companyId"]},
            ).one_or_none()
        assert company_row is not None
        assert company_row[0] == seeded["companyName"]

        # 3. Financial integrity survived: debits still equal credits, and
        # the real amount from the real remittance is still there --
        # not just "some data", the SAME data.
        target_debit, target_credit = _trial_balance(target_engine)
        assert target_debit == target_credit == Decimal(seeded["remittanceAmount"])

        # 4. Login survives: the real Argon2id hash restores intact and
        # verify_password() (the exact function auth_service.login() uses)
        # accepts the original plaintext password against it.
        with target_engine.connect() as conn:
            user_row = conn.execute(
                text("SELECT password_hash FROM users WHERE email = :email"),
                {"email": seeded["userEmail"]},
            ).one_or_none()
        assert user_row is not None
        assert user_row[0] == seeded["userPasswordHash"]
        assert verify_password("BackupRestoreTest123!", user_row[0])

        target_engine.dispose()
    finally:
        for db_name in (_SOURCE_DB, _TARGET_DB):
            subprocess.run(["dropdb", "--if-exists", db_name], check=True)
        _DUMP_PATH.unlink(missing_ok=True)
