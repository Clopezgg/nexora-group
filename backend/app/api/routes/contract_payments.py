"""Project Contract Payment Control — API (orden maestra final §6, §17-§23).

Subledger contractual. NO contabiliza; el pago sigue pasando por
`/ap/supplier-invoices/{id}/payments`.
"""

import uuid
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.deps_correlation import get_correlation_id
from app.domain.errors import InvalidFinancialReferenceError, OverpaymentError
from app.models.contract_payment import ContractPaymentSchedule
from app.models.supplier import SupplierContract
from app.schemas.base import CamelModel
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
            installment_kind=s.installment_kind,
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
            regular_number=s.regular_number,
            regular_count=s.regular_count,
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
        due_day=schedule.due_day,
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

    due_day = payload.due_day
    if payload.installments:
        rows = [i.model_dump() for i in payload.installments]
    elif payload.regular_months and payload.first_period:
        # Modo canónico §16: base regular = valor - anticipo.
        advance = payload.advance_amount if payload.advance_amount is not None else (
            contract.advance_amount or Decimal("0")
        )
        rows = cps.build_contract_plan(
            contract_value=contract.value,
            advance_amount=advance,
            advance_due_date=payload.advance_due_date or contract.advance_due_date,
            retention_percentage=contract.retention_percentage,
            regular_months=payload.regular_months,
            due_day=payload.due_day or 1,
            first_period=payload.first_period,
        )
        due_day = payload.due_day or 1
    else:
        raise HTTPException(
            status_code=422,
            detail=(
                "Indica `installments` (plan CUSTOM), o "
                "`regularMonths` + `firstPeriod` [+ `advanceAmount` + `dueDay`] "
                "para el plan canónico (anticipo + N mensualidades)."
            ),
        )

    try:
        schedule = cps.create_schedule(
            db,
            supplier_contract_id=contract.id,
            schedule_type=payload.schedule_type,
            installments=rows,
            due_day=due_day,
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
        advance_scheduled=s.advance_scheduled,
        regular_scheduled=s.regular_scheduled,
        total_contractual_scheduled=s.total_contractual_scheduled,
        advance_paid=s.advance_paid,
        advance_remaining=s.advance_remaining,
        retention_outstanding=s.retention_outstanding,
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


class AdvanceInvoiceRequest(CamelModel):
    payable_account_id: uuid.UUID
    cost_center_id: uuid.UUID | None = None
    amount: Decimal | None = None


@router.post("/schedules/{schedule_id}/advance-invoice", status_code=201)
def prepare_advance_invoice(
    schedule_id: uuid.UUID,
    payload: AdvanceInvoiceRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("ap.supplier_invoice", "create")),
    correlation_id: str = Depends(get_correlation_id),
) -> dict:
    """Prepara la obligación AP del ANTICIPO (§12/§14/§38).

    Usa la cuenta contable de anticipos de la compañía como cuenta de activo.
    La operación queda en DRAFT: quien puede crear una obligación no obtiene
    implícitamente facultad de aprobarla ni de contabilizar su accrual. El
    workflow de AP aplica la aprobación/SoD antes del pago. Fail-closed si la
    compañía no tiene configurada la cuenta de anticipos.
    """
    from app.models.company import Company
    from app.models.contract_payment import ContractPaymentInstallment
    from app.models.supplier import SupplierContract
    from app.services import ap_service

    schedule = _schedule_or_404(db, schedule_id)
    assert_company_access(
        db, user_id=user.id, resource="ap.supplier_invoice", action="create",
        company_id=schedule.company_id,
    )
    company = db.get(Company, schedule.company_id)
    if company is None or company.supplier_advance_account_id is None:
        raise HTTPException(
            status_code=422,
            detail=(
                "Configura la cuenta contable para anticipos a "
                "proveedores/contratistas antes de registrar este pago."
            ),
        )
    contract = db.get(SupplierContract, schedule.supplier_contract_id)
    advance = db.execute(
        select(ContractPaymentInstallment).where(
            ContractPaymentInstallment.schedule_id == schedule_id,
            ContractPaymentInstallment.installment_kind == "ADVANCE",
        )
    ).scalar_one_or_none()
    if advance is None:
        raise HTTPException(status_code=404, detail="Este plan no tiene un anticipo.")

    summaries = {s.installment_id: s for s in cps.installment_summaries(db, schedule_id=schedule_id)}
    remaining = summaries[advance.id].remaining
    amount = payload.amount if payload.amount is not None else remaining
    if amount <= 0 or amount > remaining:
        raise HTTPException(
            status_code=422,
            detail=f"El monto debe estar entre 0 y el saldo del anticipo ({remaining}).",
        )

    scope = "PROJECT" if contract.project_id else "GENERAL"
    number = f"ANT-{contract.contract_number}-{advance.due_date.isoformat()}"
    try:
        invoice = ap_service.create_supplier_invoice(
            db,
            company_id=company.id,
            supplier_id=contract.supplier_id,
            invoice_number=number,
            scope=scope,
            project_id=contract.project_id,
            cost_center_id=payload.cost_center_id,
            expense_account_id=company.supplier_advance_account_id,
            payable_account_id=payload.payable_account_id,
            currency_code=contract.currency_code,
            amount=amount,
            tax_amount=Decimal("0"),
            invoice_date=advance.due_date,
            due_date=advance.due_date,
            description=f"Anticipo contractual {contract.contract_number}",
            supplier_contract_id=contract.id,
            commit=False,
        )
        audit_service.record(
            db,
            actor_user_id=user.id,
            action="contract.advance_invoice.prepare",
            entity_type="ap.supplier_invoice",
            entity_id=invoice.id,
            company_id=company.id,
            project_id=contract.project_id,
            before=None,
            after={"contractNumber": contract.contract_number, "amount": str(amount)},
            correlation_id=correlation_id,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    return {
        "invoiceId": str(invoice.id),
        "advanceInstallmentId": str(advance.id),
        "amount": str(amount),
        "status": invoice.status,
    }


class ScheduleRebuildRequest(CamelModel):
    reason: str = ""
    advance_amount: Decimal | None = None
    advance_due_date: date | None = None
    retention_percentage: Decimal | None = None
    regular_months: int = 0
    due_day: int = 1
    first_period: date | None = None


class SchedulePreviewRequest(CamelModel):
    advance_amount: Decimal | None = None
    advance_due_date: date | None = None
    retention_percentage: Decimal | None = None
    regular_months: int = 0
    due_day: int = 1
    first_period: date | None = None


class SchedulePlanSnapshot(CamelModel):
    total_scheduled: str
    installments: list[dict]


class SchedulePreviewResponse(CamelModel):
    blocked: bool
    blocked_reason: str | None = None
    before: SchedulePlanSnapshot
    after: SchedulePlanSnapshot | None = None


def _rebuild_prechecks(db: Session, schedule_id: uuid.UUID, *, regular_months: int, first_period):
    schedule = _schedule_or_404(db, schedule_id)
    blocked_reason: str | None = None
    if cps.schedule_has_active_allocations(db, schedule_id):
        blocked_reason = (
            "El plan tiene pagos aplicados. No se puede recalcular: usa una "
            "enmienda formal del plan que preserve los períodos ya pagados."
        )
    if not regular_months or not first_period:
        raise HTTPException(status_code=422, detail="Indica `regularMonths` y `firstPeriod`.")
    return schedule, blocked_reason


@router.post("/schedules/{schedule_id}/rebuild/preview", response_model=SchedulePreviewResponse)
def preview_rebuild_schedule(
    schedule_id: uuid.UUID,
    payload: SchedulePreviewRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("contract.payment_schedule", "read")),
) -> SchedulePreviewResponse:
    """Previsualiza (§10) la corrección del plan: ANTES / DESPUÉS con el motor
    canónico, sin persistir nada ni auditar. `blocked` avisa si hay pagos
    aplicados (el APPLY lo rechazará)."""
    schedule, blocked_reason = _rebuild_prechecks(
        db, schedule_id, regular_months=payload.regular_months, first_period=payload.first_period
    )
    assert_company_access(
        db, user_id=user.id, resource="contract.payment_schedule", action="read",
        company_id=schedule.company_id,
    )
    before = cps.current_schedule_snapshot(db, schedule_id)
    _contract, _rows, after = cps.build_rebuild_rows(
        db,
        schedule=schedule,
        regular_months=payload.regular_months,
        first_period=payload.first_period,
        due_day=payload.due_day,
        advance_amount=payload.advance_amount,
        advance_due_date=payload.advance_due_date,
        retention_percentage=payload.retention_percentage,
    )
    return SchedulePreviewResponse(
        blocked=blocked_reason is not None,
        blocked_reason=blocked_reason,
        before=SchedulePlanSnapshot(**before),
        after=SchedulePlanSnapshot(**after),
    )


@router.post("/schedules/{schedule_id}/rebuild", response_model=ScheduleResponse)
def rebuild_schedule(
    schedule_id: uuid.UUID,
    payload: ScheduleRebuildRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("contract.payment_schedule", "manage")),
    correlation_id: str = Depends(get_correlation_id),
) -> ScheduleResponse:
    """Corrección AUDITADA del plan (§9/§45-§47). SOLO si no hay allocations
    activas. Snapshot antes/después + AuditLog. Nunca borra el SupplierContract."""
    if len((payload.reason or "").strip()) < 10:
        raise HTTPException(status_code=422, detail="Indica un motivo (mínimo 10 caracteres).")

    schedule, blocked_reason = _rebuild_prechecks(
        db, schedule_id, regular_months=payload.regular_months, first_period=payload.first_period
    )
    assert_company_access(
        db, user_id=user.id, resource="contract.payment_schedule", action="manage",
        company_id=schedule.company_id,
    )
    if blocked_reason is not None:
        raise HTTPException(status_code=409, detail=blocked_reason)

    before, after = cps.apply_schedule_rebuild(
        db,
        schedule=schedule,
        regular_months=payload.regular_months,
        first_period=payload.first_period,
        due_day=payload.due_day,
        advance_amount=payload.advance_amount,
        advance_due_date=payload.advance_due_date,
        retention_percentage=payload.retention_percentage,
    )

    audit_service.record(
        db,
        actor_user_id=user.id,
        action="contract.payment_schedule.rebuild",
        entity_type="contract.payment_schedule",
        entity_id=schedule.id,
        company_id=schedule.company_id,
        project_id=schedule.project_id,
        before=before,
        after={**after, "reason": payload.reason},
        correlation_id=correlation_id,
    )
    db.commit()
    db.refresh(schedule)
    return _schedule_payload(db, schedule)
