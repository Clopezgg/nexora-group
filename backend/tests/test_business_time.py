from datetime import date, datetime, timezone

import pytest

from app.core.business_time import business_today


def test_business_today_stays_on_previous_calendar_date_before_honduras_midnight():
    assert business_today(datetime(2026, 8, 31, 3, 30, tzinfo=timezone.utc)) == date(2026, 8, 30)


def test_business_today_rolls_at_honduras_midnight():
    assert business_today(datetime(2026, 8, 31, 6, 30, tzinfo=timezone.utc)) == date(2026, 8, 31)


def test_business_today_rejects_naive_datetime():
    with pytest.raises(ValueError, match="timezone-aware"):
        business_today(datetime(2026, 8, 31, 3, 30))
