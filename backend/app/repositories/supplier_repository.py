import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.errors import InvalidFinancialReferenceError
from app.models.supplier import Supplier, SupplierContract


def list_suppliers(db: Session, *, company_id: uuid.UUID) -> list[Supplier]:
    stmt = select(Supplier).where(Supplier.company_id == company_id).order_by(Supplier.legal_name)
    return list(db.execute(stmt).scalars())


def get_supplier(db: Session, supplier_id: uuid.UUID) -> Supplier | None:
    return db.get(Supplier, supplier_id)


def create_supplier(
    db: Session,
    *,
    company_id: uuid.UUID,
    legal_name: str,
    trade_name: str | None,
    tax_id: str | None,
    contact_name: str | None,
    email: str | None,
    phone: str | None,
    address: str | None,
    classification: str | None,
    payment_terms: str | None,
    banking_details: dict | None,
) -> Supplier:
    supplier = Supplier(
        company_id=company_id,
        legal_name=legal_name,
        trade_name=trade_name,
        tax_id=tax_id,
        contact_name=contact_name,
        email=email,
        phone=phone,
        address=address,
        classification=classification,
        payment_terms=payment_terms,
        banking_details=banking_details,
    )
    db.add(supplier)
    db.flush()
    return supplier


def list_contracts(
    db: Session, *, company_id: uuid.UUID, category: str | None = None
) -> list[SupplierContract]:
    stmt = (
        select(SupplierContract)
        .where(SupplierContract.company_id == company_id)
        .order_by(SupplierContract.contract_number)
    )
    if category:
        stmt = stmt.where(SupplierContract.contract_category == category)
    return list(db.execute(stmt).scalars())


def create_contract(
    db: Session,
    *,
    company_id: uuid.UUID,
    supplier_id: uuid.UUID,
    project_id: uuid.UUID | None,
    contract_number: str,
    contract_category: str = "OTHER",
    scope_description: str | None,
    value,
    currency_code: str,
    start_date,
    end_date,
    advance_percentage,
    retention_percentage,
    payment_terms: str | None,
) -> SupplierContract:
    existing = db.execute(
        select(SupplierContract.id).where(
            SupplierContract.company_id == company_id,
            SupplierContract.contract_number == contract_number,
        )
    ).first()
    if existing is not None:
        raise InvalidFinancialReferenceError(
            f"Ya existe un contrato con el número {contract_number!r} en esta compañía"
        )
    contract = SupplierContract(
        company_id=company_id,
        supplier_id=supplier_id,
        project_id=project_id,
        contract_number=contract_number,
        contract_category=contract_category,
        scope_description=scope_description,
        value=value,
        currency_code=currency_code,
        start_date=start_date,
        end_date=end_date,
        advance_percentage=advance_percentage,
        retention_percentage=retention_percentage,
        payment_terms=payment_terms,
    )
    db.add(contract)
    db.flush()
    return contract
