Agent: Claude Code recovery controller (took over from two parallel Codex
sessions on 2026-08-25; see `.recovery/git-state.txt` for the raw recovery
evidence)
Repository: Clopezgg/nexora-group
Canonical branch: feat/nexora-greenfield
Latest integrated SHA: see `git log -1` on `feat/nexora-greenfield`
(financial statements slice: `0cfd7cb`/`4603fa5`/`4b928fd`; AP →
Approval Inbox slice: `8500050`/`3b804c8`/`49b7409`; GL audit
instrumentation: `adff21c`/`97e2d33`; real AP accrued/paid in Budget vs
Actual: `0db6ecf`/`17bb521`; Inventory Returns: `dc91a68`/`06213ed`;
Crews: `b8ee232`/`7c7cda3`; Supplier Contracts + company-isolation fix:
`a1cdb47`/`53908a3`; RFQ/Quotation company-isolation fixes + Bid
Comparison: `66364b2`/`a3c1c65`/`2a9e6d2`; systematic route audit:
`83ca9f0`/`2aa138f`; Corrections/reversal-sync for AP/AR: `6cfca55`;
Tax architecture: `66cebf1`; Auth lockout + CSRF guard: `9858ee9`, docs
commit follows this file)

**This session is now operating under the user's "CANDADO FINAL" order**:
no partial/rounded completion claims, `main` stays locked until every
single gate in that order is independently verified green — not just
"mostly green" or "no obvious regressions". Re-read that order's exact
gate list before ever considering a merge to `main`.

## Canonical state

The plan `docs/superpowers/plans/2026-08-25-reports-search-analytics.md`
is CLOSED. Its follow-up subproject
`docs/superpowers/plans/2026-08-25-financial-statements.md` is also CLOSED.
Do not repeat the Global Search merge, the Trial Balance/Budget vs Actual
build, or the General Ledger/Balance Sheet/Income Statement build —
verify against `docs/REQUIREMENTS_TRACEABILITY.md` (`NXR-REQ-0093` row)
and `git log` before re-doing any reporting work.

Integrated deliverables (all on `feat/nexora-greenfield`):

- Global Search, all ten scoped entity types (`NXR-REQ-0092`).
- Trial Balance + Budget vs Actual + CSV (`NXR-REQ-0093/0094`, first
  sub-scope).
- Company Settings + Integration Architecture (`NXR-REQ-0095/0096`).
- General Ledger (paginated) + Balance Sheet + Income Statement
  (`NXR-REQ-0093`, financial-statements sub-scope, 2026-08-25): see
  `docs/PROGRESS.md` entry "Financial Statements: General Ledger +
  Balance Sheet + Income Statement". `reporting_service.general_ledger`/
  `balance_sheet`/`income_statement` in `app/services/reporting_service.py`,
  three new `GET /api/reports/...` routes, three new tabs under
  `/control/reportes`. `NXR-REQ-0093` stays `IN_PROGRESS`: Cash Flow,
  Treasury/Procurement reports, and composed Project/Earned-Value reports
  remain genuinely unbuilt.
- AP wired into the real Approval Inbox, `DEFERRED-FINAL-016` RESOLVED
  (`NXR-REQ-0023`, 2026-08-25): see `docs/PROGRESS.md` entry "AP wired
  into the real Approval Inbox". `ap_service.submit_supplier_invoice_for_
  approval` (DRAFT -> REVIEW) is the first real caller of
  `approval_service.create_request` in the whole backend, behind
  `POST /api/ap/supplier-invoices/{id}/submit-for-approval`; deciding it
  via `/api/approvals/{id}/decide` now really exercises the
  `ap_service.apply_approval_decision` adapter. `submittal_service` is
  still NOT wired to `create_request` — that remains open, see
  `docs/DEFERRED.md` (`DEFERRED-FINAL-016` entry, updated not deleted) if
  a future session wants to extend the same pattern there.

Combined verification on 2026-08-25 (both slices above, run from this
session, real PostgreSQL, real commands — not inferred):

- Alembic: one head, `234785d5331f`; no migration added by either slice.
- Backend: 235/235 pytest (`cd backend && ./.venv/bin/pytest -q`);
  `python -m compileall -q app tests` clean.
- Frontend: `npm run typecheck` and `npm run lint` clean; 79/79 Vitest
  (`npm test -- --run`); `npm run build` clean (PWA/Vite). The existing
  >500 kB chunk warning is unchanged and still tracked in
  `DEFERRED-FINAL-017`.
- `git diff --check` clean.
- General Ledger audit instrumentation (`accounting.journal_entry.create`/
  `.reverse`, commit `adff21c`): closes that line in `docs/AUDIT.md`'s
  backlog. 237/237 backend tests at that point.
- Real AP accrued/paid in Budget vs Actual (commit `0db6ecf`, closes
  `NXR-REQ-0034`/`NXR-REQ-0035`): `budget_service.compute_summary` was
  hardcoding `accrued`/`paid` to `Decimal("0")` — a real financial figure
  presented as data, forbidden by `CLAUDE.md`. Now real, via
  `ap_repository.project_accrued_total`/`project_paid_total`. Also
  reconciled a stale `NXR-REQ-0016` row (was `NOT_STARTED` under a
  phantom owner; the same scope was actually built under `NXR-REQ-0093`
  — moved to `IN_PROGRESS`, only Cash Flow remains there). 240/240
  backend tests.
- Inventory Returns (commit `dc91a68`, closes `NXR-REQ-0054`):
  `inventory_service.return_to_supplier`, `POST /api/inventory/stock/
  return-to-supplier`. `movement_type="RETURN"` existed only as
  documented intentional debt before this. 243/243 backend tests.
- Crews (commits `b8ee232`/`7c7cda3`, closes `NXR-REQ-0074`): `Crew`/
  `CrewMember` (migration `24e79c9cb218`), 5 endpoints under
  `/api/workforce/crews`, new `CrewMembershipError` (`NXR-WORKFORCE-002`,
  409 — do NOT let membership errors fall through as a bare 500).
  `CrewsPage.tsx` at `/recursos/cuadrillas` (was a reserved-but-unwired
  nav entry). 247/247 backend, 83/83 frontend tests.
- Supplier Contracts + a real bug fix (commits `a1cdb47`/`53908a3`,
  closes `NXR-REQ-0059`/`NXR-REQ-0060`): switched strategy here — from
  working the `NOT_STARTED` list to reconciling `IN_PROGRESS` rows against
  the real code, since that technique had already found two real defects
  this session. Writing the tests `NXR-REQ-0059`'s row said were missing
  exposed a genuine `INV-COMP-001` gap: contract creation never validated
  `supplier_id`/`project_id` against the company. Fixed with the same
  guards AP/Budget/Treasury already use. `SupplierContractsPage.tsx` at
  `/abastecimiento/contratos` (reserved-but-unwired nav entry). 251/251
  backend, 86/86 frontend tests.
- RFQ/Quotation company-isolation fixes + Bid Comparison (commits
  `66364b2`/`a3c1c65`/`2a9e6d2`, closes `NXR-REQ-0044`, enriches
  `NXR-REQ-0042`/`0043`): building the comparison screen surfaced a real
  **cross-tenant READ leak** — `GET /rfqs/{rfq_id}/quotations` had zero
  `assert_company_access`, so any user with `procurement.quotation/read`
  in any company could read another company's confidential supplier
  quotations by guessing an `rfq_id`. Also fixed: `submit_quotation`
  missing the same check plus no supplier-company validation,
  `create_rfq` not validating `supplier_ids` against `company_id`, and
  the already-documented `create_purchase_order_from_quotation` gap (a PO
  could be created in Company A sourced from Company B's quotation).
  Added `GET /api/procurement/rfqs` (didn't exist). `BidComparisonPage.tsx`
  at `/abastecimiento/comparativos` (reserved-but-unwired nav entry) is
  now the one screen that makes RFQ/Quotations visible — they were
  deliberately backend-only before. 258/258 backend, 89/89 frontend
  tests.
- Systematic company-isolation route audit (commit `83ca9f0`): fixed 6
  more `INV-COMP-001` gaps — 2 mutation routes with zero
  `assert_company_access` (requisition approve, physical-count approve),
  1 real cross-tenant **read leak** (goods-receipts listing by PO id,
  zero check), 1 more zero-check mutation (three-way-match), 1 latent
  500-instead-of-404 bug (order-not-found skipped the check via `if
  order is not None:` then unconditionally read `order.company_id`
  anyway), and 1 platform-wide dashboard leak (`active_projects` counted
  every company's active projects for every authenticated user,
  regardless of access). 264/264 backend tests. **This audit already
  covered every route file — do not repeat it from scratch.**
- `NXR-REQ-0025` Corrections (commit `6cfca55`): reversal already
  satisfied the general requirement (CLAUDE.md §8), but reversing an
  AP/AR accrual through the generic endpoint left the invoice `APPROVED`
  (still payable/collectible) pointing at a `REVERSED` document — a real,
  reachable financial-invariant gap, not speculative.
  `posting_service.register_reversal_hook` (same pattern as
  `approval_service.register_decision_adapter`) fixes it for AP/AR;
  payment/receipt reversal explicitly deferred as `DEFERRED-FINAL-018`
  (not silently dropped). 267/267 backend tests.
- Traceability tally after all of the above: 0 `VERIFIED`, 101
  `IMPLEMENTED`, 16 `IN_PROGRESS`, 5 `NOT_STARTED`, 2 `BLOCKED_EXTERNAL`
  across 124 rows. **This is still far from 100\% by the CANDADO FINAL
  definition** — 21 rows are not yet `IMPLEMENTED`, and zero rows are
  `VERIFIED` (VERIFIED requires E2E/independent verification per row,
  which hasn't started). Do not round this up.

Housekeeping notes for whoever reads this next:

- `.recovery/` (untracked) is evidence from the git-state recovery this
  session ran before resuming build work; left in place, not committed
  (it is a point-in-time dump, not durable documentation).
- `AGENTS.md` (untracked, root) is a Codex-facing mirror of `CLAUDE.md`'s
  rules, created by a prior Codex session. Content-identical modulo
  "Codex"/"Claude" wording. Left untracked/unresolved — decide once
  whether to commit it (so Codex sessions get it automatically) or delete
  it (if `CLAUDE.md` alone is considered sufficient); do not silently drop
  it without that decision.
- `backup-before-recovery-20260825-131454` branch and the `stash@{0}`
  ("backup before Codex recovery") are safety nets from the pre-session
  recovery reset to `origin/feat/nexora-greenfield`. All work since then
  is confirmed ahead of that point (`git log backup-before-recovery...
  ^feat/nexora-greenfield` is empty going the other direction — the backup
  is a strict ancestor). Safe to discard once someone actively confirms
  they're no longer needed; not deleted automatically per the "don't
  delete until relationship to HEAD is determined" rule — the relationship
  IS now determined (strict ancestor, superseded), this is just a note
  that deletion still needs an explicit human-adjacent decision per
  session norms, not a blocker to further work.

## Next priority

RESOLVED this session — do not re-do any of these: `DEFERRED-FINAL-016`
(AP → Approval Inbox), General Ledger audit instrumentation, real AP
accrued/paid in Budget vs Actual (`NXR-REQ-0034`/`0035`), the
`NXR-REQ-0016` traceability reconciliation, `NXR-REQ-0054` Returns
(`inventory_service.return_to_supplier`, commit `dc91a68`), `NXR-REQ-0074`
Crews (`Crew`/`CrewMember`, commits `b8ee232`/`7c7cda3`),
`NXR-REQ-0059`/`0060` Supplier Contracts/Subcontracts + the
`SupplierContract` company-isolation fix (commits `a1cdb47`/`53908a3`),
`NXR-REQ-0044` Bid Comparison + the RFQ/Quotation pipeline
company-isolation fixes (commits `66364b2`/`a3c1c65`/`2a9e6d2`), and the
full systematic route-by-route company-isolation audit (a dedicated
sub-agent read every file in `backend/app/api/routes/*.py`) that found
and fixed 6 more `INV-COMP-001` gaps (commit `83ca9f0`) — requisition
approval, goods-receipts listing, three-way-match, physical-count
approval, a latent 500-instead-of-404 bug on two routes, and a
platform-wide dashboard leak. **Do not re-run that audit from scratch —
it already covered every route file.** If you add a NEW entity-id route
in the future, apply the same check yourself rather than waiting for
another audit pass. Also `NXR-REQ-0025` Corrections (commit `6cfca55`):
`posting_service.register_reversal_hook` now syncs
`SupplierInvoice`/`CustomerInvoice` status when their accrual is
reversed — see `DEFERRED-FINAL-018` for the explicitly-scoped-out
payment/receipt-reversal follow-up. Also `NXR-REQ-0006` Tax architecture
(commit `66cebf1`): `TaxCode`/`TaxLine` were pure unused scaffolding
(model only, no service, no API, nothing ever created one or called
`post_manual` with `tax_lines`) — now `tax_service.create_tax_code`/
`compute_tax` and `GET/POST /api/master-data/tax-codes` are real. AP/AR/
Procurement still take a manual `tax_amount` rather than a computed one —
deliberate, documented scope boundary, not wiring further this round.
Also `NXR-REQ-0008`/`NXR-REQ-0009` Authentication/Sessions (commit
`9858ee9`): `User.failed_login_attempts`/`locked_until` (migration
`c15db6e5d9ca`) lock an account for `settings.lockout_minutes` after
`settings.max_login_attempts` consecutive failures (423, even with the
correct password once tripped); `app/api/csrf.py` adds a uniform
`Origin`-header guard on every mutating request (documented decision —
CORS+SameSite already cover the JSON API, the real gap was
`multipart/form-data` on `POST /api/evidence` skipping CORS preflight).
IP-based rate-limiting (vs. per-account lockout) stays a deliberate
90%+-phase infra item (Azure Front Door/WAF), not done this round.

**Working pattern that paid off repeatedly this session — keep using
it**: pick a row whose description names a *specific, narrow* gap (not
"needs full hardening"), write the tests that gap implies, and see what
breaks before assuming the description is accurate. This found SIX real
defects hiding behind rows that looked like simple scope gaps: hardcoded
`Decimal("0")` financial figures (`NXR-REQ-0034/0035`), a stale
traceability ownership note (`NXR-REQ-0016`), and four `INV-COMP-001`
cross-company guards missing across AP/Procurement/RFQ (`NXR-REQ-0059`,
`NXR-REQ-0044` ×3 — including one **read-path** leak, not just write
paths, on `GET /rfqs/{id}/quotations`). When a row says "X exists but Y
screen/test is missing," don't just build Y — check whether X was ever
actually exercised end-to-end. It often wasn't.

Remaining domain-logic `IN_PROGRESS` rows worth this same treatment
(narrow, code-reconcilable — NOT the infra/deployment/hardening
`IN_PROGRESS` rows like `NXR-REQ-0105-0121`, which need actual Azure work,
not code review):

1. `NXR-REQ-0001` Core platform — very broad ("🔶" across most columns),
   likely not a single reconcilable gap; read what it actually still
   expects before touching it. This is the last domain-logic
   `IN_PROGRESS` row that looks code-reconcilable at a glance — read it
   carefully before assuming so, per the row's own breadth warning.

That's close to exhausting the well-scoped `IN_PROGRESS` domain-logic
rows (down to ~16, mostly infra/deployment/hardening —
`NXR-REQ-0105-0121` and similar, which need actual Azure work or a full
`docs/PRODUCTION_READINESS.md` pass, not more code-reconciliation).

**The systematic company-isolation route audit is DONE** (commit
`83ca9f0`, see above) — every file in `backend/app/api/routes/*.py` was
read and checked for a route missing `assert_company_access` against a
fetched entity's `company_id`. 6 gaps found and fixed. Do not re-run this
audit from scratch; if a NEW entity-id route gets added in a future
session, apply the same check as part of building it, not as a separate
audit pass.

Then continue the audit-instrumentation backlog in `docs/AUDIT.md` (still
open: Project Control, Enterprise Resources, Commercial, Construction
Control, and Transfers/General Expenses/Fund Restrictions/Bank
Reconciliation within Financial Core; also AP invoice create/cancel
specifically).

Lower priority / optional: extend the Approval Inbox pattern to
`submittal_service` (deliberately left out — Submittal has its own
`respond`/`decide` flow without an assignment concept, so this is a real
design decision, not a mechanical copy); the missing company-scoped
user-directory endpoint (two UI spots now use an honest free-text UUID
input instead: `QualityPage.tsx`'s `responsibleUserId`, the AP
submit-for-approval modal).

Re-read `docs/MASTER_PLAN.md`, `docs/REQUIREMENTS_TRACEABILITY.md`,
`docs/DEFERRED.md` and `docs/PRODUCTION_READINESS.md` before picking
between these — do not assume this list is exhaustive or still accurate
if significant time has passed; confirm against `git log` and grep first.

Continue autonomously through build-width work. At 90% real, enter feature
freeze and burn down every `DEFERRED-FINAL-*`, then run the complete
`docs/PRODUCTION_READINESS.md` gate. Never provision billable Azure
resources without the point-in-time confirmation required by `CLAUDE.md`
§11.1, and never claim 100%/VERIFIED without real evidence. `main` stays
read-only until every gate in the user's recovery order is green — do not
merge, push, cherry-pick, or rebase anything onto `main`.

## 2026-08-25 — Critical Journey E2E built and green (NXR-REQ-0112/0113 → VERIFIED, first VERIFIED rows in the matrix)

`frontend/e2e/critical-journey.spec.ts` + `frontend/playwright.config.ts`
(own DB `nexora_e2e`, own ports 8010/5175, fresh-install `alembic upgrade
head`, `npm run test:e2e` from `frontend/`) — one continuous real
recorrido through essentially the whole system, 2/2 green. Full detail
and the 3 real bugs it found/fixed (treasury same-GL-account cancellation,
AP submit-for-approval SCOPE_ANY + missing SoD guard, ProjectsPage
company creation missing `functionalCurrencyCode`) are in
`docs/PROGRESS.md`'s `2026-08-25 — Real Critical Journey E2E built...`
entry — read that before touching Treasury/AP-approval/company-creation
code again so you don't reintroduce any of the three.

**Update (same day, immediate continuation):** the user-management gap
flagged right below was NOT deliberately left open — it turned out to be
the same, still-open `DEFERRED-FINAL-015` from an earlier track. It's
now resolved: `GET/POST /api/master-data/users` is real
(Administrator-only create, per-role-scoped read), and
`QualityPage.tsx`/`SafetyPage.tsx`/`AccountsPayablePage.tsx` all use a
real user picker now, no more free-text UUID inputs. Full detail in
`docs/PROGRESS.md`'s `2026-08-25 — DEFERRED-FINAL-015 closed for
real...` entry. Do not re-add a free-text UUID field anywhere a
responsible/approver user is picked — use `useCompanyUsers`
(`frontend/src/hooks/useCompanyUsers.ts`) instead.

Do NOT re-run or re-debug the Critical Journey from scratch — it passes.
If it starts failing after a future change, that's a real regression;
bisect from `git log` on `frontend/e2e/critical-journey.spec.ts` and the
files it exercises, don't rewrite the test.

Verification run this session before declaring the above done: 280/280
backend pytest, `tsc -b --noEmit` clean, `eslint .` clean, 89/89 frontend
vitest, Critical Journey E2E 2/2 green. Nothing committed/pushed yet as
of writing this entry — see git status for what's staged vs. pending.

## 2026-08-25 — DEFERRED-FINAL-015 closed (user directory + real user-management API)

Direct continuation of the entry above, same session, no user
intervention between the two — the user explicitly ordered continuing
through the canonical priority list without stopping. Checked
`docs/PRODUCTION_READINESS.md` first: it explicitly says its 35-block
certification checklist (including `NXR-REQ-0109` Backup/Restore, which
the user suggested as a starting point) is **not active work yet** while
still in Build Width First — confirmed correct to skip it and pick the
real next independent gap instead, which was `DEFERRED-FINAL-015`
(already open, well-scoped, no Azure dependency, and re-confirmed real
by the Critical Journey work). Full detail in `docs/PROGRESS.md`'s
`2026-08-25 — DEFERRED-FINAL-015 closed for real...` entry.

Committed and pushed to `feat/nexora-greenfield` — check `git log` for
the exact commit if picking this up later; `main` is still untouched.

**Next gap, per the same canonical-priority check that led here:**
`docs/AGENT_HANDOFF.md`'s own earlier backlog (this file, above) lists
`NXR-REQ-0016`/`0093` (Cash Flow — needs a real activity-classification
schema decision) as the one remaining well-scoped domain-logic gap.
After that, everything left (`0105-0122`) is Track G
platform-completion/hardening — re-read `docs/PRODUCTION_READINESS.md`'s
own "no aplicar todavía" gate before starting any of its 35 blocks; some
Track G rows (security, observability, migrations, CI/CD) may be
legitimate incremental work per `docs/MASTER_PLAN.md` §4 ("Track G se
completa incrementalmente junto con cada track funcional") even before
90% — read each row's own evidence text before assuming it's gated.

Do not re-derive the "who belongs to this company" semantics question
from scratch if touching `assert_user_belongs_to_company` or
`list_users_for_company` again — read the wrong-turn writeup in
`docs/PROGRESS.md` first (the "any SCOPE_ANY grant" version was wrong
and caught by tests, not by review).

Verification before this entry: 290/290 backend pytest, `tsc -b --noEmit`
clean, `eslint .` clean, 89/89 frontend vitest, Critical Journey E2E 2/2
green (using the new real user-management API, no more subprocess
workaround).

## 2026-08-25 — Cash Flow statement built (NXR-REQ-0016 → IMPLEMENTED)

Direct continuation, same session, still no user intervention between
entries. This closes the last well-scoped domain-logic gap this
session's earlier backlog named (`NXR-REQ-0016`/`0093` Cash Flow —
"needs a real schema decision"). Full design/implementation detail in
`docs/PROGRESS.md`'s `2026-08-25 — Cash Flow statement built for
real...` entry: direct method, `Account.cash_flow_activity` (new
nullable column, migration `8496f11b1227`), cash identified structurally
via `TreasuryAccount.gl_account_id` rather than tagged per-account,
explicit `unclassified` bucket instead of hiding/guessing.

Do not re-derive the "why doesn't this need to correlate documents or
exclude Treasury-to-Treasury transfers explicitly" reasoning from
scratch if touching `reporting_service.cash_flow_statement` again — it's
a direct consequence of double-entry conservation, explained in both the
function's docstring and the PROGRESS.md entry.

**What's left after this, per the same canonical-priority check:** the
domain-logic gap-hunting backlog this session worked through is now
genuinely exhausted (`NXR-REQ-0058` Supplier Performance stays
deliberately deferred — still no real PO/GR volume to compute honest
metrics off). Everything remaining in `IN_PROGRESS`/`NOT_STARTED` is
Track G platform-completion/hardening/Azure
(`NXR-REQ-0105-0122`) or `BLOCKED_EXTERNAL` (`0123`/`0124`, real Azure
deployment). Before starting any of those: re-read
`docs/PRODUCTION_READINESS.md`'s own "no aplicar todavía" gate (Build
Width First) against the CURRENT state — some Track G rows may
legitimately be incremental work already per `docs/MASTER_PLAN.md` §4,
but confirm per-row rather than assuming either way. This is a natural
point to re-run the full `docs/REQUIREMENTS_TRACEABILITY.md` reconcile
sweep (row by row, not by memory) before picking the next specific gap,
since several rows have shifted this session.

Verification before this entry: 296/296 backend pytest, `tsc -b --noEmit`
clean, `eslint .` clean, 91/91 frontend vitest, Critical Journey E2E
green (confirms the new migration doesn't break fresh-install).

## 2026-08-25 — Migrations certified for real (NXR-REQ-0106 → IMPLEMENTED), found + fixed a real downgrade bug

Direct continuation, same session. Full detail in `docs/PROGRESS.md`'s
`2026-08-25 — Migrations certified for real...` entry. Built
`tests/test_migrations.py` (real Alembic CLI against a dedicated
PostgreSQL DB: fresh install → full `downgrade base` → `upgrade head`
again) to close `NXR-REQ-0106`'s own "falta certificar... upgrade
matrix" gap. It failed immediately on first run: 6 constraints across 4
migration files (`131a6debf189`/`c622defc2308`/`f1075e290473`/
`eaf5b6c0d061`) were autogenerated with `create_foreign_key(None, ...)`/
`create_unique_constraint(None, ...)`, so their own `downgrade()` could
never resolve `drop_constraint(None, ...)` to a real constraint — every
`downgrade()` in the whole chain was broken from the earliest offender
onward, and had apparently never been run for real before. Fixed by
naming all six explicitly at creation.

If touching any of those four migration files again: they now have
explicit constraint names (`fk_projects_cost_center_id`,
`fk_projects_currency_code`, `uq_companies_code`,
`fk_companies_functional_currency_code`,
`fk_customer_invoices_customer_id`, `fk_progress_records_evidence_id`) —
don't let a future autogenerate silently reintroduce an unnamed one; run
`tests/test_migrations.py` after any migration change, not just
`upgrade head`.

With this and Cash Flow, the well-scoped domain-logic + platform-gap
backlog this session's earlier entries named is now genuinely exhausted.
Remaining `IN_PROGRESS`/`NOT_STARTED` rows are Track G hardening/Azure
(`NXR-REQ-0093` remainder, `0105`/`0107`/`0108`/`0110`/`0114-0121`) or
deliberately deferred (`0058`) — re-read `docs/PRODUCTION_READINESS.md`'s
gate and `docs/MASTER_PLAN.md` §4 per-row before picking the next one,
same guidance as the entry above.

Verification before this entry: 297/297 backend pytest, Critical Journey
E2E green (confirms fresh-install still works after editing four
historical migrations).

## 2026-08-25 — Accessibility audited for real (NXR-REQ-0105 → IMPLEMENTED), 2 real WCAG AA contrast bugs found + fixed

Direct continuation, same session. Full detail in `docs/PROGRESS.md`'s
`2026-08-25 — Accessibility audited for real...` entry. Added
`@axe-core/playwright` + `frontend/e2e/accessibility.spec.ts` (scans
login + 6 real authenticated screens, shares the Critical Journey's
webServer infra, runs in the same `npm run test:e2e`). Found real
`color-contrast` violations: `--nx-gray-400` (used as text color in
~14 places) was 2.44:1 against white, fixed at the token level
(`#64707f`, ≥5:1). That fix then surfaced a *second* bug: the dark
sidebar reused the same token and dropped to 3.9:1 against navy — one
gray can't satisfy AA on both light and dark backgrounds, so it got its
own token (`--nx-navy-100`, 9.4:1). Also caught and reverted a
self-inflicted `replace_all` mistake mid-fix (repainted a light-bg
element with the new dark-bg token) by re-scanning immediately rather
than trusting the edit — see PROGRESS.md for the exact sequence.

**If you touch `--nx-gray-400`, `--nx-navy-100`, `.nx-sidebar__link`,
`.nx-sidebar__group-label`, or `.nx-topbar__user-role` again**: re-run
`npx playwright test e2e/accessibility.spec.ts` before considering it
done, not just a visual check — this exact class of bug (one shared
gray token, two backgrounds) is exactly what silently regressed once
already this session.

**Explicit remaining gap, not hidden:** a real manual screen-reader
pass (VoiceOver/NVDA) is human-only work no agent session can perform
or fabricate evidence for. `NXR-REQ-0105` is `IMPLEMENTED` on the
strength of the real automated tool audit specifically, with this
named as the one deliberately-remaining piece.

With this, `NXR-REQ-0016`/`0106`/`0105` all closed this session on top
of `DEFERRED-FINAL-015` and the original Critical Journey E2E build.
Remaining `IN_PROGRESS`/`NOT_STARTED`: `NXR-REQ-0093` (Treasury/
Procurement/Earned Value reports, genuinely out of scope), `0107`
(Security §121 remainder), `0108` (Observability structured logging),
`0110` (unit tests, grows naturally with each track), `0114` (CI/CD
gate completion), `0115-0121` (Bicep/Azure IaC — `az bicep build`/
`what-if` are pre-authorized, actual `az deployment ... create` is not,
per `CLAUDE.md` §11.1), `0058` (deliberately deferred), `0109`
(Backup/Restore, gated behind 90% real per
`docs/PRODUCTION_READINESS.md`), `0122` (OIDC federated credentials,
needs GitHub-side config this agent can't do alone). Re-verify
per-row before picking the next one — this list may already be stale
by the time it's read.

Verification before this entry: 297/297 backend pytest, `tsc -b
--noEmit` clean, `eslint .` clean, 91/91 frontend vitest, combined
`npm run test:e2e` (Critical Journey + Accessibility) 3/3 green.

## 2026-08-25 — Structured logging + real correlation_id (NXR-REQ-0108 → IMPLEMENTED)

Direct continuation, same session. Dispatched a research-only fork to
pick between `0107`/`0108`/`0114` (confirmed by direct code inspection:
`0108` had the cleanest, purely-local remaining scope — `0107`/`0114`'s
remaining pieces are more Azure-deployment-shaped). Full detail in
`docs/PROGRESS.md`'s `2026-08-25 — Structured logging with a real
correlation_id...` entry.

`app/core/logging.py` (ContextVar + JSON formatter) +
`app/api/correlation.py`'s `CorrelationIdMiddleware` (deliberately pure
ASGI, not `BaseHTTPMiddleware` — avoids a known Starlette gotcha where a
`ContextVar` set in `dispatch()` isn't reliably visible past
`call_next()`). Along the way, fixed a real inconsistency:
`error_handlers.py`/`csrf.py` used to mint their own random
`uuid.uuid4()` for an error's `correlationId`, disconnected from
whatever the 5 routes with `Depends(get_correlation_id)` used for audit
logging. Now one shared `ContextVar` backs all of it: response header,
error bodies, audit log rows, and actual log lines.

**If you add new middleware to `app/main.py`**: registration order is
non-obvious in Starlette (`add_middleware()` prepends internally, stack
built in `reversed()` order, so the middleware added *last* ends up
*outermost*/runs first). `CorrelationIdMiddleware` is added after
`register_csrf_guard()` on purpose so the correlation id exists before
CSRF's own error path needs it — don't reorder these without
re-running `tests/test_observability.py`, which actually asserts on
this (not just documents it).

With this, the Observability half of what remained is done.
`NXR-REQ-0107`'s narrower remaining piece (security headers middleware
— CSP/X-Frame-Options/HSTS/etc., currently zero coverage, confirmed by
grep) is the natural next candidate if continuing down this same
local/non-Azure vein — same effort shape as the CSRF guard and this
correlation-id middleware, no new infra needed.

Verification before this entry: 303/303 backend pytest, `tsc -b
--noEmit` clean, `eslint .` clean, 91/91 frontend vitest, combined
Critical Journey + Accessibility E2E 3/3 green with real structured
JSON logs visible in the run output.

## 2026-08-25 — Real security headers (NXR-REQ-0107 evidence updated, deliberately stays IN_PROGRESS)

Direct continuation, same session, exactly the "natural next candidate"
the entry above named. Full detail in `docs/PROGRESS.md`'s `2026-08-25
— Real security response headers...` entry.
`app/api/security_headers.py`'s `SecurityHeadersMiddleware`, registered
as the outermost layer of the whole stack (after
`CorrelationIdMiddleware`) so headers apply even to CORS/CSRF 403s.
`X-Content-Type-Options`/`X-Frame-Options`/`Referrer-Policy` always; a
strict `Content-Security-Policy` everywhere except `/docs`/`/redoc`
(would break Swagger UI's real CDN assets); `Strict-Transport-Security`
only when `settings.is_production`.

**Important, do not accidentally "fix" this later**: `NXR-REQ-0107` was
deliberately left `IN_PROGRESS`, not moved to `IMPLEMENTED`, even though
its headers piece is done — the row's own name includes "rate-limit,"
which is still genuinely missing and is real Azure Front Door/WAF
infrastructure work, not something completable from this codebase
alone. Don't move this row to `IMPLEMENTED` without either building
rate-limiting for real or splitting the row.

With `0105`/`0106`/`0108`/`0016` done this session plus `0107`'s
headers piece, the purely-local, non-Azure Track G backlog is now
genuinely thin. What's left: `NXR-REQ-0093` (Treasury/Procurement/
Earned Value reports, deliberately out of scope), `0107`'s rate-limit
remainder (Azure-shaped), `0110` (unit tests, grows naturally — not a
discrete task to "complete"), `0114` (CI/CD gate — its remaining scope
is genuinely deployment-shaped per the earlier fork's finding), `0115-
0121` (Bicep/Azure IaC — `az bicep build`/`what-if` pre-authorized,
`az deployment ... create` is not, per `CLAUDE.md` §11.1), `0058`
(deliberately deferred), `0109` (Backup/Restore, gated behind 90% real),
`0122` (OIDC, needs GitHub-side config this agent can't do alone). At
this point, re-reading `docs/PRODUCTION_READINESS.md`'s own gate
against the CURRENT state (not assumed from memory) before picking
anything further is the right move — the easy, purely-local wins in
this backlog are largely exhausted.

Verification before this entry: 307/307 backend pytest, `tsc -b
--noEmit` clean, `eslint .` clean, 91/91 frontend vitest, combined
Critical Journey + Accessibility E2E 3/3 green.

## 2026-08-25 — Real Backup/Restore executed (NXR-REQ-0109 → IMPLEMENTED)

Direct continuation, same session, under the user's explicit
"stop deferring implementable work" master order. Full detail in
`docs/PROGRESS.md`'s `2026-08-25 — Real Backup/Restore, executed and
verified...` entry. `scripts/db_backup.sh`/`db_restore.sh` (real
`pg_dump`/`pg_restore`) + `backend/tests/test_backup_restore.py`
exercises every item `docs/PRODUCTION_READINESS.md` block 4 names
against real PostgreSQL: migrations/state, login (real Argon2id hash +
`verify_password()`), datos críticos, integridad contable (real
double-entry total surviving the round trip). `docs/BACKUP_RESTORE.md`
has the strategy/retention/RPO-RTO — DEV values are real and measured;
Azure DEV/prod values are honestly left undeclared, not invented,
since no Azure Postgres is deployed yet.

**If you touch this again**: don't re-invent the RPO/RTO for Azure
DEV/prod from a guess — measure it for real once `NXR-REQ-0118` is
actually deployed, using the exact same verification steps this test
already runs (migrations/login/data/integrity), and update
`docs/BACKUP_RESTORE.md`'s table in place.

Verification before this entry: 308/308 backend pytest.

## Continuing the master order (2026-08-25) — remaining canonical backlog

Per the user's absolute-closure order: work through every remaining
`NOT_STARTED`/`IN_PROGRESS`/`DEFERRED-FINAL` row until only genuine
external blockers remain. As of this entry, re-verified against the
live table (`grep -oE ...`, not memory): 107 `IMPLEMENTED`, 11
`IN_PROGRESS` (`NXR-REQ-0093/0107/0110/0114/0115/0116/0117/0118/0119/
0120/0121`), 2 `NOT_STARTED` (`NXR-REQ-0058/0122`), 2 `BLOCKED_EXTERNAL`
(`0123/0124`), 2 `VERIFIED`. Next up per the order's own explicit
priority: `NXR-REQ-0058` (Supplier Performance — the order explicitly
says build it with real controlled fixtures, not defer it for lack of
volume), then the concurrency/idempotency real-race-condition testing
pass (order §10), then the remaining CI/CD-completable-locally pieces,
then the security review checklist (§9), before reassessing what's
left against `docs/PRODUCTION_READINESS.md` in full.

Do NOT re-plan this from scratch on resume — this list is the current
real state as of the moment it was written; re-verify against the live
traceability table before trusting it if time has passed.

## 2026-08-25 — Supplier Performance built with real fixtures (NXR-REQ-0058 → IMPLEMENTED)

Direct continuation, same session, under the user's absolute-closure
order which explicitly named this row and forbade deferring it further
for "not enough historical volume." Full detail in `docs/PROGRESS.md`'s
`2026-08-25 — Supplier Performance built with real controlled
fixtures...` entry. `reporting_service.supplier_performance`: on-time
delivery (PO+quotation delivery_days vs real GoodsReceipt), three-way-
match clean rate, price variance — every rate is `None` with an
explicit `sample_size`, never a fabricated 0%/100%, when there isn't
enough real data.

**Real gap found building the real fixtures, not by reading the
model**: `SupplierQuotationLine` has no `item_id` at all (free text
only) — grouping price variance by `item_id` would have silently
produced zero samples for every quotation-derived PO, the only real
path this system supports. Grouped by `description` instead. If you
touch this metric again and it's returning suspiciously empty samples,
check this first before assuming the fixtures are wrong.

3 new backend tests, 1 frontend test. 311/311 backend pytest, 92/92
frontend vitest, `tsc`/`eslint` clean, combined E2E 3/3 green.

## Live backlog re-check (2026-08-25, this entry)

Re-verified against the live table, not memory: 108 `IMPLEMENTED`, 11
`IN_PROGRESS` (`NXR-REQ-0093/0107/0110/0114/0115/0116/0117/0118/0119/
0120/0121`), **1 `NOT_STARTED`** (`NXR-REQ-0122`, OIDC — needs GitHub-
side federated credential config this agent cannot do alone), 2
`BLOCKED_EXTERNAL` (`0123/0124`, real Azure deployment). The
domain-logic backlog named at the top of this document is now fully
closed. What's left is Track G platform/hardening/Azure work — continue
per the user's absolute-closure order into concurrency/idempotency race
testing (§10), the security review checklist (§9: IDOR, horizontal/
vertical escalation, file upload security, secrets, dependency
vulnerabilities), and the CI/CD pieces completable without GitHub admin
access, before reassessing against `docs/PRODUCTION_READINESS.md` in
full. Azure subscription (UNAH) is `ReadOnlyDisabledSubscription` as of
this entry — `az bicep build` stays available, `what-if`/deploy do not
until it's re-enabled externally.

## 2026-08-25 — Concurrency/idempotency race testing (master order §10): 2 real bugs found and fixed (NXR-REQ-0110 → VERIFIED)

Direct continuation, same session. Full detail in `docs/PROGRESS.md`'s
`2026-08-25 — Real concurrency/race testing...` entry. New
`backend/tests/test_concurrency.py`: 5 tests, each using independent
`SessionLocal()` per thread via `ThreadPoolExecutor` against the same
live PostgreSQL test DB (never the shared `db_session` fixture, which
isn't thread-safe and can't reproduce a real race) — numbering
create-race + steady-state, idempotency replay, concurrent remittances
(lost-update check on reported GL balance), concurrent full payments
on one invoice.

**2 real production bugs found**: `numbering_service.
next_document_number` and `idempotency_service.begin` both raised an
uncaught `sqlalchemy.exc.IntegrityError` when two concurrent callers
raced to INSERT the very first `NumberSequence`/`IdempotencyRecord`
row for a given key (nothing exists yet to `SELECT ... FOR UPDATE`).
**Fixed** in both with the same pattern: `db.begin_nested()`
(SAVEPOINT) around the INSERT, catch `IntegrityError`, roll back only
the savepoint (never the caller's outer transaction — callers like
`posting_service.post_manual` may have other pending work staged
already), then re-`SELECT ... FOR UPDATE` the winner's row. For
idempotency specifically the re-fetch must *block* on the winner's
commit so the loser sees `COMPLETED`, not a stale `PENDING`.

**If you touch either service again**: preserve the SAVEPOINT pattern
exactly — a plain re-`SELECT` without `begin_nested()` would either
lose the outer transaction's other pending work on rollback, or (for
idempotency) risk the loser reading a not-yet-committed `PENDING`
record and wrongly re-executing the real side effect.

The AP-payment race test found no bug: `pay_supplier_invoice`'s
existing `SELECT ... FOR UPDATE` on the invoice row already serializes
correctly (losers correctly get `OverpaymentError` or
`InvalidInvoiceStateError` depending on which guard their stale
in-memory status trips first — both are correct rejections).

Verification: `test_concurrency.py` 5/5 green × 5 consecutive runs;
full backend suite 316/316 (was 315), zero regressions. `NXR-REQ-0110`
moved `IN_PROGRESS` → `VERIFIED`.

## 2026-08-25 — Extended concurrency sweep: 3 more real bugs (NXR-REQ-0110 evidence extended)

Direct continuation. Dispatched a research subagent to survey
`ar_service`/`treasury_service`/`procurement_service`/
`inventory_service`/`budget_service`/`approval_service` for unlocked
read-then-write races. AR receipt, Treasury reconciliation, and
approval decisions already lock correctly (no bug). Two real races
found and fixed, plus one more latent bug found while fixing the
second — full detail in `docs/PROGRESS.md`'s `2026-08-25 — Extended
concurrency sweep...` entry:

1. `procurement_service.record_goods_receipt` read `PurchaseOrderLine.
   quantity_received` unlocked -- concurrent receipts could over-receive
   beyond what was ordered. Fixed with `procurement_repository.
   get_purchase_order_line_for_update`.
2. `inventory_service._current_position` derived stock position from
   the last (unlocked) `StockLedgerEntry` -- the ledger is genuinely
   append-only (no mutable "current qty" row), so a plain
   `SELECT...FOR UPDATE` can't actually block a concurrent INSERT
   (phantom-row problem). Fixed with `pg_advisory_xact_lock` keyed by
   `(company_id, item_id, warehouse_id)` in `_lock_stock_position`.
   `transfer_stock` pre-locks both warehouses in canonical sorted
   order to avoid a deadlock against an opposite-direction concurrent
   transfer (advisory xact-locks are reentrant, safe to re-acquire).
3. **Found while verifying #2** (not obvious from reading the code,
   only surfaced via a raw-SQL reproduction outside the ORM): even
   with the lock correctly serializing writers, `get_last_ledger_entry`
   still intermittently returned the WRONG "last" row because it
   ordered by `created_at DESC` -- PostgreSQL's `now()`/`created_at`
   is the transaction's *start* time, not write time, so under lock
   queueing an early-starting-but-slow transaction can write its row
   *after* a later-starting-but-fast one, breaking `created_at`
   ordering. The `id DESC` tiebreaker didn't help since `id` is a
   random UUID. Fixed by adding `StockLedgerEntry.entry_seq` (a real
   PostgreSQL `SEQUENCE`, `nextval()` evaluated at actual INSERT time
   -- genuinely monotonic) via migration `20da9f0955af`.

**If you touch `inventory_service` or the stock ledger again**:
`get_last_ledger_entry` MUST keep ordering by `entry_seq DESC` alone
-- never reintroduce `created_at`/`id` as the ordering key for "what's
the current position," even as a tiebreaker. Any other query that
needs "insertion order" for `StockLedgerEntry` has the same trap;
`entry_seq` is the only column that means what it looks like it means.

New tests in `test_concurrency.py` (now 7 total):
`test_concurrent_goods_receipts_never_over_receive_beyond_ordered_
quantity`, `test_concurrent_stock_issues_never_over_issue_beyond_on_
hand_quantity`. Verification: 5/5 green × 5 runs (+ an isolated 20x
loop while root-causing #3); full backend suite 318/318 (was 316);
Alembic fresh-install + downgrade -1 + upgrade head verified on a
scratch DB.

## Live backlog re-check (2026-08-25, this entry)

Re-verified against the live table: 108 `IMPLEMENTED`, 10
`IN_PROGRESS` (`NXR-REQ-0093/0107/0114/0115/0116/0117/0118/0119/0120/
0121`), 1 `NOT_STARTED` (`NXR-REQ-0122`, OIDC — external GitHub config),
2 `BLOCKED_EXTERNAL` (`0123/0124`), 3 `VERIFIED`. Per the
absolute-closure order, next canonical gaps in priority order: the
order's own §10 concurrency list is now substantially covered (AR
receipt/reconciliation/approvals confirmed already-safe this pass;
numbering/idempotency/AP-payment/goods-receipt/inventory all tested
and fixed) — two completeness gaps were flagged but NOT fixed (out of
scope for a concurrency regression, they're missing business-rule
guards, not races): `treasury_service.register_transfer` has no
negative-balance guard at all, and there is no budget-consumption
guard anywhere in the codebase to check spend against remaining
budget. Both should become their own gap (not a concurrency test) if
in canonical 100% scope — check `docs/REQUIREMENTS_TRACEABILITY.md`
for whether budget enforcement/overdraft prevention has an NXR-REQ row
before building either. Next candidate work: the §9 security review
checklist (app-layer rate limiting per the order's explicit
instruction not to claim Azure-only without proving app-layer is
insufficient first; brute force beyond existing lockout; session/token
expiration+revocation; cookies; CORS; IDOR; horizontal/vertical
privilege escalation; file upload security; secrets handling;
dependency vulnerabilities; error/log leakage) — or `docs/AUDIT.md`
backlog closure — before reassessing against
`docs/PRODUCTION_READINESS.md` in full. Do not stop between these;
continue automatically per the order.
