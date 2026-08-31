import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

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
    db.add(ChartOfAccount(company_id=company.id, name=f"Catálogo contable — {name}"))
    db.flush()
    return company


def update_company(
    db: Session,
    *,
    company: Company,
    name: str | None = None,
    code: str | None = None,
    legal_name: str | None = None,
    functional_currency_code: str | None = None,
    country: str | None = None,
    fiscal_id: str | None = None,
    voucher_payer_name: str | None = None,
    voucher_approver_name: str | None = None,
) -> Company:
    if name is not None:
        company.name = name.strip()
    if code is not None:
        normalized_code = code.strip()
        if company.code is not None and normalized_code != company.code:
            raise ValueError("El código de compañía ya fue asignado y es inmutable")
        company.code = normalized_code
    if functional_currency_code is not None:
        normalized_currency = functional_currency_code.upper().strip()
        if (
            company.functional_currency_code is not None
            and normalized_currency != company.functional_currency_code
        ):
            raise ValueError("La moneda funcional ya fue asignada y es inmutable")
        company.functional_currency_code = normalized_currency
    if legal_name is not None:
        company.legal_name = legal_name.strip() or None
    if country is not None:
        company.country = country.upper().strip() or None
    if fiscal_id is not None:
        company.fiscal_id = fiscal_id.strip() or None
    if voucher_payer_name is not None:
        normalized_payer = voucher_payer_name.strip()
        if company.voucher_payer_name and normalized_payer != company.voucher_payer_name:
            raise ValueError(
                "El pagador de comprobantes ya fue asignado y es inmutable"
            )
        company.voucher_payer_name = normalized_payer or None
    if voucher_approver_name is not None:
        company.voucher_approver_name = voucher_approver_name.strip() or None
    db.flush()
    return company
