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
`a1cdb47`/`53908a3`, docs commit follows this file)

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
- Traceability tally after all of the above: 0 `VERIFIED`, 96
  `IMPLEMENTED`, 21 `IN_PROGRESS`, 5 `NOT_STARTED`, 2 `BLOCKED_EXTERNAL`
  across 124 rows. **This is still far from 100\% by the CANDADO FINAL
  definition** — 26 rows are not yet `IMPLEMENTED`, and zero rows are
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
`SupplierContract` company-isolation fix (commits `a1cdb47`/`53908a3`).

**Working pattern that paid off repeatedly this session**: pick a row
whose description names a *specific, narrow* gap (not "needs full
hardening"), write the tests that gap implies, and see what breaks before
assuming the description is accurate. This found three real defects
hiding behind rows that looked like simple scope gaps: hardcoded
`Decimal("0")` financial figures (`NXR-REQ-0034/0035`), a stale
traceability ownership note (`NXR-REQ-0016`), and a missing
`INV-COMP-001` cross-company guard (`NXR-REQ-0059`). Keep using it.

Remaining domain-logic `IN_PROGRESS` rows worth this same treatment
(narrow, code-reconcilable — NOT the infra/deployment/hardening
`IN_PROGRESS` rows like `NXR-REQ-0105-0121`, which need actual Azure work,
not code review):

1. `NXR-REQ-0044` Bid Comparison — `quotation_total()` exists per
   quotation; row says "no hay endpoint agregado de comparación ni
   pantalla". `/abastecimiento/comparativos` is ALSO a reserved-but-unwired
   nav entry (like Crews/Contracts were) — check `docs/PROCUREMENT.md`
   before designing the aggregate endpoint.
2. `NXR-REQ-0025` Corrections (posted docs) — row says reversal covers
   the general case but a domain might need a distinct "correction" flow;
   verify whether any domain has actually hit this gap in practice before
   building anything speculative.
3. `NXR-REQ-0006` Tax architecture — `TaxCode`/`TaxLine` exist and feed
   `posting_service.post_manual`, but there's no tax calculation service
   or API. Verify whether any domain actually needs computed tax before
   building — this could be legitimately out of scope rather than a gap.
4. `NXR-REQ-0008`/`NXR-REQ-0009` Authentication/Sessions — row says
   "sigue faltando CSRF/rate-limit/lockout"; this overlaps with
   `NXR-REQ-0107` Security, which is more clearly a 90%+ hardening-phase
   item. Lower priority than 1-3 above.
5. `NXR-REQ-0001` Core platform — very broad ("🔶" across most columns),
   likely not a single reconcilable gap; read what it actually still
   expects before touching it.

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
