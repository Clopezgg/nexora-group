"""Project Contract Payment Control — subledger contractual (orden maestra
final §1-§16, §22-§23, §60-§61).

Nunca escribe contabilidad: el pago sigue generando su AccountingDocument por
el Posting Engine (§46). Este servicio explica *qué mes contractual* liquidó
*qué dinero*, y produce el historial ACUMULATIVO (sólo hasta el período del
comprobante, nunca meses futuros — §2/§38/§60).
"""

from __future__ import annotations

import calendar
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.errors import (
    InvalidFinancialReferenceError,
    OverpaymentError,
)
from app.models.contract_payment import (
    ContractPaymentAllocation,
    ContractPaymentInstallment,
    ContractPaymentSchedule,
)
from app.models.supplier import Supplier, SupplierContract

_ZERO = Decimal("0.00")


def _q(value: Decimal | int | float | str) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"))


class ContractScheduleExistsError(InvalidFinancialReferenceError):
    """Ya hay un plan de pagos para ese contrato."""


class InstallmentClosedError(InvalidFinancialReferenceError):
    """La cuota no admite más aplicaciones (PAID / CANCELLED)."""


@dataclass(frozen=True)
class InstallmentSummary:
    installment_id: uuid.UUID
    sequence: int
    period_year: int
    period_month: int
    period_label: str
    due_date: date
    scheduled_amount: Decimal
    retention_amount: Decimal
    net_due: Decimal
    paid: Decimal
    remaining: Decimal
    status: str


@dataclass(frozen=True)
class ContractSummary:
    contract_value: Decimal
    total_scheduled_to_date: Decimal
    paid_accumulated: Decimal
    contract_balance: Decimal
    overdue_balance: Decimal
    next_due_period: str | None
    next_due_amount: Decimal | None
    currency_code: str


_MONTHS_ES = [
    "", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
]


def period_label(year: int, month: int) -> str:
    return f"{_MONTHS_ES[month]} {year}"


# --------------------------------------------------------------------------- #
# Creación del plan                                                            #
# --------------------------------------------------------------------------- #

def _add_months(anchor: date, months: int) -> date:
    total = anchor.month - 1 + months
    year = anchor.year + total // 12
    month = total % 12 + 1
    day = min(anchor.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def build_monthly_installments(
    *,
    start_period: date,
    count: int,
    monthly_amount: Decimal,
    total_value: Decimal | None = None,
    retention_percentage: Decimal = _ZERO,
) -> list[dict]:
    """Cuotas mensuales iguales. La última absorbe el redondeo para que la
    suma cuadre exactamente con `total_value` cuando se da (§14)."""
    monthly_amount = _q(monthly_amount)
    rows: list[dict] = []
    running = _ZERO
    for i in range(count):
        due = _add_months(date(start_period.year, start_period.month, 1), i)
        amount = monthly_amount
        if total_value is not None and i == count - 1:
            amount = _q(total_value) - running
        running += amount
        retention = _q(amount * retention_percentage / Decimal("100")) if retention_percentage else _ZERO
        rows.append(
            {
                "period_year": due.year,
                "period_month": due.month,
                "due_date": _add_months(date(due.year, due.month, 1), 1) - _one_day(),
                "scheduled_amount": amount,
                "retention_amount": retention,
                "net_due": _q(amount - retention),
            }
        )
    return rows


def _one_day():
    from datetime import timedelta

    return timedelta(days=1)


def create_schedule(
    db: Session,
    *,
    supplier_contract_id: uuid.UUID,
    schedule_type: str,
    installments: list[dict],
    commit: bool = True,
) -> ContractPaymentSchedule:
    contract = db.get(SupplierContract, supplier_contract_id)
    if contract is None:
        raise InvalidFinancialReferenceError(
            f"SupplierContract {supplier_contract_id} no existe"
        )
    existing = db.execute(
        select(ContractPaymentSchedule).where(
            ContractPaymentSchedule.supplier_contract_id == supplier_contract_id
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise ContractScheduleExistsError(
            f"El contrato {contract.contract_number} ya tiene un plan de pagos."
        )
    if schedule_type not in {"MONTHLY", "CUSTOM"}:
        raise InvalidFinancialReferenceError(f"schedule_type inválido: {schedule_type!r}")
    if not installments:
        raise InvalidFinancialReferenceError("El plan debe tener al menos una cuota.")

    normalized: list[dict] = []
    for raw in installments:
        amount = _q(raw["scheduled_amount"])
        if amount <= _ZERO:
            raise InvalidFinancialReferenceError("Cada cuota debe ser mayor que cero.")
        retention = _q(raw.get("retention_amount", _ZERO))
        if retention < _ZERO or retention > amount:
            raise InvalidFinancialReferenceError("Retención inválida para la cuota.")
        month = int(raw["period_month"])
        if not 1 <= month <= 12:
            raise InvalidFinancialReferenceError("period_month debe estar entre 1 y 12.")
        normalized.append(
            {
                "period_year": int(raw["period_year"]),
                "period_month": month,
                "due_date": raw["due_date"],
                "scheduled_amount": amount,
                "retention_amount": retention,
                "net_due": _q(raw.get("net_due", amount - retention)),
                "description": raw.get("description"),
            }
        )

    periods = {(r["period_year"], r["period_month"]) for r in normalized}
    if len(periods) != len(normalized):
        raise InvalidFinancialReferenceError("Hay períodos contractuales duplicados en el plan.")

    total = sum((r["scheduled_amount"] for r in normalized), _ZERO)
    if total > _q(contract.value):
        raise OverpaymentError(
            "El total del plan supera el valor contractual "
            f"({total} > {contract.value})."
        )

    normalized.sort(key=lambda r: (r["period_year"], r["period_month"]))
    schedule = ContractPaymentSchedule(
        company_id=contract.company_id,
        supplier_contract_id=contract.id,
        project_id=contract.project_id,
        currency_code=contract.currency_code,
        schedule_type=schedule_type,
        start_period=date(normalized[0]["period_year"], normalized[0]["period_month"], 1),
        end_period=date(normalized[-1]["period_year"], normalized[-1]["period_month"], 1),
        total_scheduled=_q(total),
        status="ACTIVE",
    )
    db.add(schedule)
    db.flush()

    for seq, r in enumerate(normalized, start=1):
        db.add(
            ContractPaymentInstallment(
                schedule_id=schedule.id,
                sequence=seq,
                period_year=r["period_year"],
                period_month=r["period_month"],
                due_date=r["due_date"],
                scheduled_amount=r["scheduled_amount"],
                retention_amount=r["retention_amount"],
                net_due=r["net_due"],
                status="UPCOMING",
                description=r["description"],
            )
        )
    db.flush()
    if commit:
        db.commit()
    return schedule


# --------------------------------------------------------------------------- #
# Estado y resúmenes                                                           #
# --------------------------------------------------------------------------- #

def _paid_by_installment(db: Session, installment_ids: list[uuid.UUID]) -> dict[uuid.UUID, Decimal]:
    if not installment_ids:
        return {}
    rows = db.execute(
        select(
            ContractPaymentAllocation.installment_id,
            func.coalesce(func.sum(ContractPaymentAllocation.amount_applied), 0),
        )
        .where(
            ContractPaymentAllocation.installment_id.in_(installment_ids),
            ContractPaymentAllocation.reversed_at.is_(None),
        )
        .group_by(ContractPaymentAllocation.installment_id)
    ).all()
    return {row[0]: _q(row[1]) for row in rows}


def _status_for(
    installment: ContractPaymentInstallment, paid: Decimal, *, as_of: date
) -> str:
    if installment.status == "CANCELLED":
        return "CANCELLED"
    net = _q(installment.net_due)
    if paid >= net and net > _ZERO:
        return "PAID"
    if paid > _ZERO:
        return "PARTIALLY_PAID"
    if installment.due_date < as_of:
        return "OVERDUE"
    if installment.due_date <= _add_months(date(as_of.year, as_of.month, 1), 1) - _one_day():
        return "DUE"
    return "UPCOMING"


def installment_summaries(
    db: Session, *, schedule_id: uuid.UUID, as_of: date | None = None
) -> list[InstallmentSummary]:
    as_of = as_of or date.today()
    rows = list(
        db.execute(
            select(ContractPaymentInstallment)
            .where(ContractPaymentInstallment.schedule_id == schedule_id)
            .order_by(ContractPaymentInstallment.sequence)
        ).scalars()
    )
    paid_map = _paid_by_installment(db, [r.id for r in rows])
    out: list[InstallmentSummary] = []
    for r in rows:
        paid = paid_map.get(r.id, _ZERO)
        net = _q(r.net_due)
        out.append(
            InstallmentSummary(
                installment_id=r.id,
                sequence=r.sequence,
                period_year=r.period_year,
                period_month=r.period_month,
                period_label=period_label(r.period_year, r.period_month),
                due_date=r.due_date,
                scheduled_amount=_q(r.scheduled_amount),
                retention_amount=_q(r.retention_amount),
                net_due=net,
                paid=paid,
                remaining=_q(max(net - paid, _ZERO)),
                status=_status_for(r, paid, as_of=as_of),
            )
        )
    return out


def history_through(
    db: Session,
    *,
    schedule_id: uuid.UUID,
    period_year: int,
    period_month: int,
    as_of: date | None = None,
) -> list[InstallmentSummary]:
    """Historial ACUMULATIVO: sólo cuotas cuyo período contractual es <= el
    período dado. Nunca meses futuros (§2/§38/§60)."""
    cutoff = period_year * 12 + period_month
    return [
        s
        for s in installment_summaries(db, schedule_id=schedule_id, as_of=as_of)
        if s.period_year * 12 + s.period_month <= cutoff
    ]


def contract_summary(
    db: Session, *, schedule_id: uuid.UUID, as_of: date | None = None
) -> ContractSummary:
    as_of = as_of or date.today()
    schedule = db.get(ContractPaymentSchedule, schedule_id)
    if schedule is None:
        raise InvalidFinancialReferenceError(f"ContractPaymentSchedule {schedule_id} no existe")
    contract = db.get(SupplierContract, schedule.supplier_contract_id)
    summaries = installment_summaries(db, schedule_id=schedule_id, as_of=as_of)

    to_date = sum(
        (s.scheduled_amount for s in summaries if date(s.period_year, s.period_month, 1) <= as_of),
        _ZERO,
    )
    paid_accumulated = sum((s.paid for s in summaries), _ZERO)
    overdue = sum((s.remaining for s in summaries if s.status == "OVERDUE"), _ZERO)
    upcoming = [s for s in summaries if s.status in {"UPCOMING", "DUE"} and s.remaining > _ZERO]
    nxt = min(upcoming, key=lambda s: s.due_date) if upcoming else None

    return ContractSummary(
        contract_value=_q(contract.value if contract else schedule.total_scheduled),
        total_scheduled_to_date=_q(to_date),
        paid_accumulated=_q(paid_accumulated),
        contract_balance=_q(
            (contract.value if contract else schedule.total_scheduled) - paid_accumulated
        ),
        overdue_balance=_q(overdue),
        next_due_period=nxt.period_label if nxt else None,
        next_due_amount=nxt.remaining if nxt else None,
        currency_code=schedule.currency_code,
    )


# --------------------------------------------------------------------------- #
# Asignación de pagos (allocation)                                             #
# --------------------------------------------------------------------------- #

def allocate_payment(
    db: Session,
    *,
    supplier_payment_id: uuid.UUID,
    allocations: list[dict],
    override_reason: str | None = None,
    commit: bool = True,
) -> list[ContractPaymentAllocation]:
    """Aplica un SupplierPayment a una o varias cuotas contractuales.
    Valida: sin sobrepago por cuota (§10), cuota abierta, montos > 0."""
    if not allocations:
        raise InvalidFinancialReferenceError("Debes indicar al menos una asignación.")

    inst_ids = [uuid.UUID(str(a["installment_id"])) for a in allocations]
    paid_map = _paid_by_installment(db, inst_ids)
    created: list[ContractPaymentAllocation] = []
    now = datetime.now(timezone.utc)

    for a in allocations:
        inst_id = uuid.UUID(str(a["installment_id"]))
        amount = _q(a["amount_applied"])
        if amount <= _ZERO:
            raise InvalidFinancialReferenceError("El monto a aplicar debe ser mayor que cero.")
        installment = db.get(ContractPaymentInstallment, inst_id)
        if installment is None:
            raise InvalidFinancialReferenceError(f"Cuota {inst_id} no existe")
        if installment.status == "CANCELLED":
            raise InstallmentClosedError("La cuota está cancelada.")
        already = paid_map.get(inst_id, _ZERO)
        remaining = _q(installment.net_due) - already
        if amount > remaining:
            raise OverpaymentError(
                f"El monto {amount} supera el saldo de la cuota ({remaining})."
            )
        alloc = ContractPaymentAllocation(
            supplier_payment_id=supplier_payment_id,
            installment_id=inst_id,
            amount_applied=amount,
            applied_at=now,
            override_reason=override_reason,
        )
        db.add(alloc)
        created.append(alloc)
        paid_map[inst_id] = already + amount

    db.flush()
    if commit:
        db.commit()
    return created


def reverse_payment_allocations(db: Session, *, supplier_payment_id: uuid.UUID) -> int:
    """Marca como revertidas todas las asignaciones contractuales activas de un
    pago (§57/§58). Reabre el saldo de las cuotas: como
    `installment_summaries` sólo suma allocations con `reversed_at IS NULL`,
    el estado de la cuota se recalcula solo."""
    rows = list(
        db.execute(
            select(ContractPaymentAllocation).where(
                ContractPaymentAllocation.supplier_payment_id == supplier_payment_id,
                ContractPaymentAllocation.reversed_at.is_(None),
            )
        ).scalars()
    )
    now = datetime.now(timezone.utc)
    for row in rows:
        row.reversed_at = now
    db.flush()
    return len(rows)


def resolve_schedule_for_invoice(db: Session, invoice) -> ContractPaymentSchedule | None:
    contract_id = getattr(invoice, "supplier_contract_id", None)
    if contract_id is None:
        return None
    return db.execute(
        select(ContractPaymentSchedule).where(
            ContractPaymentSchedule.supplier_contract_id == contract_id
        )
    ).scalar_one_or_none()


def prior_unpaid_before(
    db: Session,
    *,
    schedule_id: uuid.UUID,
    period_year: int,
    period_month: int,
    as_of: date | None = None,
) -> list[InstallmentSummary]:
    """Cuotas anteriores al período dado que aún tienen saldo (§11)."""
    cutoff = period_year * 12 + period_month
    return [
        s
        for s in installment_summaries(db, schedule_id=schedule_id, as_of=as_of)
        if s.period_year * 12 + s.period_month < cutoff and s.remaining > _ZERO
        and s.status != "CANCELLED"
    ]


def propose_fifo(
    db: Session, *, schedule_id: uuid.UUID, amount: Decimal, as_of: date | None = None
) -> list[dict]:
    """Distribución FIFO contractual: aplica el monto a las cuotas más antiguas
    con saldo primero (§12). Devuelve el preview, NO persiste."""
    remaining = _q(amount)
    proposal: list[dict] = []
    for s in installment_summaries(db, schedule_id=schedule_id, as_of=as_of):
        if remaining <= _ZERO:
            break
        if s.status == "CANCELLED" or s.remaining <= _ZERO:
            continue
        applied = min(remaining, s.remaining)
        proposal.append(
            {
                "installment_id": s.installment_id,
                "period_label": s.period_label,
                "amount_applied": applied,
            }
        )
        remaining -= applied
    return proposal
