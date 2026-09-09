"""Independent PostgreSQL sessions execute one logical setup exactly once."""

import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.budget import Budget
from app.models.permission import UserProjectAccess
from app.models.project import Project
from app.models.project_setup import ProjectSetupRun
from app.models.wbs import WBSNode
from app.services import project_setup_service
from tests.helpers import create_company, login_admin
from tests.test_project_setup_workflow import _payload


def test_two_stale_draft_executors_create_one_complete_project(client, db_session):
    login_admin(client)
    company = create_company(client)
    response = client.post(
        "/api/projects/setup-runs",
        json=_payload(company["id"]),
        headers={"Idempotency-Key": "concurrent-setup"},
    )
    assert response.status_code == 201, response.text
    run_id = uuid.UUID(response.json()["id"])
    engine = db_session.get_bind()
    barrier = Barrier(2)

    def execute(number):
        with Session(engine) as session:
            run = session.get(ProjectSetupRun, run_id)
            assert run.status == "DRAFT"
            barrier.wait(timeout=10)
            result = project_setup_service.execute(
                session, run=run, correlation_id=f"race-{number}"
            )
            session.commit()
            return result.project_id, result.status

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(execute, [1, 2]))
    assert results[0] == results[1]
    project_id, status = results[0]
    assert status == "COMPLETED"
    db_session.expire_all()
    assert db_session.get(Project, project_id).status == "ACTIVE"
    for model in (Project, WBSNode, Budget, UserProjectAccess):
        assert db_session.scalar(select(func.count()).select_from(model)) == 1
    assert db_session.get(ProjectSetupRun, run_id).project_id == project_id
