# Financial Statements — Design

Status: approved under the user's explicit autonomous-execution order. This
is the first follow-up subproject for the still-`IN_PROGRESS`
`NXR-REQ-0093`; it does not claim to close the entire reporting catalog.

## Goal

Add three real, company-isolated reports derived exclusively from the
General Ledger: paginated General Ledger detail, Balance Sheet, and Income
Statement. Preserve the current Trial Balance and Budget vs Actual reports.

## Grounding in the current code

- `Account.account_type` already stores exactly `ASSET`, `LIABILITY`,
  `EQUITY`, `REVENUE`, or `EXPENSE`. The older Reports/Search design's claim
  that statement categorization was missing is factually obsolete; no schema
  field or migration is needed.
- `AccountingDocument` owns `company_id`, `status`, `posted_at`, scope and
  project attribution. `JournalLine` owns account, debit and credit. Both the
  original side of a reversal (`REVERSED`) and its posted reversal document
  must be included so their balances cancel correctly; only `DRAFT` is
  excluded.
- `treasury_service.account_balance()` is correct for existing all-time
  single-account consumers but performs one query per account and has no date
  bounds. These statements use one aggregate SQL query over the GL instead of
  calling it in a loop.
- There is no persisted cash-flow activity classification. A Cash Flow
  statement grouped into operating/investing/financing cannot be produced
  faithfully yet and remains outside this subproject.

## Approaches considered

1. **Direct GL aggregation (selected).** Query immutable journal data,
   aggregate by account, and derive natural-sign statement balances from
   `account_type`. It has one source of truth, no synchronization problem and
   no migration.
2. **Add a statement-category column.** Rejected because it duplicates the
   existing `account_type` vocabulary and creates migration/backfill work
   without adding information.
3. **Reporting snapshots/materialized tables.** Rejected until performance
   evidence warrants them. They add refresh, invalidation and reconciliation
   failure modes during Build Width First.

## Backend design

`reporting_service` gains a private aggregate query returning account code,
name, type, debits, credits and net debit-minus-credit for one company. It
joins `JournalLine -> AccountingDocument` and `Account -> ChartOfAccount`,
filters both chart and document by `company_id`, and includes document status
in `POSTED | REVERSED`. Optional date bounds compare the date component of
`posted_at`; bounds are inclusive.

### General Ledger

`general_ledger(db, *, company_id, date_from=None, date_to=None,
account_id=None, offset=0, limit=50) -> GeneralLedgerReport` returns detail
rows ordered by `posted_at`, `document_number`, journal-line ID. Each row
contains document and line IDs, document number/date/status, account
ID/code/name/type, scope, project ID, description, debit and credit. The
response includes `total`, `offset`, `limit`, `total_debit` and
`total_credit`; totals cover the full filtered result, not only the page.
`limit` is constrained to 1..100. If `account_id` is supplied, it must belong
to the requested company or the API returns 404, without revealing whether an
account exists in another company.

Endpoint: `GET /api/reports/general-ledger?companyId=&dateFrom=&dateTo=&accountId=&offset=&limit=`.

### Balance Sheet

`balance_sheet(db, *, company_id, as_of=None) -> BalanceSheetReport` uses
all postings through `as_of` (or all postings when omitted). Natural balances
are:

- assets: debit minus credit;
- liabilities and equity: credit minus debit;
- current earnings: revenue credit-minus-debit less expense
  debit-minus-credit, all-time through the same `as_of`.

The report exposes separate asset/liability/equity rows and totals,
`current_earnings`, `total_equity_including_earnings`,
`total_liabilities_and_equity`, and `equation_delta = assets -
(liabilities + equity + current earnings)`. The service raises if the delta is
non-zero; a financial statement never silently returns an unbalanced result.
Contra accounts remain negative rows within their declared account type.

Endpoint: `GET /api/reports/balance-sheet?companyId=&asOf=`.

### Income Statement

`income_statement(db, *, company_id, date_from=None, date_to=None) ->
IncomeStatementReport` returns revenue rows as credit-minus-debit, expense
rows as debit-minus-credit, their totals, and `net_income = revenue -
expense`. Bounds are inclusive. No date range means all history.

Endpoint: `GET /api/reports/income-statement?companyId=&dateFrom=&dateTo=`.

All three routes use `assert_company_access`. New read permissions are
`reports.general_ledger`, `reports.balance_sheet`, and
`reports.income_statement`, granted to the same roles and scopes as the
existing Trial Balance permission.

## Frontend design

`ReportsPage` adds three tabs without changing navigation:

- Libro Mayor — paginated table with Previous/Next controls and honest empty,
  loading and error states;
- Balance General — Assets, Liabilities and Equity/current earnings sections,
  showing both sides of the accounting equation and any delta;
- Estado de Resultados — Revenue and Expense sections plus net income.

Every report exports exactly its loaded/displayed real data through the
existing CSV utility. Date filters are deliberately omitted from this first
UI slice; the API contract supports them for integrations and future UI
extension. General Ledger pagination is real at the API and UI layers.

## Error handling and invariants

- Invalid date ranges (`dateFrom > dateTo`) return HTTP 422.
- Unknown or cross-company account filters never expose data.
- Empty ledgers return empty rows and zero totals, never fabricated examples.
- Decimal remains end-to-end; no financial calculation uses float.
- Balance Sheet equality is asserted in service tests with known posted
  documents and with a reversal.

## Testing

Backend tests post real journals and verify:

- company isolation for every new endpoint;
- General Ledger pagination, filter totals and no draft leakage;
- Balance Sheet `Assets = Liabilities + Equity + current earnings`;
- Income Statement revenue, expenses and net income from known postings;
- reversed documents net to zero when original and reversal are included;
- invalid ranges return 422.

Frontend tests stub the API boundary and verify each tab renders server data,
pagination requests the next offset, empty states are honest, and CSV buttons
are disabled when no rows exist. Full backend/frontend gates and a final
traceability recount close the subproject.

## Explicitly out of scope

- Cash Flow classification and statement.
- Treasury operational reports.
- Procurement operational reports.
- Project Earned Value/progress report composition.
- XLSX/PDF exports.
- Reporting snapshots, materialized views, or new infrastructure.

Those are subsequent independently testable `NXR-REQ-0093` subprojects; the
requirement remains `IN_PROGRESS` after this design is implemented.
