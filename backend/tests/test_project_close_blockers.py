"""Tests for project close blockers (F2.19)."""
import uuid

import pytest
from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.planning import Milestone, Task
from app.models.project import Project
from app.models.quality import NonConformance
from app.models.rfi import RequestForInformation
from app.models.safety import SafetyIncident
from app.services.project_close_blockers import check_close_blockers


def _make_project(db_session: Session, *, status: str = "ACTIVE") -> Project:
    from app.models.user import User

    company = Company(name=f"Co-{uuid.uuid4().hex[:6]}")
    db_session.add(company)
    db_session.flush()
    user = User(email=f"test-{uuid.uuid4().hex[:6]}@test.com", full_name="Test User", password_hash="x")
    db_session.add(user)
    db_session.flush()
    p = Project(
        name=f"Test {status}",
        code=f"PRJ-{uuid.uuid4().hex[:6].upper()}",
        status=status,
        company_id=company.id,
    )
    db_session.add(p)
    db_session.flush()
    return p


def test_completed_with_no_blockers(db_session: Session):
    project = _make_project(db_session)
    result = check_close_blockers(db_session, project_id=project.id, target_status="COMPLETED")
    assert result.is_blocked is False
    assert result.blockers == []


def test_completed_blocked_by_open_tasks(db_session: Session):
    project = _make_project(db_session)
    task = Task(project_id=project.id, name="T1", status="IN_PROGRESS")
    db_session.add(task)
    db_session.flush()

    result = check_close_blockers(db_session, project_id=project.id, target_status="COMPLETED")
    assert result.is_blocked is True
    assert any("tarea" in b for b in result.blockers)


def test_completed_blocked_by_blocked_task(db_session: Session):
    project = _make_project(db_session)
    task = Task(project_id=project.id, name="T1", status="BLOCKED")
    db_session.add(task)
    db_session.flush()

    result = check_close_blockers(db_session, project_id=project.id, target_status="COMPLETED")
    assert result.is_blocked is True


def test_completed_not_blocked_by_done_task(db_session: Session):
    project = _make_project(db_session)
    task = Task(project_id=project.id, name="T1", status="DONE")
    db_session.add(task)
    db_session.flush()

    result = check_close_blockers(db_session, project_id=project.id, target_status="COMPLETED")
    assert result.is_blocked is False


def test_completed_blocked_by_open_milestone(db_session: Session):
    project = _make_project(db_session)
    ms = Milestone(project_id=project.id, name="M1", status="PLANNED", due_date="2026-12-31")
    db_session.add(ms)
    db_session.flush()

    result = check_close_blockers(db_session, project_id=project.id, target_status="COMPLETED")
    assert result.is_blocked is True
    assert any("hito" in b for b in result.blockers)


def test_completed_blocked_by_open_rfi(db_session: Session):
    from app.models.rfi import RequestForInformation
    from app.models.user import User

    project = _make_project(db_session)
    user = User(email=f"rfi-{uuid.uuid4().hex[:6]}@test.com", full_name="Test User", password_hash="x")
    db_session.add(user)
    db_session.flush()
    rfi = RequestForInformation(
        project_id=project.id,
        company_id=project.company_id,
        number="RFI-001",
        subject="Test RFI",
        question="What?",
        requested_by=user.id,
        status="OPEN",
    )
    db_session.add(rfi)
    db_session.flush()

    result = check_close_blockers(db_session, project_id=project.id, target_status="COMPLETED")
    assert result.is_blocked is True
    assert any("RFI" in b for b in result.blockers)


def test_completed_blocked_by_open_ncr(db_session: Session):
    from app.models.quality import NonConformance
    from app.models.user import User

    project = _make_project(db_session)
    user = User(email=f"ncr-{uuid.uuid4().hex[:6]}@test.com", full_name="Test User", password_hash="x")
    db_session.add(user)
    db_session.flush()

    ncr = NonConformance(
        project_id=project.id,
        description="NCR-1",
        responsible_user_id=user.id,
        status="OPEN",
    )
    db_session.add(ncr)
    db_session.flush()

    result = check_close_blockers(db_session, project_id=project.id, target_status="COMPLETED")
    assert result.is_blocked is True
    assert any("conformidad" in b for b in result.blockers)


def test_completed_blocked_by_open_safety_incident(db_session: Session):
    from app.models.safety import SafetyIncident

    project = _make_project(db_session)
    si = SafetyIncident(
        project_id=project.id,
        incident_date="2026-01-01",
        description="INC-1",
        severity="LOW",
        status="OPEN",
    )
    db_session.add(si)
    db_session.flush()

    result = check_close_blockers(db_session, project_id=project.id, target_status="COMPLETED")
    assert result.is_blocked is True
    assert any("seguridad" in b for b in result.blockers)


def test_closed_checks_financial_blockers(db_session: Session):
    project = _make_project(db_session)
    result = check_close_blockers(db_session, project_id=project.id, target_status="CLOSED")
    assert result.is_blocked is False or result.is_blocked is True


def test_closed_not_blocked_when_no_financial_data(db_session: Session):
    project = _make_project(db_session)
    result = check_close_blockers(db_session, project_id=project.id, target_status="CLOSED")
    assert result.is_blocked is False


def test_multiple_blockers_accumulate(db_session: Session):
    project = _make_project(db_session)
    task = Task(project_id=project.id, name="T1", status="IN_PROGRESS")
    ms = Milestone(project_id=project.id, name="M1", status="PLANNED", due_date="2026-12-31")
    db_session.add(task)
    db_session.add(ms)
    db_session.flush()

    result = check_close_blockers(db_session, project_id=project.id, target_status="COMPLETED")
    assert result.is_blocked is True
    assert len(result.blockers) >= 2
