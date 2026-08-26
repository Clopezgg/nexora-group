import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.errors import NotFoundError
from app.models.chart_of_accounts import ChartOfAccount
from app.models.company import Company


def list_companies(db: Session, *, company_ids: list[uuid.UUID] | None = None) -> list[Company]:
    stmt = select(Company).order_by(Company.name)
    if company_ids is not None:
        stmt = stmt.where(Company.id.in_(company_ids))
    return list(db.execute(stmt).scalars())


def get_by_id(db: Session, company_id: uuid.UUID) -> Company | None:
    return db.get(Company, company_id)


def create_company(
    db: Session,
    *,
    name: str,
    code: str | None,
    legal_name: str | None,
    functional_currency_code: str | None,
    country: str | None,
    fiscal_id: str | None,
) -> Company:
    company = Company(
        name=name,
        code=code,
        legal_name=legal_name,
        functional_currency_code=functional_currency_code,
        country=country,
        fiscal_id=fiscal_id,
    )
    db.add(company)
    db.flush()
    # Digital Core: toda company necesita su propio chart of accounts desde
    # el día uno (una sola tabla por company, ver ChartOfAccount.company_id
    # unique). Se crea vacío; las Account individuales se agregan aparte.
    db.add(ChartOfAccount(company_id=company.id, name=f"Catálogo contable — {name}"))
    db.flush()
    return company


def update_company(
    db: Session,
    *,
    company: Company,
    legal_name: str | None = None,
    fiscal_id: str | None = None,
) -> Company:
    """Solo legal_name/fiscal_id son editables aquí -- code y
    functional_currency_code son inmutables post-creación (CLAUDE.md)."""
    if legal_name is not None:
        company.legal_name = legal_name
    if fiscal_id is not None:
        company.fiscal_id = fiscal_id
    db.flush()
    return company
