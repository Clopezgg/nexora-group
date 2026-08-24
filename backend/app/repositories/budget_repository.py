import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.budget import Budget, BudgetLine


def get_active_budget(db: Session, project_id: uuid.UUID) -> Budget | None:
    stmt = select(Budget).where(Budget.project_id == project_id, Budget.status == "ACTIVE")
    return db.execute(stmt).scalars().first()


def get_baseline_budget(db: Session, project_id: uuid.UUID) -> Budget | None:
    stmt = select(Budget).where(Budget.project_id == project_id, Budget.version == "BASELINE")
    return db.execute(stmt).scalars().first()


def list_budgets_for_project(db: Session, project_id: uuid.UUID) -> list[Budget]:
    stmt = select(Budget).where(Budget.project_id == project_id).order_by(Budget.created_at)
    return list(db.execute(stmt).scalars())


def list_lines(db: Session, budget_id: uuid.UUID) -> list[BudgetLine]:
    stmt = select(BudgetLine).where(BudgetLine.budget_id == budget_id)
    return list(db.execute(stmt).scalars())


def sum_authorized(db: Session, budget_id: uuid.UUID) -> Decimal:
    lines = list_lines(db, budget_id)
    return sum((line.authorized_amount for line in lines), Decimal("0"))
