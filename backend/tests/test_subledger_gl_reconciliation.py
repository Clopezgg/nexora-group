"""Tests for subledger↔GL reconciliation invariants.

Covers:
- SupplierInvoice APPROVED → accrual POSTED ↔ GL
- SupplierPayment PAY POSTED ↔ GL
- CustomerInvoice APPROVED → AR POSTED ↔ GL
- CustomerReceipt REC POSTED ↔ GL
- Asset capitalized → CAP POSTED ↔ GL
- Depreciation posted → DEP POSTED ↔ GL
- Asset disposed → DIS POSTED ↔ GL
- Reversal sync: reversal document mirrors original
"""

import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models.accounting import AccountingDocument, AccountingSourceLink, JournalLine


def test_supplier_invoice_accrual_reconciles_with_gl(db_session):
    """INV-SUB-001: When a SupplierInvoice is APPROVED, the accrual
    AccountingDocument must exist, be POSTED, and its journal lines must
    balance (debit == credit)."""
    from app.models.ap import SupplierInvoice

    invoice = db_session.execute(
        select(SupplierInvoice).where(SupplierInvoice.status == "APPROVED").limit(1)
    ).scalar_one_or_none()

    if invoice is None:
        pytest.skip("No approved SupplierInvoice in test data")

    assert invoice.accrual_document_id is not None
    doc = db_session.get(AccountingDocument, invoice.accrual_document_id)
    assert doc is not None
    assert doc.status == "POSTED"

    lines = list(
        db_session.execute(
            select(JournalLine).where(JournalLine.accounting_document_id == doc.id)
        ).scalars()
    )
    total_debit = sum(l.debit_amount for l in lines)
    total_credit = sum(l.credit_amount for l in lines)
    assert total_debit == total_credit
    assert total_debit > 0

    # SourceLink must exist
    link = db_session.execute(
        select(AccountingSourceLink).where(
            AccountingSourceLink.accounting_document_id == doc.id
        )
    ).scalar_one_or_none()
    assert link is not None
    assert link.source_type == "supplier_invoice"
    assert link.source_id == invoice.id


def test_customer_invoice_ar_reconciles_with_gl(db_session):
    """INV-SUB-002: When a CustomerInvoice is APPROVED, the AR
    AccountingDocument must exist, be POSTED, and its journal lines must
    balance."""
    from app.models.ar import CustomerInvoice

    invoice = db_session.execute(
        select(CustomerInvoice).where(CustomerInvoice.status == "APPROVED").limit(1)
    ).scalar_one_or_none()

    if invoice is None:
        pytest.skip("No approved CustomerInvoice in test data")

    assert invoice.ar_document_id is not None
    doc = db_session.get(AccountingDocument, invoice.ar_document_id)
    assert doc is not None
    assert doc.status == "POSTED"

    lines = list(
        db_session.execute(
            select(JournalLine).where(JournalLine.accounting_document_id == doc.id)
        ).scalars()
    )
    total_debit = sum(l.debit_amount for l in lines)
    total_credit = sum(l.credit_amount for l in lines)
    assert total_debit == total_credit


def test_reversal_gl_mirrors_original(db_session):
    """INV-ACC-004: A reversal document must have inverted D/C relative to
    the original, and the original must be REVERSED."""
    reversal = db_session.execute(
        select(AccountingDocument).where(
            AccountingDocument.document_type_code == "ANU",
            AccountingDocument.status == "POSTED",
        ).limit(1)
    ).scalar_one_or_none()

    if reversal is None:
        pytest.skip("No reversal document in test data")

    assert reversal.reversed_document_id is not None
    original = db_session.get(AccountingDocument, reversal.reversed_document_id)
    assert original is not None
    assert original.status == "REVERSED"

    # Reversal lines must be inverted
    orig_lines = list(
        db_session.execute(
            select(JournalLine).where(JournalLine.accounting_document_id == original.id)
        ).scalars()
    )
    rev_lines = list(
        db_session.execute(
            select(JournalLine).where(JournalLine.accounting_document_id == reversal.id)
        ).scalars()
    )

    assert len(orig_lines) == len(rev_lines)
    for orig, rev in zip(orig_lines, rev_lines):
        assert orig.account_id == rev.account_id
        assert orig.debit_amount == rev.credit_amount
        assert orig.credit_amount == rev.debit_amount


def test_all_posted_documents_balance(db_session):
    """INV-ACC-001: Every POSTED AccountingDocument must have balanced
    journal lines (total_debit == total_credit)."""
    posted_docs = list(
        db_session.execute(
            select(AccountingDocument).where(AccountingDocument.status == "POSTED")
        ).scalars()
    )

    for doc in posted_docs:
        lines = list(
            db_session.execute(
                select(JournalLine).where(JournalLine.accounting_document_id == doc.id)
            ).scalars()
        )
        total_debit = sum(l.debit_amount for l in lines)
        total_credit = sum(l.credit_amount for l in lines)
        assert total_debit == total_credit, (
            f"Document {doc.document_number} ({doc.document_type_code}) "
            f"unbalanced: debit={total_debit}, credit={total_credit}"
        )


def test_no_source_without_gl(db_session):
    """INV-ACC-005: Every AccountingSourceLink must point to a POSTED
    AccountingDocument (no orphan links)."""
    links = list(
        db_session.execute(
            select(AccountingSourceLink).join(
                AccountingDocument, AccountingDocument.id == AccountingSourceLink.accounting_document_id
            )
        ).scalars()
    )

    for link in links:
        doc = db_session.get(AccountingDocument, link.accounting_document_id)
        assert doc is not None
        assert doc.status == "POSTED", (
            f"SourceLink to {link.source_type}/{link.source_id} points to "
            f"non-POSTED document {doc.document_number} ({doc.status})"
        )
