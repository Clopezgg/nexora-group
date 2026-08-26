import uuid
from datetime import datetime
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


class StatementRowResponse(CamelModel):
    account_id: uuid.UUID
    account_code: str
    account_name: str
    account_type: str
    balance: Decimal


class BalanceSheetReportResponse(CamelModel):
    assets: list[StatementRowResponse]
    liabilities: list[StatementRowResponse]
    equity: list[StatementRowResponse]
    total_assets: Decimal
    total_liabilities: Decimal
    total_equity: Decimal
    current_earnings: Decimal
    total_equity_including_earnings: Decimal
    total_liabilities_and_equity: Decimal
    equation_delta: Decimal


class IncomeStatementReportResponse(CamelModel):
    revenue: list[StatementRowResponse]
    expenses: list[StatementRowResponse]
    total_revenue: Decimal
    total_expenses: Decimal
    net_income: Decimal


class GeneralLedgerRowResponse(CamelModel):
    line_id: uuid.UUID
    document_id: uuid.UUID
    document_number: str
    posted_at: datetime | None
    document_status: str
    account_id: uuid.UUID
    account_code: str
    account_name: str
    account_type: str
    scope: str
    project_id: uuid.UUID | None
    description: str | None
    debit_amount: Decimal
    credit_amount: Decimal


class GeneralLedgerReportResponse(CamelModel):
    rows: list[GeneralLedgerRowResponse]
    total: int
    offset: int
    limit: int
    total_debit: Decimal
    total_credit: Decimal


class CashFlowReportResponse(CamelModel):
    operating: list[StatementRowResponse]
    investing: list[StatementRowResponse]
    financing: list[StatementRowResponse]
    unclassified: list[StatementRowResponse]
    total_operating: Decimal
    total_investing: Decimal
    total_financing: Decimal
    total_unclassified: Decimal
    net_change_in_cash: Decimal
