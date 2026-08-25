Agent: Claude Code recovery controller (took over from two parallel Codex
sessions on 2026-08-25; see `.recovery/git-state.txt` for the raw recovery
evidence)
Repository: Clopezgg/nexora-group
Canonical branch: feat/nexora-greenfield
Latest integrated SHA: see `git log -1` on `feat/nexora-greenfield`
(financial statements slice: `0cfd7cb`/`4603fa5`/`4b928fd`; AP →
Approval Inbox slice: `8500050`/`3b804c8`/`49b7409`; GL audit
instrumentation: `adff21c`, docs commit follows this file)

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
- Traceability tally unchanged at the row-status level (`NXR-REQ-0093` and
  `NXR-REQ-0023` descriptions updated, statuses unchanged — both were
  already `IN_PROGRESS`/`IMPLEMENTED`): 0 `VERIFIED`, 90 `IMPLEMENTED`,
  22 `IN_PROGRESS`, 10 `NOT_STARTED`, 2 `BLOCKED_EXTERNAL` across 124
  rows.

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

`DEFERRED-FINAL-016` is now RESOLVED (see above) — do not re-do it or
re-wire AP again. The General Ledger (manual entries/reversal) audit gap
is also RESOLVED (`accounting.journal_entry.create`/`.reverse`, commit
`adff21c`) — do not re-instrument it. Highest-value dependency-free gaps
at this checkpoint, confirmed against the real code (grep, not
assumption) as of 2026-08-25:

1. Continue the explicit audit-instrumentation backlog documented in
   `docs/AUDIT.md` — still open: Project Control (WBS/Budgets/Change
   Orders/Progress), Enterprise Resources (Fixed Assets/Equipment/
   Workforce), Commercial (CRM/AR), Construction Control (Documents/RFI/
   Submittals/Daily Reports/Quality/Safety), and within Financial Core:
   Transfers/General Expenses/Fund Restrictions/Bank Reconciliation. Also
   AP invoice create/cancel specifically (called out in the
   `NXR-REQ-0023` traceability row) — only approve/pay/submit are
   instrumented on AP so far.
2. Optionally extend the same Approval Inbox pattern just built for AP to
   `submittal_service` (still not wired to `approval_service.
   create_request`, see `docs/DEFERRED.md` `DEFERRED-FINAL-016` for why it
   was deliberately left out this round — Submittal already has its own
   `respond`/`decide` flow without an assignment concept, so this is a
   real design decision, not a mechanical copy).
3. Remaining `NXR-REQ-0093` report catalog: Cash Flow (needs a persisted
   operating/investing/financing activity classification — evaluate
   whether that requires a schema decision before committing to a design,
   unlike General Ledger/Balance Sheet/Income Statement which needed
   none), Treasury/Procurement operational reports, and composed
   Project/Earned-Value reports.
4. The missing company-scoped user-directory endpoint (no `GET /api/.../
   users?companyId=` exists anywhere) is now a real UX gap in two places
   (`QualityPage.tsx`'s `responsibleUserId`, the new AP submit-for-
   approval modal) — both use an honest free-text UUID input instead of a
   fabricated Select. Worth its own small vertical slice if picked up.

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
