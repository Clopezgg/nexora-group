Agent: Claude Code recovery controller (took over from two parallel Codex
sessions on 2026-08-25; see `.recovery/git-state.txt` for the raw recovery
evidence)
Repository: Clopezgg/nexora-group
Canonical branch: feat/nexora-greenfield
Latest integrated SHA: see `git log -1` on `feat/nexora-greenfield`
(financial statements slice: `0cfd7cb`/`4603fa5`/`4b928fd`; AP →
Approval Inbox slice: `8500050`/`3b804c8`/`49b7409`; GL audit
instrumentation: `adff21c`/`97e2d33`; real AP accrued/paid in Budget vs
Actual: `0db6ecf`, docs commit follows this file)

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
- Traceability tally after all of the above: 0 `VERIFIED`, 92
  `IMPLEMENTED`, 23 `IN_PROGRESS`, 7 `NOT_STARTED`, 2 `BLOCKED_EXTERNAL`
  across 124 rows. **This is still far from 100\% by the CANDADO FINAL
  definition** — 30 rows are not yet `IMPLEMENTED`, and zero rows are
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
`NXR-REQ-0016` traceability reconciliation.

The 7 rows genuinely `NOT_STARTED` as of this checkpoint (verify with
`grep -oE '\| NOT_STARTED \|' docs/REQUIREMENTS_TRACEABILITY.md` combined
with the row names before trusting this list — it will drift):

1. `NXR-REQ-0054` Returns — `movement_type="RETURN"` already exists in
   the inventory model (DB ✅), no service function or endpoint yet.
   Smallest-scoped genuine gap on this list; good next pick.
2. `NXR-REQ-0074` Crews — nothing built (`⬜` across the board).
3. `NXR-REQ-0058` Supplier Performance — deliberately deferred (not
   enough real PO/GR volume to compute honest metrics without fabricating
   them); re-evaluate only if that premise has changed.
4. `NXR-REQ-0109` Backup/Restore, `NXR-REQ-0112` E2E (Playwright),
   `NXR-REQ-0113` Critical User Journey — these are 90–100%
   feature-freeze-phase items per `CLAUDE.md` §10's own "Build Width
   First" philosophy. With 30/124 rows still not `IMPLEMENTED`, this
   project is not at 90% width yet — prioritize closing more
   `NOT_STARTED`/`IN_PROGRESS` rows before these, unless the user
   explicitly asks to jump ahead.
5. `NXR-REQ-0122` OIDC deployment — blocked on GitHub federated
   credentials configuration; likely an `EXTERNAL-BLOCKER`, confirm before
   attempting.

Then continue the audit-instrumentation backlog in `docs/AUDIT.md` (still
open: Project Control, Enterprise Resources, Commercial, Construction
Control, and Transfers/General Expenses/Fund Restrictions/Bank
Reconciliation within Financial Core; also AP invoice create/cancel
specifically). Also worth a scan: this session found TWO real bugs
(hardcoded `Decimal("0")` financial figures, a stale traceability row)
just by reading code adjacent to what it was already touching — a
deliberate pass over the 23 `IN_PROGRESS` rows' descriptions against the
real code, looking for the same class of issue, is likely to surface
more before jumping to E2E/hardening.

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
