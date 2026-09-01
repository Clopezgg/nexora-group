"""Project Contract Payment Control — API (orden maestra final §6, §17-§23).

Subledger contractual. NO contabiliza; el pago sigue pasando por
`/ap/supplier-invoices/{id}/payments`.
"""

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.deps_correlation import get_correlation_id
from app.domain.errors import InvalidFinancialReferenceError, OverpaymentError
from app.models.contract_payment import ContractPaymentSchedule
from app.models.supplier import SupplierContract
from app.schemas.contract_payment import (
    ContractSummaryResponse,
    FifoPreviewItem,
    FifoPreviewRequest,
    InstallmentResponse,
    ScheduleCreateRequest,
    ScheduleResponse,
)
from app.services import audit_service, contract_payment_service as cps
from app.services.permission_service import assert_company_access, require_permission

router = APIRouter(prefix="/contract-payments", tags=["contract-payments"])


def _schedule_or_404(db: Session, schedule_id: uuid.UUID) -> ContractPaymentSchedule:
    schedule = db.get(ContractPaymentSchedule, schedule_id)
    if schedule is None:
        raise HTTPException(status_code=404, detail="Plan de pagos no encontrado")
    return schedule


def _installments_payload(db: Session, schedule_id: uuid.UUID) -> list[InstallmentResponse]:
    return [
        InstallmentResponse(
            installment_id=s.installment_id,
            sequence=s.sequence,
            period_year=s.period_year,
            period_month=s.period_month,
            period_label=s.period_label,
            due_date=s.due_date,
            scheduled_amount=s.scheduled_amount,
            retention_amount=s.retention_amount,
            net_due=s.net_due,
            paid=s.paid,
            remaining=s.remaining,
            status=s.status,
        )
        for s in cps.installment_summaries(db, schedule_id=schedule_id)
    ]


def _schedule_payload(db: Session, schedule: ContractPaymentSchedule) -> ScheduleResponse:
    return ScheduleResponse(
        id=schedule.id,
        company_id=schedule.company_id,
        supplier_contract_id=schedule.supplier_contract_id,
        project_id=schedule.project_id,
        currency_code=schedule.currency_code,
        schedule_type=schedule.schedule_type,
        total_scheduled=schedule.total_scheduled,
        status=schedule.status,
        installments=_installments_payload(db, schedule.id),
    )


@router.post("/schedules", response_model=ScheduleResponse, status_code=201)
def create_schedule(
    payload: ScheduleCreateRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("contract.payment_schedule", "manage")),
    correlation_id: str = Depends(get_correlation_id),
) -> ScheduleResponse:
    contract = db.get(SupplierContract, payload.supplier_contract_id)
    if contract is None:
        raise HTTPException(status_code=404, detail="Contrato no encontrado")
    assert_company_access(
        db,
        user_id=user.id,
        resource="contract.payment_schedule",
        action="manage",
        company_id=contract.company_id,
    )

    if payload.installments:
        rows = [i.model_dump() for i in payload.installments]
    elif payload.start_period and payload.months and payload.monthly_amount:
        rows = cps.build_monthly_installments(
            start_period=payload.start_period,
            count=payload.months,
            monthly_amount=payload.monthly_amount,
            total_value=contract.value,
            retention_percentage=contract.retention_percentage,
        )
    else:
        raise HTTPException(
            status_code=422,
            detail="Indica `installments` o (`startPeriod` + `months` + `monthlyAmount`).",
        )

    try:
        schedule = cps.create_schedule(
            db,
            supplier_contract_id=contract.id,
            schedule_type=payload.schedule_type,
            installments=rows,
            commit=False,
        )
    except OverpaymentError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except InvalidFinancialReferenceError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    audit_service.record(
        db,
        actor_user_id=user.id,
        action="contract.payment_schedule.create",
        entity_type="contract.payment_schedule",
        entity_id=schedule.id,
        company_id=schedule.company_id,
        project_id=schedule.project_id,
        before=None,
        after={
            "contractNumber": contract.contract_number,
            "totalScheduled": str(schedule.total_scheduled),
            "installments": len(rows),
        },
        correlation_id=correlation_id,
    )
    db.commit()
    db.refresh(schedule)
    return _schedule_payload(db, schedule)


@router.get("/schedules", response_model=list[ScheduleResponse])
def list_schedules(
    company_id: uuid.UUID = Query(alias="companyId"),
    contract_id: uuid.UUID | None = Query(default=None, alias="contractId"),
    db: Session = Depends(get_db),
    user=Depends(require_permission("contract.payment_schedule", "read")),
) -> list[ScheduleResponse]:
    assert_company_access(
        db, user_id=user.id, resource="contract.payment_schedule", action="read", company_id=company_id
    )
    stmt = select(ContractPaymentSchedule).where(ContractPaymentSchedule.company_id == company_id)
    if contract_id is not None:
        stmt = stmt.where(ContractPaymentSchedule.supplier_contract_id == contract_id)
    return [_schedule_payload(db, s) for s in db.execute(stmt).scalars()]


@router.get("/schedules/{schedule_id}/summary", response_model=ContractSummaryResponse)
def get_summary(
    schedule_id: uuid.UUID,
    as_of: date | None = Query(default=None, alias="asOf"),
    db: Session = Depends(get_db),
    user=Depends(require_permission("contract.payment_schedule", "read")),
) -> ContractSummaryResponse:
    schedule = _schedule_or_404(db, schedule_id)
    assert_company_access(
        db, user_id=user.id, resource="contract.payment_schedule", action="read",
        company_id=schedule.company_id,
    )
    s = cps.contract_summary(db, schedule_id=schedule_id, as_of=as_of)
    return ContractSummaryResponse(
        contract_value=s.contract_value,
        total_scheduled_to_date=s.total_scheduled_to_date,
        paid_accumulated=s.paid_accumulated,
        contract_balance=s.contract_balance,
        overdue_balance=s.overdue_balance,
        next_due_period=s.next_due_period,
        next_due_amount=s.next_due_amount,
        currency_code=s.currency_code,
    )


@router.post("/schedules/{schedule_id}/fifo-preview", response_model=list[FifoPreviewItem])
def fifo_preview(
    schedule_id: uuid.UUID,
    payload: FifoPreviewRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("contract.payment_schedule", "read")),
) -> list[FifoPreviewItem]:
    schedule = _schedule_or_404(db, schedule_id)
    assert_company_access(
        db, user_id=user.id, resource="contract.payment_schedule", action="read",
        company_id=schedule.company_id,
    )
    return [
        FifoPreviewItem(
            installment_id=p["installment_id"],
            period_label=p["period_label"],
            amount_applied=p["amount_applied"],
        )
        for p in cps.propose_fifo(
            db, schedule_id=schedule_id, amount=payload.amount, as_of=payload.as_of
        )
    ]


@router.get("/by-contract/{contract_id}", response_model=ScheduleResponse)
def get_by_contract(
    contract_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("contract.payment_schedule", "read")),
) -> ScheduleResponse:
    schedule = db.execute(
        select(ContractPaymentSchedule).where(
            ContractPaymentSchedule.supplier_contract_id == contract_id
        )
    ).scalar_one_or_none()
    if schedule is None:
        raise HTTPException(status_code=404, detail="El contrato no tiene plan de pagos")
    assert_company_access(
        db, user_id=user.id, resource="contract.payment_schedule", action="read",
        company_id=schedule.company_id,
    )
    return _schedule_payload(db, schedule)
