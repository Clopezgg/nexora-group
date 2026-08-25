import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.errors import (
    InvalidFinancialReferenceError,
    InvalidInvoiceStateError,
    InvalidTransferError,
)
from app.models.accounting import AccountingDocument, JournalLine
from app.models.treasury import (
    BankStatement,
    BankStatementLine,
    CashClosing,
    FundRestriction,
    GeneralExpense,
    ReconciliationMatch,
    Remittance,
    TreasuryAccount,
    TreasuryTransfer,
)
from app.services import posting_service
from app.services.financial_validation_service import (
    assert_account_belongs_to_company,
    assert_project_belongs_to_company,
)
from app.services.posting_service import JournalLineInput

"""Treasury (orden maestra §26-33, CLAUDE.md §7/§8). Todo movimiento de
dinero real pasa por posting_service.post_manual -- este servicio solo
arma las líneas correctas para cada caso de negocio (remesa, gasto
general, transferencia, cierre de caja) y nunca contabiliza a mano."""


def account_balance(db: Session, *, gl_account_id: uuid.UUID) -> Decimal:
    """Saldo contable de una cuenta (débito - crédito). Cuentas de
    Tesorería son ASSET, así que un saldo positivo es normal."""
    lines = db.execute(
        select(JournalLine).where(JournalLine.account_id == gl_account_id)
    ).scalars()
    total = Decimal("0")
    for line in lines:
        total += line.debit_amount - line.credit_amount
    return total


def treasury_account_balance(db: Session, treasury_account: TreasuryAccount) -> Decimal:
    return account_balance(db, gl_account_id=treasury_account.gl_account_id)


def create_treasury_account(
    db: Session,
    *,
    company_id: uuid.UUID,
    name: str,
    kind: str,
    institution: str | None,
    account_reference: str | None,
    currency_code: str,
    gl_account_id: uuid.UUID,
) -> TreasuryAccount:
    assert_account_belongs_to_company(
        db,
        account_id=gl_account_id,
        company_id=company_id,
        field_name="gl_account_id",
    )
    existing_mapping = db.execute(
        select(TreasuryAccount.id).where(TreasuryAccount.gl_account_id == gl_account_id)
    ).scalar_one_or_none()
    if existing_mapping is not None:
        raise InvalidFinancialReferenceError(
            "gl_account_id ya está asignada a otra cuenta de tesorería"
        )
    account = TreasuryAccount(
        company_id=company_id,
        name=name,
        kind=kind,
        institution=institution,
        account_reference=account_reference,
        currency_code=currency_code,
        gl_account_id=gl_account_id,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


def get_treasury_account(db: Session, *, treasury_account_id: uuid.UUID) -> TreasuryAccount | None:
    return db.get(TreasuryAccount, treasury_account_id)


def get_cash_closing(db: Session, *, cash_closing_id: uuid.UUID) -> CashClosing | None:
    return db.get(CashClosing, cash_closing_id)


def get_bank_statement(db: Session, *, bank_statement_id: uuid.UUID) -> BankStatement | None:
    return db.get(BankStatement, bank_statement_id)


def get_bank_statement_line(
    db: Session, *, bank_statement_line_id: uuid.UUID
) -> BankStatementLine | None:
    return db.get(BankStatementLine, bank_statement_line_id)


def company_id_for_bank_statement(db: Session, statement: BankStatement) -> uuid.UUID:
    account = db.get(TreasuryAccount, statement.treasury_account_id)
    if account is None:
        raise InvalidFinancialReferenceError("La cuenta del estado bancario no existe")
    return account.company_id


def company_id_for_bank_statement_line(db: Session, line: BankStatementLine) -> uuid.UUID:
    statement = db.get(BankStatement, line.bank_statement_id)
    if statement is None:
        raise InvalidFinancialReferenceError("El estado bancario de la línea no existe")
    return company_id_for_bank_statement(db, statement)


def register_remittance(
    db: Session,
    *,
    company_id: uuid.UUID,
    treasury_account_id: uuid.UUID,
    counter_account_id: uuid.UUID,
    sender: str,
    provider: str | None,
    channel: str | None,
    currency_code: str,
    original_amount: Decimal,
    fx_rate: Decimal,
    reference: str | None,
    remittance_date: date,
    notes: str | None,
    commit: bool = True,
) -> Remittance:
    """Siempre scope=CENTRAL, project_id=None (orden maestra §27) -- lo
    aplica post_manual, que ya rechaza cualquier otra combinación."""
    if original_amount <= 0 or fx_rate <= 0:
        raise InvalidFinancialReferenceError("La remesa requiere montos y tasa positivos")
    treasury_account = db.get(TreasuryAccount, treasury_account_id)
    if treasury_account is None:
        raise ValueError(f"TreasuryAccount {treasury_account_id} no existe")
    if treasury_account.company_id != company_id:
        raise InvalidFinancialReferenceError(
            "treasury_account_id debe pertenecer a la compañía de la remesa"
        )
    if treasury_account.currency_code != currency_code:
        raise InvalidFinancialReferenceError(
            "treasury_account_id debe usar la moneda de la remesa"
        )
    assert_account_belongs_to_company(
        db,
        account_id=counter_account_id,
        company_id=company_id,
        field_name="counter_account_id",
    )

    base_amount = (original_amount * fx_rate).quantize(Decimal("0.01"))

    document = posting_service.post_manual(
        db,
        company_id=company_id,
        document_type_code="REM",
        scope="CENTRAL",
        project_id=None,
        currency_code=currency_code,
        fx_rate=fx_rate,
        lines=[
            JournalLineInput(
                account_id=treasury_account.gl_account_id,
                debit_amount=original_amount,
                description=f"Remesa de {sender}",
            ),
            JournalLineInput(
                account_id=counter_account_id,
                credit_amount=original_amount,
                description=f"Remesa de {sender}",
            ),
        ],
        description=f"Remesa de {sender} ({provider or 'sin proveedor'})",
        commit=False,
    )

    remittance = Remittance(
        company_id=company_id,
        treasury_account_id=treasury_account_id,
        counter_account_id=counter_account_id,
        sender=sender,
        provider=provider,
        channel=channel,
        currency_code=currency_code,
        original_amount=original_amount,
        fx_rate=fx_rate,
        base_amount=base_amount,
        reference=reference,
        remittance_date=remittance_date,
        notes=notes,
        accounting_document_id=document.id,
    )
    db.add(remittance)
    if commit:
        db.commit()
    else:
        db.flush()
    db.refresh(remittance)
    return remittance


def register_general_expense(
    db: Session,
    *,
    company_id: uuid.UUID,
    treasury_account_id: uuid.UUID,
    expense_account_id: uuid.UUID,
    category: str,
    amount: Decimal,
    currency_code: str,
    expense_date: date,
    description: str,
    commit: bool = True,
) -> GeneralExpense:
    """Siempre scope=GENERAL, project_id=None. NO consume Project Budget;
    se paga de inmediato contra Treasury (orden maestra §28)."""
    if amount <= 0:
        raise InvalidFinancialReferenceError("El gasto requiere amount > 0")
    treasury_account = db.get(TreasuryAccount, treasury_account_id)
    if treasury_account is None:
        raise ValueError(f"TreasuryAccount {treasury_account_id} no existe")
    if treasury_account.company_id != company_id:
        raise InvalidFinancialReferenceError(
            "treasury_account_id debe pertenecer a la compañía del gasto"
        )
    if treasury_account.currency_code != currency_code:
        raise InvalidFinancialReferenceError(
            "treasury_account_id debe usar la moneda del gasto"
        )
    assert_account_belongs_to_company(
        db,
        account_id=expense_account_id,
        company_id=company_id,
        field_name="expense_account_id",
    )

    document = posting_service.post_manual(
        db,
        company_id=company_id,
        document_type_code="GGE",
        scope="GENERAL",
        project_id=None,
        currency_code=currency_code,
        lines=[
            JournalLineInput(account_id=expense_account_id, debit_amount=amount, description=description),
            JournalLineInput(
                account_id=treasury_account.gl_account_id, credit_amount=amount, description=description
            ),
        ],
        description=description,
        commit=False,
    )

    expense = GeneralExpense(
        company_id=company_id,
        treasury_account_id=treasury_account_id,
        expense_account_id=expense_account_id,
        category=category,
        amount=amount,
        currency_code=currency_code,
        expense_date=expense_date,
        description=description,
        accounting_document_id=document.id,
    )
    db.add(expense)
    if commit:
        db.commit()
    else:
        db.flush()
    db.refresh(expense)
    return expense


def register_transfer(
    db: Session,
    *,
    company_id: uuid.UUID,
    source_treasury_account_id: uuid.UUID,
    destination_treasury_account_id: uuid.UUID,
    amount: Decimal,
    currency_code: str,
    transfer_date: date,
    notes: str | None,
    commit: bool = True,
) -> TreasuryTransfer:
    """NO Revenue, NO Expense -- transferencia de activos (orden maestra
    §30). scope=CENTRAL porque es administración central de tesorería."""
    if amount <= 0:
        raise InvalidTransferError("La transferencia requiere amount > 0")
    if source_treasury_account_id == destination_treasury_account_id:
        raise InvalidTransferError("La cuenta origen y destino no pueden ser la misma")

    source = db.get(TreasuryAccount, source_treasury_account_id)
    destination = db.get(TreasuryAccount, destination_treasury_account_id)
    if source is None or destination is None:
        raise ValueError("Cuenta de tesorería origen/destino no existe")
    if source.company_id != company_id or destination.company_id != company_id:
        raise InvalidFinancialReferenceError(
            "Las cuentas origen y destino deben pertenecer a la compañía de la transferencia"
        )
    if source.currency_code != currency_code or destination.currency_code != currency_code:
        raise InvalidTransferError(
            "Transferencia entre monedas distintas no soportada todavía "
            "(DEFERRED-FINAL-TRANSFER-FX-001)"
        )

    document = posting_service.post_manual(
        db,
        company_id=company_id,
        document_type_code="TRF",
        scope="CENTRAL",
        project_id=None,
        currency_code=currency_code,
        lines=[
            JournalLineInput(account_id=destination.gl_account_id, debit_amount=amount, description=notes),
            JournalLineInput(account_id=source.gl_account_id, credit_amount=amount, description=notes),
        ],
        description=notes or "Transferencia entre cuentas de tesorería",
        commit=False,
    )

    transfer = TreasuryTransfer(
        company_id=company_id,
        source_treasury_account_id=source_treasury_account_id,
        destination_treasury_account_id=destination_treasury_account_id,
        amount=amount,
        currency_code=currency_code,
        transfer_date=transfer_date,
        notes=notes,
        accounting_document_id=document.id,
    )
    db.add(transfer)
    if commit:
        db.commit()
    else:
        db.flush()
    db.refresh(transfer)
    return transfer


def create_cash_closing(
    db: Session,
    *,
    treasury_account_id: uuid.UUID,
    closing_date: date,
    opening_amount: Decimal,
    expected_amount: Decimal,
    counted_amount: Decimal,
    responsible_user_id: uuid.UUID,
) -> CashClosing:
    if opening_amount < 0 or expected_amount < 0 or counted_amount < 0:
        raise InvalidFinancialReferenceError("Los montos del cierre de caja no pueden ser negativos")
    treasury_account = db.get(TreasuryAccount, treasury_account_id)
    if treasury_account is None:
        raise InvalidFinancialReferenceError("treasury_account_id no existe")
    closing = CashClosing(
        treasury_account_id=treasury_account_id,
        closing_date=closing_date,
        opening_amount=opening_amount,
        expected_amount=expected_amount,
        counted_amount=counted_amount,
        difference_amount=counted_amount - expected_amount,
        responsible_user_id=responsible_user_id,
        status="DRAFT",
    )
    db.add(closing)
    db.commit()
    db.refresh(closing)
    return closing


def approve_cash_closing(
    db: Session,
    *,
    cash_closing_id: uuid.UUID,
    approved_by_user_id: uuid.UUID,
    difference_account_id: uuid.UUID | None,
    company_id: uuid.UUID,
    commit: bool = True,
) -> CashClosing:
    """Si hay diferencia (sobrante/faltante de caja), se contabiliza un
    ajuste GENERAL contra `difference_account_id` (obligatorio en ese
    caso). Sin diferencia, no hay posting -- solo aprobación."""
    closing = db.execute(
        select(CashClosing).where(CashClosing.id == cash_closing_id).with_for_update()
    ).scalar_one_or_none()
    if closing is None:
        raise ValueError(f"CashClosing {cash_closing_id} no existe")
    if closing.status != "DRAFT":
        raise InvalidInvoiceStateError(
            f"Solo se puede aprobar un cierre DRAFT (estado actual: {closing.status})"
        )
    treasury_account = db.get(TreasuryAccount, closing.treasury_account_id)
    if treasury_account is None or treasury_account.company_id != company_id:
        raise InvalidFinancialReferenceError(
            "El cierre de caja debe pertenecer a la compañía indicada"
        )

    if closing.difference_amount != 0:
        if difference_account_id is None:
            raise ValueError("difference_account_id es obligatorio cuando hay diferencia de caja")
        assert_account_belongs_to_company(
            db,
            account_id=difference_account_id,
            company_id=company_id,
            field_name="difference_account_id",
        )
        amount = abs(closing.difference_amount)
        if closing.difference_amount > 0:
            # Sobrante: aumenta la caja, se acredita la cuenta de diferencia.
            lines = [
                JournalLineInput(account_id=treasury_account.gl_account_id, debit_amount=amount),
                JournalLineInput(account_id=difference_account_id, credit_amount=amount),
            ]
        else:
            lines = [
                JournalLineInput(account_id=difference_account_id, debit_amount=amount),
                JournalLineInput(account_id=treasury_account.gl_account_id, credit_amount=amount),
            ]
        document = posting_service.post_manual(
            db,
            company_id=company_id,
            document_type_code="CCL",
            scope="GENERAL",
            project_id=None,
            currency_code=treasury_account.currency_code,
            lines=lines,
            description=f"Ajuste de cierre de caja {closing.id}",
            commit=False,
        )
        closing.accounting_document_id = document.id

    closing.status = "APPROVED"
    closing.approved_by_user_id = approved_by_user_id
    closing.approved_at = datetime.now(timezone.utc)
    if commit:
        db.commit()
    else:
        db.flush()
    db.refresh(closing)
    return closing


def create_bank_statement(
    db: Session,
    *,
    treasury_account_id: uuid.UUID,
    statement_date: date,
    opening_balance: Decimal,
    closing_balance: Decimal,
    reference: str | None,
) -> BankStatement:
    treasury_account = db.get(TreasuryAccount, treasury_account_id)
    if treasury_account is None:
        raise InvalidFinancialReferenceError("treasury_account_id no existe")
    statement = BankStatement(
        treasury_account_id=treasury_account_id,
        statement_date=statement_date,
        opening_balance=opening_balance,
        closing_balance=closing_balance,
        reference=reference,
    )
    db.add(statement)
    db.commit()
    db.refresh(statement)
    return statement


def add_bank_statement_line(
    db: Session, *, bank_statement_id: uuid.UUID, line_date: date, description: str, amount: Decimal
) -> BankStatementLine:
    """Append-only: una vez creada, esta línea nunca se edita/borra."""
    if amount == 0:
        raise InvalidFinancialReferenceError("Una línea bancaria no puede tener monto cero")
    if db.get(BankStatement, bank_statement_id) is None:
        raise InvalidFinancialReferenceError("bank_statement_id no existe")
    line = BankStatementLine(
        bank_statement_id=bank_statement_id,
        line_date=line_date,
        description=description,
        amount=amount,
        status="UNMATCHED",
    )
    db.add(line)
    db.commit()
    db.refresh(line)
    return line


def match_reconciliation_line(
    db: Session,
    *,
    bank_statement_line_id: uuid.UUID,
    accounting_document_id: uuid.UUID,
    matched_amount: Decimal,
    matched_by_user_id: uuid.UUID,
) -> ReconciliationMatch:
    if matched_amount <= 0:
        raise InvalidFinancialReferenceError("matched_amount debe ser positivo")
    line = db.execute(
        select(BankStatementLine)
        .where(BankStatementLine.id == bank_statement_line_id)
        .with_for_update()
    ).scalar_one_or_none()
    if line is None:
        raise ValueError(f"BankStatementLine {bank_statement_line_id} no existe")
    if line.status not in ("UNMATCHED", "PARTIAL"):
        raise InvalidFinancialReferenceError(
            f"Una línea {line.status} no admite nuevos matches"
        )
    statement = db.get(BankStatement, line.bank_statement_id)
    treasury_account = db.get(TreasuryAccount, statement.treasury_account_id)
    document = db.execute(
        select(AccountingDocument)
        .where(AccountingDocument.id == accounting_document_id)
        .with_for_update()
    ).scalar_one_or_none()
    if document is None:
        raise InvalidFinancialReferenceError("accounting_document_id no existe")
    if document.company_id != treasury_account.company_id:
        raise InvalidFinancialReferenceError(
            "El documento contable debe pertenecer a la compañía del estado bancario"
        )
    document_side = (
        JournalLine.debit_amount if line.amount > 0 else JournalLine.credit_amount
    )
    document_capacity = Decimal(
        db.execute(
            select(func.coalesce(func.sum(document_side), 0)).where(
                JournalLine.accounting_document_id == accounting_document_id,
                JournalLine.account_id == treasury_account.gl_account_id,
            )
        ).scalar_one()
    )
    if document_capacity <= 0:
        direction = "débito" if line.amount > 0 else "crédito"
        raise InvalidFinancialReferenceError(
            "El documento no contiene un movimiento de "
            f"{direction} en la cuenta GL de tesorería conciliada"
        )
    same_direction = (
        BankStatementLine.amount > 0
        if line.amount > 0
        else BankStatementLine.amount < 0
    )
    document_already_allocated = Decimal(
        db.execute(
            select(func.coalesce(func.sum(ReconciliationMatch.matched_amount), 0))
            .join(
                BankStatementLine,
                ReconciliationMatch.bank_statement_line_id == BankStatementLine.id,
            )
            .join(
                BankStatement,
                BankStatementLine.bank_statement_id == BankStatement.id,
            )
            .where(
                ReconciliationMatch.accounting_document_id == accounting_document_id,
                BankStatement.treasury_account_id == treasury_account.id,
                same_direction,
            )
        ).scalar_one()
    )
    if document_already_allocated + matched_amount > document_capacity:
        raise InvalidFinancialReferenceError(
            "La asignación acumulada excede el movimiento disponible del documento"
        )
    already_matched = db.execute(
        select(func.coalesce(func.sum(ReconciliationMatch.matched_amount), 0)).where(
            ReconciliationMatch.bank_statement_line_id == bank_statement_line_id
        )
    ).scalar_one()
    cumulative_amount = Decimal(already_matched) + matched_amount
    line_amount = abs(line.amount)
    if cumulative_amount > line_amount:
        raise InvalidFinancialReferenceError(
            f"La conciliación acumulada ({cumulative_amount}) excede la línea ({line_amount})"
        )

    match = ReconciliationMatch(
        bank_statement_line_id=bank_statement_line_id,
        accounting_document_id=accounting_document_id,
        matched_amount=matched_amount,
        matched_by_user_id=matched_by_user_id,
        matched_at=datetime.now(timezone.utc),
    )
    db.add(match)
    line.status = "MATCHED" if cumulative_amount == line_amount else "PARTIAL"
    db.commit()
    db.refresh(match)
    return match


def exclude_reconciliation_line(db: Session, *, bank_statement_line_id: uuid.UUID) -> BankStatementLine:
    line = db.execute(
        select(BankStatementLine)
        .where(BankStatementLine.id == bank_statement_line_id)
        .with_for_update()
    ).scalar_one_or_none()
    if line is None:
        raise ValueError(f"BankStatementLine {bank_statement_line_id} no existe")
    match_count = db.execute(
        select(func.count(ReconciliationMatch.id)).where(
            ReconciliationMatch.bank_statement_line_id == bank_statement_line_id
        )
    ).scalar_one()
    if line.status != "UNMATCHED" or match_count:
        raise InvalidFinancialReferenceError(
            "Solo una línea UNMATCHED sin historial de conciliación puede excluirse"
        )
    line.status = "EXCLUDED"
    db.commit()
    db.refresh(line)
    return line


def create_fund_restriction(
    db: Session,
    *,
    treasury_account_id: uuid.UUID,
    restricted_for_project_id: uuid.UUID | None,
    amount: Decimal,
    description: str,
) -> FundRestriction:
    """IMPORTANTE: esto nunca transfiere la propiedad del dinero al
    proyecto -- Treasury sigue siendo el dueño (CLAUDE.md §7)."""
    if amount <= 0:
        raise InvalidFinancialReferenceError("La restricción requiere amount > 0")
    treasury_account = db.get(TreasuryAccount, treasury_account_id)
    if treasury_account is None:
        raise InvalidFinancialReferenceError("treasury_account_id no existe")
    assert_project_belongs_to_company(
        db,
        project_id=restricted_for_project_id,
        company_id=treasury_account.company_id,
    )
    restriction = FundRestriction(
        treasury_account_id=treasury_account_id,
        restricted_for_project_id=restricted_for_project_id,
        amount=amount,
        description=description,
    )
    db.add(restriction)
    db.commit()
    db.refresh(restriction)
    return restriction
