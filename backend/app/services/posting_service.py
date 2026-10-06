import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.business_time import business_today
from app.domain.errors import (
    FiscalPeriodClosedError,
    ImmutableDocumentError,
    InvalidFinancialReferenceError,
    InvalidOperationScopeError,
    UnbalancedJournalEntryError,
)
from app.models.accounting import (
    OPERATION_SCOPES,
    AccountingDocument,
    AccountingSourceLink,
    JournalLine,
    TaxLine,
)
from app.models.company import Company
from app.models.fiscal import FiscalPeriod, FiscalYear
from app.services import numbering_service
from app.services.financial_validation_service import (
    assert_account_belongs_to_company,
    assert_cost_center_belongs_to_company,
    assert_project_belongs_to_company,
)

"""Posting Engine central (orden maestra §22, CLAUDE.md §8).

Contrato: ningún módulo de dominio construye AccountingDocument/JournalLine a
mano. Todos llaman a este servicio. El motor valida los invariantes contables,
la fecha económica, el alcance operativo y las referencias financieras antes de
persistir el asiento.
"""

ReversalHook = Callable[[Session, uuid.UUID, str, date], None]
_REVERSAL_HOOKS: dict[str, ReversalHook] = {}


def register_reversal_hook(source_type: str, hook: ReversalHook) -> None:
    _REVERSAL_HOOKS[source_type] = hook


@dataclass
class JournalLineInput:
    account_id: uuid.UUID
    debit_amount: Decimal = Decimal("0")
    credit_amount: Decimal = Decimal("0")
    description: str | None = None
    project_id: uuid.UUID | None = None
    cost_center_id: uuid.UUID | None = None
    extra_dimensions: dict | None = field(default=None)


def _validate_scope(scope: str, project_id: uuid.UUID | None) -> None:
    if scope not in OPERATION_SCOPES:
        raise InvalidOperationScopeError(f"scope inválido: {scope!r}")
    if scope in ("CENTRAL", "GENERAL") and project_id is not None:
        raise InvalidOperationScopeError(
            f"scope={scope} requiere project_id=None (INV-OPS-001/002)"
        )
    if scope == "PROJECT" and project_id is None:
        raise InvalidOperationScopeError("scope=PROJECT requiere project_id (INV-OPS-003)")


def _validate_balance(lines: list[JournalLineInput]) -> None:
    if not lines:
        raise UnbalancedJournalEntryError("Un asiento debe contener al menos una línea")
    total_debit = sum((line.debit_amount for line in lines), Decimal("0"))
    total_credit = sum((line.credit_amount for line in lines), Decimal("0"))
    if total_debit != total_credit:
        raise UnbalancedJournalEntryError(
            f"Asiento desbalanceado: débito={total_debit} crédito={total_credit} (INV-ACC-001)"
        )
    if total_debit == Decimal("0"):
        raise UnbalancedJournalEntryError("Un asiento no puede tener monto total cero")
    for line in lines:
        if line.debit_amount != 0 and line.credit_amount != 0:
            raise UnbalancedJournalEntryError(
                "Una línea no puede tener débito y crédito simultáneamente"
            )
        if line.debit_amount < 0 or line.credit_amount < 0:
            raise UnbalancedJournalEntryError("Los montos de línea no pueden ser negativos")


def _validate_tax_lines(tax_lines: list[tuple[uuid.UUID, Decimal, Decimal]] | None) -> None:
    for tax_code_id, base_amount, tax_amount in tax_lines or []:
        if not tax_code_id:
            raise InvalidFinancialReferenceError("Cada línea fiscal requiere tax_code_id")
        if base_amount < 0 or tax_amount < 0:
            raise UnbalancedJournalEntryError("Base y monto fiscal no pueden ser negativos")


def _validate_line_scope(
    scope: str, document_project_id: uuid.UUID | None, lines: list[JournalLineInput]
) -> None:
    """A PROJECT posting cannot silently carry lines for another/no project.

    CENTRAL/GENERAL may still carry project dimensions on individual lines for
    legitimate allocations; the header itself remains project-less.
    """
    if scope != "PROJECT":
        return
    for line in lines:
        if line.project_id != document_project_id:
            raise InvalidOperationScopeError(
                "scope=PROJECT requiere que cada línea use el mismo project_id del documento"
            )


def _assert_fiscal_period_open(db: Session, *, company_id: uuid.UUID, as_of: date) -> None:
    period = db.execute(
        select(FiscalPeriod)
        .where(
            FiscalPeriod.company_id == company_id,
            FiscalPeriod.start_date <= as_of,
            FiscalPeriod.end_date >= as_of,
        )
        .with_for_update(read=True)
        .execution_options(populate_existing=True)
    ).scalar_one_or_none()
    if period is None:
        calendar_exists = db.execute(
            select(FiscalYear.id).where(FiscalYear.company_id == company_id).limit(1)
        ).scalar_one_or_none()
        if calendar_exists is not None:
            raise FiscalPeriodClosedError(
                f"El calendario fiscal tiene un gap para effective_date={as_of.isoformat()}"
            )
        return
    if period.status == "CLOSED":
        raise FiscalPeriodClosedError(
            f"El período fiscal {period.id} está CLOSED, no admite nuevos postings"
        )


def _assert_fiscal_period_allows_posting(
    db: Session, *, company_id: uuid.UUID, as_of: date, document_type_code: str
) -> None:
    period = db.execute(
        select(FiscalPeriod)
        .where(
            FiscalPeriod.company_id == company_id,
            FiscalPeriod.start_date <= as_of,
            FiscalPeriod.end_date >= as_of,
        )
        .with_for_update(read=True)
        .execution_options(populate_existing=True)
    ).scalar_one_or_none()
    if period is None:
        calendar_exists = db.execute(
            select(FiscalYear.id).where(FiscalYear.company_id == company_id).limit(1)
        ).scalar_one_or_none()
        if calendar_exists is not None:
            raise FiscalPeriodClosedError(
                f"El calendario fiscal tiene un gap para effective_date={as_of.isoformat()}"
            )
        return
    if period.status == "CLOSED":
        raise FiscalPeriodClosedError(
            f"El período fiscal {period.id} está CLOSED, no admite nuevos postings"
        )
    if period.status == "SOFT_CLOSED" and document_type_code not in {"COR", "ANU"}:
        raise FiscalPeriodClosedError(
            f"El período fiscal {period.id} está SOFT_CLOSED; solo se permiten correcciones (COR) y anulaciones (ANU)"
        )


def _validate_financial_references(
    db: Session,
    *,
    company_id: uuid.UUID,
    document_project_id: uuid.UUID | None,
    lines: list[JournalLineInput],
) -> None:
    assert_project_belongs_to_company(
        db, project_id=document_project_id, company_id=company_id
    )
    for line in lines:
        assert_account_belongs_to_company(
            db, account_id=line.account_id, company_id=company_id, field_name="lines.account_id"
        )
        assert_project_belongs_to_company(
            db, project_id=line.project_id, company_id=company_id
        )
        assert_cost_center_belongs_to_company(
            db, cost_center_id=line.cost_center_id, company_id=company_id
        )


def post_manual(
    db: Session,
    *,
    company_id: uuid.UUID,
    document_type_code: str,
    scope: str,
    project_id: uuid.UUID | None,
    currency_code: str,
    lines: list[JournalLineInput],
    fx_rate: Decimal = Decimal("1"),
    description: str | None = None,
    effective_date: date | None = None,
    source_type: str | None = None,
    source_id: uuid.UUID | None = None,
    tax_lines: list[tuple[uuid.UUID, Decimal, Decimal]] | None = None,
    commit: bool = True,
) -> AccountingDocument:
    _validate_scope(scope, project_id)
    _validate_balance(lines)
    _validate_tax_lines(tax_lines)
    if fx_rate <= 0:
        raise InvalidFinancialReferenceError("fx_rate debe ser mayor que cero")
    if (source_type is None) != (source_id is None):
        raise InvalidFinancialReferenceError(
            "source_type y source_id deben proporcionarse juntos para preservar trazabilidad"
        )

    company = db.get(Company, company_id)
    if company is None or not company.functional_currency_code:
        raise InvalidFinancialReferenceError("La compañía no tiene moneda funcional configurada")
    if currency_code != company.functional_currency_code:
        raise InvalidFinancialReferenceError(
            "El Posting Engine requiere importes de línea en la moneda funcional "
            f"{company.functional_currency_code}; no existe una política FX autoritativa "
            f"para contabilizar {currency_code}"
        )
    _validate_financial_references(
        db, company_id=company_id, document_project_id=project_id, lines=lines
    )
    _validate_line_scope(scope, project_id, lines)
    posting_date = effective_date or business_today()
    _assert_fiscal_period_allows_posting(
        db, company_id=company_id, as_of=posting_date, document_type_code=document_type_code
    )

    document_number = numbering_service.next_document_number(
        db, company_id=company_id, document_type_code=document_type_code
    )
    document = AccountingDocument(
        company_id=company_id,
        document_type_code=document_type_code,
        document_number=document_number,
        scope=scope,
        project_id=project_id,
        currency_code=currency_code,
        fx_rate=fx_rate,
        status="POSTED",
        description=description,
        effective_date=posting_date,
        posted_at=datetime.now(timezone.utc),
    )
    db.add(document)
    db.flush()

    for line in lines:
        db.add(
            JournalLine(
                accounting_document_id=document.id,
                account_id=line.account_id,
                debit_amount=line.debit_amount,
                credit_amount=line.credit_amount,
                description=line.description,
                project_id=line.project_id,
                cost_center_id=line.cost_center_id,
                extra_dimensions=line.extra_dimensions,
            )
        )
    for tax_code_id, base_amount, tax_amount in tax_lines or []:
        db.add(
            TaxLine(
                accounting_document_id=document.id,
                tax_code_id=tax_code_id,
                base_amount=base_amount,
                tax_amount=tax_amount,
            )
        )
    if source_type is not None and source_id is not None:
        db.add(
            AccountingSourceLink(
                accounting_document_id=document.id, source_type=source_type, source_id=source_id
            )
        )
    if commit:
        db.commit()
    else:
        db.flush()
    db.refresh(document)
    return document


def reverse_document(
    db: Session, *, document_id: uuid.UUID, reason: str, commit: bool = True
) -> AccountingDocument:
    original = db.execute(
        select(AccountingDocument)
        .where(AccountingDocument.id == document_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).scalar_one_or_none()
    if original is None:
        raise ValueError(f"AccountingDocument {document_id} no existe")
    if original.status != "POSTED":
        raise ImmutableDocumentError(
            f"Solo se puede revertir un documento POSTED (estado actual: {original.status})"
        )
    if not reason or not reason.strip():
        raise ImmutableDocumentError("La reversión requiere un motivo no vacío")

    reversal_effective_date = business_today()
    link = db.execute(
        select(AccountingSourceLink)
        .where(AccountingSourceLink.accounting_document_id == original.id)
    ).scalar_one_or_none()
    if link is not None:
        hook = _REVERSAL_HOOKS.get(link.source_type)
        if hook is not None:
            hook(db, link.source_id, original.document_type_code, reversal_effective_date)

    original_lines = db.execute(
        select(JournalLine).where(JournalLine.accounting_document_id == original.id)
    ).scalars().all()
    reversal_lines = [
        JournalLineInput(
            account_id=line.account_id,
            debit_amount=line.credit_amount,
            credit_amount=line.debit_amount,
            description=f"Reversal de {original.document_number}: {line.description or ''}".strip(),
            project_id=line.project_id,
            cost_center_id=line.cost_center_id,
            extra_dimensions=line.extra_dimensions,
        )
        for line in original_lines
    ]
    reversal = post_manual(
        db,
        company_id=original.company_id,
        document_type_code="ANU",
        scope=original.scope,
        project_id=original.project_id,
        currency_code=original.currency_code,
        fx_rate=original.fx_rate,
        lines=reversal_lines,
        description=f"Reversal de {original.document_number}: {reason}",
        effective_date=reversal_effective_date,
        commit=False,
    )
    original.status = "REVERSED"
    original.reversed_document_id = reversal.id
    original.reversal_reason = reason
    if commit:
        db.commit()
    else:
        db.flush()
    db.refresh(original)
    return reversal


def assert_document_is_mutable_or_raise(document: AccountingDocument) -> None:
    if document.status not in ("DRAFT",):
        raise ImmutableDocumentError(
            f"AccountingDocument {document.document_number} está {document.status}; "
            "no se puede modificar, solo revertir vía reverse_document()"
        )
