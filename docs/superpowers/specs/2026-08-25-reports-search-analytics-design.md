# Reports / Search / Analytics — Design

Status: internal brainstorm per user's explicit standing order this
session ("brainstorm interno sin preguntarme... decide tú"). No
AskUserQuestion pauses — scope rulings below are the controller's
judgment calls, recorded so they can be reworked if wrong.

## Goal

Close NXR-REQ-0092 through 0096 (the PLATFORM block's remaining rows):
Global Search, Reporting, Export, Settings, Integration architecture.

## Grounding in real code (checked before writing this spec)

- `frontend/src/design-system/primitives/CommandPalette.tsx:15-21` already
  exists (Track F), searches local nav today, and its own docstring names
  the exact contract a real search must satisfy: `CommandItem { id,
  label, group, path }`, fed by `GET /api/v1/search`. **Correction**: no
  route in this codebase uses an `/api/v1` prefix — `backend/app/main.py`
  registers every router under plain `/api`. This plan builds
  `GET /api/search`, matching the real house convention; Track F's
  comment was aspirational/inaccurate on the exact path, not the shape.
- `backend/app/services/accounting_service.py::account_balance(db, *,
  gl_account_id) -> Decimal` already exists — the real building block for
  a Trial Balance (sum every account's balance, assert total debits =
  total credits).
- `backend/app/services/budget_service.py::compute_summary(db, *,
  project_id) -> BudgetSummary` already exists — the real building block
  for a Budget vs Actual report.
- No `Settings` concept exists anywhere in the frontend yet — genuinely
  greenfield within this plan.

## Scope rulings (decided per the user's "decide tú" standing order)

**Global Search (NXR-REQ-0092) — full scope, this plan.** One backend
endpoint (`GET /api/search?q=...`), company-isolated, aggregating across
a fixed, named set of entities matching the master order's own list:
Project, Supplier, Customer, SupplierInvoice/CustomerInvoice
("Invoice"), PurchaseOrder ("PO"), Document, RequestForInformation
("RFI"), FixedAsset ("Asset"), Equipment. Real pagination (a result cap
per entity type, not an unbounded scan). Wires the already-built
`CommandPalette` to real results instead of local-nav-only.

**Reporting (NXR-REQ-0093) — a real first slice, not the full brief.**
The user's mega-instruction named Financial Statements (Trial
Balance/GL/Balance Sheet/P&L/Cash Flow), Treasury reports, Project
reports (Budget vs Actual/Commitments/Accruals/Payments/Forecast/Earned
Value/CPI-SPI-EAC-VAC/progress), and Procurement reports as one giant
block. Building all of that with real, correct accounting logic
(Balance Sheet and P&L require mapping every `Account` to a statement
category — asset/liability/equity/revenue/expense — which does not
exist as a field on `ChartOfAccount`/`Account` today) is a multi-week
accounting-modeling effort on its own, not a slice of a Search/Export
plan. This plan builds the two reports with the clearest existing data
foundation and the highest standalone value:
- **Trial Balance** (real: sum of every account's real ledger balance
  via the existing `account_balance` function, DEBIT total = CREDIT
  total asserted, per company).
- **Budget vs Actual** (real: reuses `budget_service.compute_summary`
  per project, table of budgeted/committed/actual/variance).
Everything else named in the brief (Balance Sheet, P&L, Cash Flow,
Treasury reports, Earned Value/CPI/SPI/EAC/VAC, Procurement reports) is
explicitly NOT built in this plan and is recorded honestly as
`NOT_STARTED` sub-scope of NXR-REQ-0093 in the traceability update, with
a named reason (Balance Sheet/P&L need an `Account.statement_category`
field that doesn't exist yet; Earned Value needs a schedule-variance
model Project Control never built) — not silently implied done. Cost if
wrong: NXR-REQ-0093 stays `IN_PROGRESS` rather than `IMPLEMENTED` after
this plan; a follow-up plan closes the rest.

**Export (NXR-REQ-0094) — CSV only, on the two reports this plan
builds.** XLSX/PDF are explicitly out of scope (YAGNI — CSV is the
simplest format that satisfies "export real, not just a button" and
every table in this app already renders from the same row-shaped data a
CSV needs). A generic `toCsv(rows, columns)` frontend utility, reused by
both report pages.

**Settings (NXR-REQ-0095) — a real, minimal company-profile page.**
View/edit `Company.legal_name`/`Company.fiscal_id` (fields that already
exist on the model per Foundation), read-only display of
`functional_currency`/`code` (changing functional currency mid-stream is
a real accounting hazard this plan does not open). Not a general
"settings" framework — one real, working screen for the one settings
concept that already has backing data.

**Integration architecture (NXR-REQ-0096) — documentation only, per the
traceability matrix's own markers.** The existing row
(`docs/REQUIREMENTS_TRACEABILITY.md`) already marks this row's FE and
E2E columns `➖` (not applicable) — the matrix itself treats this as a
backend/architecture concern, not a UI feature. This plan produces
`docs/INTEGRATION_ARCHITECTURE.md`: the real extension-point contract
future SAP/AI adapters would use, grounded in what already exists
(the `AuditLog`/`Notification` event points Track G built are the
natural hook — document how an external adapter would subscribe to
them), not speculative new code for integrations nothing in this
project has asked for yet.

## Components

### 1. Global Search

**Service** `search_service.search(db, *, company_id: uuid.UUID, query:
str, limit_per_type: int = 5) -> list[SearchResult]` — one `ILIKE`
query per entity type (Project.name, Supplier.legal_name,
Customer.legal_name, SupplierInvoice.invoice_number,
CustomerInvoice.invoice_number, PurchaseOrder.number, Document.title,
RequestForInformation.number, FixedAsset.name, Equipment.name — exact
field names verified against each model file at implementation time,
not guessed), each capped at `limit_per_type`, all scoped by
`company_id`. `SearchResult { id, label, group, path, entity_type }`
maps directly onto `CommandItem`.

**API** `GET /api/search?companyId=...&q=...` — company-isolated
(`assert_company_access` is not quite right here since this crosses
many resource types; use the same pattern `GET /api/audit` established:
require a real permission grant `search.global/read` and check
`UserCompanyAccess`, not per-entity-type checks).

**Frontend**: `frontend/src/services/searchService.ts` calls the real
endpoint; `AppLayout.tsx`/`Topbar.tsx` feeds `CommandPalette` a merged
list (existing local nav items + debounced real search results) instead
of nav-only.

### 2. Reporting: Trial Balance + Budget vs Actual

**Trial Balance**: `reporting_service.trial_balance(db, *, company_id:
uuid.UUID) -> TrialBalanceReport` — iterates every `Account` for the
company's `ChartOfAccount`, calls the real `accounting_service.
account_balance` per account, returns rows + asserts
`sum(debit_balances) == sum(credit_balances)` (INV-ACC-001 restated as a
report-level invariant, not just a per-document one). API:
`GET /api/reports/trial-balance?companyId=...`.

**Budget vs Actual**: `reporting_service.budget_vs_actual(db, *,
project_id: uuid.UUID) -> BudgetVsActualReport` — thin wrapper over the
real `budget_service.compute_summary`, reshaped for a report table
(budgeted/committed/actual/variance per WBS line). API:
`GET /api/reports/budget-vs-actual?projectId=...`.

**Frontend**: `frontend/src/features/reports/TrialBalancePage.tsx`,
`frontend/src/features/reports/BudgetVsActualPage.tsx`, both with a
"Exportar CSV" button using the shared `toCsv` utility.

### 3. Settings

**API**: reuses the existing `Company` model/repository (no new
backend files beyond a schema + one PATCH route) —
`PATCH /api/master-data/companies/{id}` if a company-update endpoint
doesn't already exist (check `backend/app/api/routes/master_data.py`
first — do not assume), or add one following its exact existing
create-company pattern.

**Frontend**: `frontend/src/features/settings/CompanySettingsPage.tsx`.

## Testing

Real TDD per component, same house pattern as every prior task:
- Search: company isolation (a company-A search never returns a
  company-B row); each entity type returns real matches from real
  fixtures, not fabricated data.
- Trial Balance: DEBIT total = CREDIT total on a real posted document
  set; company isolation.
- Budget vs Actual: matches `budget_service.compute_summary`'s own
  already-tested numbers exactly (no parallel calculation).
- Settings: update persists, company isolation on the PATCH.

## Out of scope (explicit, not hidden)

- Balance Sheet, P&L, Cash Flow, Treasury reports, Procurement reports,
  Earned Value/CPI/SPI/EAC/VAC — see the Reporting ruling above.
- XLSX/PDF export.
- A general Settings framework beyond company profile.
- Any real SAP/AI adapter code (NXR-REQ-0096 is documentation-only in
  this plan, per the matrix's own `➖` FE/E2E markers).
- Changing `functional_currency` post-creation.
