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
Tax architecture: `66cebf1`, docs commit follows this file)

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
- Traceability tally after all of the above: 0 `VERIFIED`, 99
  `IMPLEMENTED`, 18 `IN_PROGRESS`, 5 `NOT_STARTED`, 2 `BLOCKED_EXTERNAL`
  across 124 rows. **This is still far from 100\% by the CANDADO FINAL
  definition** — 23 rows are not yet `IMPLEMENTED`, and zero rows are
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

1. `NXR-REQ-0008`/`NXR-REQ-0009` Authentication/Sessions — row says
   "sigue faltando CSRF/rate-limit/lockout"; this overlaps with
   `NXR-REQ-0107` Security, which is more clearly a 90%+ hardening-phase
   item covered by `docs/PRODUCTION_READINESS.md` §13 (Security). Could
   still pick off the narrow, code-level pieces now (CSRF decision,
   rate-limit/lockout on login) separately from the full hardening pass.
2. `NXR-REQ-0001` Core platform — very broad ("🔶" across most columns),
   likely not a single reconcilable gap; read what it actually still
   expects before touching it.

That's close to exhausting the well-scoped `IN_PROGRESS` domain-logic
rows (down to ~18, mostly infra/hardening/deployment).

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
