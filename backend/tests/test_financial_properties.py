"""Property tests for NEXORA's non-negotiable accounting invariants."""

import uuid
from decimal import Decimal

import pytest
from hypothesis import given, strategies as st

from app.domain.errors import (
    InvalidOperationScopeError,
    UnbalancedJournalEntryError,
)
from app.services.posting_service import (
    JournalLineInput,
    _validate_balance,
    _validate_scope,
)


money = st.decimals(
    min_value=Decimal("0.01"),
    max_value=Decimal("999999999.99"),
    places=2,
    allow_nan=False,
    allow_infinity=False,
)


@given(money)
def test_property_balanced_entry_is_accepted(amount):
    account_a = uuid.uuid4()
    account_b = uuid.uuid4()

    _validate_balance(
        [
            JournalLineInput(
                account_id=account_a,
                debit_amount=amount,
            ),
            JournalLineInput(
                account_id=account_b,
                credit_amount=amount,
            ),
        ]
    )


@given(money, money)
def test_property_unbalanced_entry_is_rejected(debit, credit):
    if debit == credit:
        credit += Decimal("0.01")

    with pytest.raises(UnbalancedJournalEntryError):
        _validate_balance(
            [
                JournalLineInput(
                    account_id=uuid.uuid4(),
                    debit_amount=debit,
                ),
                JournalLineInput(
                    account_id=uuid.uuid4(),
                    credit_amount=credit,
                ),
            ]
        )


@given(money)
def test_property_negative_debit_is_rejected(amount):
    with pytest.raises(UnbalancedJournalEntryError):
        _validate_balance(
            [
                JournalLineInput(
                    account_id=uuid.uuid4(),
                    debit_amount=-amount,
                ),
                JournalLineInput(
                    account_id=uuid.uuid4(),
                    credit_amount=-amount,
                ),
            ]
        )


@given(money)
def test_property_single_line_cannot_have_debit_and_credit(amount):
    with pytest.raises(UnbalancedJournalEntryError):
        _validate_balance(
            [
                JournalLineInput(
                    account_id=uuid.uuid4(),
                    debit_amount=amount,
                    credit_amount=amount,
                )
            ]
        )


@given(st.sampled_from(["CENTRAL", "GENERAL"]))
def test_property_non_project_scope_rejects_project(scope):
    with pytest.raises(InvalidOperationScopeError):
        _validate_scope(scope, uuid.uuid4())


def test_property_project_scope_requires_project():
    with pytest.raises(InvalidOperationScopeError):
        _validate_scope("PROJECT", None)


@given(st.sampled_from(["CENTRAL", "GENERAL"]))
def test_property_non_project_scope_accepts_null_project(scope):
    _validate_scope(scope, None)


def test_property_project_scope_accepts_project():
    _validate_scope("PROJECT", uuid.uuid4())
