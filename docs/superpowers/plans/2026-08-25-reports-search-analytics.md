# Reports / Search / Analytics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close NXR-REQ-0092 through 0096: Global Search wired to the
already-built `CommandPalette`, Trial Balance + Budget vs Actual
reporting with CSV export, a real company-profile Settings page, and a
documentation-only Integration Architecture record.

**Architecture:** Task 1 (Global Search), Task 2 (Reporting), and Task 3
(Settings + Integration Architecture) are genuinely independent —
different files, different domains, no shared interface between them —
and run in parallel in three separate worktrees, same pattern the
construction-control plan used for Documents+Evidence vs Workforce UI.
Task 4 is combined verification and traceability recount after all
three merge.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2, Alembic, PostgreSQL
16, Pytest, React, TypeScript, Vite, TanStack Query, Vitest/RTL — same
stack and house conventions as every prior track.

**Spec:** `docs/superpowers/specs/2026-08-25-reports-search-analytics-design.md`,
`docs/MASTER_PLAN.md`, `docs/REQUIREMENTS_TRACEABILITY.md`, `CLAUDE.md`.

## Global Constraints

- Company isolation on every new resource. Search and Reports use a
  real permission grant + `assert_company_access`, same pattern every
  prior track used.
- PostgreSQL only.
- Never mark anything `VERIFIED`.
- No new service function signature changes on existing files — only
  new functions/files. This plan is purely additive (search, reports,
  one settings PATCH route); nothing here should need to touch existing
  domain transition logic at all.
- Reuse real existing functions, never reimplement: Trial Balance uses
  `accounting_service.account_balance`; Budget vs Actual uses
  `budget_service.compute_summary`. Do not write a parallel balance
  calculation.
- `GET /api/search` — NOT `/api/v1/search` (Track F's original comment
  in `CommandPalette.tsx` names `/api/v1/search`; verified against
  `backend/app/main.py` that no route in this codebase uses an `/api/v1`
  prefix — use plain `/api`, matching every other router).
- Domain → DB → Alembic (if a migration is needed) → repository/service
  → API → permission → frontend → test for each slice.
- CSV export only (no XLSX/PDF) — a shared `toCsv(rows, columns)`
  frontend utility, not a new dependency.
- Explicitly out of scope, do not build: Balance Sheet, P&L, Cash Flow,
  Treasury reports, Procurement reports, Earned Value/CPI/SPI/EAC/VAC,
  any real SAP/AI adapter code, changing `functional_currency` after
  creation. If you find yourself about to build one of these, stop —
  it's out of scope for this plan.

---

### Task 1: Global Search (NXR-REQ-0092)

**Files:**
- Create: `backend/app/services/search_service.py`
- Create: `backend/app/api/routes/search.py`
- Create: `backend/app/schemas/search.py`
- Modify: `backend/app/main.py` (register `search.router`)
- Modify: `backend/app/repositories/permission_repository.py` (add
  `search.global` permission grants)
- Test: `backend/tests/test_search.py`
- Create: `frontend/src/services/searchService.ts`,
  `frontend/src/types/search.ts`
- Modify: `frontend/src/layouts/AppLayout.tsx` (feed `CommandPalette`
  real results, not just local nav)
- Test: `frontend/tests/AppShell.test.tsx` (extend — add one test for
  real search results appearing) or a new
  `frontend/tests/GlobalSearch.test.tsx` if cleaner (your call, keep
  the existing `AppShell.test.tsx` scoped to what it already tests)

**Interfaces:**
- Consumes: existing models `Project`, `Supplier`, `Customer`,
  `SupplierInvoice`, `CustomerInvoice`, `PurchaseOrder`, `Document`,
  `RequestForInformation`, `FixedAsset`, `Equipment` (read-only — no
  changes to any of these files).
- Produces: `search_service.search(db, *, company_id: uuid.UUID, query:
  str, limit_per_type: int = 5) -> list[SearchResult]` where
  `SearchResult` is a small dataclass `{id: uuid.UUID, label: str,
  group: str, path: str, entity_type: str}`.

- [ ] **Step 1: Write the failing test for a single entity type (Project)**

```python
# backend/tests/test_search.py
import uuid

from tests.helpers import create_company, login_admin


def test_search_finds_project_by_name(client, db_session):
    login_admin(client)
    company = create_company(client)
    client.post(
        "/api/projects",
        json={"companyId": company["id"], "name": "Torre Reforma Norte"},
    )

    response = client.get(f"/api/search?companyId={company['id']}&q=Reforma")
    assert response.status_code == 200, response.text
    results = response.json()
    assert any(r["entityType"] == "project" and "Reforma" in r["label"] for r in results)
```

Check the real `POST /api/projects` request shape first (read
`backend/app/api/routes/projects.py` and
`backend/app/schemas/project.py`) — the field names above are
illustrative, use the real ones.

- [ ] **Step 2: Run it, confirm it fails**

Run: `cd backend && /Users/clopezg/nexora-group/backend/.venv/bin/pytest tests/test_search.py -v`
Expected: FAIL — `404 Not Found` (no `/api/search` route yet).

- [ ] **Step 3: Implement `search_service.py`, `schemas/search.py`, `routes/search.py`**

```python
# backend/app/services/search_service.py
import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.asset import FixedAsset
from app.models.customer import Customer  # verify real module path first
from app.models.document import Document
from app.models.equipment import Equipment
from app.models.procurement import PurchaseOrder
from app.models.project import Project
from app.models.rfi import RequestForInformation
from app.models.supplier import Supplier


@dataclass
class SearchResult:
    id: uuid.UUID
    label: str
    group: str
    path: str
    entity_type: str


def search(
    db: Session, *, company_id: uuid.UUID, query: str, limit_per_type: int = 5
) -> list[SearchResult]:
    q = f"%{query}%"
    results: list[SearchResult] = []

    projects = db.execute(
        select(Project)
        .where(Project.company_id == company_id, Project.name.ilike(q))
        .limit(limit_per_type)
    ).scalars()
    results += [
        SearchResult(p.id, p.name, "Proyectos", "/proyectos", "project") for p in projects
    ]

    suppliers = db.execute(
        select(Supplier)
        .where(Supplier.company_id == company_id, Supplier.legal_name.ilike(q))
        .limit(limit_per_type)
    ).scalars()
    results += [
        SearchResult(s.id, s.legal_name, "Proveedores", "/abastecimiento/proveedores", "supplier")
        for s in suppliers
    ]

    # Repeat this exact shape for Customer.legal_name (path
    # "/comercial/clientes", group "Clientes", entity_type "customer"),
    # SupplierInvoice.invoice_number ("/finanzas/cuentas-por-pagar",
    # "Facturas de proveedor", "supplier_invoice"),
    # CustomerInvoice.invoice_number ("/finanzas/cuentas-por-cobrar",
    # "Facturas de cliente", "customer_invoice"),
    # PurchaseOrder.po_number ("/abastecimiento/ordenes-de-compra",
    # "Órdenes de compra", "purchase_order"), Document.title
    # ("/control/documentos", "Documentos", "document"),
    # RequestForInformation.subject ("/proyectos/rfi-submittals", "RFI",
    # "rfi"), FixedAsset.name ("/finanzas/activos", "Activos fijos",
    # "fixed_asset"), Equipment.name ("/recursos/equipos", "Equipos",
    # "equipment") — verify each model's real field name and the real
    # route path from routes.tsx before writing each block, do not
    # guess. Every added block must scope by that model's own
    # company_id column and respect limit_per_type.

    return results
```

```python
# backend/app/schemas/search.py
import uuid

from app.schemas.base import CamelModel


class SearchResultResponse(CamelModel):
    id: uuid.UUID
    label: str
    group: str
    path: str
    entity_type: str
```

```python
# backend/app/api/routes/search.py
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.search import SearchResultResponse
from app.services import search_service
from app.services.permission_service import assert_company_access, require_permission

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=list[SearchResultResponse])
def global_search(
    company_id: uuid.UUID,
    q: str,
    db: Session = Depends(get_db),
    user=Depends(require_permission("search.global", "read")),
) -> list[SearchResultResponse]:
    assert_company_access(
        db, user_id=user.id, resource="search.global", action="read", company_id=company_id
    )
    if not q or len(q.strip()) < 2:
        return []
    results = search_service.search(db, company_id=company_id, query=q.strip())
    return [
        SearchResultResponse(
            id=r.id, label=r.label, group=r.group, path=r.path, entity_type=r.entity_type
        )
        for r in results
    ]
```

Verify the `company_id`/`q` query-param names produce the camelCase
`companyId` the frontend/tests expect — FastAPI's default query-param
name IS the Python parameter name (`company_id` stays `company_id` in
the URL unless aliased). Check how `backend/app/api/routes/approvals.py`
handled this exact issue (Task 2 of the prior plan hit this same bug and
fixed it with `Query(alias="companyId")`) and apply the same fix here:
`company_id: uuid.UUID = Query(alias="companyId")`.

Register the router in `main.py` (additive), add permission grants in
`permission_repository.py`: `("search.global", "read", "Buscar
entidades globalmente")` in `_BASE_PERMISSIONS`, granted broadly (most
roles should be able to search) — check the existing grant pattern for
a widely-granted read permission (e.g. how `document.document`/`read`
is distributed across roles) and mirror it.

- [ ] **Step 4: Run the test, confirm it passes; then add one test per
      remaining entity type (Supplier, Customer, SupplierInvoice,
      CustomerInvoice, PurchaseOrder, Document, RequestForInformation,
      FixedAsset, Equipment) following Step 1's exact pattern — RED
      then GREEN for each, using real API calls to create each fixture
      (reuse `tests/helpers.py` creators where they exist — `create_supplier`,
      `create_customer` — and the real API request shape from each
      domain's own existing tests where a helper doesn't exist)**

- [ ] **Step 5: Write the company-isolation test**

```python
# backend/tests/test_search.py — add
def test_search_never_returns_another_companys_results(client, db_session):
    login_admin(client)
    company_a = create_company(client, name="Search A")
    company_b = create_company(client, name="Search B")
    client.post("/api/projects", json={"companyId": company_a["id"], "name": "Unico Alpha"})

    response = client.get(f"/api/search?companyId={company_b['id']}&q=Alpha")
    assert response.status_code == 200
    assert response.json() == []
```

Run RED then GREEN.

- [ ] **Step 6: Wire the frontend**

```typescript
// frontend/src/types/search.ts
export interface SearchResult {
  id: string
  label: string
  group: string
  path: string
  entityType: string
}
```

```typescript
// frontend/src/services/searchService.ts
import { apiFetch } from './httpClient'
import type { SearchResult } from '../types/search'

export async function globalSearch(companyId: string, query: string): Promise<SearchResult[]> {
  if (query.trim().length < 2) return []
  const params = new URLSearchParams({ companyId, q: query })
  return apiFetch(`/search?${params.toString()}`)
}
```

Verify `apiFetch`'s real signature/return-parsing against
`frontend/src/services/auditService.ts` (Track G Task 1) before using
it — same pattern.

Modify `AppLayout.tsx` to merge live search results into
`CommandPalette`'s items. `CommandPalette` currently only takes a
static `items` prop and filters client-side — this task needs it to
also show real async results as the user types. Read
`frontend/src/design-system/primitives/CommandPalette.tsx`'s real
current implementation (already grounded in the spec's context) and
choose the smallest change that adds a debounced real-search branch
without breaking the existing local-nav-filter behavior (e.g. when
`query.length >= 2`, merge `filtered` local matches with async results
fetched via a `useQuery` in `AppLayout.tsx`, passed down as an
additional prop, OR move the debounced fetch inside `CommandPalette`
itself if that's architecturally cleaner — your call, but keep the
existing nav-only behavior working when the backend call hasn't
resolved yet, never show a blank palette while loading).

- [ ] **Step 7: Write a frontend test proving real results appear**

Follow the mock-fetch-then-assert-DOM pattern used throughout this
project's frontend tests (e.g. `TimeEntriesPage.test.tsx`,
`ApprovalInboxPage.test.tsx`) — mock `GET /api/search` returning a
realistic `SearchResult[]`, open the palette (simulate Cmd/Ctrl+K or
call the same trigger the existing `AppShell.test.tsx` uses), type a
query, assert a result from the mock appears and is clickable
(navigates via `path`).

- [ ] **Step 8: Run full gates, update docs, commit**

```bash
cd backend
./.venv/bin/pytest -q
./.venv/bin/python -m compileall -q app tests
cd ../frontend
npm run typecheck && npm run lint && npm test -- --run && npm run build
```

Update `docs/PROGRESS.md`/`docs/REQUIREMENTS_TRACEABILITY.md` for
NXR-REQ-0092 (Global Search) — `IMPLEMENTED` only if genuinely all ten
named entity types are wired and tested; if you had to cut any for time,
mark `IN_PROGRESS` and name exactly which types are missing, honestly.

### Task 2: Reporting — Trial Balance + Budget vs Actual + CSV Export (NXR-REQ-0093/0094)

**Files:**
- Create: `backend/app/services/reporting_service.py`
- Create: `backend/app/api/routes/reports.py`
- Create: `backend/app/schemas/reporting.py`
- Modify: `backend/app/main.py`, `backend/app/repositories/permission_repository.py`
- Test: `backend/tests/test_reporting.py`
- Create: `frontend/src/utils/csv.ts` (shared `toCsv` utility)
- Create: `frontend/src/features/reports/TrialBalancePage.tsx`,
  `frontend/src/features/reports/BudgetVsActualPage.tsx`,
  `frontend/src/services/reportingService.ts`,
  `frontend/src/types/reporting.ts`
- Modify: `frontend/src/app/routes.tsx`, `frontend/src/app/navigation.ts`
  (check for existing reserved nav entries first — e.g. this plan's
  earlier tasks found `/inicio/aprobaciones` and `/control/auditoria`
  already reserved; check the same way for a Reports section before
  inventing new paths)
- Test: `frontend/tests/TrialBalancePage.test.tsx`,
  `frontend/tests/BudgetVsActualPage.test.tsx`

**Interfaces:**
- Consumes: `accounting_service.account_balance(db, *, gl_account_id:
  uuid.UUID) -> Decimal` (existing, read `backend/app/services/accounting_service.py`
  first for its exact import path), `budget_service.compute_summary(db,
  *, project_id: uuid.UUID) -> BudgetSummary` (existing, read
  `backend/app/services/budget_service.py` for `BudgetSummary`'s real
  field names before reshaping it).
- Produces: `reporting_service.trial_balance(db, *, company_id:
  uuid.UUID) -> TrialBalanceReport`,
  `reporting_service.budget_vs_actual(db, *, project_id: uuid.UUID) ->
  BudgetVsActualReport`.

- [ ] **Step 1: Read `accounting_service.account_balance` and the real
      `Account`/`ChartOfAccount` models to understand how to enumerate
      every account for a company**

```bash
grep -n "class Account\|class ChartOfAccount" backend/app/models/chart_of_accounts.py
```

- [ ] **Step 2: Write the failing Trial Balance test**

```python
# backend/tests/test_reporting.py
import uuid
from decimal import Decimal

from tests.helpers import create_account, create_company, login_admin


def test_trial_balance_debits_equal_credits_after_a_real_posting(client, db_session):
    login_admin(client)
    company = create_company(client)
    expense = create_account(client, company_id=company["id"], code="6000", name="Gastos", account_type="EXPENSE")
    cash = create_account(client, company_id=company["id"], code="1000", name="Caja", account_type="ASSET")

    client.post(
        "/api/accounting/journal-entries",
        json={
            "companyId": company["id"],
            "documentTypeCode": "JRN",
            "scope": "GENERAL",
            "currencyCode": "HNL",
            "lines": [
                {"accountId": expense["id"], "debitAmount": "100.00"},
                {"accountId": cash["id"], "creditAmount": "100.00"},
            ],
        },
    )

    response = client.get(f"/api/reports/trial-balance?companyId={company['id']}")
    assert response.status_code == 200, response.text
    body = response.json()
    total_debit = sum(Decimal(row["debitBalance"]) for row in body["rows"])
    total_credit = sum(Decimal(row["creditBalance"]) for row in body["rows"])
    assert total_debit == total_credit == Decimal("100.00")
```

Verify the real `POST /api/accounting/journal-entries` request shape
first (`backend/app/api/routes/accounting.py`,
`backend/app/schemas/accounting.py`) — field names above are
illustrative.

- [ ] **Step 3: Run it, confirm it fails (404, no route yet)**

- [ ] **Step 4: Implement `reporting_service.trial_balance`, the schema, and the route**

```python
# backend/app/services/reporting_service.py
import uuid
from dataclasses import dataclass, field
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.chart_of_accounts import Account, ChartOfAccount
from app.services import accounting_service


@dataclass
class TrialBalanceRow:
    account_code: str
    account_name: str
    debit_balance: Decimal
    credit_balance: Decimal


@dataclass
class TrialBalanceReport:
    rows: list[TrialBalanceRow] = field(default_factory=list)
    total_debit: Decimal = Decimal("0")
    total_credit: Decimal = Decimal("0")


def trial_balance(db: Session, *, company_id: uuid.UUID) -> TrialBalanceReport:
    chart = db.execute(
        select(ChartOfAccount).where(ChartOfAccount.company_id == company_id)
    ).scalar_one_or_none()
    if chart is None:
        return TrialBalanceReport()

    accounts = db.execute(
        select(Account).where(Account.chart_of_account_id == chart.id)
    ).scalars()

    report = TrialBalanceReport()
    for account in accounts:
        balance = accounting_service.account_balance(db, gl_account_id=account.id)
        if balance == Decimal("0"):
            continue
        debit = balance if balance > 0 else Decimal("0")
        credit = -balance if balance < 0 else Decimal("0")
        report.rows.append(
            TrialBalanceRow(account.code, account.name, debit, credit)
        )
        report.total_debit += debit
        report.total_credit += credit
    return report
```

Verify `Account`'s real `chart_of_account_id`/`code`/`name` field names
and `account_balance`'s real sign convention (does a positive result
mean debit-balance or could it be signed the other way for
liability/equity accounts?) against the actual
`accounting_service.py`/`chart_of_accounts.py` files before trusting
this illustrative code — adjust the debit/credit split logic to match
reality, and add a regression test if the sign convention turns out
more nuanced than "positive = debit."

Write `backend/app/schemas/reporting.py` (`TrialBalanceRowResponse`,
`TrialBalanceReportResponse`, `BudgetVsActualRowResponse`,
`BudgetVsActualReportResponse` — `CamelModel` pattern, mirror Task 1's
`schemas/search.py`) and `backend/app/api/routes/reports.py`
(`GET /api/reports/trial-balance?companyId=...`,
`GET /api/reports/budget-vs-actual?projectId=...`, both with
`assert_company_access` — for budget-vs-actual, resolve the project
first to get its `company_id`, same pattern as every prior
resource-scoped route in this codebase).

- [ ] **Step 5: Run the Trial Balance test, confirm it passes**

- [ ] **Step 6: Write the failing Budget vs Actual test, reusing
      `budget_service.compute_summary`'s real, already-tested numbers**

```python
# backend/tests/test_reporting.py — top of file
import uuid
from decimal import Decimal

from tests.helpers import create_company, login_admin


def _create_project(client, *, company_id: str, name: str = "Reporte Torre I") -> dict:
    response = client.post(
        "/api/projects",
        json={"companyId": company_id, "name": name, "code": "RPT-001", "currencyCode": "HNL"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_budget_vs_actual_matches_budget_service_compute_summary(client, db_session):
    from app.services import budget_service

    login_admin(client)
    company = create_company(client)
    project = _create_project(client, company_id=company["id"])
    client.post(
        f"/api/projects/{project['id']}/budgets/baseline",
        json={"currencyCode": "HNL", "lines": [{"authorizedAmount": "1000.00"}]},
    )

    response = client.get(f"/api/reports/budget-vs-actual?projectId={project['id']}")
    assert response.status_code == 200, response.text
    body = response.json()

    trusted = budget_service.compute_summary(db_session, project_id=uuid.UUID(project["id"]))
    assert Decimal(body["authorized"]) == trusted.authorized
    assert Decimal(body["committed"]) == trusted.committed
    assert Decimal(body["accrued"]) == trusted.accrued
    assert Decimal(body["paid"]) == trusted.paid
    assert Decimal(body["available"]) == trusted.available
```

Verify `BudgetSummary`'s real field names (`authorized`/`committed`/
`accrued`/`paid`/`available` are illustrative, taken from the existing
`GET /api/projects/{id}/budgets/summary` endpoint's real response shape
in `backend/tests/test_project_control.py:178-182` — confirm they match
`budget_service.py`'s actual `BudgetSummary` dataclass fields before
writing the reshaping code in Step 7) before trusting this test
verbatim.

- [ ] **Step 7: Implement `reporting_service.budget_vs_actual`, run RED then GREEN**

Thin reshaping of `budget_service.compute_summary`'s real return value
— do not recompute anything `compute_summary` already computes.

- [ ] **Step 8: Write the company-isolation tests for both report endpoints**

Follow Task 1's `test_search_never_returns_another_companys_results`
pattern.

- [ ] **Step 9: Build the shared CSV export utility and the two frontend pages**

```typescript
// frontend/src/utils/csv.ts
export function toCsv<T extends Record<string, unknown>>(
  rows: T[],
  columns: { key: keyof T; label: string }[],
): string {
  const header = columns.map((c) => `"${c.label}"`).join(',')
  const body = rows
    .map((row) =>
      columns.map((c) => `"${String(row[c.key] ?? '').replace(/"/g, '""')}"`).join(','),
    )
    .join('\n')
  return `${header}\n${body}`
}

export function downloadCsv(filename: string, csv: string): void {
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  URL.revokeObjectURL(url)
}
```

Build `TrialBalancePage.tsx`/`BudgetVsActualPage.tsx` following
`AuditLogPage.tsx`'s structure (TanStack Query, `useActiveCompany`,
real `Table` component), each with an "Exportar CSV" button calling
`toCsv` + `downloadCsv` on the currently-loaded rows.

- [ ] **Step 10: Write frontend tests for both pages (real API mock,
      real render, and a test that the export button produces a CSV
      string with the expected header/rows — test `toCsv` directly as
      a pure-function unit test, not by intercepting a real file
      download)**

```typescript
// frontend/tests/csv.test.ts — pure unit test for the utility
import { describe, it, expect } from 'vitest'
import { toCsv } from '../src/utils/csv'

describe('toCsv', () => {
  it('produces a header row and one row per input record', () => {
    const csv = toCsv(
      [{ code: '1000', name: 'Caja', debit: '100.00' }],
      [
        { key: 'code', label: 'Código' },
        { key: 'name', label: 'Cuenta' },
        { key: 'debit', label: 'Débito' },
      ],
    )
    expect(csv).toBe('"Código","Cuenta","Débito"\n"1000","Caja","100.00"')
  })
})
```

- [ ] **Step 11: Run full gates, update docs, commit**

```bash
cd backend
./.venv/bin/pytest -q
./.venv/bin/python -m compileall -q app tests
cd ../frontend
npm run typecheck && npm run lint && npm test -- --run && npm run build
```

Update `docs/PROGRESS.md`/`docs/REQUIREMENTS_TRACEABILITY.md` for
NXR-REQ-0093 — mark `IN_PROGRESS`, not `IMPLEMENTED`: this task
deliberately builds only Trial Balance + Budget vs Actual, not the full
Financial Statements/Treasury/Procurement report brief (per the spec's
Reporting ruling) — the traceability evidence column must say exactly
that, naming what's built and what remains. NXR-REQ-0094 (Export) can
be `IMPLEMENTED` for CSV-only scope, honestly noting XLSX/PDF are out
of scope.

### Task 3: Settings + Integration Architecture (NXR-REQ-0095/0096)

**Files:**
- Modify: `backend/app/api/routes/master_data.py` (add a company-update
  route if none exists — verified before this plan was written: none
  does)
- Modify: `backend/app/schemas/master_data.py` (add a
  `CompanyUpdateRequest` schema if the file doesn't already have one)
- Test: extend `backend/tests/test_master_data.py` (find the real file
  name for Foundation's master-data tests — grep for `create_company`
  usage in `backend/tests/` if `test_master_data.py` doesn't exist)
- Create: `frontend/src/features/settings/CompanySettingsPage.tsx`,
  `frontend/src/services/settingsService.ts` (or extend
  `masterDataService.ts` if one already exists — check first)
- Modify: `frontend/src/app/routes.tsx`, `frontend/src/app/navigation.ts`
- Test: `frontend/tests/CompanySettingsPage.test.tsx`
- Create: `docs/INTEGRATION_ARCHITECTURE.md`

**Interfaces:**
- Consumes: the existing `Company` model (`backend/app/models/company.py`
  — read it first for the exact real field names before writing the
  update schema/route).
- Produces: `PATCH /api/master-data/companies/{id}` (or whatever the
  real existing route file's naming convention is — match it, don't
  invent a different verb/path shape).

- [ ] **Step 1: Read `backend/app/models/company.py` and
      `backend/app/api/routes/master_data.py` in full to find the real
      field names and the real existing create-company route's exact
      pattern (dependency injection, permission check, response
      shape)**

- [ ] **Step 2: Write the failing test for updating a company**

```python
# backend/tests/test_master_data.py — add (create the file if none
# exists with this name; check first for the real existing file)
def test_updating_company_persists_legal_name_and_fiscal_id(client, db_session):
    from tests.helpers import create_company, login_admin

    login_admin(client)
    company = create_company(client)

    response = client.patch(
        f"/api/master-data/companies/{company['id']}",
        json={"legalName": "Constructora Actualizada S.A.", "fiscalId": "0801-1990-12345"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["legalName"] == "Constructora Actualizada S.A."

    refetch = client.get("/api/master-data/companies").json()
    updated = next(c for c in refetch if c["id"] == company["id"])
    assert updated["fiscalId"] == "0801-1990-12345"
```

Verify `legal_name`/`fiscal_id` are the real field names on `Company`
first (per Foundation's own build notes referenced in
`docs/PROGRESS.md`, `Company` was extended with
`code/legal_name/functional_currency/country/fiscal_id` — confirm
against the actual model file, not this plan's memory of that note).

- [ ] **Step 3: Run it, confirm it fails**

- [ ] **Step 4: Add the update schema and route**

Follow the exact create-company route's dependency/permission/response
pattern from `master_data.py` — likely `require_permission("core.company",
"update")` (check whether `"update"` is an existing granted action for
`core.company` in `permission_repository.py`; if only `create`/`read`
exist today, add `update` as a new permission tuple, granted to the
same roles that already have `create`).

- [ ] **Step 5: Run the test, confirm it passes; add a company-isolation
      test (a user without access to company B cannot PATCH it), RED
      then GREEN**

- [ ] **Step 6: Build `CompanySettingsPage.tsx`**

Read-only display of `code`/`functional_currency`, editable form for
`legal_name`/`fiscal_id`, using the design system's existing form
components (check `frontend/src/features/documents/DocumentsPage.tsx`
or a similar create-form page for the real `Input`/`Button` import
paths). Register at a real nav path — check `navigation.ts` for any
already-reserved Settings/Configuración entry first (same discipline
every prior task in this project followed); if none exists, add one
following the existing sectioning convention rather than inventing a
new top-level section arbitrarily.

- [ ] **Step 7: Write a frontend test proving the update actually calls
      the real API and the field reflects the new value after save**

- [ ] **Step 8: Write `docs/INTEGRATION_ARCHITECTURE.md`**

Document the real extension-point contract: how an external adapter
(SAP, an AI agent, etc.) would integrate with NEXORA today, grounded in
what actually exists — the `AuditLog` table (Track G Task 1) as an
event feed an external poller could tail (`GET /api/audit` with
`entityType`/`entity_id` filters already exists), the `Notification`
mechanism (Track G Task 3) as a per-user event surface, and the
existing REST API surface itself (every domain already has a real,
authenticated, company-isolated API). Name what does NOT exist yet
(no webhook/push mechanism, no API key/service-account auth distinct
from user login, no rate limiting) as honest NOT_STARTED groundwork a
future integration effort would need — do not design speculative new
endpoints or adapters, this is a documentation task recording the real
current extension surface, per the plan's own scope ruling.

- [ ] **Step 9: Run full gates, update docs, commit**

```bash
cd backend
./.venv/bin/pytest -q
./.venv/bin/python -m compileall -q app tests
cd ../frontend
npm run typecheck && npm run lint && npm test -- --run && npm run build
```

Update `docs/PROGRESS.md`/`docs/REQUIREMENTS_TRACEABILITY.md` for
NXR-REQ-0095 (`IMPLEMENTED` for the one real company-profile screen)
and NXR-REQ-0096 (`IMPLEMENTED` for the documentation deliverable,
honestly noting it's architecture-only per the matrix's own `➖` FE/E2E
markers, not code).

### Task 4: Combined verification and traceability recount

**Files:**
- Verify: all files touched by Tasks 1-3 once integrated on
  `feat/nexora-greenfield`
- Modify only if evidence warrants it: `docs/PROGRESS.md`,
  `docs/REQUIREMENTS_TRACEABILITY.md`, `docs/DEFERRED.md`

**Interfaces:**
- Consumes: the fully integrated Search/Reporting/Settings/Integration-doc
  system.
- Produces: one reproducible integration head and an honest
  traceability update for NXR-REQ-0092 through 0096.

- [ ] **Step 1: Verify Git topology and exact modified file set**

```bash
git status
git log --graph --decorate --oneline -30
git diff --check
git diff --stat origin/feat/nexora-greenfield...HEAD
```

- [ ] **Step 2: Verify one Alembic head, upgrade path, fresh-install
      path** (only relevant if any task actually added a migration —
      this plan's scope as designed needs none; confirm no task
      silently added one without a real schema need)

```bash
./.venv/bin/alembic heads
./.venv/bin/alembic upgrade head   # on a fresh disposable database, then drop it
```

- [ ] **Step 3: Run complete backend/frontend verification from the
      integration worktree**

```bash
./.venv/bin/pytest -q
./.venv/bin/python -m compileall -q app tests
npm run typecheck && npm run lint && npm test -- --run && npm run build
```

- [ ] **Step 4: Recount `docs/REQUIREMENTS_TRACEABILITY.md` row-by-row
      against its own summary (same method used four times already
      this session). Update `docs/DEFERRED.md` with any new items the
      three tasks' own reports name (deliberately-out-of-scope
      sub-pieces of Reporting, any Search entity types cut for time,
      etc.) — do not silently drop what the implementers themselves
      flagged. Continue with the highest-dependency-free next slice
      from `docs/MASTER_PLAN.md` rather than inflating completion.**
