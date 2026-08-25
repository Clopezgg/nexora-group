import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.repositories import crm_repository
from app.schemas.crm import (
    CustomerCreateRequest,
    CustomerResponse,
    LeadConversionResponse,
    LeadCreateRequest,
    LeadResponse,
    OpportunityResponse,
    QuotationCreateRequest,
    QuotationResponse,
    SalesContractBillRequest,
    SalesContractConvertRequest,
    SalesContractResponse,
)
from app.services import crm_service
from app.services.permission_service import assert_company_access, require_permission

router = APIRouter(prefix="/crm", tags=["crm"])


def _resolve_lead(db: Session, lead_id: uuid.UUID):
    lead = crm_repository.get_lead(db, lead_id)
    if lead is None:
        raise ValueError(f"Lead {lead_id} no existe")
    return lead


def _resolve_quotation(db: Session, quotation_id: uuid.UUID):
    quotation = crm_repository.get_quotation(db, quotation_id)
    if quotation is None:
        raise ValueError(f"Quotation {quotation_id} no existe")
    return quotation


def _resolve_sales_contract(db: Session, sales_contract_id: uuid.UUID):
    contract = crm_repository.get_sales_contract(db, sales_contract_id)
    if contract is None:
        raise ValueError(f"SalesContract {sales_contract_id} no existe")
    return contract


# ---------------------------------------------------------------- Customer


@router.post("/customers", response_model=CustomerResponse, status_code=201)
def create_customer(
    payload: CustomerCreateRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("crm.customer", "create")),
) -> CustomerResponse:
    assert_company_access(
        db, user_id=user.id, resource="crm.customer", action="create", company_id=payload.company_id
    )
    customer = crm_repository.create_customer(
        db,
        company_id=payload.company_id,
        legal_name=payload.legal_name,
        trade_name=payload.trade_name,
        tax_id=payload.tax_id,
        contact_name=payload.contact_name,
        email=payload.email,
        phone=payload.phone,
        address=payload.address,
    )
    db.commit()
    db.refresh(customer)
    return CustomerResponse.model_validate(customer, from_attributes=True)


@router.get("/customers", response_model=list[CustomerResponse])
def list_customers(
    company_id: uuid.UUID = Query(alias="companyId"),
    db: Session = Depends(get_db),
    user=Depends(require_permission("crm.customer", "read")),
) -> list[CustomerResponse]:
    assert_company_access(
        db, user_id=user.id, resource="crm.customer", action="read", company_id=company_id
    )
    return [
        CustomerResponse.model_validate(c, from_attributes=True)
        for c in crm_repository.list_customers(db, company_id=company_id)
    ]


# --------------------------------------------------------------------- Lead


@router.post("/leads", response_model=LeadResponse, status_code=201)
def create_lead(
    payload: LeadCreateRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("crm.lead", "create")),
) -> LeadResponse:
    assert_company_access(
        db, user_id=user.id, resource="crm.lead", action="create", company_id=payload.company_id
    )
    lead = crm_repository.create_lead(
        db,
        company_id=payload.company_id,
        name=payload.name,
        contact_name=payload.contact_name,
        email=payload.email,
        phone=payload.phone,
        source=payload.source,
    )
    db.commit()
    db.refresh(lead)
    return LeadResponse.model_validate(lead, from_attributes=True)


@router.get("/leads", response_model=list[LeadResponse])
def list_leads(
    company_id: uuid.UUID = Query(alias="companyId"),
    db: Session = Depends(get_db),
    user=Depends(require_permission("crm.lead", "read")),
) -> list[LeadResponse]:
    assert_company_access(db, user_id=user.id, resource="crm.lead", action="read", company_id=company_id)
    return [
        LeadResponse.model_validate(lead, from_attributes=True)
        for lead in crm_repository.list_leads(db, company_id=company_id)
    ]


@router.post("/leads/{lead_id}/convert", response_model=LeadConversionResponse)
def convert_lead(
    lead_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("crm.lead", "convert")),
) -> LeadConversionResponse:
    lead = _resolve_lead(db, lead_id)
    assert_company_access(
        db, user_id=user.id, resource="crm.lead", action="convert", company_id=lead.company_id
    )
    lead, customer, opportunity = crm_service.convert_lead(db, lead_id=lead_id)
    return LeadConversionResponse(
        lead=LeadResponse.model_validate(lead, from_attributes=True),
        customer=CustomerResponse.model_validate(customer, from_attributes=True),
        opportunity=OpportunityResponse.model_validate(opportunity, from_attributes=True),
    )


# ------------------------------------------------------------- Opportunity


@router.get("/opportunities", response_model=list[OpportunityResponse])
def list_opportunities(
    company_id: uuid.UUID = Query(alias="companyId"),
    db: Session = Depends(get_db),
    user=Depends(require_permission("crm.opportunity", "read")),
) -> list[OpportunityResponse]:
    assert_company_access(
        db, user_id=user.id, resource="crm.opportunity", action="read", company_id=company_id
    )
    return [
        OpportunityResponse.model_validate(o, from_attributes=True)
        for o in crm_repository.list_opportunities(db, company_id=company_id)
    ]


# --------------------------------------------------------------- Quotation


@router.post("/quotations", response_model=QuotationResponse, status_code=201)
def create_quotation(
    payload: QuotationCreateRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("crm.quotation", "create")),
) -> QuotationResponse:
    assert_company_access(
        db, user_id=user.id, resource="crm.quotation", action="create", company_id=payload.company_id
    )
    quotation = crm_service.create_quotation(
        db,
        company_id=payload.company_id,
        opportunity_id=payload.opportunity_id,
        customer_id=payload.customer_id,
        project_id=payload.project_id,
        quotation_number=payload.quotation_number,
        amount=payload.amount,
        currency_code=payload.currency_code,
        valid_until=payload.valid_until,
        description=payload.description,
    )
    return QuotationResponse.model_validate(quotation, from_attributes=True)


@router.get("/quotations", response_model=list[QuotationResponse])
def list_quotations(
    company_id: uuid.UUID = Query(alias="companyId"),
    db: Session = Depends(get_db),
    user=Depends(require_permission("crm.quotation", "read")),
) -> list[QuotationResponse]:
    assert_company_access(
        db, user_id=user.id, resource="crm.quotation", action="read", company_id=company_id
    )
    return [
        QuotationResponse.model_validate(q, from_attributes=True)
        for q in crm_repository.list_quotations(db, company_id=company_id)
    ]


@router.post("/quotations/{quotation_id}/accept", response_model=QuotationResponse)
def accept_quotation(
    quotation_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("crm.quotation", "accept")),
) -> QuotationResponse:
    quotation = _resolve_quotation(db, quotation_id)
    assert_company_access(
        db, user_id=user.id, resource="crm.quotation", action="accept", company_id=quotation.company_id
    )
    quotation = crm_service.accept_quotation(db, quotation_id=quotation_id)
    return QuotationResponse.model_validate(quotation, from_attributes=True)


@router.post("/quotations/{quotation_id}/convert", response_model=SalesContractResponse, status_code=201)
def convert_quotation(
    quotation_id: uuid.UUID,
    payload: SalesContractConvertRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("crm.quotation", "convert")),
) -> SalesContractResponse:
    quotation = _resolve_quotation(db, quotation_id)
    assert_company_access(
        db, user_id=user.id, resource="crm.quotation", action="convert", company_id=quotation.company_id
    )
    contract = crm_service.convert_quotation_to_sales_contract(
        db,
        quotation_id=quotation_id,
        contract_number=payload.contract_number,
        start_date=payload.start_date,
    )
    return SalesContractResponse.model_validate(contract, from_attributes=True)


# ---------------------------------------------------------- Sales Contract


@router.get("/sales-contracts", response_model=list[SalesContractResponse])
def list_sales_contracts(
    company_id: uuid.UUID = Query(alias="companyId"),
    db: Session = Depends(get_db),
    user=Depends(require_permission("crm.sales_contract", "read")),
) -> list[SalesContractResponse]:
    assert_company_access(
        db, user_id=user.id, resource="crm.sales_contract", action="read", company_id=company_id
    )
    return [
        SalesContractResponse.model_validate(c, from_attributes=True)
        for c in crm_repository.list_sales_contracts(db, company_id=company_id)
    ]


@router.post("/sales-contracts/{sales_contract_id}/bill", response_model=SalesContractResponse, status_code=201)
def bill_sales_contract(
    sales_contract_id: uuid.UUID,
    payload: SalesContractBillRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("crm.sales_contract", "bill")),
) -> SalesContractResponse:
    contract = _resolve_sales_contract(db, sales_contract_id)
    assert_company_access(
        db, user_id=user.id, resource="crm.sales_contract", action="bill", company_id=contract.company_id
    )
    contract = crm_service.bill_sales_contract(
        db,
        sales_contract_id=sales_contract_id,
        invoice_number=payload.invoice_number,
        invoice_date=payload.invoice_date,
        due_date=payload.due_date,
        revenue_account_id=payload.revenue_account_id,
        receivable_account_id=payload.receivable_account_id,
        description=payload.description,
    )
    return SalesContractResponse.model_validate(contract, from_attributes=True)
