"""Atomic, resumable initial Project configuration."""

from sqlalchemy import select

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

    monkeypatch.setattr(project_setup_service.project_control_repository, "create_wbs_node", original)
    retried = client.post(f"/api/projects/setup-runs/{run['id']}/execute")
    assert retried.status_code == 200, retried.text
    assert retried.json()["status"] == "COMPLETED"
    assert len(db_session.execute(select(Project)).scalars().all()) == 1
