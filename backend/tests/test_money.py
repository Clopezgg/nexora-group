from decimal import Decimal

import pytest

from app.core.money import format_money


@pytest.mark.parametrize(
    ("value", "currency", "expected"),
    [
        ("150000", "HNL", "L 150,000.00"),
        (150000, "HNL", "L 150,000.00"),
        (Decimal("1250.5"), "HNL", "L 1,250.50"),
        (Decimal("-1250.5"), "HNL", "-L 1,250.50"),
        ("0", "HNL", "L 0.00"),
        ("1000", "USD", "$ 1,000.00"),
        ("50", "PAB", "PAB 50.00"),
        (Decimal("1234.005"), "HNL", "L 1,234.01"),
    ],
)
def test_format_money(value, currency, expected):
    assert format_money(value, currency) == expected


def test_format_money_never_returns_bare_number():
    out = format_money("150000", "HNL")
    assert out != "150000"
    assert "," in out and "." in out


def test_approval_verification_code_is_deterministic():
    from datetime import date

    from app.services.voucher_service import approval_verification_code

    a = approval_verification_code(
        document_number="REM-2026-0001", approved_by="carlos lopez", issued_on=date(2026, 8, 31)
    )
    b = approval_verification_code(
        document_number="REM-2026-0001", approved_by="CARLOS LOPEZ", issued_on=date(2026, 8, 31)
    )
    c = approval_verification_code(
        document_number="REM-2026-0001", approved_by="CARLOS LOPEZ", issued_on=date(2026, 9, 1)
    )
    assert a == b  # case-insensitive
    assert a != c  # la fecha cambia el código
    assert len(a) == 12 and a.isalnum()
