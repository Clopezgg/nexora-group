Agent: Claude Code
Repository: Clopezgg/nexora-group
Canonical branch: feat/nexora-greenfield
Latest integrated SHA: 81fa5aa (merge: integrate Track D (Enterprise Resources) into greenfield mission) — pushed to origin/feat/nexora-greenfield

Current working branch: feat/nexora-greenfield (main worktree /Users/clopezg/nexora-group)

Real Progress:

This continues the plan at
`docs/superpowers/plans/2026-08-24-interrupted-tracks-recovery.md`, ledger
at `.superpowers/sdd/2026-08-24-interrupted-tracks-recovery/progress.md`
(READ THE LEDGER FIRST — it is the authoritative task-by-task record with
every ruling and commit range).

Completed and merged into feat/nexora-greenfield (each independently
reviewed by a fresh subagent, then independently re-verified by the
controller with real commands, then pushed):
- Track F (Experience/design system), Foundation (master data, RBAC,
  OperationScope, double-entry posting engine), Track B (Project Control),
  Track C (Supply Chain: procurement, inventory) — from before this
  session.
- Task 4 — Track A (Financial Core: Treasury/AP/AR) integrated on top of
  B+C, merged as `dd00a59`. Supplier reference on AP invoices given a real
  FK to Track C's Supplier entity.
- Task 5 — Track D (Enterprise Resources: Fixed Assets/Depreciation,
  Equipment/Maintenance, Workforce/Time) integrated, merged as `81fa5aa`.
  Depreciation posts through the real central Posting Engine. Workforce/Time
  backend-only (no UI yet, honestly IN_PROGRESS). Documents/Site/Quality
  NOT_STARTED.

In Progress (STOP HERE FIRST — do not re-implement, resume the review loop):

- Task 6 — Track E (Commercial: Lead→Opportunity→Customer/Quotation→Sales
  Contract→AR invoice). Implementer reported DONE on branch
  `track/e-commercial` in worktree `/Users/clopezg/nexora-group-trackE`,
  HEAD `25f8c36`, base `5f60a18`. Commits: `231a7be` (CRM domain), `80d6e16`
  (AR `customer_ref` → real Customer FK), `148ec73` (CRM UI), `25f8c36`
  (docs). Implementer-reported gates: backend 144/144 pytest, frontend
  typecheck/lint clean + 38/38 vitest + build OK, Alembic single head,
  clean upgrade on 3 fresh disposable DBs. Billing calls
  `ar_service.create_customer_invoice(..., commit=False)` directly — same
  convention as Track D calling the Posting Engine.

  **This has NOT been reviewed or merged yet.** This session was
  checkpointed on a usage-limit warning right after the implementer's DONE
  report, before the task-reviewer dispatch. Resume exactly at:
  `superpowers:subagent-driven-development`, step 3 (task review) of the
  loop, for Task 6:
  1. `scripts/review-package docs/superpowers/plans/2026-08-24-interrupted-tracks-recovery.md 5f60a18 25f8c36`
  2. Dispatch the task reviewer per `task-reviewer-prompt.md`, using
     `task-6-brief.md` and `task-6-report.md` in the SDD workspace. Direct
     it to specifically verify two things the implementer self-flagged:
     (a) the new Alembic migration that makes `customer_invoices.customer_id`
     `NOT NULL` — confirm it is a NEW incremental migration on top of the
     already-merged/pushed `58ce35982711`, not an edit to that published
     revision; (b) the implementer closed an unspecified domain gap on its
     own initiative (quotation.customer_id must match its opportunity's
     customer_id) — confirm this was reasonable scope, not overreach.
  3. Run the fix loop if findings come back (same pattern as Tasks 4/5,
     both of which needed exactly one fix round).
  4. Once review is clean: in the main worktree, `git merge --no-ff
     track/e-commercial`, then independently re-run `alembic heads` (must
     stay one head), a fresh-disposable-DB `alembic upgrade head`, the full
     backend pytest suite, `compileall`, and frontend
     typecheck/lint/test/build — do not trust the implementer's or
     reviewer's numbers, re-run them yourself as Tasks 4/5 did — then
     update the ledger and push.

Not Started:

- Task 7 — Combined-system verification and next-track handoff (final
  gates across the fully-integrated A+B+C+D+E system, traceability
  recount, then continue to whatever track has the fewest unmet
  dependencies next — see the plan file's Task 7 for the exact checklist).
- Documents/Site/Quality slice within Track D (see `DEFERRED-FINAL-009`).
- Any track beyond A–F: not yet scoped in the current plan; do not invent
  new phases outside `docs/MASTER_PLAN.md`.

Deferred: see `docs/DEFERRED.md` (13 non-blocking items, `DEFERRED-FINAL-001`
through `013`, mostly UI-completeness/coverage gaps across Tracks A/C/D and
one pending-review item on Track E's new NOT NULL migration). One external
blocker: `EXTERNAL-BLOCKER-001` (Azure resources not yet deployed; do not
run `az deployment ... create` without an explicit point-in-time
confirmation).

External blockers: EXTERNAL-BLOCKER-001 (Azure deploy) — see
`docs/DEFERRED.md`.

Alembic head: `7423072b11d4` on `feat/nexora-greenfield` as of `81fa5aa`
(Track E's worktree has since advanced this further, unmerged — verify the
real head from `track/e-commercial` once you resume Task 6).

Backend tests: 140/140 passing on `feat/nexora-greenfield` @ `81fa5aa`
(independently re-run by the controller, not just implementer-reported).
Track E's worktree reports 144/144 unmerged.

Frontend tests: 34/34 Vitest passing on `feat/nexora-greenfield` @
`81fa5aa` (independently re-run), typecheck/lint/build all clean. Track E's
worktree reports 38/38 unmerged.

Azure status: subscription ACTIVE, bootstrap resource group and GitHub OIDC
configured, Bicep build + what-if PASS. No Azure resources deployed yet
(PostgreSQL/Container Apps/Static Web Apps/Storage/Key Vault). API
Management must NOT be created. Review DEV cost-conscious sizing before any
real deploy.

Immediate next 5 tasks:
1. Review Task 6 (Track E) per the resume steps above — dispatch the task
   reviewer, run the fix loop if needed.
2. Controller-merge Track E into `feat/nexora-greenfield`, independently
   verify, update the ledger, push.
3. Run Task 7 (combined-system verification: full gates on the fully
   integrated branch, honest traceability recount).
4. Delete this plan's SDD workspace once Task 7's final review is clean
   (`.superpowers/sdd/2026-08-24-interrupted-tracks-recovery/`) — the git
   history is the record after that.
5. Continue the next highest-dependency-free track from `docs/MASTER_PLAN.md`
   / `docs/PROGRESS.md` (do not reinterpret scope from scratch — those two
   files plus `CLAUDE.md` are the source of truth per §6 of `CLAUDE.md`).
