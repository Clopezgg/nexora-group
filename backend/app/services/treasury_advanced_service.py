import uuid
from decimal import Decimal

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.domain.errors import InvalidFinancialReferenceError
from app.models.accounting import AccountingDocument, JournalLine
from app.models.treasury import (
    BankStatement,
    BankStatementLine,
    CashClosing,
    FundRestriction,
    ReconciliationMatch,
    TreasuryAccount,
)
from app.services import treasury_service


def list_cash_closings(db: Session, *, company_id: uuid.UUID) -> list[CashClosing]:
    return list(
        db.execute(
            select(CashClosing)
            .join(TreasuryAccount, CashClosing.treasury_account_id == TreasuryAccount.id)
            .where(TreasuryAccount.company_id == company_id)
            .order_by(CashClosing.closing_date.desc(), CashClosing.created_at.desc())
        ).scalars()
    )


def list_bank_statements(db: Session, *, company_id: uuid.UUID) -> list[BankStatement]:
    return list(
        db.execute(
            select(BankStatement)
            .join(TreasuryAccount, BankStatement.treasury_account_id == TreasuryAccount.id)
            .where(TreasuryAccount.company_id == company_id)
            .order_by(BankStatement.statement_date.desc(), BankStatement.created_at.desc())
        ).scalars()
    )


def list_statement_lines(db: Session, *, bank_statement_id: uuid.UUID) -> list[BankStatementLine]:
    return list(
        db.execute(
            select(BankStatementLine)
            .where(BankStatementLine.bank_statement_id == bank_statement_id)
            .order_by(BankStatementLine.line_date, BankStatementLine.created_at)
        ).scalars()
    )


def list_line_matches(db: Session, *, bank_statement_line_id: uuid.UUID) -> list[ReconciliationMatch]:
    return list(
        db.execute(
            select(ReconciliationMatch)
            .where(ReconciliationMatch.bank_statement_line_id == bank_statement_line_id)
            .order_by(ReconciliationMatch.matched_at)
        ).scalars()
    )


def reconciliation_candidates(db: Session, *, line: BankStatementLine) -> list[dict]:
    statement = db.get(BankStatement, line.bank_statement_id)
    if statement is None:
        raise InvalidFinancialReferenceError("El estado bancario de la línea no existe")
    treasury_account = db.get(TreasuryAccount, statement.treasury_account_id)
    if treasury_account is None:
        raise InvalidFinancialReferenceError("La cuenta de tesorería del estado no existe")

    amount_column = JournalLine.debit_amount if line.amount > 0 else JournalLine.credit_amount
    rows = db.execute(
        select(
            AccountingDocument.id,
            AccountingDocument.document_number,
            AccountingDocument.document_type_code,
            AccountingDocument.description,
            func.sum(amount_column).label("capacity"),
        )
        .join(JournalLine, JournalLine.accounting_document_id == AccountingDocument.id)
        .where(
            AccountingDocument.company_id == treasury_account.company_id,
            AccountingDocument.status == "POSTED",
            JournalLine.account_id == treasury_account.gl_account_id,
            amount_column > 0,
        )
        .group_by(
            AccountingDocument.id,
            AccountingDocument.document_number,
            AccountingDocument.document_type_code,
            AccountingDocument.description,
        )
        .order_by(AccountingDocument.posted_at.desc())
    ).all()

    result: list[dict] = []
    target = abs(line.amount)
    for document_id, number, type_code, description, capacity in rows:
        allocated = Decimal(
            db.execute(
                select(func.coalesce(func.sum(ReconciliationMatch.matched_amount), 0))
                .join(BankStatementLine, ReconciliationMatch.bank_statement_line_id == BankStatementLine.id)
                .join(BankStatement, BankStatementLine.bank_statement_id == BankStatement.id)
                .where(
                    ReconciliationMatch.accounting_document_id == document_id,
                    BankStatement.treasury_account_id == treasury_account.id,
                    (BankStatementLine.amount > 0) if line.amount > 0 else (BankStatementLine.amount < 0),
                )
            ).scalar_one()
        )
        available = Decimal(capacity) - allocated
        if available <= 0:
            continue
        result.append(
            {
                "accountingDocumentId": document_id,
                "documentNumber": number,
                "documentTypeCode": type_code,
                "description": description,
                "availableAmount": available,
                "exactMatch": available == target,
            }
        )
    result.sort(key=lambda item: (not item["exactMatch"], item["documentNumber"]))
    return result[:25]


def unmatch_line(db: Session, *, line_id: uuid.UUID, commit: bool = True) -> tuple[BankStatementLine, list[dict]]:
    line = db.execute(
        select(BankStatementLine).where(BankStatementLine.id == line_id).with_for_update()
    ).scalar_one_or_none()
    if line is None:
        raise InvalidFinancialReferenceError("La línea bancaria no existe")
    matches = list(
        db.execute(
            select(ReconciliationMatch).where(
                ReconciliationMatch.bank_statement_line_id == line_id
            )
        ).scalars()
    )
    if not matches or line.status not in ("MATCHED", "PARTIAL"):
        raise InvalidFinancialReferenceError("La línea no tiene conciliaciones activas para deshacer")
    history = [
        {
            "matchId": str(match.id),
            "accountingDocumentId": str(match.accounting_document_id),
            "matchedAmount": str(match.matched_amount),
        }
        for match in matches
    ]
    db.execute(
        delete(ReconciliationMatch).where(ReconciliationMatch.bank_statement_line_id == line_id)
    )
    line.status = "UNMATCHED"
    if commit:
        db.commit()
        db.refresh(line)
    else:
        db.flush()
    return line, history


def release_fund_restriction(db: Session, *, restriction_id: uuid.UUID, commit: bool = True) -> FundRestriction:
    restriction = db.execute(
        select(FundRestriction).where(FundRestriction.id == restriction_id).with_for_update()
    ).scalar_one_or_none()
    if restriction is None:
        raise InvalidFinancialReferenceError("La restricción de fondos no existe")
    if not restriction.active:
        raise InvalidFinancialReferenceError("La restricción ya fue liberada")
    restriction.active = False
    if commit:
        db.commit()
        db.refresh(restriction)
    else:
        db.flush()
    return restriction


def reserved_amount(
    db: Session,
    *,
    treasury_account_id: uuid.UUID,
    allowed_project_id: uuid.UUID | None = None,
) -> Decimal:
    stmt = select(func.coalesce(func.sum(FundRestriction.amount), 0)).where(
        FundRestriction.treasury_account_id == treasury_account_id,
        FundRestriction.active.is_(True),
    )
    if allowed_project_id is not None:
        stmt = stmt.where(
            (FundRestriction.restricted_for_project_id.is_(None))
            | (FundRestriction.restricted_for_project_id != allowed_project_id)
        )
    return Decimal(db.execute(stmt).scalar_one())


def available_balance(
    db: Session,
    *,
    treasury_account_id: uuid.UUID,
    allowed_project_id: uuid.UUID | None = None,
) -> tuple[Decimal, Decimal, Decimal]:
    account = db.get(TreasuryAccount, treasury_account_id)
    if account is None:
        raise InvalidFinancialReferenceError("La cuenta de tesorería no existe")
    balance = treasury_service.treasury_account_balance(db, account)
    reserved = reserved_amount(
        db,
        treasury_account_id=treasury_account_id,
        allowed_project_id=allowed_project_id,
    )
    return balance, reserved, balance - reserved


def assert_outflow_available(
    db: Session,
    *,
    treasury_account_id: uuid.UUID,
    amount: Decimal,
    allowed_project_id: uuid.UUID | None = None,
) -> None:
    if amount <= 0:
        raise InvalidFinancialReferenceError("El importe de salida debe ser positivo")
    _balance, _reserved, available = available_balance(
        db,
        treasury_account_id=treasury_account_id,
        allowed_project_id=allowed_project_id,
    )
    if amount > available:
        raise InvalidFinancialReferenceError(
            "Saldo disponible insuficiente: existen fondos activos restringidos que no pueden utilizarse para esta operación"
        )
