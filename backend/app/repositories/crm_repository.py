import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.crm import Customer, Lead, Opportunity, Quotation, SalesContract

# CRUD simple (sin invariantes de negocio) para el dominio comercial. Las
# transiciones de estado (convertir lead, aceptar/convertir cotizacion,
# facturar contrato) viven en app/services/crm_service.py -- mismo patron
# que repositories/supplier_repository.py vs. app/services/ap_service.py.


def create_customer(
    db: Session,
    *,
    company_id: uuid.UUID,
    legal_name: str,
    trade_name: str | None = None,
    tax_id: str | None = None,
    contact_name: str | None = None,
    email: str | None = None,
    phone: str | None = None,
    address: str | None = None,
) -> Customer:
    customer = Customer(
        company_id=company_id,
        legal_name=legal_name,
        trade_name=trade_name,
        tax_id=tax_id,
        contact_name=contact_name,
        email=email,
        phone=phone,
        address=address,
    )
    db.add(customer)
    db.flush()
    return customer


def list_customers(db: Session, *, company_id: uuid.UUID) -> list[Customer]:
    stmt = select(Customer).where(Customer.company_id == company_id).order_by(Customer.legal_name)
    return list(db.execute(stmt).scalars())


def get_customer(db: Session, customer_id: uuid.UUID) -> Customer | None:
    return db.get(Customer, customer_id)


def create_lead(
    db: Session,
    *,
    company_id: uuid.UUID,
    name: str,
    contact_name: str | None = None,
    email: str | None = None,
    phone: str | None = None,
    source: str | None = None,
) -> Lead:
    lead = Lead(
        company_id=company_id,
        name=name,
        contact_name=contact_name,
        email=email,
        phone=phone,
        source=source,
    )
    db.add(lead)
    db.flush()
    return lead


def list_leads(db: Session, *, company_id: uuid.UUID) -> list[Lead]:
    stmt = select(Lead).where(Lead.company_id == company_id).order_by(Lead.created_at.desc())
    return list(db.execute(stmt).scalars())


def get_lead(db: Session, lead_id: uuid.UUID) -> Lead | None:
    return db.get(Lead, lead_id)


def list_opportunities(db: Session, *, company_id: uuid.UUID) -> list[Opportunity]:
    stmt = (
        select(Opportunity)
        .where(Opportunity.company_id == company_id)
        .order_by(Opportunity.created_at.desc())
    )
    return list(db.execute(stmt).scalars())


def get_opportunity(db: Session, opportunity_id: uuid.UUID) -> Opportunity | None:
    return db.get(Opportunity, opportunity_id)


def create_quotation(
    db: Session,
    *,
    company_id: uuid.UUID,
    opportunity_id: uuid.UUID,
    customer_id: uuid.UUID,
    project_id: uuid.UUID | None,
    quotation_number: str,
    amount: Decimal,
    currency_code: str,
    valid_until: date | None = None,
    description: str | None = None,
) -> Quotation:
    quotation = Quotation(
        company_id=company_id,
        opportunity_id=opportunity_id,
        customer_id=customer_id,
        project_id=project_id,
        quotation_number=quotation_number,
        amount=amount,
        currency_code=currency_code,
        valid_until=valid_until,
        description=description,
    )
    db.add(quotation)
    db.flush()
    return quotation


def list_quotations(db: Session, *, company_id: uuid.UUID) -> list[Quotation]:
    stmt = (
        select(Quotation).where(Quotation.company_id == company_id).order_by(Quotation.created_at.desc())
    )
    return list(db.execute(stmt).scalars())


def get_quotation(db: Session, quotation_id: uuid.UUID) -> Quotation | None:
    return db.get(Quotation, quotation_id)


def list_sales_contracts(db: Session, *, company_id: uuid.UUID) -> list[SalesContract]:
    stmt = (
        select(SalesContract)
        .where(SalesContract.company_id == company_id)
        .order_by(SalesContract.created_at.desc())
    )
    return list(db.execute(stmt).scalars())


def get_sales_contract(db: Session, sales_contract_id: uuid.UUID) -> SalesContract | None:
    return db.get(SalesContract, sales_contract_id)
