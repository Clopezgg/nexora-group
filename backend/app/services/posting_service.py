import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.errors import (
    FiscalPeriodClosedError,
    ImmutableDocumentError,
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
from app.models.fiscal import FiscalPeriod
from app.services import numbering_service
from app.services.financial_validation_service import (
    assert_account_belongs_to_company,
    assert_cost_center_belongs_to_company,
    assert_project_belongs_to_company,
)

"""Posting Engine central (orden maestra §22, CLAUDE.md §8).

Contrato: ningún módulo de dominio (Treasury, AP, AR, Procurement, ...)
construye un AccountingDocument/JournalLine a mano. Todos llaman a
`post_manual()` (o, cuando exista una PostingRule aplicable, a
`post_via_rule()`) con las líneas ya resueltas por su propia lógica de
negocio. Este servicio SOLO se encarga de: validar los invariantes de
dominio contable (doble partida, OperationScope, período fiscal abierto,
inmutabilidad), numerar el documento y persistirlo -- nunca decide qué
cuentas usar para un caso de negocio que no conoce.
"""


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


def _assert_fiscal_period_open(db: Session, *, company_id: uuid.UUID, as_of: date) -> None:
    """INV-ACC-003. Si no hay ningún FiscalPeriod configurado que cubra la
    fecha, se permite postear (todavía no se configuró el calendario fiscal
    de la company) -- pero si existe uno y está CLOSED, se bloquea."""
    period = db.execute(
        select(FiscalPeriod).where(
            FiscalPeriod.company_id == company_id,
            FiscalPeriod.start_date <= as_of,
            FiscalPeriod.end_date >= as_of,
        )
    ).scalar_one_or_none()
    if period is not None and period.status == "CLOSED":
        raise FiscalPeriodClosedError(
            f"El período fiscal {period.id} está CLOSED, no admite nuevos postings"
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
            db,
            account_id=line.account_id,
            company_id=company_id,
            field_name="lines.account_id",
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
    source_type: str | None = None,
    source_id: uuid.UUID | None = None,
    tax_lines: list[tuple[uuid.UUID, Decimal, Decimal]] | None = None,
    commit: bool = True,
) -> AccountingDocument:
    """Crea y contabiliza (POSTED) un AccountingDocument balanceado. Lanza
    UnbalancedJournalEntryError / InvalidOperationScopeError /
    FiscalPeriodClosedError si algún invariante no se cumple -- en ese caso
    no se persiste nada (la transacción se puede hacer rollback por el
    caller; este servicio no captura esas excepciones)."""
    _validate_scope(scope, project_id)
    _validate_balance(lines)
    _validate_financial_references(
        db,
        company_id=company_id,
        document_project_id=project_id,
        lines=lines,
    )
    _assert_fiscal_period_open(db, company_id=company_id, as_of=datetime.now(timezone.utc).date())

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
    db: Session, *, document_id: uuid.UUID, reason: str
) -> AccountingDocument:
    """Reversal completo (orden maestra §83): el original se preserva
    intacto (nunca se le tocan sus líneas/montos), se crea un nuevo
    AccountingDocument con débitos/créditos invertidos, y ambos quedan
    enlazados. La única mutación permitida sobre el original es la
    transición de estado POSTED -> REVERSED + el link al reversal; sus
    JournalLine nunca se tocan."""
    original = db.get(AccountingDocument, document_id)
    if original is None:
        raise ValueError(f"AccountingDocument {document_id} no existe")
    if original.status != "POSTED":
        raise ImmutableDocumentError(
            f"Solo se puede revertir un documento POSTED (estado actual: {original.status})"
        )

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
    )

    original.status = "REVERSED"
    original.reversed_document_id = reversal.id
    original.reversal_reason = reason
    db.commit()
    db.refresh(original)
    return reversal


def assert_document_is_mutable_or_raise(document: AccountingDocument) -> None:
    """Guard explícito para cualquier código que intente tocar un documento
    fuera de este servicio. INV-ACC-002."""
    if document.status not in ("DRAFT",):
        raise ImmutableDocumentError(
            f"AccountingDocument {document.document_number} está {document.status}; "
            "no se puede modificar, solo revertir vía reverse_document()"
        )
