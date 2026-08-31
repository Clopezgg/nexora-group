"""Accounting Closing Center (orden maestra FINAL, Phase 4).

El cierre duro (`CLOSED`) de un período fiscal es irreversible
(`_ALLOWED_PERIOD_TRANSITIONS["CLOSED"] == set()`). Antes de permitirlo se
corre un checklist de pre-cierre: cada check es bloqueante o de advertencia.
Un `AccountingDocument` posteado es inmutable, así que "el código parece
correcto" no basta — el checklist valida el estado real de la base.
"""

from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.accounting import AccountingDocument, JournalLine
from app.models.fiscal import FiscalPeriod
from app.models.treasury import BankStatementLine
from app.services import subledger_reconciliation_service


@dataclass(frozen=True)
class ClosingCheck:
    key: str
    label: str
    passed: bool
    blocking: bool
    detail: str


@dataclass(frozen=True)
class PreCloseChecklist:
    period_id: str
    period_label: str
    period_status: str
    can_hard_close: bool
    checks: list[ClosingCheck]


class ClosingBlockedError(Exception):
    """El período no puede cerrarse en duro porque hay checks bloqueantes
    sin pasar y no se forzó explícitamente."""


def _period_or_raise(db: Session, period_id) -> FiscalPeriod:
    period = db.get(FiscalPeriod, period_id)
    if period is None:
        raise ValueError("Período fiscal no encontrado")
    return period


def build_checklist(db: Session, *, company_id, period_id) -> PreCloseChecklist:
    period = _period_or_raise(db, period_id)
    if period.company_id != company_id:
        raise ValueError("El período no pertenece a esta compañía")

    checks: list[ClosingCheck] = []

    # 1. Estado del período.
    checks.append(
        ClosingCheck(
            key="period_state",
            label="El período está abierto o en cierre preliminar",
            passed=period.status in ("OPEN", "SOFT_CLOSED"),
            blocking=True,
            detail=f"Estado actual: {period.status}.",
        )
    )

    # 2. Subledgers cuadran contra el GL.
    recon = subledger_reconciliation_service.reconcile(db, company_id=company_id)
    unreconciled = [line.subledger for line in recon if not line.reconciled]
    checks.append(
        ClosingCheck(
            key="subledger_gl",
            label="Todos los subledgers cuadran contra el GL",
            passed=not unreconciled,
            blocking=True,
            detail=(
                "Cuadran: Tesorería, AP y AR."
                if not unreconciled
                else f"Descuadre en: {', '.join(unreconciled)}."
            ),
        )
    )

    # 3. Sin documentos contables en borrador dentro del período.
    draft_count = db.execute(
        select(func.count(AccountingDocument.id))
        .where(AccountingDocument.company_id == company_id)
        .where(AccountingDocument.status == "DRAFT")
        .where(func.date(AccountingDocument.posted_at).between(period.start_date, period.end_date))
    ).scalar_one()
    checks.append(
        ClosingCheck(
            key="no_draft_documents",
            label="No hay documentos contables sin postear en el período",
            passed=draft_count == 0,
            blocking=True,
            detail=f"Documentos en borrador: {draft_count}.",
        )
    )

    # 4. Doble partida — invariante, tripwire.
    unbalanced = db.execute(
        select(func.count())
        .select_from(
            select(
                AccountingDocument.id,
                func.coalesce(func.sum(JournalLine.debit_amount), Decimal("0")).label("d"),
                func.coalesce(func.sum(JournalLine.credit_amount), Decimal("0")).label("c"),
            )
            .join(JournalLine, JournalLine.accounting_document_id == AccountingDocument.id)
            .where(AccountingDocument.company_id == company_id)
            .where(func.date(AccountingDocument.posted_at).between(period.start_date, period.end_date))
            .group_by(AccountingDocument.id)
            .having(
                func.coalesce(func.sum(JournalLine.debit_amount), Decimal("0"))
                != func.coalesce(func.sum(JournalLine.credit_amount), Decimal("0"))
            )
            .subquery()
        )
    ).scalar_one()
    checks.append(
        ClosingCheck(
            key="double_entry",
            label="Todos los asientos del período tienen TOTAL DÉBITO = TOTAL CRÉDITO",
            passed=unbalanced == 0,
            blocking=True,
            detail=f"Asientos descuadrados: {unbalanced}.",
        )
    )

    # 5. Conciliación bancaria — advertencia, no bloqueante.
    unmatched_lines = db.execute(
        select(func.count(BankStatementLine.id))
        .where(BankStatementLine.status == "UNMATCHED")
        .where(BankStatementLine.line_date.between(period.start_date, period.end_date))
    ).scalar_one()
    checks.append(
        ClosingCheck(
            key="bank_reconciliation",
            label="Sin líneas bancarias por conciliar en el período",
            passed=unmatched_lines == 0,
            blocking=False,
            detail=f"Líneas UNMATCHED en el período: {unmatched_lines}.",
        )
    )

    can_hard_close = all(check.passed for check in checks if check.blocking)
    return PreCloseChecklist(
        period_id=str(period.id),
        period_label=f"P{period.period_number:02d}",
        period_status=period.status,
        can_hard_close=can_hard_close,
        checks=checks,
    )


def hard_close(
    db: Session,
    *,
    company_id,
    period_id,
    force: bool = False,
    reason: str | None = None,
) -> dict:
    """Ejecuta el cierre duro. Devuelve el manifiesto de cierre. Lanza
    `ClosingBlockedError` si hay checks bloqueantes sin pasar y `force` es
    falso."""
    period = _period_or_raise(db, period_id)
    if period.company_id != company_id:
        raise ValueError("El período no pertenece a esta compañía")
    if period.status == "CLOSED":
        raise ValueError("El período ya está cerrado.")

    checklist = build_checklist(db, company_id=company_id, period_id=period_id)

    if not checklist.can_hard_close and not force:
        raise ClosingBlockedError(
            "El período tiene checks de pre-cierre bloqueantes sin pasar."
        )
    if force and not reason:
        raise ValueError("Forzar el cierre requiere un motivo explícito.")

    from app.services import fiscal_service

    fiscal_service.transition_period_status(db, period_id=period_id, target_status="CLOSED")

    closed_at = datetime.now(timezone.utc)
    manifest = {
        "periodId": str(period.id),
        "periodLabel": f"P{period.period_number:02d}",
        "companyId": str(company_id),
        "closedAt": closed_at.isoformat(),
        "forced": force,
        "forceReason": reason,
        "checks": [
            {
                "key": c.key,
                "label": c.label,
                "passed": c.passed,
                "blocking": c.blocking,
                "detail": c.detail,
            }
            for c in checklist.checks
        ],
    }
    return manifest
