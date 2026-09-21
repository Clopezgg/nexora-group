"""Atomic, resumable initial Project configuration."""

import uuid

from sqlalchemy import select

from app.models.audit import AuditLog
from app.models.project import Project
from app.models.project_setup import ProjectSetupRun
from app.models.wbs import WBSNode
from tests.helpers import create_company, login_admin


def _payload(company_id: str) -> dict:
    return {
        "project": {
            "companyId": company_id,
            "name": "Proyecto orquestado",
            "code": "SETUP-01",
            "currencyCode": "HNL",
            "plannedStart": "2026-01-01",
            "plannedEnd": "2026-12-31",
        },
        "wbs": {"code": "1.0", "name": "Obra inicial"},
        "baselineAmount": "100.00",
        "activate": True,
    }


def test_project_setup_is_idempotent_and_executes_as_one_command(client, db_session):
    login_admin(client)
    company = create_company(client)
    headers = {"Idempotency-Key": "project-setup-one"}
    created = client.post("/api/projects/setup-runs", json=_payload(company["id"]), headers=headers)
    assert created.status_code == 201, created.text
    run = created.json()
    assert run["status"] == "DRAFT"
    assert db_session.execute(select(Project)).scalars().all() == []

    replay = client.post("/api/projects/setup-runs", json=_payload(company["id"]), headers=headers)
    assert replay.status_code == 201, replay.text
    assert replay.json()["id"] == run["id"]

    finished = client.post(f"/api/projects/setup-runs/{run['id']}/execute")
    assert finished.status_code == 200, finished.text
    assert finished.json()["status"] == "COMPLETED"
    assert finished.json()["projectId"]
    assert len(db_session.execute(select(Project)).scalars().all()) == 1
    assert len(db_session.execute(select(WBSNode)).scalars().all()) == 1

    second_execute = client.post(f"/api/projects/setup-runs/{run['id']}/execute")
    assert second_execute.status_code == 200, second_execute.text
    assert second_execute.json()["projectId"] == finished.json()["projectId"]
    assert len(db_session.execute(select(Project)).scalars().all()) == 1
    setup_audits = db_session.scalars(
        select(AuditLog).where(AuditLog.entity_id == uuid.UUID(run["id"]))
    ).all()
    assert [row.action for row in setup_audits].count("project.setup.create") == 1
    assert [row.action for row in setup_audits].count("project.setup.complete") == 1


def test_project_setup_failure_rolls_back_all_core_rows_and_is_retryable(client, db_session, monkeypatch):
    login_admin(client)
    company = create_company(client)
    run = client.post(
        "/api/projects/setup-runs", json=_payload(company["id"]), headers={"Idempotency-Key": "project-setup-retry"}
    ).json()

    from app.services import project_setup_service

    original = project_setup_service.project_control_repository.create_wbs_node
    monkeypatch.setattr(
        project_setup_service.project_control_repository,
        "create_wbs_node",
        lambda *args, **kwargs: (_ for _ in ()).throw(ValueError("WBS boundary failure")),
    )
    failed = client.post(f"/api/projects/setup-runs/{run['id']}/execute")
    assert failed.status_code >= 400
    assert db_session.execute(select(Project)).scalars().all() == []
    stored = db_session.get(ProjectSetupRun, run["id"])
    assert stored.status == "FAILED"
    assert stored.failure_step == "WBS"
    failed_audits = db_session.scalars(
        select(AuditLog).where(AuditLog.entity_id == uuid.UUID(run["id"]))
    ).all()
    assert [row.action for row in failed_audits].count("project.setup.fail") == 1

    monkeypatch.setattr(project_setup_service.project_control_repository, "create_wbs_node", original)
    retried = client.post(f"/api/projects/setup-runs/{run['id']}/execute")
    assert retried.status_code == 200, retried.text
    assert retried.json()["status"] == "COMPLETED"
    assert len(db_session.execute(select(Project)).scalars().all()) == 1


def test_concurrent_setup_execution_writes_only_one_completion_audit(client, db_session, monkeypatch):
    """Two stale DRAFT reads must serialize before completion and its audit."""
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from sqlalchemy.orm import Session

    from app.api.routes import projects
    from app.models.user import User
    from app.services import project_setup_service
    from tests.conftest import BOOTSTRAP_ADMIN_EMAIL

    login_admin(client)
    company = create_company(client)
    created = client.post(
        "/api/projects/setup-runs",
        json=_payload(company["id"]),
        headers={"Idempotency-Key": "project-setup-race"},
    )
    assert created.status_code == 201, created.text
    run_id = uuid.UUID(created.json()["id"])
    engine = db_session.get_bind()
    barrier = Barrier(2)
    original_get = project_setup_service.get_run

    def synchronized_unlocked_read(db, identifier):
        row = original_get(db, identifier)
        if row is not None and row.status == "DRAFT":
            barrier.wait(timeout=15)
        return row

    monkeypatch.setattr(project_setup_service, "get_run", synchronized_unlocked_read)

    def invoke(_):
        with Session(engine) as session:
            user = session.scalar(select(User).where(User.email == BOOTSTRAP_ADMIN_EMAIL))
            return projects.execute_setup_run(
                run_id, db=session, user=user, correlation_id="setup-concurrent",
            )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(invoke, range(2)))
    assert [r.status for r in results] == ["COMPLETED", "COMPLETED"]
    assert results[0].project_id == results[1].project_id
    db_session.expire_all()
    projects_created = db_session.scalars(
        select(Project).where(Project.company_id == uuid.UUID(company["id"]))
    ).all()
    assert len(projects_created) == 1
    completion_audits = db_session.scalars(
        select(AuditLog).where(
            AuditLog.entity_id == run_id,
            AuditLog.action == "project.setup.complete",
        )
    ).all()
    assert len(completion_audits) == 1
