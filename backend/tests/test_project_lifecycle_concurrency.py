"""Race the real transition handler with independent sessions and stale reads."""

import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.routes import project_management
from app.models.audit import AuditLog
from app.models.project import Project
from app.models.user import User
from app.schemas.project_control import ProjectStatusTransitionRequest
from tests.conftest import BOOTSTRAP_ADMIN_EMAIL
from tests.helpers import create_company, login_admin
from tests.test_project_lifecycle import _project, _status


def test_competing_transitions_revalidate_locked_state(client, db_session, monkeypatch):
    login_admin(client)
    company = create_company(client)
    project = _project(client, company["id"])
    assert _status(client, project["id"], "ACTIVE").status_code == 200
    project_id = uuid.UUID(project["id"])
    engine = db_session.get_bind()
    barrier = Barrier(2)
    original_read = project_management._get_project_or_404

    def synchronized_read(db, identifier):
        value = original_read(db, identifier)
        assert value.status == "ACTIVE"
        barrier.wait(timeout=10)
        return value

    # Only schedules the unlocked reads; all authorization, locking, domain
    # validation, writes and audit are executed by the production handler.
    monkeypatch.setattr(project_management, "_get_project_or_404", synchronized_read)

    def transition(target):
        with Session(engine) as session:
            user = session.scalar(
                select(User).where(User.email == BOOTSTRAP_ADMIN_EMAIL)
            )
            try:
                response = project_management.transition_project_status(
                    project_id,
                    ProjectStatusTransitionRequest(status=target),
                    db=session,
                    user=user,
                    correlation_id="lifecycle-race",
                )
                return response.status
            except HTTPException as exc:
                session.rollback()
                assert exc.status_code == 409
                return "CONFLICT"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(transition, ["ON_HOLD", "COMPLETED"]))
    assert results.count("CONFLICT") == 1
    winner = next(value for value in results if value != "CONFLICT")
    db_session.expire_all()
    assert db_session.get(Project, project_id).status == winner
    audits = db_session.scalars(
        select(AuditLog).where(AuditLog.correlation_id == "lifecycle-race")
    ).all()
    assert len(audits) == 1
    assert audits[0].before == {"status": "ACTIVE"}
    assert audits[0].after["status"] == winner
