import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.errors import InvalidFinancialReferenceError, NotFoundError
from app.models.chart_of_accounts import Account, ChartOfAccount


def get_chart_of_account_for_company(db: Session, company_id: uuid.UUID) -> ChartOfAccount | None:
    stmt = select(ChartOfAccount).where(ChartOfAccount.company_id == company_id)
    return db.execute(stmt).scalar_one_or_none()


def list_accounts_for_company(db: Session, company_id: uuid.UUID) -> list[Account]:
    chart = get_chart_of_account_for_company(db, company_id)
    if chart is None:
        return []
    stmt = select(Account).where(Account.chart_of_account_id == chart.id).order_by(Account.code)
    return list(db.execute(stmt).scalars())


def create_account(
    db: Session,
    *,
    company_id: uuid.UUID,
    code: str,
    name: str,
    account_type: str,
    parent_id: uuid.UUID | None = None,
) -> Account:
    chart = get_chart_of_account_for_company(db, company_id)
    if chart is None:
        raise NotFoundError(f"La company {company_id} no tiene chart of accounts")
    if parent_id is not None:
        parent = db.get(Account, parent_id)
        if parent is None or parent.chart_of_account_id != chart.id:
            raise InvalidFinancialReferenceError(
                "parent_id debe pertenecer al catálogo contable de la compañía propietaria"
            )
    account = Account(
        chart_of_account_id=chart.id,
        code=code,
        name=name,
        account_type=account_type,
        parent_id=parent_id,
    )
    db.add(account)
    db.flush()
    return account


def get_by_id(db: Session, account_id: uuid.UUID) -> Account | None:
    return db.get(Account, account_id)


def update_cash_flow_activity(db: Session, *, account: Account, cash_flow_activity: str | None) -> Account:
    account.cash_flow_activity = cash_flow_activity
    db.flush()
    return account
