import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.tax import TaxCode


def create_tax_code(
    db: Session, *, company_id: uuid.UUID, code: str, name: str, rate_percent: Decimal
) -> TaxCode:
    tax_code = TaxCode(company_id=company_id, code=code, name=name, rate_percent=rate_percent)
    db.add(tax_code)
    db.flush()
    return tax_code


def get_tax_code(db: Session, tax_code_id: uuid.UUID) -> TaxCode | None:
    return db.get(TaxCode, tax_code_id)


def get_tax_code_by_code(db: Session, *, company_id: uuid.UUID, code: str) -> TaxCode | None:
    stmt = select(TaxCode).where(TaxCode.company_id == company_id, TaxCode.code == code)
    return db.execute(stmt).scalar_one_or_none()


def list_tax_codes(db: Session, *, company_id: uuid.UUID) -> list[TaxCode]:
    stmt = select(TaxCode).where(TaxCode.company_id == company_id).order_by(TaxCode.code)
    return list(db.execute(stmt).scalars())
