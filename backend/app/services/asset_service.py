import uuid
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.errors import DepreciationAlreadyPostedError, InvalidAssetStateError
from app.models.accounting import AccountingDocument
from app.models.ap import SupplierInvoice
from app.models.asset import ASSET_DISPOSAL_STATUSES, ASSET_STATUSES, DepreciationEntry, FixedAsset
from app.models.chart_of_accounts import Account
from app.repositories import asset_repository
from app.services import posting_service
from app.services.financial_validation_service import (
    assert_account_belongs_to_company,
    assert_cost_center_belongs_to_company,
    assert_operation_scope,
    assert_project_belongs_to_company,
)

"""Fixed Assets / straight-line depreciation (orden maestra §62/§69,
docs/ACCOUNTING.md). `create_fixed_asset` numera cada activo vía nombre
libre (no requiere NumberSequence -- a diferencia de un documento contable,
un FixedAsset no es en sí un AccountingDocument); `generate_depreciation_entry`
sí pasa por el Posting Engine central (posting_service.post_manual), nunca
construye JournalLine a mano (CLAUDE.md §8)."""

_ASSET_TERMINAL_STATUSES = ("DISPOSED", "RETIRED")
_CAPITALIZABLE_INVOICE_STATUSES = (
    "APPROVED",
    "SCHEDULED",
    "PARTIALLY_PAID",
    "PAID",
    "RECONCILED",
)


def _assert_account_type(
    db: Session,
    *,
    account_id: uuid.UUID,
    company_id: uuid.UUID,
    expected_type: str,
    field_name: str,
) -> None:
    assert_account_belongs_to_company(
        db,
        account_id=account_id,
        company_id=company_id,
        field_name=field_name,
    )
    account = db.get(Account, account_id)
    if account is None or account.account_type != expected_type or not account.is_postable:
        raise InvalidAssetStateError(
            f"{field_name} debe ser una cuenta registrable {expected_type} de la compañía"
        )


def create_fixed_asset(
    db: Session,
    *,
    company_id: uuid.UUID,
    category: str,
    name: str,
    acquisition_date: date,
    cost: Decimal,
    currency_code: str,
    useful_life_months: int,
    salvage_value: Decimal,
    location: str | None,
    responsible: str | None,
    scope: str,
    project_id: uuid.UUID | None,
    cost_center_id: uuid.UUID | None,
    depreciation_expense_account_id: uuid.UUID,
    accumulated_depreciation_account_id: uuid.UUID,
    commit: bool = True,
) -> FixedAsset:
    assert_operation_scope(scope, project_id)
    assert_project_belongs_to_company(db, project_id=project_id, company_id=company_id)
    assert_cost_center_belongs_to_company(db, cost_center_id=cost_center_id, company_id=company_id)
    _assert_account_type(
        db,
        account_id=depreciation_expense_account_id,
        company_id=company_id,
        expected_type="EXPENSE",
        field_name="depreciation_expense_account_id",
    )
    _assert_account_type(
        db,
        account_id=accumulated_depreciation_account_id,
        company_id=company_id,
        expected_type="ASSET",
        field_name="accumulated_depreciation_account_id",
    )
    asset = asset_repository.create_fixed_asset(
        db,
        company_id=company_id,
        category=category,
        name=name,
        acquisition_date=acquisition_date,
        cost=cost,
        currency_code=currency_code,
        useful_life_months=useful_life_months,
        salvage_value=salvage_value,
        location=location,
        responsible=responsible,
        scope=scope,
        project_id=project_id,
        cost_center_id=cost_center_id,
        depreciation_expense_account_id=depreciation_expense_account_id,
        accumulated_depreciation_account_id=accumulated_depreciation_account_id,
    )
    if commit:
        db.commit()
        db.refresh(asset)
    else:
        db.flush()
    return asset


def capitalize_supplier_invoice_as_asset(
    db: Session,
    *,
    supplier_invoice_id: uuid.UUID,
    category: str,
    name: str,
    useful_life_months: int,
    salvage_value: Decimal,
    location: str | None,
    responsible: str | None,
    asset_account_id: uuid.UUID,
    depreciation_expense_account_id: uuid.UUID,
    accumulated_depreciation_account_id: uuid.UUID,
    commit: bool = True,
) -> FixedAsset:
    invoice = db.execute(
        select(SupplierInvoice)
        .where(SupplierInvoice.id == supplier_invoice_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).scalar_one_or_none()
    if invoice is None:
        raise ValueError(f"SupplierInvoice {supplier_invoice_id} no existe")
    if invoice.status not in _CAPITALIZABLE_INVOICE_STATUSES:
        raise InvalidAssetStateError(
            f"La factura debe estar aprobada para capitalizarse (estado actual: {invoice.status})"
        )
    if invoice.accrual_document_id is None:
        raise InvalidAssetStateError("La factura aprobada no tiene un accrual contable trazable")
    accrual = db.get(AccountingDocument, invoice.accrual_document_id)
    if accrual is None or accrual.status != "POSTED":
        raise InvalidAssetStateError("El accrual de la factura no está POSTED y no puede capitalizarse")
    existing = db.execute(
        select(FixedAsset.id).where(FixedAsset.supplier_invoice_id == invoice.id)
    ).scalar_one_or_none()
    if existing is not None:
        raise InvalidAssetStateError("La factura ya fue capitalizada como activo fijo")

    _assert_account_type(
        db,
        account_id=asset_account_id,
        company_id=invoice.company_id,
        expected_type="ASSET",
        field_name="asset_account_id",
    )
    total = invoice.amount + invoice.tax_amount
    if salvage_value >= total:
        raise InvalidAssetStateError("salvage_value debe ser menor que el costo capitalizado")

    asset = create_fixed_asset(
        db,
        company_id=invoice.company_id,
        category=category,
        name=name,
        acquisition_date=invoice.invoice_date,
        cost=total,
        currency_code=invoice.currency_code,
        useful_life_months=useful_life_months,
        salvage_value=salvage_value,
        location=location,
        responsible=responsible,
        scope=invoice.scope,
        project_id=invoice.project_id,
        cost_center_id=invoice.cost_center_id,
        depreciation_expense_account_id=depreciation_expense_account_id,
        accumulated_depreciation_account_id=accumulated_depreciation_account_id,
        commit=False,
    )
    asset.supplier_invoice_id = invoice.id
    asset.capitalization_account_id = asset_account_id
    capitalization = posting_service.post_manual(
        db,
        company_id=invoice.company_id,
        document_type_code="CAP",
        scope=invoice.scope,
        project_id=invoice.project_id,
        currency_code=invoice.currency_code,
        effective_date=invoice.invoice_date,
        lines=[
            posting_service.JournalLineInput(
                account_id=asset_account_id,
                debit_amount=total,
                description=f"Capitalización {asset.name} desde factura {invoice.invoice_number}",
                project_id=invoice.project_id,
                cost_center_id=invoice.cost_center_id,
            ),
            posting_service.JournalLineInput(
                account_id=invoice.expense_account_id,
                credit_amount=total,
                description=f"Reclasificación factura {invoice.invoice_number}",
                project_id=invoice.project_id,
                cost_center_id=invoice.cost_center_id,
            ),
        ],
        description=f"Capitalización activo {asset.name} desde factura {invoice.invoice_number}",
        source_type="fixed_asset",
        source_id=asset.id,
        commit=False,
    )
    asset.capitalization_document_id = capitalization.id
    if commit:
        db.commit()
        db.refresh(asset)
    else:
        db.flush()
    return asset


def get_fixed_asset(db: Session, asset_id: uuid.UUID) -> FixedAsset | None:
    return asset_repository.get_fixed_asset(db, asset_id)


def list_fixed_assets(db: Session, *, company_id: uuid.UUID) -> list[FixedAsset]:
    return asset_repository.list_fixed_assets(db, company_id=company_id)


def change_asset_status(db: Session, *, asset_id: uuid.UUID, status: str, commit: bool = True) -> FixedAsset:
    asset = asset_repository.get_fixed_asset(db, asset_id)
    if asset is None:
        raise ValueError(f"FixedAsset {asset_id} no existe")
    if status not in ASSET_STATUSES:
        raise InvalidAssetStateError(f"status inválido: {status!r}")
    if asset.status in _ASSET_TERMINAL_STATUSES:
        raise InvalidAssetStateError(
            f"El activo {asset.id} está {asset.status}; no admite más transiciones de estado"
        )
    asset.status = status
    if commit:
        db.commit()
        db.refresh(asset)
    else:
        db.flush()
    return asset


def apply_capitalization_reversal(
    db: Session, *, asset_id: uuid.UUID, document_type_code: str
) -> None:
    """Synchronize a formal CAP reversal with the source asset.

    A capitalized asset remains immutable historical evidence, but it can no
    longer be active once its capitalization leaves the ledger. Depreciation
    must be reversed first because silently retiring an asset with posted DEP
    entries would leave the asset subledger inconsistent with GL.
    """
    if document_type_code != "CAP":
        return
    asset = db.execute(
        select(FixedAsset)
        .where(FixedAsset.id == asset_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).scalar_one_or_none()
    if asset is None:
        raise ValueError(f"FixedAsset {asset_id} no existe")
    has_depreciation = db.execute(
        select(DepreciationEntry.id).where(DepreciationEntry.asset_id == asset.id).limit(1)
    ).first()
    if has_depreciation is not None:
        raise InvalidAssetStateError(
            "No se puede revertir la capitalización de un activo con depreciaciones registradas"
        )
    asset.status = "RETIRED"


def _accumulated_depreciation_total(db: Session, *, asset_id: uuid.UUID) -> Decimal:
    """Only effective DEP documents contribute to the asset subledger.

    `POSTED` only, never `REVERSED`: reversing a DEP document nets its effect
    to zero in GL (original REVERSED + its POSTED ANU reversal), but no
    compensating DepreciationEntry exists (no reversal hook for this source
    type), so counting a REVERSED entry would keep a subledger event that GL
    already canceled -- the forbidden GL-REVERSED/subledger-active divergence.
    """
    result = db.execute(
        select(func.coalesce(func.sum(DepreciationEntry.amount), 0))
        .outerjoin(AccountingDocument, AccountingDocument.id == DepreciationEntry.accounting_document_id)
        .where(
            DepreciationEntry.asset_id == asset_id,
            AccountingDocument.status == "POSTED",
        )
    ).scalar_one()
    return Decimal(str(result))


def dispose_asset(
    db: Session,
    *,
    asset_id: uuid.UUID,
    disposal_date: date,
    proceeds: Decimal = Decimal("0"),
    proceeds_account_id: uuid.UUID | None = None,
    commit: bool = True,
) -> FixedAsset:
    """INV-AST-005: dispose/retire an asset with proper GL posting.

    The disposal entry:
      Dr  Accumulated Depreciation  (reverse all depreciation)
      Dr  Cash/Receivable           (proceeds, if any)
      Cr  Fixed Asset               (historical cost)
      Dr/Cr Gain/Loss on Disposal   (plug to balance)

    An asset can only be disposed once (DISPOSED/RETIRED are terminal).
    Accumulated depreciation is computed from posted DepreciationEntries,
    not from a mutable column, ensuring the subledger stays consistent.
    """
    asset = db.execute(
        select(FixedAsset)
        .where(FixedAsset.id == asset_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).scalar_one_or_none()
    if asset is None:
        raise ValueError(f"FixedAsset {asset_id} no existe")
    if asset.status in ASSET_DISPOSAL_STATUSES:
        raise InvalidAssetStateError(
            f"El activo {asset.id} ya está {asset.status}; no se puede disponer nuevamente"
        )

    accumulated_depr = _accumulated_depreciation_total(db, asset_id=asset_id)
    book_value = asset.cost - accumulated_depr
    gain_loss = proceeds - book_value

    lines = []

    # Dr Accumulated Depreciation (reverse all depreciation)
    if accumulated_depr > 0:
        lines.append(
            posting_service.JournalLineInput(
                account_id=asset.accumulated_depreciation_account_id,
                debit_amount=accumulated_depr,
                description=f"Baja depreciación acumulada {asset.name}",
                project_id=asset.project_id,
                cost_center_id=asset.cost_center_id,
            )
        )

    # Dr Cash/Receivable for proceeds
    if proceeds > 0:
        if proceeds_account_id is None:
            raise InvalidAssetStateError(
                "Se requiere proceeds_account_id cuando hay ingresos por disposición"
            )
        assert_account_belongs_to_company(
            db, account_id=proceeds_account_id, company_id=asset.company_id,
            field_name="proceeds_account_id",
        )
        lines.append(
            posting_service.JournalLineInput(
                account_id=proceeds_account_id,
                debit_amount=proceeds,
                description=f"Ingresos por disposición {asset.name}",
                project_id=asset.project_id,
                cost_center_id=asset.cost_center_id,
            )
        )

    # Cr Fixed Asset (historical cost)
    asset_account_id = asset.capitalization_account_id
    if asset_account_id is None:
        raise InvalidAssetStateError(
            "El activo no tiene capitalization_account_id configurado para la baja"
        )
    lines.append(
        posting_service.JournalLineInput(
            account_id=asset_account_id,
            credit_amount=asset.cost,
            description=f"Baja activo {asset.name}",
            project_id=asset.project_id,
            cost_center_id=asset.cost_center_id,
        )
    )

    # Gain/Loss plug (Dr if loss, Cr if gain)
    if gain_loss < 0:
        # Loss: debit the loss account (use depreciation_expense_account as loss proxy)
        lines.append(
            posting_service.JournalLineInput(
                account_id=asset.depreciation_expense_account_id,
                debit_amount=abs(gain_loss),
                description=f"Pérdida por disposición {asset.name}",
                project_id=asset.project_id,
                cost_center_id=asset.cost_center_id,
            )
        )
    elif gain_loss > 0:
        # Gain: credit the gain account (use accumulated_depreciation_account as gain proxy)
        lines.append(
            posting_service.JournalLineInput(
                account_id=asset.accumulated_depreciation_account_id,
                credit_amount=gain_loss,
                description=f"Ganancia por disposición {asset.name}",
                project_id=asset.project_id,
                cost_center_id=asset.cost_center_id,
            )
        )

    disposal_doc = posting_service.post_manual(
        db,
        company_id=asset.company_id,
        document_type_code="DIS",
        scope=asset.scope,
        project_id=asset.project_id,
        currency_code=asset.currency_code,
        effective_date=disposal_date,
        lines=lines,
        description=f"Disposición activo {asset.name}",
        source_type="fixed_asset",
        source_id=asset.id,
        commit=False,
    )

    asset.status = "DISPOSED"
    asset.disposal_date = disposal_date
    asset.disposal_proceeds = proceeds
    asset.disposal_account_id = proceeds_account_id
    asset.disposal_document_id = disposal_doc.id
    asset.accumulated_depreciation = accumulated_depr

    if commit:
        db.commit()
        db.refresh(asset)
    else:
        db.flush()
    return asset


def _monthly_depreciation_amount(asset: FixedAsset) -> Decimal:
    """Straight-line: (cost - salvage_value) / useful_life_months, redondeado
    a 2 decimales. Nunca un número inventado -- siempre derivado de los
    campos reales del activo."""
    raw = (asset.cost - asset.salvage_value) / Decimal(asset.useful_life_months)
    return raw.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def generate_depreciation_entry(
    db: Session,
    *,
    asset_id: uuid.UUID,
    period_start: date,
    period_end: date,
    post: bool = True,
    commit: bool = True,
) -> DepreciationEntry:
    """INV-AST-001: un mismo asset+periodo nunca genera dos entries/postings
    DEP. La verificación aquí es defensa en profundidad (rechazo temprano,
    mensaje de dominio claro); el constraint real de PostgreSQL
    (`uq_depreciation_entries_asset_period`) es la garantía última bajo
    escritura concurrente."""
    asset = asset_repository.get_fixed_asset(db, asset_id)
    if asset is None:
        raise ValueError(f"FixedAsset {asset_id} no existe")
    if asset.status in _ASSET_TERMINAL_STATUSES:
        raise InvalidAssetStateError(
            f"El activo {asset.id} está {asset.status}; no se puede depreciar"
        )
    if period_end < asset.acquisition_date:
        raise InvalidAssetStateError("No se puede depreciar antes de la fecha de adquisición")

    existing = asset_repository.get_depreciation_entry_for_period(
        db, asset_id=asset_id, period_start=period_start
    )
    if existing is not None:
        raise DepreciationAlreadyPostedError(
            f"Ya existe un DepreciationEntry para el activo {asset_id} en el periodo "
            f"{period_start.isoformat()}"
        )

    already_depreciated = _accumulated_depreciation_total(db, asset_id=asset_id)
    depreciable_base = asset.cost - asset.salvage_value
    remaining_base = depreciable_base - already_depreciated
    if remaining_base <= 0:
        raise InvalidAssetStateError("El activo ya alcanzó su base depreciable")
    amount = min(_monthly_depreciation_amount(asset), remaining_base).quantize(Decimal("0.01"))

    entry = asset_repository.create_depreciation_entry(
        db, asset_id=asset_id, period_start=period_start, period_end=period_end, amount=amount
    )

    if post:
        document = posting_service.post_manual(
            db,
            company_id=asset.company_id,
            document_type_code="DEP",
            scope=asset.scope,
            project_id=asset.project_id,
            currency_code=asset.currency_code,
            effective_date=period_end,
            lines=[
                posting_service.JournalLineInput(
                    account_id=asset.depreciation_expense_account_id,
                    debit_amount=amount,
                    description=f"Depreciación {asset.name} {period_start.isoformat()}",
                    project_id=asset.project_id,
                    cost_center_id=asset.cost_center_id,
                ),
                posting_service.JournalLineInput(
                    account_id=asset.accumulated_depreciation_account_id,
                    credit_amount=amount,
                    description=f"Depreciación acumulada {asset.name} {period_start.isoformat()}",
                    project_id=asset.project_id,
                    cost_center_id=asset.cost_center_id,
                ),
            ],
            source_type="DepreciationEntry",
            source_id=entry.id,
            commit=False,
        )
        entry.accounting_document_id = document.id

    if commit:
        db.commit()
        db.refresh(entry)
    else:
        db.flush()
    return entry


def list_depreciation_entries(db: Session, *, asset_id: uuid.UUID) -> list[DepreciationEntry]:
    return asset_repository.list_depreciation_entries(db, asset_id=asset_id)


def bulk_depreciate_all_assets(
    db: Session,
    *,
    company_id: uuid.UUID,
    period_start: date,
    period_end: date,
    commit: bool = True,
) -> list[DepreciationEntry]:
    """Bulk depreciation run for all active assets in a company.

    Generates a DepreciationEntry (with GL posting) for each active asset
    that doesn't already have an entry for this period. Skips assets that
    already have a DEP entry for the period (idempotent). Returns the list
    of entries created.
    """
    assets = db.execute(
        select(FixedAsset).where(
            FixedAsset.company_id == company_id,
            FixedAsset.status.in_(["ACTIVE", "UNDER_MAINTENANCE"]),
        )
    ).scalars().all()

    created = []
    for asset in assets:
        existing = asset_repository.get_depreciation_entry_for_period(
            db, asset_id=asset.id, period_start=period_start
        )
        if existing is not None:
            continue

        entry = generate_depreciation_entry(
            db,
            asset_id=asset.id,
            period_start=period_start,
            period_end=period_end,
            post=True,
            commit=False,
        )
        created.append(entry)

    if commit:
        db.commit()
        for entry in created:
            db.refresh(entry)
    else:
        db.flush()
    return created
