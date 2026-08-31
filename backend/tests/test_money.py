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
