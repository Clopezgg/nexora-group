from decimal import Decimal

from app.schemas.base import CamelModel


class TrialBalanceRowResponse(CamelModel):
    account_code: str
    account_name: str
    debit_balance: Decimal
    credit_balance: Decimal


class TrialBalanceReportResponse(CamelModel):
    rows: list[TrialBalanceRowResponse]
    total_debit: Decimal
    total_credit: Decimal


class BudgetVsActualReportResponse(CamelModel):
    authorized: Decimal
    committed: Decimal
    accrued: Decimal
    paid: Decimal
    available: Decimal
