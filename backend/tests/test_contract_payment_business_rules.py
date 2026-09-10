from datetime import date
from decimal import Decimal

import pytest

from app.models.contract_payment import ContractPaymentInstallment
from app.services import contract_payment_service as cps


def _installment(*, year: int, month: int) -> ContractPaymentInstallment:
    return ContractPaymentInstallment(
        schedule_id="00000000-0000-0000-0000-000000000001",
        sequence=1,
        installment_kind="REGULAR",
        period_year=year,
        period_month=month,
        due_date=date(year, month, 28),
        scheduled_amount=Decimal("100.00"),
        retention_amount=Decimal("0.00"),
        net_due=Decimal("100.00"),
        status="UPCOMING",
    )


def test_current_and_previous_contractual_months_are_payable(monkeypatch):
    monkeypatch.setattr(cps, "business_today", lambda: date(2026, 9, 15))

    assert cps.is_installment_payable(_installment(year=2026, month=9))
    assert cps.is_installment_payable(_installment(year=2026, month=8))


def test_future_contractual_month_is_rejected_even_with_future_reference_date(monkeypatch):
    monkeypatch.setattr(cps, "business_today", lambda: date(2026, 9, 15))
    future = _installment(year=2026, month=10)

    with pytest.raises(cps.InvalidFinancialReferenceError):
        cps.assert_installment_payable(future)


def test_business_today_is_default_for_contract_reporting(monkeypatch):
    monkeypatch.setattr(cps, "business_today", lambda: date(2026, 9, 15))
    assert cps._status_for(_installment(year=2026, month=10), Decimal("0.00"), as_of=cps.business_today()) == "UPCOMING"
