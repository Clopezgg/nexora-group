from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain.errors import (
    InvalidFinancialReferenceError,
    InvalidOperationScopeError,
    UnbalancedJournalEntryError,
)
from app.services.posting_service import (
    JournalLineInput,
    _validate_balance,
    _validate_line_scope,
    _validate_tax_lines,
)


def _line(*, project_id=None, debit="100", credit="0"):
    return JournalLineInput(
        account_id=uuid4(),
        project_id=project_id,
        debit_amount=Decimal(debit),
        credit_amount=Decimal(credit),
    )


def test_empty_journal_is_rejected():
    with pytest.raises(UnbalancedJournalEntryError):
        _validate_balance([])


def test_project_posting_requires_every_line_to_match_header_project():
    project_id = uuid4()
    with pytest.raises(InvalidOperationScopeError):
        _validate_line_scope(
            "PROJECT",
            project_id,
            [_line(project_id=project_id), _line(project_id=None, debit="0", credit="100")],
        )


def test_general_posting_allows_project_dimension_on_line():
    project_id = uuid4()
    _validate_line_scope(
        "GENERAL",
        None,
        [_line(project_id=project_id), _line(project_id=project_id, debit="0", credit="100")],
    )


def test_negative_tax_amount_is_rejected():
    with pytest.raises(UnbalancedJournalEntryError):
        _validate_tax_lines([(uuid4(), Decimal("100"), Decimal("-15"))])


def test_missing_tax_code_is_rejected():
    with pytest.raises(InvalidFinancialReferenceError):
        _validate_tax_lines([(None, Decimal("100"), Decimal("15"))])
