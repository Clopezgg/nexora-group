# Financial Statements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add company-isolated General Ledger, Balance Sheet, and Income Statement reports derived from the real immutable General Ledger.

**Architecture:** Extend the existing reporting vertical slice with aggregate SQL over `AccountingDocument` and `JournalLine`; do not create reporting tables or duplicate account classification. Expose three read-only FastAPI endpoints and three tabs under the existing Reports page, reusing the CSV utility and design system.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2, PostgreSQL 16, Pytest, React 19, TypeScript, TanStack Query, Vitest/RTL.

**Spec:** `docs/superpowers/specs/2026-08-25-financial-statements-design.md`

## Global Constraints

- Treasury remains the sole owner of money; these reports are read-only views over GL.
- Include `POSTED` and `REVERSED` source documents so original+reversal net correctly; exclude `DRAFT`.
- Company isolation is mandatory on every endpoint and optional account filter.
- Use `Decimal`/`Numeric`; never float for financial calculations.
- No migration, new dependency, reporting snapshot, Cash Flow classification, XLSX/PDF, or Azure provisioning.
- `NXR-REQ-0093` remains `IN_PROGRESS` after this subproject because Treasury, Procurement, Project report composition and Cash Flow remain.

---

### Task 1: Backend financial statement services and APIs

**Files:**
- Modify: `backend/app/services/reporting_service.py`
- Modify: `backend/app/schemas/reporting.py`
- Modify: `backend/app/api/routes/reports.py`
- Modify: `backend/app/repositories/permission_repository.py`
- Modify: `backend/tests/test_reporting.py`

**Interfaces:**
- Consumes: `Account.account_type`, `ChartOfAccount.company_id`, `AccountingDocument.company_id/status/posted_at`, `JournalLine.debit_amount/credit_amount`.
- Produces: `general_ledger(...) -> GeneralLedgerReport`, `balance_sheet(...) -> BalanceSheetReport`, `income_statement(...) -> IncomeStatementReport`; GET routes `/api/reports/general-ledger`, `/balance-sheet`, `/income-statement`.

- [ ] **Step 1: Write failing service/API tests for known postings**

Add tests that post real journals using the existing `/api/accounting/journal-entries` helper pattern:

```python
def test_balance_sheet_balances_with_current_earnings(client):
    # Post cash debit 150 / equity credit 100 / revenue credit 50.
    response = client.get(f"/api/reports/balance-sheet?companyId={company['id']}")
    assert response.status_code == 200
    body = response.json()
    assert body["totalAssets"] == "150.00"
    assert body["totalLiabilitiesAndEquity"] == "150.00"
    assert body["currentEarnings"] == "50.00"
    assert body["equationDelta"] == "0.00"


def test_income_statement_uses_natural_revenue_and_expense_signs(client):
    # Post cash 100 / revenue 100, then expense 25 / cash 25.
    body = client.get(f"/api/reports/income-statement?companyId={company['id']}").json()
    assert body["totalRevenue"] == "100.00"
    assert body["totalExpenses"] == "25.00"
    assert body["netIncome"] == "75.00"


def test_general_ledger_paginates_and_totals_full_filter(client):
    first = client.get(
        f"/api/reports/general-ledger?companyId={company['id']}&offset=0&limit=1"
    ).json()
    assert first["total"] == 2
    assert len(first["rows"]) == 1
    assert first["totalDebit"] == "100.00"
    assert first["totalCredit"] == "100.00"
```

Also add focused tests for reversal netting, date-range validation, account-filter 404 without cross-company leakage, and company-access 403 on each endpoint.

- [ ] **Step 2: Run focused tests and confirm RED**

Run:

```bash
cd backend
./.venv/bin/pytest tests/test_reporting.py -q
```

Expected: existing five tests pass; new tests fail with 404 or missing service symbols.

- [ ] **Step 3: Add dataclasses and the aggregate query**

Add exact public result types in `reporting_service.py`:

```python
@dataclass
class StatementRow:
    account_id: uuid.UUID
    account_code: str
    account_name: str
    account_type: str
    balance: Decimal


@dataclass
class BalanceSheetReport:
    assets: list[StatementRow]
    liabilities: list[StatementRow]
    equity: list[StatementRow]
    total_assets: Decimal
    total_liabilities: Decimal
    total_equity: Decimal
    current_earnings: Decimal
    total_equity_including_earnings: Decimal
    total_liabilities_and_equity: Decimal
    equation_delta: Decimal


@dataclass
class IncomeStatementReport:
    revenue: list[StatementRow]
    expenses: list[StatementRow]
    total_revenue: Decimal
    total_expenses: Decimal
    net_income: Decimal


@dataclass
class GeneralLedgerRow:
    line_id: uuid.UUID
    document_id: uuid.UUID
    document_number: str
    posted_at: datetime
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


@dataclass
class GeneralLedgerReport:
    rows: list[GeneralLedgerRow]
    total: int
    offset: int
    limit: int
    total_debit: Decimal
    total_credit: Decimal
```

Implement one grouped account-activity query and one reusable detail filter. Both join through company-owned tables, include document status `POSTED`/`REVERSED`, use inclusive date bounds, and order deterministically. Do not call `treasury_service.account_balance()` in a loop.

- [ ] **Step 4: Implement statement calculations**

Use these exact natural-sign rules:

```python
asset = debit - credit
liability_or_equity = credit - debit
revenue = credit - debit
expense = debit - credit
current_earnings = total_revenue - total_expenses
equation_delta = total_assets - (
    total_liabilities + total_equity + current_earnings
)
if equation_delta != Decimal("0"):
    raise RuntimeError("Balance Sheet no cuadra con el General Ledger")
```

Omit zero-balance rows but retain negative contra-account rows. Return zero totals on an empty ledger.

- [ ] **Step 5: Add schemas, routes and permissions**

Add `CamelModel` response models mirroring every dataclass. Route query parameters use explicit aliases `companyId`, `dateFrom`, `dateTo`, `asOf`, `accountId`. Validate `dateFrom <= dateTo` with `HTTPException(422, "dateFrom no puede ser posterior a dateTo")`; use `Query(ge=0)` for offset and `Query(ge=1, le=100)` for limit. Resolve `accountId` against the requested company's chart and return 404 if it does not belong.

Add base permissions:

```python
("reports.general_ledger", "read", "Ver el Libro Mayor"),
("reports.balance_sheet", "read", "Ver el Balance General"),
("reports.income_statement", "read", "Ver el Estado de Resultados"),
```

Grant all three exactly wherever `reports.trial_balance/read` is granted, with the same scope.

- [ ] **Step 6: Run focused backend tests GREEN**

Run:

```bash
cd backend
./.venv/bin/pytest tests/test_reporting.py -q
./.venv/bin/python -m compileall -q app tests
```

Expected: all reporting tests pass and compileall emits no output.

- [ ] **Step 7: Commit backend slice**

```bash
git add backend/app/services/reporting_service.py backend/app/schemas/reporting.py \
  backend/app/api/routes/reports.py backend/app/repositories/permission_repository.py \
  backend/tests/test_reporting.py
git commit -m "feat(reports): add general ledger and financial statements"
```

### Task 2: Frontend report tabs and CSV export

**Files:**
- Modify: `frontend/src/types/reporting.ts`
- Modify: `frontend/src/services/reportingService.ts`
- Create: `frontend/src/features/reports/GeneralLedgerPage.tsx`
- Create: `frontend/src/features/reports/BalanceSheetPage.tsx`
- Create: `frontend/src/features/reports/IncomeStatementPage.tsx`
- Modify: `frontend/src/features/reports/ReportsPage.tsx`
- Create: `frontend/tests/FinancialStatementsPage.test.tsx`
- Create: `frontend/tests/GeneralLedgerPage.test.tsx`

**Interfaces:**
- Consumes: the three Task 1 JSON response contracts and existing `toCsv`/`downloadCsv`, `Tabs`, `Table`, `Card`, loading/error/empty primitives.
- Produces: three additional tabs inside `/control/reportes`, paginated GL UI, real CSV export from loaded rows.

- [ ] **Step 1: Write failing component tests**

```tsx
it('renders the balance-sheet equation from the real API response', async () => {
  render(renderApp('/control/reportes'))
  await userEvent.click(await screen.findByRole('button', { name: /balance general/i }))
  expect(await screen.findByText(/activos: 150.00/i)).toBeInTheDocument()
  expect(screen.getByText(/pasivo \+ patrimonio: 150.00/i)).toBeInTheDocument()
})

it('requests the next general-ledger page with a real offset', async () => {
  render(renderApp('/control/reportes'))
  await userEvent.click(await screen.findByRole('button', { name: /libro mayor/i }))
  await userEvent.click(await screen.findByRole('button', { name: /siguiente/i }))
  expect(fetch).toHaveBeenCalledWith(
    expect.stringContaining('offset=25&limit=25'),
    expect.anything(),
  )
})
```

Also assert Income Statement revenue/expense/net-income values and disabled CSV buttons for empty rows.

- [ ] **Step 2: Run component tests and confirm RED**

Run:

```bash
cd frontend
npm test -- --run tests/FinancialStatementsPage.test.tsx tests/GeneralLedgerPage.test.tsx
```

Expected: imports/components or tab labels do not exist.

- [ ] **Step 3: Add TypeScript contracts and service methods**

Mirror backend camelCase fields exactly. Add:

```ts
getGeneralLedger(companyId: string, offset = 0, limit = 25)
getBalanceSheet(companyId: string)
getIncomeStatement(companyId: string)
```

Use `URLSearchParams` for GL pagination; do not hand-build an unescaped filter query.

- [ ] **Step 4: Implement the three pages**

Follow `TrialBalancePage`'s `useActiveCompany` and state patterns. General Ledger keeps `offset` in local state, resets only through explicit controls, disables Previous at zero and Next when `offset + rows.length >= total`. CSV serializes the currently loaded page and each statement's visible rows, using section labels where needed. Every page renders `LoadingState`, `ErrorState`, and an honest empty `Table`/summary.

- [ ] **Step 5: Wire tabs without changing navigation**

Extend `ReportsPage.tsx` with stable keys and labels:

```tsx
{ key: 'libro-mayor', label: 'Libro Mayor', content: <GeneralLedgerPage /> },
{ key: 'balance-general', label: 'Balance General', content: <BalanceSheetPage /> },
{ key: 'estado-resultados', label: 'Estado de Resultados', content: <IncomeStatementPage /> },
```

Keep the two existing tabs intact.

- [ ] **Step 6: Run focused and complete frontend gates**

```bash
cd frontend
npm test -- --run tests/FinancialStatementsPage.test.tsx tests/GeneralLedgerPage.test.tsx
npm run typecheck
npm run lint
npm test -- --run
npm run build
```

Expected: all commands pass; the known bundle-size warning may remain and is already tracked as `DEFERRED-FINAL-017`.

- [ ] **Step 7: Commit frontend slice**

```bash
git add frontend/src/types/reporting.ts frontend/src/services/reportingService.ts \
  frontend/src/features/reports frontend/tests/FinancialStatementsPage.test.tsx \
  frontend/tests/GeneralLedgerPage.test.tsx
git commit -m "feat(reports): add financial statement screens"
```

### Task 3: Traceability and combined verification

**Files:**
- Modify: `docs/PROGRESS.md`
- Modify: `docs/REQUIREMENTS_TRACEABILITY.md`
- Modify: `docs/AGENT_HANDOFF.md`

**Interfaces:**
- Consumes: integrated Tasks 1-2.
- Produces: reproducible verification evidence and honest `NXR-REQ-0093` sub-scope state.

- [ ] **Step 1: Update documentation without changing status to IMPLEMENTED**

Record General Ledger, Balance Sheet and Income Statement as completed
sub-scope. Keep `NXR-REQ-0093` at `IN_PROGRESS` and name Cash Flow,
Treasury, Procurement and composed Project/Earned-Value reports as remaining.
Do not change the 124-row status tally unless a row status truly changed.

- [ ] **Step 2: Run combined gates from the integration branch**

```bash
cd backend
./.venv/bin/alembic heads
./.venv/bin/pytest -q
./.venv/bin/python -m compileall -q app tests
cd ../frontend
npm run typecheck
npm run lint
npm test -- --run
npm run build
cd ..
git diff --check
```

Expected: one Alembic head (`234785d5331f`), no new migration, all tests and builds pass.

- [ ] **Step 3: Review the final diff and commit docs**

```bash
git status --short
git diff --stat HEAD~2..HEAD
git diff --check
git add docs/PROGRESS.md docs/REQUIREMENTS_TRACEABILITY.md docs/AGENT_HANDOFF.md
git commit -m "docs: record financial statements verification"
```

- [ ] **Step 4: Push the verified checkpoint**

```bash
git push origin feat/nexora-greenfield
```
