import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.errors import InvalidCommercialStateError
from app.models.crm import Customer, Lead, Opportunity, Quotation, SalesContract
from app.repositories import crm_repository
from app.services import ar_service
from app.services.financial_validation_service import (
    assert_customer_belongs_to_company,
    assert_project_belongs_to_company,
)

"""Comercial (orden maestra §72-76): Lead -> Opportunity -> Customer/
Quotation -> SalesContract -> AR invoice. `bill_sales_contract` es el unico
punto de entrada al modulo AR real de Track A (Financial Core) -- llama
directamente a `ar_service.create_customer_invoice` (mismo patron que
`asset_service` llama a `posting_service` directamente dentro del mismo
proceso, sin una segunda API HTTP interna). Este servicio nunca escribe en
`customer_invoices`/`customer_receipts` -- esas tablas son propiedad
exclusiva de Track A."""


def convert_lead(db: Session, *, lead_id: uuid.UUID, commit: bool = True) -> tuple[Lead, Customer, Opportunity]:
    """Idempotente: convertir el mismo lead dos veces devuelve el mismo
    Customer/Opportunity y NO crea una segunda fila (INV-CRM-idempotencia).
    El lock FOR UPDATE serializa intentos concurrentes sobre el mismo lead."""
    lead = db.execute(select(Lead).where(Lead.id == lead_id).with_for_update()).scalar_one_or_none()
    if lead is None:
        raise ValueError(f"Lead {lead_id} no existe")

    if lead.status == "CONVERTED":
        customer = db.get(Customer, lead.converted_customer_id)
        opportunity = db.execute(
            select(Opportunity).where(Opportunity.lead_id == lead.id)
        ).scalar_one()
        return lead, customer, opportunity

    if lead.status == "LOST":
        raise InvalidCommercialStateError(
            f"No se puede convertir un lead en estado {lead.status}"
        )

    customer = Customer(
        company_id=lead.company_id,
        legal_name=lead.name,
        contact_name=lead.contact_name,
        email=lead.email,
        phone=lead.phone,
    )
    db.add(customer)
    db.flush()

    opportunity = Opportunity(
        company_id=lead.company_id,
        lead_id=lead.id,
        customer_id=customer.id,
        name=f"Oportunidad - {lead.name}",
        stage="OPEN",
    )
    db.add(opportunity)
    db.flush()

    lead.status = "CONVERTED"
    lead.converted_customer_id = customer.id

    if commit:
        db.commit()
        db.refresh(lead)
        db.refresh(customer)
        db.refresh(opportunity)
    else:
        db.flush()
    return lead, customer, opportunity


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
    valid_until: date | None,
    description: str | None,
    commit: bool = True,
) -> Quotation:
    opportunity = db.get(Opportunity, opportunity_id)
    if opportunity is None or opportunity.company_id != company_id:
        raise InvalidCommercialStateError(
            "opportunity_id debe pertenecer a la compañía propietaria"
        )
    assert_customer_belongs_to_company(db, customer_id=customer_id, company_id=company_id)
    if opportunity.customer_id != customer_id:
        raise InvalidCommercialStateError(
            "customer_id debe coincidir con el cliente de la oportunidad"
        )
    assert_project_belongs_to_company(db, project_id=project_id, company_id=company_id)

    quotation = crm_repository.create_quotation(
        db,
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
    if commit:
        db.commit()
        db.refresh(quotation)
    else:
        db.flush()
    return quotation


def accept_quotation(db: Session, *, quotation_id: uuid.UUID, commit: bool = True) -> Quotation:
    quotation = db.execute(
        select(Quotation).where(Quotation.id == quotation_id).with_for_update()
    ).scalar_one_or_none()
    if quotation is None:
        raise ValueError(f"Quotation {quotation_id} no existe")
    if quotation.status not in ("DRAFT", "SENT"):
        raise InvalidCommercialStateError(
            f"No se puede aceptar una cotización en estado {quotation.status}"
        )
    quotation.status = "ACCEPTED"
    if commit:
        db.commit()
        db.refresh(quotation)
    else:
        db.flush()
    return quotation


def convert_quotation_to_sales_contract(
    db: Session, *, quotation_id: uuid.UUID, contract_number: str, start_date: date, commit: bool = True,
) -> SalesContract:
    """Solo una Quotation ACCEPTED puede convertirse; preserva amount,
    company, customer y project tal cual (orden maestra §75)."""
    quotation = db.execute(
        select(Quotation).where(Quotation.id == quotation_id).with_for_update()
    ).scalar_one_or_none()
    if quotation is None:
        raise ValueError(f"Quotation {quotation_id} no existe")
    if quotation.status != "ACCEPTED":
        raise InvalidCommercialStateError(
            f"Solo una cotización ACCEPTED puede convertirse a contrato (estado actual: {quotation.status})"
        )

    existing = db.execute(
        select(SalesContract).where(SalesContract.quotation_id == quotation.id)
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    scope = "PROJECT" if quotation.project_id is not None else "GENERAL"
    contract = SalesContract(
        company_id=quotation.company_id,
        quotation_id=quotation.id,
        customer_id=quotation.customer_id,
        project_id=quotation.project_id,
        contract_number=contract_number,
        scope=scope,
        amount=quotation.amount,
        currency_code=quotation.currency_code,
        start_date=start_date,
        status="ACTIVE",
    )
    db.add(contract)
    db.flush()

    if commit:
        db.commit()
        db.refresh(contract)
    else:
        db.flush()
    return contract


def bill_sales_contract(
    db: Session,
    *,
    sales_contract_id: uuid.UUID,
    invoice_number: str,
    invoice_date: date,
    due_date: date,
    revenue_account_id: uuid.UUID,
    receivable_account_id: uuid.UUID,
    description: str | None = None,
    commit: bool = True,
) -> SalesContract:
    """Factura un SalesContract creando UNA factura real de AR a traves del
    ar_service de Track A -- nunca duplica Accounts Receivable. No produce
    ningun movimiento de tesoreria (eso solo ocurre cuando la factura AR se
    cobra via ar_service.collect_customer_receipt, fuera del alcance de este
    servicio)."""
    contract = db.execute(
        select(SalesContract).where(SalesContract.id == sales_contract_id).with_for_update()
    ).scalar_one_or_none()
    if contract is None:
        raise ValueError(f"SalesContract {sales_contract_id} no existe")
    if contract.status != "ACTIVE":
        raise InvalidCommercialStateError(
            f"Solo un contrato ACTIVE puede facturarse (estado actual: {contract.status})"
        )

    invoice = ar_service.create_customer_invoice(
        db,
        company_id=contract.company_id,
        customer_id=contract.customer_id,
        invoice_number=invoice_number,
        scope=contract.scope,
        project_id=contract.project_id,
        revenue_account_id=revenue_account_id,
        receivable_account_id=receivable_account_id,
        currency_code=contract.currency_code,
        amount=contract.amount,
        invoice_date=invoice_date,
        due_date=due_date,
        description=description or f"Facturación contrato {contract.contract_number}",
        commit=False,
    )

    contract.status = "BILLED"
    contract.customer_invoice_id = invoice.id
    if commit:
        db.commit()
        db.refresh(contract)
        db.refresh(invoice)
    else:
        db.flush()
    return contract
