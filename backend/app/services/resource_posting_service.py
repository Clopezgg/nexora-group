import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.errors import InvalidFinancialReferenceError
from app.models.accounting import AccountingDocument, AccountingSourceLink
from app.models.company import Company
from app.models.resource_posting import RESOURCE_POSTING_SOURCES, ResourcePostingConfig
from app.services import posting_service
from app.services.financial_validation_service import assert_account_belongs_to_company
from app.services.posting_service import JournalLineInput

_DOCUMENT_TYPES = {
    "FUEL": "FUE",
    "MAINTENANCE": "MNT",
    "LABOR": "LAB",
}
_SOURCE_LINK_TYPES = {
    "FUEL": "fuel_log",
    "MAINTENANCE": "maintenance_order",
    "LABOR": "time_entry",
}


def _validate_source(source_type: str) -> None:
    if source_type not in RESOURCE_POSTING_SOURCES:
        raise InvalidFinancialReferenceError(f"Origen de posting de recursos inválido: {source_type}")


def list_configs(db: Session, *, company_id: uuid.UUID) -> list[ResourcePostingConfig]:
    return list(
        db.execute(
            select(ResourcePostingConfig)
            .where(ResourcePostingConfig.company_id == company_id)
            .order_by(ResourcePostingConfig.source_type)
        ).scalars()
    )


def upsert_config(
    db: Session,
    *,
    company_id: uuid.UUID,
    source_type: str,
    expense_account_id: uuid.UUID,
    offset_account_id: uuid.UUID,
    active: bool = True,
    commit: bool = True,
) -> ResourcePostingConfig:
    _validate_source(source_type)
    expense = assert_account_belongs_to_company(
        db, account_id=expense_account_id, company_id=company_id, field_name="expense_account_id"
    )
    offset = assert_account_belongs_to_company(
        db, account_id=offset_account_id, company_id=company_id, field_name="offset_account_id"
    )
    if expense.account_type != "EXPENSE":
        raise InvalidFinancialReferenceError("expense_account_id debe ser una cuenta EXPENSE postable")
    if offset.account_type != "LIABILITY":
        raise InvalidFinancialReferenceError("offset_account_id debe ser una cuenta LIABILITY postable")
    row = db.execute(
        select(ResourcePostingConfig)
        .where(
            ResourcePostingConfig.company_id == company_id,
            ResourcePostingConfig.source_type == source_type,
        )
        .with_for_update()
    ).scalar_one_or_none()
    if row is None:
        row = ResourcePostingConfig(
            company_id=company_id,
            source_type=source_type,
            expense_account_id=expense_account_id,
            offset_account_id=offset_account_id,
            active=active,
        )
        db.add(row)
    else:
        row.expense_account_id = expense_account_id
        row.offset_account_id = offset_account_id
        row.active = active
    if commit:
        db.commit()
        db.refresh(row)
    else:
        db.flush()
    return row


def _existing_document(
    db: Session, *, source_type: str, source_id: uuid.UUID
) -> AccountingDocument | None:
    source_link_type = _SOURCE_LINK_TYPES[source_type]
    return db.execute(
        select(AccountingDocument)
        .join(AccountingSourceLink, AccountingSourceLink.accounting_document_id == AccountingDocument.id)
        .where(
            AccountingSourceLink.source_type == source_link_type,
            AccountingSourceLink.source_id == source_id,
        )
        .order_by(AccountingDocument.created_at)
    ).scalar_one_or_none()


def post_resource_cost(
    db: Session,
    *,
    company_id: uuid.UUID,
    source_type: str,
    source_id: uuid.UUID,
    amount: Decimal,
    scope: str,
    project_id: uuid.UUID | None,
    description: str,
) -> AccountingDocument:
    """Post one resource cost exactly once.

    The business event and accounting document are expected to share the caller's
    transaction (`post_manual(commit=False)`). A pre-existing source link is
    returned rather than posting twice, so retries remain idempotent.
    """
    _validate_source(source_type)
    existing = _existing_document(db, source_type=source_type, source_id=source_id)
    if existing is not None:
        return existing
    if amount <= 0:
        raise InvalidFinancialReferenceError("El costo a contabilizar debe ser mayor que cero")

    config = db.execute(
        select(ResourcePostingConfig).where(
            ResourcePostingConfig.company_id == company_id,
            ResourcePostingConfig.source_type == source_type,
            ResourcePostingConfig.active.is_(True),
        )
    ).scalar_one_or_none()
    if config is None:
        raise InvalidFinancialReferenceError(
            f"Falta configuración contable activa para {source_type}; define cuentas de gasto y contrapartida en Configuración"
        )
    expense = assert_account_belongs_to_company(
        db,
        account_id=config.expense_account_id,
        company_id=company_id,
        field_name="expense_account_id",
    )
    offset = assert_account_belongs_to_company(
        db,
        account_id=config.offset_account_id,
        company_id=company_id,
        field_name="offset_account_id",
    )
    if expense.account_type != "EXPENSE":
        raise InvalidFinancialReferenceError("La cuenta de gasto configurada ya no es EXPENSE postable")
    if offset.account_type != "LIABILITY":
        raise InvalidFinancialReferenceError("La contrapartida configurada ya no es LIABILITY postable")

    company = db.get(Company, company_id)
    if company is None or not company.functional_currency_code:
        raise InvalidFinancialReferenceError(
            "La compañía debe definir moneda funcional antes del posting automático de recursos"
        )

    return posting_service.post_manual(
        db,
        company_id=company_id,
        document_type_code=_DOCUMENT_TYPES[source_type],
        scope=scope,
        project_id=project_id,
        currency_code=company.functional_currency_code,
        lines=[
            JournalLineInput(
                account_id=expense.id,
                debit_amount=amount,
                description=description,
                project_id=project_id,
            ),
            JournalLineInput(
                account_id=offset.id,
                credit_amount=amount,
                description=description,
                project_id=project_id,
            ),
        ],
        description=description,
        source_type=_SOURCE_LINK_TYPES[source_type],
        source_id=source_id,
        commit=False,
    )
