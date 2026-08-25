Agent: Claude Code
Repository: Clopezgg/nexora-group
Canonical branch: feat/nexora-greenfield
Latest integrated SHA: 9eba0ac (merge: integrate Documents + Evidence foundation into greenfield mission) — pushed to origin/feat/nexora-greenfield

Current working branch: feat/nexora-greenfield (main worktree /Users/clopezg/nexora-group)

Real Progress:

The `2026-08-24-interrupted-tracks-recovery` plan (Tracks A/C/D/E
integration) is fully CLOSED — see git history, its SDD workspace was
deleted. Do not reopen it.

A new plan is IN PROGRESS: `docs/superpowers/plans/2026-08-25-track-d-construction-control.md`,
ledger at `.superpowers/sdd/2026-08-25-track-d-construction-control/progress.md`
(READ THE LEDGER FIRST). It covers the CONSTRUCTION CONTROL block
(NXR-REQ-0077-0086: Documents, Evidence, Daily Site Reports, Quality,
Safety, RFI, Submittals) plus the Workforce/Time frontend gap.

Completed and merged into feat/nexora-greenfield (independently reviewed
+ independently re-verified by the controller, then pushed):
- Task 2 — Workforce/Time frontend (WorkersPage/TimeEntriesPage), merged
  as `d07459d`. Closed `DEFERRED-FINAL-008`.
- A test-infrastructure fix, commit `442f658`: `backend/tests/conftest.py`
  now derives its Postgres test-database name from the worktree
  directory instead of one hardcoded name shared by every worktree —
  running pytest in two worktrees at once (now routine) was corrupting
  each other's schema mid-run. Every worktree created going forward
  needs its OWN test database created once
  (`CREATE DATABASE nexora_test_<sanitized_worktree_dirname>;` via
  `psql -U nexora -h localhost -d postgres`) before pytest will work
  there — this is not automatic.
- Task 1 — Documents + Evidence foundation, merged as `9eba0ac`. Real
  `Document`/`DocumentVersion` (append-only, SUPERSEDED-on-new-version,
  backed by a real partial unique index) and `Evidence` (wraps the
  pre-existing `get_evidence_container_client()`, MIME/size validated
  before any blob call, `EvidenceStorageNotConfigured` surfaces as a real
  503, never a fake success). **Attachment-FK contract for any future
  domain** (documented in `docs/DOCUMENTS_EVIDENCE.md`): single
  attachment via `evidence_id: UUID | None` FK to `evidence.id`,
  validated with `assert_evidence_belongs_to_company` before persist;
  multiple attachments via a join table (same shape as `RfqSupplier`).
  `ProgressRecord.evidence_ref` was given a real FK to `Evidence`
  (cross-company rejection proven). Alembic head after this merge:
  `eaf5b6c0d061`. Needed `python-multipart` installed into the shared
  venv (`/Users/clopezg/nexora-group/backend/.venv`) — already done.

**IN PROGRESS — READ CAREFULLY, DO NOT RE-DISPATCH FROM SCRATCH:**

Task 3 (Daily Site Reports + Quality + Safety, NXR-REQ-0081/0082/0083/0084)
and Task 4 (RFI + Submittals, NXR-REQ-0085/0086) were dispatched in
parallel from base `9eba0ac`. **Both implementer subagents hit the
account-wide session usage limit mid-task** (reset 5:20am
America/Tegucigalpa) and terminated before producing a DONE report — this
was a quota event, not a code failure or a plan defect. Substantial
uncommitted work existed in both worktrees at the moment of failure; the
controller committed it as-is with an explicit WIP/NOT-VERIFIED label
(so nothing was silently lost) and pushed both branches to origin. These
commits are NOT reviewed, NOT tested, NOT confirmed to even compile —
treat them as a paused implementer's scratch state, not a finished task.

- **Task 3**: worktree `/Users/clopezg/nexora-group-trackD-site`, branch
  `track/d-site-quality-safety` (pushed to origin). WIP commit has
  backend domain/DB/repository/service/API for `DailySiteReport`,
  `QualityInspection`/`NonConformance`/`CorrectiveAction`,
  `SafetyObservation`/`SafetyIncident`, plus Alembic revision
  `04d3e460a8a7` and frontend service/type files — but NO frontend
  `.tsx` page files were present at checkpoint time, meaning the
  implementer likely hadn't reached that step yet. Nothing verified.
- **Task 4**: worktree `/Users/clopezg/nexora-group-trackD-rfi`, branch
  `track/d-rfi-submittals` (pushed to origin). WIP commit has backend
  domain/DB/repository/service/API for `RequestForInformation`/
  `Submittal` (reusing the existing `NumberSequence` service), Alembic
  revision `f66768a419c3`, frontend pages (`RfiPage.tsx`,
  `SubmittalsPage.tsx`, `RfiSubmittalsPage.tsx`), a frontend test, and
  in-progress `docs/PROGRESS.md`/`docs/REQUIREMENTS_TRACEABILITY.md`
  edits. Looks further along than Task 3 but is equally unverified.

**Resume steps for both:**
1. `cd` into each worktree's `backend/`, run
   `/Users/clopezg/nexora-group/backend/.venv/bin/pytest -q` and
   `.../bin/alembic heads` to see the REAL current state — do not assume
   anything from this doc's description is still accurate, the WIP may
   be broken in ways not yet discovered. Both worktrees' isolated test
   databases already exist
   (`nexora_test_nexora_group_trackd_site`,
   `nexora_test_nexora_group_trackd_rfi`) — no setup needed there.
2. Verify each task's Alembic `down_revision` actually chains onto
   `eaf5b6c0d061` (the real head both branched from) — and once one of
   Task 3/4 merges into `feat/nexora-greenfield` first, the other must
   relink onto the new real head before its own merge, same pattern
   every prior pair of tracks in this project used.
3. Dispatch a fresh implementer per task via
   `superpowers:subagent-driven-development`, explicitly telling it:
   "a prior implementer attempted this task and hit the account session
   limit mid-work; the branch already has real, uncommitted-then-
   preserved progress — read the existing diff first, verify/fix/finish
   it, do not start over from an empty branch." Then proceed through the
   normal task-review → fix-loop → controller-merge pipeline.
4. After both land: Task 5 of this plan (combined verification +
   traceability recount, same method as the prior plan's Task 7).

Not Started (after this plan closes):
- Workflow/Approvals/Audit/Notifications (Track G) — the user's
  Priority 3. No audit-log mechanism exists anywhere in the codebase yet
  (see `DEFERRED-FINAL-014`, surfaced during Task 1's review) — this is
  Track G's first real job, not a bug in any specific track.
- Reports/Search/Analytics (Track G) — the user's Priority 4.
- Whatever else `docs/MASTER_PLAN.md` names after those.

Deferred: see `docs/DEFERRED.md`. 13 open items (`DEFERRED-FINAL-001`
through `014` minus resolved `002`/`008`/`013`). One external blocker:
`EXTERNAL-BLOCKER-001` (Azure deploy — do not run `az deployment ...
create` without an explicit point-in-time confirmation, `CLAUDE.md`
§11.1).

Alembic head: `eaf5b6c0d061` on `feat/nexora-greenfield` @ `9eba0ac`
(single head, fresh-DB-upgrade verified by the controller). Tasks 3/4's
WIP branches each have ONE further unmerged, unverified revision on top
of this — do not assume either is correct without checking.

Backend tests: 154/154 passing on `feat/nexora-greenfield` @ `9eba0ac`
(independently re-run by the controller, including installing
`python-multipart` which Task 1 declared but this venv didn't have yet).

Frontend tests: 44/44 Vitest passing on `feat/nexora-greenfield` @
`9eba0ac` (independently re-run), typecheck/lint/build all clean.

Azure status: unchanged — subscription ACTIVE, no resources deployed,
do not deploy without explicit point-in-time confirmation.

Immediate next 5 tasks:
1. Resume Task 3 and Task 4 (see detailed resume steps above) — verify
   real state first, do not assume, do not restart from scratch.
2. Review + controller-merge each once its implementer reports DONE and
   review is clean, same pipeline as every prior task.
3. Run Task 5 of this plan (combined verification, traceability
   recount for NXR-REQ-0081-0086).
4. Delete this plan's SDD workspace once Task 5's review is clean.
5. Start planning Track G (Workflow/Approvals/Audit/Notifications) per
   the user's Priority 3 — this needs its own brainstorm/plan, it's a
   substantial platform capability (configurable state machines,
   segregation of duties, approval inbox) that shouldn't be crammed into
   this construction-control plan.
