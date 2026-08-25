# Interrupted Tracks Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Recover, complete, certify, and safely integrate Tracks C, A, D, and E without discarding any interrupted-session work.

**Architecture:** Preserve each existing worktree and branch as the unit of ownership. Integrate Track C first, then Track A so procurement entities are available to AP; linearize the unpublished Alembic revisions as each track is brought onto `feat/nexora-greenfield`. After those integrations, bring D and E up to the latest integration head and implement vertical slices that reuse the existing Posting Engine, RBAC, ActiveUIContext, design system, and domain APIs.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2, Alembic, PostgreSQL 16, Pytest, React, TypeScript, Vite, TanStack Query, Vitest/RTL.

**Spec:** `docs/MASTER_PLAN.md`, `docs/REQUIREMENTS_TRACEABILITY.md`, `CLAUDE.md`

## Global Constraints

- Treasury is the sole owner of money; Project never owns cash.
- `OperationScope` is exactly `CENTRAL | GENERAL | PROJECT`; `ActiveUIContext` remains independent.
- All backend state is persisted in PostgreSQL; no in-memory or filesystem-persistent substitutes.
- No new infrastructure dependency and no real Azure provisioning.
- Every domain slice follows domain/DB/service/API/permission/frontend/test and updates traceability honestly.
- Do not delete worktrees, branches, local changes, or checkpoint refs.
- Never mark a requirement `VERIFIED` without end-to-end evidence.

---

### Task 1: Certify and preserve Track C

**Files:**
- Existing commits: `6e92a87`, `9b5cb1f`
- Modify: `/Users/clopezg/nexora-group-trackC/docs/PROGRESS.md`
- Modify: `/Users/clopezg/nexora-group-trackC/docs/REQUIREMENTS_TRACEABILITY.md`
- Modify: `/Users/clopezg/nexora-group-trackC/frontend/src/app/routes.tsx`
- Create/retain: `/Users/clopezg/nexora-group-trackC/docs/PROCUREMENT.md`
- Create/retain: `/Users/clopezg/nexora-group-trackC/docs/INVENTORY.md`
- Create/retain: `/Users/clopezg/nexora-group-trackC/frontend/src/features/procurement/*`
- Create/retain: `/Users/clopezg/nexora-group-trackC/frontend/src/features/inventory/*`
- Test: `/Users/clopezg/nexora-group-trackC/backend/tests/test_procurement.py`
- Test: `/Users/clopezg/nexora-group-trackC/backend/tests/test_inventory.py`
- Test: `/Users/clopezg/nexora-group-trackC/frontend/tests/SuppliersPage.test.tsx`

**Interfaces:**
- Consumes: Foundation company, project, permissions, and `budget_service.compute_summary` contracts.
- Produces: supplier/item/warehouse IDs, purchase-order and receipt lifecycles, append-only stock ledger, and commitment/actual aggregations for Project Control and AP.

- [ ] **Step 1: Run the committed backend tests and capture real failures**

```bash
cd /Users/clopezg/nexora-group-trackC/backend
/Users/clopezg/nexora-group/backend/.venv/bin/pytest -q
```

- [ ] **Step 2: Run frontend gates against the recovered uncommitted UI**

```bash
cd /Users/clopezg/nexora-group-trackC/frontend
npm run typecheck
npm run lint
npm run test
npm run build
```

- [ ] **Step 3: Add failing tests for the known gaps that are in this slice**

```text
test_commitments_are_derived_from_approved_purchase_orders:
  An approved PO of 125.50 for project P contributes Decimal("125.50")
  to P's COMMITTED total; a draft PO contributes zero.
test_inventory_actuals_are_derived_from_project_issues:
  A posted project issue with value 80.00 contributes Decimal("80.00")
  to P's actual cost; warehouse transfers contribute zero.
test_company_access_blocks_cross_company_procurement_resource:
  A user scoped to company A receives HTTP 403 for a company B PO ID.
```

- [ ] **Step 4: Implement only the integration needed to satisfy those tests**

```python
# Repository queries return Decimal totals keyed by project_id/WBS.
# budget_service consumes those totals without storing cash on Project.
```

- [ ] **Step 5: Correct traceability counts and document honest partial features**

```text
Bid comparison, returns, supplier performance, and contract/subcontract gaps
remain IN_PROGRESS or NOT_STARTED unless their complete vertical slice exists.
```

- [ ] **Step 6: Re-run all Track C gates, inspect `git diff --check`, and commit the recovered UI/docs/fixes**

```bash
git diff --check
git status --short
git add backend frontend docs
git commit -m "feat(supply-chain): complete procurement and inventory slice"
```

### Task 2: Integrate Track C safely

**Files:**
- Merge: `feat/nexora-greenfield` into `track/c-supply-chain`
- Resolve: `backend/app/api/error_handlers.py`
- Resolve: `backend/app/domain/errors.py`
- Resolve: `backend/app/main.py`
- Resolve: `backend/app/models/__init__.py`
- Resolve: `backend/app/repositories/permission_repository.py`
- Modify: Track C Alembic revision `8bf7c353d327`
- Resolve: `frontend/src/app/routes.tsx`

**Interfaces:**
- Consumes: Track B revision `131a6debf189` and project-control routes/UI.
- Produces: one Alembic head and a combined application containing B+C.

- [ ] **Step 1: Merge the integration branch into Track C without discarding either side**

```bash
git merge --no-ff feat/nexora-greenfield
```

- [ ] **Step 2: Resolve central registries additively and linearize the unpublished migration**

```python
# Track C migration down_revision = "131a6debf189"
# main.py/models/__init__.py/permissions/routes retain both Track B and C entries.
```

- [ ] **Step 3: Verify migration topology and fresh upgrade**

```bash
./.venv/bin/alembic heads
./.venv/bin/alembic upgrade head
```

- [ ] **Step 4: Run full backend and frontend gates, review the merge diff, commit fixes, then merge Track C into `feat/nexora-greenfield`**

```bash
./.venv/bin/pytest -q
npm run typecheck
npm run lint
npm run test
npm run build
git diff --check
```

### Task 3: Harden, certify, and preserve Track A

**Files:**
- Retain all current changes in `/Users/clopezg/nexora-group-trackA`
- Modify: `backend/app/api/routes/ap.py`
- Modify: `backend/app/api/routes/ar.py`
- Modify: `backend/app/api/routes/treasury.py`
- Modify: `backend/app/schemas/ap.py`
- Modify: `backend/app/schemas/ar.py`
- Modify: `backend/app/schemas/treasury.py`
- Modify: `backend/app/services/ap_service.py`
- Modify: `backend/app/services/ar_service.py`
- Modify: `backend/app/services/treasury_service.py`
- Modify/Create tests: `backend/tests/test_ap_ar.py`, `backend/tests/test_treasury_operations.py`
- Modify: treasury/AP/AR frontend pages and tests
- Modify: `docs/PROGRESS.md`, `docs/REQUIREMENTS_TRACEABILITY.md`

**Interfaces:**
- Consumes: Posting Engine, supplier entities from Track C, company access, and Project/WBS attribution.
- Produces: treasury positions and operations, persisted AP/AR lists, accrual/payment/collection totals, and APIs for Commercial.

- [ ] **Step 1: Run recovered Track A tests before altering behavior**

```bash
cd /Users/clopezg/nexora-group-trackA/backend
/Users/clopezg/nexora-group/backend/.venv/bin/pytest -q
```

- [ ] **Step 2: Add failing security and accounting regression tests**

```text
test_ap_resource_from_other_company_is_denied: cross-company invoice ID -> 403.
test_payment_account_company_must_match_invoice_company: mismatched account -> 422 and no posting.
test_negative_or_zero_monetary_amount_is_rejected: zero and negative API amounts -> 422.
test_reconciliation_uses_cumulative_matches_and_blocks_overmatch: 40 + 60 matches a 100 movement; a further 1 is rejected.
test_retrying_payment_with_same_idempotency_key_does_not_duplicate_posting: two identical calls return one payment and one accounting document.
```

- [ ] **Step 3: Add failing API/UI persistence tests**

```text
test_supplier_and_customer_invoices_can_be_listed_from_database:
  Create one invoice, construct a new API client request, GET the collection,
  and assert the persisted invoice ID is returned.
```

```tsx
it('reloads AP and AR invoices from their APIs instead of component state', async () => {})
```

- [ ] **Step 4: Implement minimal validation, company isolation, idempotency, cumulative reconciliation, and list endpoints**

```python
# Resolve each resource, assert company access, validate related account/company,
# then call PostingService once behind the persisted idempotency record.
```

- [ ] **Step 5: Re-run backend/frontend gates, correct ownership documentation (A supplies AR for E), inspect the diff, and commit logical backend/UI units**

```bash
git diff --check
git status --short
```

### Task 4: Integrate Track A on top of B+C

**Files:**
- Merge: latest `feat/nexora-greenfield` into `track/a-financial-core`
- Resolve additively: shared error, main, model, permission, master-data, route, helper, and frontend registry files
- Modify: Track A Alembic revision `58ce35982711`

**Interfaces:**
- Consumes: latest integration head and Track C supplier IDs.
- Produces: a single migration head and combined B+C+A system.

- [ ] **Step 1: Merge latest integration and resolve all registries additively**

```bash
git merge --no-ff feat/nexora-greenfield
```

- [ ] **Step 2: Point the unpublished Track A revision to Track C's revision and add real supplier relations without duplicating entities**

```python
# Track A migration down_revision = "8bf7c353d327"
```

- [ ] **Step 3: Run migration, full backend/frontend gates, review diff/history, and merge Track A into `feat/nexora-greenfield`**

```bash
./.venv/bin/alembic heads
./.venv/bin/alembic upgrade head
./.venv/bin/pytest -q
npm run typecheck
npm run lint
npm run test
npm run build
```

### Task 5: Complete Track D from the recovered model drafts

**Files:**
- Retain: `/Users/clopezg/nexora-group-trackD/backend/app/models/asset.py`
- Retain: `/Users/clopezg/nexora-group-trackD/backend/app/models/equipment.py`
- Create: Track D tests, migration, schemas, repositories, services, routes, frontend features, services, types, and domain docs following existing project layout
- Modify additively: model/router/permission/frontend registries and traceability docs

**Interfaces:**
- Consumes: latest Posting Engine, company/project/WBS, evidence storage, RBAC, and design system.
- Produces: fixed assets/depreciation, equipment/fuel/maintenance, workforce/time/labor cost, and document/site/quality slices.

- [ ] **Step 1: Preserve the two recovered drafts on their existing branch, then merge latest integration before expanding them**

```bash
git add backend/app/models/asset.py backend/app/models/equipment.py
git commit -m "chore(resources): preserve interrupted model drafts"
git merge --no-ff feat/nexora-greenfield
```

- [ ] **Step 2: Write failing domain tests for positive monetary values, lifecycle transitions, straight-line depreciation uniqueness, scope constraints, labor cost, and append-only evidence/version behavior**

```text
test_depreciation_period_cannot_be_posted_twice: second asset/period entry is rejected and only one DEP posting exists.
test_project_fuel_log_requires_project_id: PROJECT without project_id violates the domain and DB constraint.
test_closed_maintenance_order_is_immutable: update after CLOSED is rejected and persisted values remain unchanged.
test_labor_cost_equals_approved_rate_times_hours: rate 125.50 x 8 approved hours records 1004.00 project cost.
```

- [ ] **Step 3: Implement one independently testable vertical slice at a time and run its focused tests before the next slice**

```text
Assets -> Equipment/Maintenance -> Workforce/Time -> Documents/Site/Quality.
```

- [ ] **Step 4: Run complete migration/backend/frontend gates, update documentation honestly, review, and integrate Track D**

```bash
./.venv/bin/alembic heads
./.venv/bin/alembic upgrade head
./.venv/bin/pytest -q
npm run typecheck
npm run lint
npm run test
npm run build
```

### Task 6: Build and integrate Track E without duplicating AR

**Files:**
- Create: CRM/customer/opportunity/quotation/contract domain, migration, repository, schema, service, API, UI, and tests in `/Users/clopezg/nexora-group-trackE`
- Reuse: Track A customer-invoice and collection services/APIs
- Modify: `Project.customer_ref` integration path, permissions, routes, frontend routes, and traceability docs

**Interfaces:**
- Consumes: latest integration head, Track A AR invoices/collections, project control, RBAC, and design system.
- Produces: lead-to-customer-to-contract flow and billing handoff into AR.

- [ ] **Step 1: Merge latest integration into the clean Track E branch**

```bash
git merge --no-ff feat/nexora-greenfield
```

- [ ] **Step 2: Write failing tests for lead conversion, opportunity lifecycle, accepted quotation to sales contract, company isolation, project/customer linkage, and billing handoff to AR**

```text
test_converting_lead_creates_customer_once: repeated conversion returns the same customer and one customer row.
test_accepted_quotation_creates_sales_contract: only ACCEPTED quotation converts; amount, company, customer and project are preserved.
test_sales_contract_billing_creates_ar_invoice_via_financial_core: billing creates one persisted Track A AR invoice and no treasury movement before collection.
```

- [ ] **Step 3: Implement the minimal vertical CRM/sales flow and real persisted UI**

```text
Lead -> Opportunity -> Customer/Quotation -> Sales Contract -> AR invoice.
```

- [ ] **Step 4: Run all gates, update evidence, review, and integrate Track E**

```bash
./.venv/bin/alembic heads
./.venv/bin/alembic upgrade head
./.venv/bin/pytest -q
npm run typecheck
npm run lint
npm run test
npm run build
```

### Task 7: Combined-system verification and next-track handoff

**Files:**
- Verify: all modified files in `feat/nexora-greenfield`
- Modify only if evidence warrants it: `docs/PROGRESS.md`, `docs/REQUIREMENTS_TRACEABILITY.md`, `docs/DEFERRED.md`

**Interfaces:**
- Consumes: integrated A/C/D/E features.
- Produces: one reproducible integration head and an evidence-backed next-track backlog.

- [ ] **Step 1: Verify Git topology and exact modified file set**

```bash
git status
git log --graph --decorate --oneline -40
git diff --check
git diff --stat origin/feat/nexora-greenfield...HEAD
```

- [ ] **Step 2: Verify one Alembic head, upgrade path, and fresh-install path**

```bash
./.venv/bin/alembic heads
./.venv/bin/alembic upgrade head
```

- [ ] **Step 3: Run complete backend/frontend verification from the integration worktree**

```bash
./.venv/bin/pytest -q
npm run typecheck
npm run lint
npm run test
npm run build
```

- [ ] **Step 4: Review traceability line by line and continue with the highest-dependency-free Track G/remaining slice rather than inflating completion**

```text
Only IMPLEMENTED/IN_PROGRESS states supported by the commands and tests above
are recorded; VERIFIED remains gated on real combined behavior/E2E evidence.
```
