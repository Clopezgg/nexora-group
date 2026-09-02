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
from decimal import ROUND_DOWN, Decimal

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


class ContractualExpenseConflictError(InvalidFinancialReferenceError):
    """Un GeneralExpense PROJECT coincide con una obligación contractual
    abierta del mismo proyecto (ORDEN MAESTRA §21). No se bloquea de forma
    absoluta: exige un reconocimiento explícito con motivo para no volverse
    el atajo fácil que duplica un pago contractual."""


@dataclass(frozen=True)
class InstallmentSummary:
    installment_id: uuid.UUID
    sequence: int
    installment_kind: str
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
    # Numeración visible SOLO entre cuotas REGULAR (§6): "Cuota 1 de 7".
    regular_number: int | None = None
    regular_count: int | None = None


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
    # Desglose contractual (§25): ANTICIPO + BASE REGULAR = TOTAL PROGRAMADO.
    advance_scheduled: Decimal = _ZERO
    regular_scheduled: Decimal = _ZERO
    total_contractual_scheduled: Decimal = _ZERO
    advance_paid: Decimal = _ZERO
    advance_remaining: Decimal = _ZERO
    retention_outstanding: Decimal = _ZERO


@dataclass(frozen=True)
class LedgerAllocationRow:
    payment_id: uuid.UUID
    payment_date: date
    installment_sequence: int
    installment_period_label: str
    amount_applied: Decimal
    bank_transaction_reference: str | None
    reversed: bool


@dataclass(frozen=True)
class ContractLedgerEntry:
    schedule_id: uuid.UUID
    supplier_contract_id: uuid.UUID
    contract_number: str
    supplier_legal_name: str | None
    project_id: uuid.UUID | None
    currency_code: str
    contract_value: Decimal
    scheduled_to_date: Decimal
    paid_accumulated: Decimal
    contract_balance: Decimal
    overdue_balance: Decimal
    installments: list[InstallmentSummary]
    allocations: list[LedgerAllocationRow]


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
    """Cuotas mensuales iguales, vencimiento a fin de mes. La última absorbe
    el redondeo para que la suma cuadre con `total_value` (§14).

    NO es el motor canónico de planes contractuales: no modela el ANTICIPO ni
    el día de pago. `build_contract_plan` es el único generador que produce un
    plan contractual completo (ORDEN MAESTRA §41). Esta función se conserva
    solo como utilidad para construir listas de cuotas iguales en pruebas y
    para planes CUSTOM armados explícitamente por el caller.
    """
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


def _due_on(year: int, month: int, day: int) -> date:
    """Vencimiento en `day` del mes; si el mes es más corto, último día válido (§19)."""
    return date(year, month, min(day, calendar.monthrange(year, month)[1]))


def build_contract_plan(
    *,
    contract_value: Decimal,
    advance_amount: Decimal = _ZERO,
    advance_due_date: date | None = None,
    retention_percentage: Decimal = _ZERO,
    regular_months: int,
    due_day: int = 1,
    first_period: date,
) -> list[dict]:
    """Plan contractual completo: ANTICIPO (kind ADVANCE, si > 0) + N
    MENSUALIDADES regulares. Todo con Decimal, nunca float (§4/§16/§18).

    - base regular = `contract_value - advance_amount` (§16).
    - cuotas 1..N-1: `quantize(base / N)`; la última absorbe el redondeo para que
      `sum(regulares) == base` EXACTO.
    - anticipo + regulares = valor contractual EXACTO.
    """
    contract_value = _q(contract_value)
    advance_amount = _q(advance_amount)
    if advance_amount < _ZERO or advance_amount > contract_value:
        raise InvalidFinancialReferenceError(
            "El anticipo debe estar entre 0 y el valor del contrato."
        )
    if regular_months < 1:
        raise InvalidFinancialReferenceError("El plan debe tener al menos una mensualidad.")
    if not 1 <= int(due_day) <= 31:
        raise InvalidFinancialReferenceError("El día de pago debe estar entre 1 y 31.")
    if retention_percentage < _ZERO or retention_percentage > Decimal("100"):
        raise InvalidFinancialReferenceError("La retención debe estar entre 0 y 100%.")
    due_day = int(due_day)

    rows: list[dict] = []
    if advance_amount > _ZERO:
        due = advance_due_date or _due_on(first_period.year, first_period.month, due_day)
        rows.append(
            {
                "installment_kind": "ADVANCE",
                "period_year": due.year,
                "period_month": due.month,
                "due_date": due,
                "scheduled_amount": advance_amount,
                "retention_amount": _ZERO,
                "net_due": advance_amount,
                "description": "Anticipo contractual",
            }
        )

    regular_base = contract_value - advance_amount
    # Cuotas 1..N-1 se truncan a 2 decimales (ROUND_DOWN); la última absorbe el
    # residuo para que sum(regulares) == base EXACTO (§3/§18).
    per = (regular_base / Decimal(regular_months)).quantize(
        Decimal("0.01"), rounding=ROUND_DOWN
    )
    running = _ZERO
    for i in range(regular_months):
        m = _add_months(date(first_period.year, first_period.month, 1), i)
        amount = per if i < regular_months - 1 else _q(regular_base - running)
        running += amount
        retention = (
            _q(amount * retention_percentage / Decimal("100"))
            if retention_percentage
            else _ZERO
        )
        rows.append(
            {
                "installment_kind": "REGULAR",
                "period_year": m.year,
                "period_month": m.month,
                "due_date": _due_on(m.year, m.month, due_day),
                "scheduled_amount": amount,
                "retention_amount": retention,
                "net_due": _q(amount - retention),
            }
        )
    return rows


def create_schedule(
    db: Session,
    *,
    supplier_contract_id: uuid.UUID,
    schedule_type: str,
    installments: list[dict],
    due_day: int | None = None,
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
        kind = raw.get("installment_kind", "REGULAR")
        if kind not in {"ADVANCE", "REGULAR", "RETENTION_RELEASE"}:
            raise InvalidFinancialReferenceError(f"installment_kind inválido: {kind!r}")
        normalized.append(
            {
                "installment_kind": kind,
                "period_year": int(raw["period_year"]),
                "period_month": month,
                "due_date": raw["due_date"],
                "scheduled_amount": amount,
                "retention_amount": retention,
                "net_due": _q(raw.get("net_due", amount - retention)),
                "description": raw.get("description"),
            }
        )

    periods = {(r["period_year"], r["period_month"], r["installment_kind"]) for r in normalized}
    if len(periods) != len(normalized):
        raise InvalidFinancialReferenceError("Hay períodos contractuales duplicados en el plan.")
    if sum(1 for r in normalized if r["installment_kind"] == "ADVANCE") > 1:
        raise InvalidFinancialReferenceError("Un contrato no puede tener más de un anticipo.")

    total = sum((r["scheduled_amount"] for r in normalized), _ZERO)
    if total > _q(contract.value):
        raise OverpaymentError(
            "El total del plan supera el valor contractual "
            f"({total} > {contract.value})."
        )

    # El plan define el modo de pago del contrato (§6): crear un
    # MONTHLY/CUSTOM schedule promueve el contrato desde LUMP_SUM.
    if contract.payment_terms_type != schedule_type:
        contract.payment_terms_type = schedule_type

    # ADVANCE primero (es la primera obligación cronológica), luego REGULAR y
    # RETENTION_RELEASE por período.
    _KIND_ORDER = {"ADVANCE": 0, "REGULAR": 1, "RETENTION_RELEASE": 2}
    normalized.sort(
        key=lambda r: (_KIND_ORDER[r["installment_kind"]], r["period_year"], r["period_month"])
    )
    schedule = ContractPaymentSchedule(
        company_id=contract.company_id,
        supplier_contract_id=contract.id,
        project_id=contract.project_id,
        currency_code=contract.currency_code,
        schedule_type=schedule_type,
        due_day=due_day,
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
                installment_kind=r["installment_kind"],
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


def find_contractual_duplicate_candidates(
    db: Session,
    *,
    company_id: uuid.UUID,
    project_id: uuid.UUID,
    amount: Decimal,
    tolerance: Decimal = _ZERO,
) -> list[dict]:
    """Obligaciones contractuales ABIERTAS del proyecto cuyo importe pendiente
    o programado coincide (± `tolerance`) con `amount`. Base del guard de §21:
    un GeneralExpense PROJECT por ese importe probablemente es el pago de esa
    cuota registrado por fuera del contrato."""
    tol = _q(tolerance) if tolerance else Decimal("0.01")
    target = _q(amount)
    contracts = list(
        db.execute(
            select(SupplierContract).where(
                SupplierContract.company_id == company_id,
                SupplierContract.project_id == project_id,
                SupplierContract.status == "ACTIVE",
            )
        ).scalars()
    )
    out: list[dict] = []
    for contract in contracts:
        schedule = db.execute(
            select(ContractPaymentSchedule).where(
                ContractPaymentSchedule.supplier_contract_id == contract.id
            )
        ).scalar_one_or_none()
        if schedule is None:
            continue
        supplier = db.get(Supplier, contract.supplier_id)
        for s in installment_summaries(db, schedule_id=schedule.id):
            if s.status in ("PAID", "CANCELLED"):
                continue
            candidates = {s.remaining, s.net_due, s.scheduled_amount}
            if any(abs(c - target) <= tol for c in candidates):
                out.append(
                    {
                        "contract_id": str(contract.id),
                        "contract_number": contract.contract_number,
                        "supplier_name": supplier.legal_name if supplier else None,
                        "schedule_id": str(schedule.id),
                        "installment_id": str(s.installment_id),
                        "installment_kind": s.installment_kind,
                        "period_label": s.period_label,
                        "due_date": s.due_date.isoformat(),
                        "scheduled_amount": str(s.scheduled_amount),
                        "net_due": str(s.net_due),
                        "remaining": str(s.remaining),
                        "status": s.status,
                    }
                )
    return out


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
    regular_rows = [r for r in rows if r.installment_kind == "REGULAR"]
    regular_count = len(regular_rows)
    regular_number_by_id = {r.id: i + 1 for i, r in enumerate(regular_rows)}
    out: list[InstallmentSummary] = []
    for r in rows:
        paid = paid_map.get(r.id, _ZERO)
        net = _q(r.net_due)
        kind = getattr(r, "installment_kind", "REGULAR")
        out.append(
            InstallmentSummary(
                installment_id=r.id,
                sequence=r.sequence,
                installment_kind=kind,
                period_year=r.period_year,
                period_month=r.period_month,
                period_label=(
                    "Anticipo" if kind == "ADVANCE"
                    else period_label(r.period_year, r.period_month)
                ),
                due_date=r.due_date,
                scheduled_amount=_q(r.scheduled_amount),
                retention_amount=_q(r.retention_amount),
                net_due=net,
                paid=paid,
                remaining=_q(max(net - paid, _ZERO)),
                status=_status_for(r, paid, as_of=as_of),
                regular_number=regular_number_by_id.get(r.id),
                regular_count=regular_count if kind == "REGULAR" else None,
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
        # El ANTICIPO siempre precede al historial regular (§29/§41).
        if s.installment_kind == "ADVANCE"
        or s.period_year * 12 + s.period_month <= cutoff
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

    # "Programado a fecha" cuenta una obligación cuando su vencimiento ya pasó
    # el corte (§27) — el anticipo entra por su due_date, no por período mensual.
    to_date = sum((s.scheduled_amount for s in summaries if s.due_date <= as_of), _ZERO)
    paid_accumulated = sum((s.paid for s in summaries), _ZERO)
    overdue = sum((s.remaining for s in summaries if s.status == "OVERDUE"), _ZERO)
    upcoming = [
        s
        for s in summaries
        if s.status in {"UPCOMING", "DUE", "OVERDUE"} and s.remaining > _ZERO
    ]
    nxt = min(upcoming, key=lambda s: s.due_date) if upcoming else None

    advance_scheduled = sum(
        (s.scheduled_amount for s in summaries if s.installment_kind == "ADVANCE"), _ZERO
    )
    advance_paid = sum(
        (s.paid for s in summaries if s.installment_kind == "ADVANCE"), _ZERO
    )
    regular_scheduled = sum(
        (s.scheduled_amount for s in summaries if s.installment_kind == "REGULAR"), _ZERO
    )
    total_contractual = sum((s.scheduled_amount for s in summaries), _ZERO)
    retention_outstanding = sum(
        (s.retention_amount for s in summaries if s.installment_kind == "REGULAR"), _ZERO
    )
    value = _q(contract.value if contract else schedule.total_scheduled)

    return ContractSummary(
        contract_value=value,
        total_scheduled_to_date=_q(to_date),
        paid_accumulated=_q(paid_accumulated),
        contract_balance=_q(value - paid_accumulated),
        overdue_balance=_q(overdue),
        next_due_period=nxt.period_label if nxt else None,
        next_due_amount=nxt.remaining if nxt else None,
        currency_code=schedule.currency_code,
        advance_scheduled=_q(advance_scheduled),
        regular_scheduled=_q(regular_scheduled),
        total_contractual_scheduled=_q(total_contractual),
        advance_paid=_q(advance_paid),
        advance_remaining=_q(max(advance_scheduled - advance_paid, _ZERO)),
        retention_outstanding=_q(retention_outstanding),
    )


def contract_payment_ledger(
    db: Session,
    *,
    company_id: uuid.UUID,
    supplier_contract_id: uuid.UUID | None = None,
    as_of: date | None = None,
) -> list[ContractLedgerEntry]:
    """Libro contractual de pagos (§54): por cada contrato con plan, sus
    cuotas con estado real + las asignaciones de pago que las liquidaron.
    Solo lectura; no toca contabilidad."""
    from app.models.ap import SupplierInvoice, SupplierPayment

    as_of = as_of or date.today()
    q = (
        select(ContractPaymentSchedule)
        .where(ContractPaymentSchedule.company_id == company_id)
        .order_by(ContractPaymentSchedule.created_at)
    )
    if supplier_contract_id is not None:
        q = q.where(ContractPaymentSchedule.supplier_contract_id == supplier_contract_id)
    schedules = list(db.execute(q).scalars())

    entries: list[ContractLedgerEntry] = []
    for schedule in schedules:
        contract = db.get(SupplierContract, schedule.supplier_contract_id)
        supplier = (
            db.get(Supplier, contract.supplier_id) if contract is not None else None
        )
        summary = contract_summary(db, schedule_id=schedule.id, as_of=as_of)
        installments = installment_summaries(db, schedule_id=schedule.id, as_of=as_of)
        by_installment = {i.installment_id: i for i in installments}

        alloc_rows = list(
            db.execute(
                select(ContractPaymentAllocation, SupplierPayment)
                .join(
                    SupplierPayment,
                    SupplierPayment.id == ContractPaymentAllocation.supplier_payment_id,
                )
                .where(
                    ContractPaymentAllocation.installment_id.in_(list(by_installment.keys()))
                )
                .order_by(SupplierPayment.payment_date, ContractPaymentAllocation.applied_at)
            ).all()
        ) if by_installment else []

        allocations = [
            LedgerAllocationRow(
                payment_id=payment.id,
                payment_date=payment.payment_date,
                installment_sequence=by_installment[alloc.installment_id].sequence,
                installment_period_label=by_installment[alloc.installment_id].period_label,
                amount_applied=_q(alloc.amount_applied),
                bank_transaction_reference=payment.bank_transaction_reference,
                reversed=alloc.reversed_at is not None,
            )
            for alloc, payment in alloc_rows
        ]

        entries.append(
            ContractLedgerEntry(
                schedule_id=schedule.id,
                supplier_contract_id=schedule.supplier_contract_id,
                contract_number=contract.contract_number if contract else "—",
                supplier_legal_name=getattr(supplier, "legal_name", None),
                project_id=schedule.project_id,
                currency_code=schedule.currency_code,
                contract_value=summary.contract_value,
                scheduled_to_date=summary.total_scheduled_to_date,
                paid_accumulated=summary.paid_accumulated,
                contract_balance=summary.contract_balance,
                overdue_balance=summary.overdue_balance,
                installments=installments,
                allocations=allocations,
            )
        )
    return entries


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
