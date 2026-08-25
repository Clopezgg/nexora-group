Agent: Claude Code
Repository: Clopezgg/nexora-group
Canonical branch: feat/nexora-greenfield
Latest integrated SHA: ba7fa01 (merge: integrate Audit trail foundation into greenfield mission) — pushed to origin/feat/nexora-greenfield

Current working branch: feat/nexora-greenfield (main worktree /Users/clopezg/nexora-group)

Real Progress:

Three plans are now fully CLOSED (git history is the record; SDD
workspaces deleted for the first two per the finishing step — do not
reopen them): `docs/superpowers/plans/2026-08-24-interrupted-tracks-recovery.md`,
`docs/superpowers/plans/2026-08-25-track-d-construction-control.md`.

A fourth plan is IN PROGRESS:
`docs/superpowers/plans/2026-08-25-track-g-workflow-audit.md` (Track G:
Workflow/Approvals/Audit/Notifications, closing NXR-REQ-0087-0096),
spec at `docs/superpowers/specs/2026-08-25-track-g-workflow-audit-design.md`,
ledger at `.superpowers/sdd/2026-08-25-track-g-workflow-audit/progress.md`
(READ THE LEDGER FIRST). Core design ruling: NO generic state-machine
framework — every existing domain keeps its own already-tested
transition logic; Track G adds three shared opt-in services (AuditLog,
ApprovalRequest, Notification) domains call into explicitly.

Completed and merged into feat/nexora-greenfield (independently
reviewed with a fix loop where findings existed, then independently
re-verified by the controller, then pushed):
- Task 1 — Audit trail foundation (`ba7fa01`). `AuditLog` (append-only,
  route-layer instrumentation — zero existing service function
  signatures changed). 5 routes instrumented: AP approve/pay, Treasury
  remittance-create/cash-closing-approve, Procurement PO-approve.
  `docs/AUDIT.md` honestly lists what's NOT instrumented yet (Project
  Control, Enterprise Resources, Commercial, Construction Control
  domains).

**IN PROGRESS — READ CAREFULLY, DO NOT RE-DISPATCH FROM SCRATCH:**

Task 2 (Approval Inbox + Segregation of Duties, NXR-REQ-0087/0088/0089)
in worktree `/Users/clopezg/nexora-group-trackG`, branch
`track/g-workflow-audit`. Implementer reported DONE at commit `cfd1dc0`
(base `597f9a8`, which already includes Task 1 merged in). Task review
came back **Approved with 2 Important findings**:
1. Unvalidated `decision` value before persistence — **FIXED**, commit
   `33675f8` on top of `cfd1dc0`, 2 new tests (191/191 full suite),
   real RED/GREEN evidence. This fix has **NOT been re-reviewed yet.**
2. `approval_service.decide()` not atomic with the audit write (a crash
   between the adapter's internal domain-commit and the route's
   subsequent audit call loses that one audit event) — **the controller
   ruled this parked, not fixed**: the only clean fix would add a
   `commit=False` parameter to `approve_supplier_invoice`/
   `decide_submittal`, which violates this plan's own Global Constraint
   against new parameters on those existing service functions. This
   exact same gap already exists unflagged in all five of Task 1's
   instrumented routes — Task 2 inherited it, didn't introduce it.
   Documented as an accepted limitation in the ledger. No action needed
   on this one — do not re-open it as a fix-loop item.

**Resume steps for Task 2:**
1. `scripts/review-package docs/superpowers/plans/2026-08-25-track-g-workflow-audit.md cfd1dc0 33675f8`
   (from `.claude/plugins/cache/claude-plugins-official/superpowers/6.3.0/skills/subagent-driven-development/`)
2. Dispatch a scoped re-review (small diff, cheap-tier model is fine)
   verifying finding #1 is ADDRESSED and no new breakage — use
   `re-review-prompt.md`'s template, findings list = just finding #1
   above (finding #2 is already adjudicated, don't include it).
3. If clean: in the main worktree, `git merge --no-ff
   track/g-workflow-audit`, then independently re-run `alembic heads`
   (must stay one head — current real head after Task 1 is
   `e91bb3d86df2`, Task 2 should add one more revision on top),
   fresh-disposable-DB `alembic upgrade head`, full backend pytest,
   `compileall`, frontend typecheck/lint/test/build — do not trust the
   implementer's or reviewer's numbers, re-run them yourself as every
   prior merge this session did — then update the ledger and push.
4. Then Task 3 (Notifications, NXR-REQ-0092) — merge latest
   `feat/nexora-greenfield` into the trackG worktree first (same pattern
   as Task 2's own Step 1), then dispatch per the plan's Task 3 section.
5. Then Task 4 (combined verification + traceability recount for
   NXR-REQ-0087-0096, same method as the two prior plans' final tasks).

Not Started (after this plan closes):
- Reports/Search/Analytics (the user's Priority 4, Track G territory
  per `docs/MASTER_PLAN.md`).
- NXR-REQ-0074 (Crews) — still NOT_STARTED, out of scope for every plan
  this session.
- The remaining audit-instrumentation backlog `docs/AUDIT.md` names
  (Project Control, Enterprise Resources, Commercial, Construction
  Control domains) — not required to close NXR-REQ-0090 as
  `IMPLEMENTED` (it already is, honestly scoped to the 5 instrumented
  routes), but needed before any future `VERIFIED` claim on audit
  completeness.
- `docs/PRODUCTION_READINESS.md` — the full "absolute definition of
  100%" checklist (backup/restore, disaster recovery, security cert,
  PROD deployment, etc.) received as a standing order this session.
  **Not actionable yet** — applies only at feature-freeze (90% real),
  which hasn't been reached. Read it before ever claiming "100%" or
  "production certified."

Deferred: see `docs/DEFERRED.md`. Track G's Task 2 added no new
DEFERRED items (finding #2 above is ledgered as a ruling, not a
DEFERRED-FINAL — it's an accepted architectural limitation, not a
task-specific gap to burn down later; if a future task changes the
domain services' commit-boundary contract project-wide, revisit it
then). One external blocker: `EXTERNAL-BLOCKER-001` (Azure deploy — do
not run `az deployment ... create` without explicit point-in-time
confirmation, `CLAUDE.md` §11.1).

Alembic head: `e91bb3d86df2` on `feat/nexora-greenfield` @ `ba7fa01`
(single head, fresh-DB-upgrade verified by the controller through the
full 13-revision chain). Task 2's unmerged branch has one further
revision (`773bebddf1a9`) on top — not yet independently verified by
the controller.

Backend tests: 182/182 passing on `feat/nexora-greenfield` @ `ba7fa01`
(independently re-run by the controller). Task 2's worktree reports
191/191 unmerged (includes the fix-round tests).

Frontend tests: 57/57 Vitest passing on `feat/nexora-greenfield` @
`ba7fa01` (independently re-run), typecheck/lint/build all clean.

Azure status: unchanged — subscription ACTIVE, no resources deployed,
do not deploy without explicit point-in-time confirmation.

Immediate next 5 tasks:
1. Scoped re-review of Task 2's fix commit `33675f8` (finding #1 only).
2. Controller-merge Task 2 into `feat/nexora-greenfield`, independently
   verify, update ledger, push.
3. Task 3 (Notifications) — dispatch, review, merge, verify, push.
4. Task 4 (combined verification + traceability recount).
5. Delete this plan's SDD workspace once Task 4's review is clean, then
   start planning Reports/Search/Analytics (Priority 4) per
   `docs/MASTER_PLAN.md`.
