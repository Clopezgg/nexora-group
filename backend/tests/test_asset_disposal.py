"""Tests for asset disposal with GL posting (Phase 2, F2.3-F2.5)."""

import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.domain.errors import InvalidAssetStateError
from app.models.accounting import AccountingDocument, JournalLine
from app.models.asset import FixedAsset
from app.models.chart_of_accounts import Account, ChartOfAccount
from app.models.company import Company
from app.models.currency import Currency
from app.models.document_type import DocumentType
from app.services import asset_service, posting_service


def _create_test_setup(db):
    currency = Currency(code="HNL", name="Lempira", symbol="L")
    db.add(currency)

    for code, name, prefix in [
        ("DEP", "Depreciación", "DEP"),
        ("ANU", "Anulación", "ANU"),
        ("DIS", "Disposición de activo fijo", "DIS"),
        ("INV", "Movimiento de inventario", "INV"),
    ]:
        db.add(DocumentType(code=code, name=name, number_prefix=prefix))

    company = Company(name="Test Disposal Co")
    db.add(company)
    db.flush()

    chart = ChartOfAccount(company_id=company.id, name="Test COA")
    db.add(chart)
    db.flush()

    accounts = {}
    for code, name, atype in [
        ("1500", "Fixed Assets", "ASSET"),
        ("1510", "Accumulated Depreciation", "ASSET"),
        ("6100", "Depreciation Expense", "EXPENSE"),
        ("1200", "Cash", "ASSET"),
    ]:
        acct = Account(
            chart_of_account_id=chart.id,
            code=code,
            name=name,
            account_type=atype,
            is_postable=True,
        )
        db.add(acct)
        accounts[code] = acct
    db.flush()
    return company, accounts


def _create_test_asset(db, company, accounts: dict, cost: Decimal = Decimal("10000")):
    asset = FixedAsset(
        company_id=company.id,
        category="EQUIPMENT",
        name="Test Equipment",
        acquisition_date=date(2025, 1, 1),
        cost=cost,
        currency_code="HNL",
        useful_life_months=60,
        salvage_value=Decimal("1000"),
        scope="GENERAL",
        depreciation_expense_account_id=accounts["6100"].id,
        accumulated_depreciation_account_id=accounts["1510"].id,
        capitalization_account_id=accounts["1500"].id,
    )
    db.add(asset)
    db.flush()
    return asset


def test_dispose_asset_posts_correct_gl(db_session):
    company, accounts = _create_test_setup(db_session)
    asset = _create_test_asset(db_session, company, accounts, cost=Decimal("10000"))

    for i in range(6):
        asset_service.generate_depreciation_entry(
            db_session,
            asset_id=asset.id,
            period_start=date(2025, i + 1, 1),
            period_end=date(2025, i + 1, 28),
            post=True,
            commit=False,
        )

    disposed = asset_service.dispose_asset(
        db_session,
        asset_id=asset.id,
        disposal_date=date(2025, 7, 1),
        proceeds=Decimal("5000"),
        proceeds_account_id=accounts["1200"].id,
        commit=False,
    )

    assert disposed.status == "DISPOSED"
    assert disposed.disposal_date == date(2025, 7, 1)
    assert disposed.disposal_proceeds == Decimal("5000")
    assert disposed.disposal_document_id is not None
    assert disposed.accumulated_depreciation == Decimal("900.00")

    doc = db_session.get(AccountingDocument, disposed.disposal_document_id)
    assert doc is not None
    assert doc.document_type_code == "DIS"
    assert doc.status == "POSTED"

    lines = list(
        db_session.execute(
            select(JournalLine).where(JournalLine.accounting_document_id == doc.id)
        ).scalars()
    )
    total_debit = sum(l.debit_amount for l in lines)
    total_credit = sum(l.credit_amount for l in lines)
    assert total_debit == total_credit


def test_dispose_asset_zero_proceeds(db_session):
    company, accounts = _create_test_setup(db_session)
    asset = _create_test_asset(db_session, company, accounts)

    disposed = asset_service.dispose_asset(
        db_session,
        asset_id=asset.id,
        disposal_date=date(2025, 7, 1),
        proceeds=Decimal("0"),
        commit=False,
    )

    assert disposed.status == "DISPOSED"
    assert disposed.disposal_proceeds == Decimal("0")


def test_dispose_already_disposed_raises(db_session):
    company, accounts = _create_test_setup(db_session)
    asset = _create_test_asset(db_session, company, accounts)

    asset_service.dispose_asset(
        db_session, asset_id=asset.id, disposal_date=date(2025, 7, 1), commit=False,
    )

    with pytest.raises(InvalidAssetStateError):
        asset_service.dispose_asset(
            db_session, asset_id=asset.id, disposal_date=date(2025, 8, 1), commit=False,
        )


def test_dispose_nonexistent_asset_raises(db_session):
    with pytest.raises(ValueError):
        asset_service.dispose_asset(
            db_session, asset_id=uuid.uuid4(), disposal_date=date(2025, 7, 1), commit=False,
        )


def test_dispose_proceeds_without_account_raises(db_session):
    company, accounts = _create_test_setup(db_session)
    asset = _create_test_asset(db_session, company, accounts)

    with pytest.raises(InvalidAssetStateError):
        asset_service.dispose_asset(
            db_session,
            asset_id=asset.id,
            disposal_date=date(2025, 7, 1),
            proceeds=Decimal("5000"),
            proceeds_account_id=None,
            commit=False,
        )


def test_reversed_depreciation_document_leaves_subledger(db_session):
    """A reversed DEP document netts to zero in GL; the asset subledger must
    NOT keep counting its amount (no compensating DepreciationEntry exists
    for the ANU reversal, so only POSTED documents are effective)."""
    company, accounts = _create_test_setup(db_session)
    asset = _create_test_asset(db_session, company, accounts)

    entry = asset_service.generate_depreciation_entry(
        db_session,
        asset_id=asset.id,
        period_start=date(2025, 1, 1),
        period_end=date(2025, 1, 28),
        post=True,
        commit=False,
    )

    reversal = posting_service.reverse_document(
        db_session, document_id=entry.accounting_document_id, reason="Corrección", commit=False,
    )
    assert reversal.document_type_code == "ANU"
    assert reversal.status == "POSTED"

    # Subledger accumulated depreciation must be zero after the reversal.
    disposed = asset_service.dispose_asset(
        db_session,
        asset_id=asset.id,
        disposal_date=date(2025, 2, 1),
        proceeds=Decimal("0"),
        commit=False,
    )
    assert disposed.accumulated_depreciation == Decimal("0")
    doc = db_session.get(AccountingDocument, disposed.disposal_document_id)
    assert doc.status == "POSTED"
    lines = list(
        db_session.execute(
            select(JournalLine).where(JournalLine.accounting_document_id == doc.id)
        ).scalars()
    )
    assert not any(l.account_id == accounts["1510"].id for l in lines)
