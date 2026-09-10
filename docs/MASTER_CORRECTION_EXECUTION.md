# Master correction execution — continuity

## Initial state (supervisor iteration 1)

- REFERENCE_AUDITED_SHA=dc58619c9cdfb8e4648eedd8fa4cba2200a9d4c8
- INITIAL_MAIN_SHA=dc58619c9cdfb8e4648eedd8fa4cba2200a9d4c8
- PROCESS_START_SHA=9eb1a4bdb0336582797bfe5f4cac9e514accb040
- Branch: `fix/nexora-phase1-core-foundations`; initially clean, one local commit ahead of remote.
- Fetch completed; existing changes preserved and subsequently published.
- Phase 1 remains incomplete; CORE_BASELINE_SHA, DOMAIN_INTEGRATION_SHA and FINAL_CERTIFIED_SHA are PENDING.

## Executed

- Commit `1be88d9d`: fiscal bootstrap now ends when a FiscalYear exists, even if no periods have been generated. Regression reproduced DID NOT RAISE before the fix.
- Targeted PostgreSQL regression: 33 passed (fiscal, posting, project setup and lifecycle).
- Backend critical Ruff checks and compileall passed.
- Frontend typecheck, lint, 65 test files / 204 tests and production build passed.
- Fresh isolated PostgreSQL database `nexora_phase1_migrations_20260908`: real Alembic upgrade to `e4f6a8b0c2d3` passed. Log: `/tmp/nexora-phase1-migrations.log`.
- Draft PR: https://github.com/Clopezgg/nexora-group/pull/114 (continue this PR; do not merge until Phase 1 requirements and CI pass).

## Running verification — inspect before starting another runner

Full serial backend `pytest -q` launched from backend, writing `/tmp/nexora-phase1-full-pytest.log`. It uses `nexora_test_nexora_group`. Do not run another schema-resetting pytest against that database while this process runs. Check running process and log; do not infer PASS from progress dots. The session's exec ID is 40489.

## Next known Phase 1 work

- Complete fiscal DB overlap and company/year integrity defenses using a NEW migration; current fiscal migration only supplies range/status/positive-number checks.
- Define and test SOFT_CLOSED authorization/audit policy centrally; current gate only rejects CLOSED.
- Add real two-session Project Setup and Lifecycle concurrency tests. Existing targeted tests do not prove concurrency.
- Revalidate posting/reversal immutability, source adapters, idempotency and economic dates across consumers against the master order.
- Finish remaining core requirements, full backend and concurrency regression, CI, safe merge, then obtain real CORE_BASELINE_SHA before Phase 2.
- Retain observed warnings for later review: Starlette httpx/422 deprecations; frontend test-environment localStorage, HydrateFallback and zero-size chart warnings. No test was skipped or error suppressed to pass.

No Azure deployment, production verification, audit-item closure or final certification is claimed.

## CI dependency correction

CI run `34303670382` failed frontend dependency audit before typecheck. Local reproduction identified GHSA-2883-xcg3-v3hh in js-yaml 4.3.1. Updated only its lockfile entry to patched 4.3.2 using `npm update js-yaml --cache /tmp/nexora-npm-cache`; npm audit at the unchanged high threshold now passes. Three moderate advisories remain in the Vitest dependency chain (GHSA-82fw-gwwq-j7x9); upstream fixes start at 4.1.11, requiring a deliberate major-version upgrade from the current 3.x, still pending. No audit exclusions or CI gate changes were introduced.

Authoritative advisories: https://github.com/advisories/GHSA-2883-xcg3-v3hh and https://github.com/advisories/GHSA-82fw-gwwq-j7x9 . Inspect latest PR checks rather than treating this initial failed run as current evidence.

## Supervisor iteration 2 — fiscal DB integrity

- Start HEAD: `a192ed5a8d6230a757cfc83aa624120d26bb7208`; fetched `origin/main` remains the audited SHA. Clean initial working tree; existing draft PR #114 retained.
- New migration `f5a7b9c1d3e4`: GiST exclusions enforce non-overlapping inclusive fiscal year/period ranges per company; composite FK enforces period/year company identity. Locked preflight rejects incompatible rows without modifying them. Requires PostgreSQL `btree_gist`.
- Four invalid-data cases reproduced `DID NOT RAISE` before implementation. Real two-session service race reproduced an uncaught DB conflict; `create_year` now locks Company before overlap validation, producing one year and one domain rejection.
- Targeted regression: **39 passed**, fiscal DB integrity/concurrency, economic-date gate, posting, setup and lifecycle. Log `/tmp/nexora-fiscal-regression-iteration2.log`. Existing Starlette deprecation warnings remain.
- Real clean Alembic upgrade succeeded on `nexora_fiscal_clean_iteration2`; upgrade from prior head succeeded on `nexora_phase1_migrations_20260908`. Single head `f5a7b9c1d3e4`; PostgreSQL catalog confirms two exclusion constraints and composite FK.
- Downgrade/preflight experiment on the isolated clean database: injected two overlapping fixture years, upgrade rejected, both rows and previous version preserved; explicitly corrected fixture dates and re-upgrade passed. Script `/tmp/nexora-fiscal-migration-check.py`.
- Critical Ruff and Python compile passed. Bicep compiled using local binary with `DOTNET_BUNDLE_EXTRACT_BASE_DIR=/tmp/nexora-dotnet`. Azure extension allowlist is declared in Bicep and prepared before the workflow's migration step; no Azure mutation/deployment was executed.
- Azure extension requirement: https://learn.microsoft.com/en-us/azure/postgresql/extensions/how-to-allow-extensions .
- Latest observed CI of prior SHA: run `34303802147`, frontend/IaC/Docker passed, backend/E2E still running. This is not evidence for the new changes until pushed and checked.
- Remaining Phase 1: SOFT_CLOSED permission/audit policy; Setup/Lifecycle two-session regression; full posting/reversal/source synchronization review; complete serial regression and CI; integration. No baseline SHA or certification yet.

## Project concurrency verification (iteration 2)

- Added two real independent-session regressions: same stale DRAFT SetupRun creates exactly one Project/WBS/Budget/access grant; competing ACTIVE→ON_HOLD / ACTIVE→COMPLETED transitions yield one winner, one 409, one audit mutation.
- Mutation verification removed row locking/refresh temporarily, then restored the exact original files: both tests failed for actual violations (two different project IDs; both incompatible transitions accepted). Log `/tmp/nexora-project-concurrency-mutation.log`.
- After restoring production locking, both tests passed again; critical Ruff and compile passed. Existing production fixes preserved without additional implementation changes.
- Prior CI run `34303802147` E2E now reports failure; backend remains running. Inspect job `102316158894` logs and newer run before Phase 1 closure. No CI-green claim.

## Supervisor iteration 4 — economic closing checks and Protected Edit E2E

- Start HEAD `8ee06693dfdf348a2ba92cb4f3276e658b8ed8b5`; successful fetch confirms `origin/main` still `dc58619c9cdfb8e4648eedd8fa4cba2200a9d4c8`. Preserved the existing uncommitted Critical Journey helper changes.
- Commit `08360a08`: closing checklist draft and double-entry checks now use `AccountingDocument.effective_date`. A real PostgreSQL/API regression first reproduced an undetected draft with `posted_at=NULL`; it now blocks hard close for its economic period. Four new cases cover inside/outside dates for draft and balance checks.
- Targeted closing/fiscal/posting regression: **31 passed**, no skips, 3 existing Starlette deprecation warnings. Logs `/tmp/nexora-closing-red-iteration4.log` and `/tmp/nexora-closing-green-iteration4.log`. Ruff critical checks, compileall and diff check passed. No schema change or migration in this commit.
- Frontend typecheck/lint, **65 files / 204 unit tests**, and production build passed. Logs `/tmp/nexora-frontend-unit-iteration4.log` and `/tmp/nexora-frontend-build-iteration4.log`.
- Full serial backend restarted because the old runner was no longer alive and its truncated log did not prove completion. New log `/tmp/nexora-phase1-full-iteration4.log`, exec session 41658, database `nexora_test_nexora_group`. Do not start a competing schema-resetting runner on that database. This is RUNNING, not a PASS claim.
- E2E root cause from CI: POST reversal returned 428 because the test helper sent Protected Edit only for PUT/PATCH/DELETE. Local real Chromium/PostgreSQL/Azurite run advanced past that with the preserved helper change and exposed a second omission: the new approver session must unlock through the UI. The test now performs 428 → UI unlock → retry and checks the actual invoice state. Verification of this final E2E change is pending below.
- Local Chromium initially could not launch under the macOS MachPort sandbox; rerunning with the permitted execution override launched the real browser. No application security setting was disabled.
- Latest inspected prior-SHA CI `34304457942`: frontend, Bicep and Docker pass; E2E fails; backend still running. PR #114 remains draft and must not merge yet.
- Core follow-up remains mandatory: SOFT_CLOSED permission/audit policy; fiscal transition/posting serialization; consolidated reversal authority (`posting_service.reverse_document` and `payment_receipt_reversal_service._reverse_posted_document` currently construct reversals separately); posting/source uniqueness and adapters; full regression/CI/integration. Existing Setup/Lifecycle concurrency corrections need no duplicate implementation.

### E2E verification and actual client correction

The explicit approval assertion exposed a production client defect: `apiFetch` still omitted the capability on POST even after UI unlock. Corrected this centrally for POST mutations; the backend still classifies and enforces protected actions. A new unit regression failed specifically for POST before the fix; all 11 HTTP-client tests pass afterward.

Final local Critical Journey: **1 passed (44.6s)** with real Chromium, clean Alembic PostgreSQL database, Azurite, UI unlock, approval and resulting APPROVED invoice checked. Log `/tmp/nexora-critical-green-iteration4.log`. The previous full E2E run had **6 passed / 1 failed** before this client correction; its six accessibility/visual tests passed, but a full same-SHA CI rerun is still required. Do not describe that previous run as fully green.

After the production-client change: frontend typecheck, lint, **65 files / 209 tests**, and build all pass. No permissions, fiscal rules, test thresholds or CI gates were relaxed. Full backend remains pending, so no phase baseline, merge or certification is claimed.

## Supervisor iteration 5 — fiscal posting/transition serialization

- Initial HEAD `2b2a1624fff8378e3c1be6fb0019edc0df719a4c`; fetched origin, clean tree, `origin/main` still audited `dc58619c9cdfb8e4648eedd8fa4cba2200a9d4c8`. PR #114 retained.
- Three new independent PostgreSQL session regressions reproduced missing synchronization: posting passed an uncommitted closure; closure passed an active eligibility transaction; stale OPEN identity allowed overwriting committed CLOSED. All three failed before implementation (`/tmp/nexora-fiscal-red-iteration5.log`).
- Central fiscal gate now acquires FOR SHARE and refreshes ORM state; period transitions acquire FOR UPDATE and refresh before evaluating the graph. Locks remain until transaction completion. Concurrent postings can share the period lock, while closure must wait.
- Directed fiscal/posting/closing regression: **40 passed**, 3 existing Starlette deprecation warnings; `/tmp/nexora-fiscal-regression-iteration5.log`. Critical Ruff, compileall and diff check passed. No schema changes or migration required.
- Tests use isolated `nexora_fiscal_iteration5_nexora_group`, not the previous full-regression database. PostgreSQL lock timeout is asserted via SQLSTATE 55P03; no sleep-based ordering or mocked persistence.
- Previous full backend iteration-4 log remains truncated at 35%; no connections to its test database remained when inspected. It is NOT a passing full regression.
- Latest observed prior-SHA CI `34305301720`: frontend/Bicep/Docker success, backend/E2E in progress. PR Deploy Azure success is not production deployment evidence.
- Still mandatory: SOFT_CLOSED explicit permission/audit policy; lock before hard-close checklist and accurate pre-transition audit snapshots; calendar bootstrap/configuration race review; consolidated reversal authority/source adapters; source uniqueness; full backend/CI and phase integration. This change does not certify all fiscal concurrency paths or close Phase 1.

### Hard-close follow-up

A fourth PostgreSQL independent-session test reproduced duplicate hard-close manifests from a stale OPEN object after another transaction committed CLOSED. `hard_close` now locks and refreshes the period **before** the checklist, so posting eligibility cannot advance while it is evaluated. Regression: **10 passed** (fiscal serialization + closing center), with existing Starlette warnings, `/tmp/nexora-hardclose-green-iteration5.log`; failing reproduction `/tmp/nexora-hardclose-red-iteration5.log`. Ruff critical checks/compileall/diff check passed. Fiscal route audit before-status snapshots still need revalidation.

Full serial regression started against `nexora_test_nexora_group`, log `/tmp/nexora-phase1-full-iteration5.log`, exec session 57521. It started at commit `1b48d1ff` before the hard-close follow-up; do not treat it as full final-SHA evidence and do not run a competing schema-resetting runner on that database. New CI for `1b48d1ff`: `34305568080`, in progress when observed. All certification SHAs remain PENDING.

---

> **Corrección de estado (2026-09-10).** Los párrafos anteriores son histórico de las
> iteraciones 1–5 y quedan superados por la integración real. Las tres fases fueron
> ejecutadas e integradas a `origin/main`:
>
> - PR #114 `fix/nexora-phase1-core-foundations` → merge `964d537c`
> - PR #115 `fix/phase1-soft-closed-complete` → merge `6fd6f6e3` (cierre Fase 1)
> - PR #116 `fix/phase2-domain-integration` → merge `c4b0394d`
> - PR #117 `fix/phase3-qa-certification` → merge `1b389698`
> - PR #118 subledger↔GL reconciliation → merge `1d28a266`
> - PR #119 test-schema-reset robustness → merge `1fddcbc7`
> - PR #120 SAP GUI theme engine → merge `55d368b3`
> - PR #121 NX-AUD model schema alignment → merge `a3cc6136`
> - PR #123 iteration-14 invariants+tema → merge `802b621d`
> - PR #124 regresión contraste SAP → merge `fa3dc1a4`
> - PR #125 F3.8 retire pre_migration_repairs → merge `e9efbe81`
>
> Tags de fase (SHAs reales de `origin/main`): FASE1_CORE_BASELINE `6fd6f6e3`,
> FASE2_DOMAIN_INTEGRATION `c4b0394d`, FASE3_QA_CERTIFICATION `1b389698`.
> Suites verdes: backend 632 passed (log `/tmp/pytest_full_run.log`), frontend 238 tests,
> e2e, Compile Azure Bicep y Docker Compose smoke en CI. Ruleset `main protection
> (ORDEN MAESTRA §42)` ahora exige los 5 gates reales (backend, frontend, e2e,
> Compile Azure Bicep, Docker Compose smoke). PR #122 cerrado como SUPERSEDIDO.
