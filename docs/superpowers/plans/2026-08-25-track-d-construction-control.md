# Track D Construction Control + Workforce UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the remaining Track D scope per `docs/MASTER_PLAN.md`
("D — Enterprise Resources: ... Documents, Quality, Site Control") and
`docs/REQUIREMENTS_TRACEABILITY.md` (NXR-REQ-0077 through 0086, plus the
Workforce UI gap on 0073/0075/0076): Document Management, Evidence,
Daily Site Reports, Quality, Safety, RFI, Submittals, and the Workforce/
Time frontend that DEFERRED-FINAL-008 tracks as missing.

**Architecture:** Task 1 (Documents + Evidence) is a hard prerequisite —
it builds the real `Evidence` entity on top of the existing (already
wired, currently unused) `backend/app/integrations/azure_blob.py` client,
which every later construction-control domain references for
photos/attachments. Task 2 (Workforce/Time frontend) has no dependency on
Task 1 — the Workforce backend is already merged — and runs in parallel
in its own worktree. Once Task 1 merges, Task 3 (Daily Site Reports +
Quality + Safety) and Task 4 (RFI + Submittals) run in parallel in their
own worktrees, each merging `feat/nexora-greenfield` first to pick up
Task 1's Evidence entity. Task 5 is combined verification.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2, Alembic, PostgreSQL
16, Pytest, React, TypeScript, Vite, TanStack Query, Vitest/RTL — same
stack, same house conventions as every prior track (domain → DB →
Alembic → repository → service → API → permission → audit → frontend →
targeted test).

**Spec:** `docs/MASTER_PLAN.md`, `docs/REQUIREMENTS_TRACEABILITY.md`,
`CLAUDE.md`. Exact requirement IDs this plan closes or advances:
NXR-REQ-0077 (Documents), 0078 (Document Versioning), 0079 (Evidence),
0081 (Daily Site Reports), 0082 (Quality), 0083 (Non-Conformance/
Corrective Action), 0084 (Safety), 0085 (RFI), 0086 (Submittals), plus
the frontend piece of 0073/0075/0076 (Workforce/Time).

## Global Constraints

- Treasury is the sole owner of money; nothing in this plan touches cash
  or GL postings directly. Labor-cost-to-GL integration remains explicitly
  deferred (`DEFERRED-FINAL-007`) — do not add GL posting in this plan.
- `OperationScope` is exactly `CENTRAL | GENERAL | PROJECT`; every new
  resource that can be Project-scoped follows the same domain+DB
  constraint pattern as Track D's `FuelLog`/`FixedAsset` (PROJECT requires
  `project_id`, DB CHECK enforces it, not just the service layer).
- All backend state is persisted in PostgreSQL; evidence/file uploads go
  through the existing `get_evidence_container_client()` in
  `backend/app/integrations/azure_blob.py` — it already fails explicit
  (`EvidenceStorageNotConfigured`) when unconfigured rather than silently
  no-opping. Do not build a second, parallel storage path, and do not
  fake a successful upload when storage isn't configured — surface the
  real failure.
- No new infrastructure dependency and no real Azure provisioning.
- Every domain slice follows domain/DB/service/API/permission/audit/
  frontend/test and updates `docs/PROGRESS.md`/
  `docs/REQUIREMENTS_TRACEABILITY.md` honestly (IMPLEMENTED/IN_PROGRESS/
  NOT_STARTED only, never `VERIFIED`).
- Do not delete worktrees, branches, or local changes belonging to other
  tracks.
- Append-only audit trail on every mutation (actor, action, entity,
  entity_id, before/after where appropriate, timestamp, company,
  project/scope) — reuse the existing audit mechanism Track A/B/C/D/E
  already use, do not invent a second one.
- Company isolation (`assert_company_access`) on every new resource,
  matching the pattern every prior track established.
- No parallel/duplicate entities: Documents/Evidence is ONE entity family
  reused by Daily Reports, Quality, Safety, RFI, and Submittals — later
  tasks must reference Task 1's `Evidence`/`Document` models, never
  redefine their own attachment storage.

---

### Task 1: Documents + Evidence foundation (NXR-REQ-0077/0078/0079)

**Files:**
- Create: `backend/app/models/document.py` (`Document`, `DocumentVersion`,
  `DocumentCategory` as an enum/lookup, `DocumentStatus` as an enum),
  `backend/app/models/evidence.py` (`Evidence` — upload metadata: blob
  key, filename, MIME type, size, uploader, date, category, optional
  polymorphic entity link)
- Create: Alembic revision on top of the current `feat/nexora-greenfield`
  head
- Create: `backend/app/repositories/document_repository.py`,
  `backend/app/repositories/evidence_repository.py`
- Create: `backend/app/services/document_service.py`,
  `backend/app/services/evidence_service.py` (wraps
  `get_evidence_container_client()`; validates MIME type against an
  allowlist — PDF/JPEG/PNG/WEBP — and a size limit before calling Azure
  Blob; on `EvidenceStorageNotConfigured`, surface a real 5xx/503, never
  fabricate a fake stored URL)
- Create: `backend/app/api/routes/documents.py`,
  `backend/app/api/routes/evidence.py`
- Modify additively: `backend/app/main.py`, `backend/app/models/__init__.py`,
  `backend/app/repositories/permission_repository.py`,
  `backend/app/api/error_handlers.py`, `backend/app/domain/errors.py`
- Create: `backend/tests/test_documents.py`, `backend/tests/test_evidence.py`
- Create: `frontend/src/features/documents/DocumentsPage.tsx`,
  `frontend/src/services/documentService.ts`,
  `frontend/src/types/document.ts`
- Modify: `frontend/src/app/routes.tsx` (real page, not `PlaceholderPage`)
- Modify: `backend/app/models/progress.py`,
  `backend/app/schemas/project_control.py` (give `ProgressRecord.evidence_ref`
  a real FK to the new `Evidence` entity, mirroring how Task 4 gave Track
  A's Supplier reference a real FK and Task 6 gave `CustomerInvoice.customer_ref`
  a real FK — same pattern, don't invent a new one)
- Create: `docs/DOCUMENTS_EVIDENCE.md` documenting the entity model,
  allowed MIME types/size limit, and the storage failure contract

**Interfaces:**
- Consumes: `get_evidence_container_client()` (already exists), company/
  project scoping helpers, RBAC engine, design system.
- Produces: `Document`/`DocumentVersion`/`Evidence` entities and their
  IDs, which Tasks 3 and 4 attach photos/files to via a foreign key —
  document this attachment contract clearly in
  `docs/DOCUMENTS_EVIDENCE.md` so Tasks 3/4 can consume it without
  guessing (e.g. "any domain object gets evidence via
  `evidence_id: UUID | None` FK to `evidence.id`, plural attachments via
  a join table if more than one is needed").

- [ ] **Step 1: Write failing tests for the acceptance behaviors below, then implement**

```text
test_document_version_supersedes_previous_and_keeps_immutable_history:
  Uploading a new version of a Document marks the prior DocumentVersion
  SUPERSEDED (immutable, never deleted/overwritten) and the Document's
  "current version" pointer moves to the new one.
test_evidence_rejects_unsupported_mime_type:
  Uploading a .exe or .zip is rejected with a 422 before any blob call.
test_evidence_rejects_oversized_file:
  Uploading a file over the configured size limit is rejected with 422.
test_evidence_upload_without_storage_configured_returns_real_error:
  With EVIDENCE_BACKEND left unconfigured in the test environment,
  the API returns a real 5xx/503 with a clear error code — never a fake
  200 with a fabricated URL.
test_company_access_blocks_cross_company_document:
  A user scoped to company A gets 403 for a company B Document ID.
test_progress_record_evidence_ref_is_a_real_evidence_fk:
  Creating a ProgressRecord with an evidence_id referencing another
  company's Evidence row is rejected before persistence.
```

- [ ] **Step 2: Run full backend/frontend gates, review diff, commit**

```bash
cd /Users/clopezg/nexora-group-trackD/backend
./.venv/bin/pytest -q
./.venv/bin/python -m compileall -q app tests
./.venv/bin/alembic heads   # must stay one head
cd ../frontend
npm run typecheck && npm run lint && npm test -- --run && npm run build
```

### Task 2: Workforce/Time frontend (closes DEFERRED-FINAL-008)

**Files:**
- Create: `frontend/src/features/workforce/WorkersPage.tsx`,
  `frontend/src/features/workforce/TimeEntriesPage.tsx`
- Create: `frontend/src/services/workforceService.ts`,
  `frontend/src/types/workforce.ts`
- Modify: `frontend/src/app/routes.tsx` (real pages under
  `/recursos/mano-de-obra`, replacing whatever placeholder or missing
  route currently sits there)
- Create: `frontend/tests/WorkersPage.test.tsx`,
  `frontend/tests/TimeEntriesPage.test.tsx`

**Interfaces:**
- Consumes: the already-merged, already-tested Workforce backend
  (`backend/app/api/routes/workforce.py`, `Worker`/`TimeEntry` — read the
  existing service/schema first, do not guess field names or the
  SUBMITTED→APPROVED/REJECTED lifecycle).
- Produces: a real, persisted-data UI — worker list/create, time entry
  list/create/approve/reject, labor cost visualization (the server-computed
  `labor_cost = hourly_rate * approved_hours`), filters by project/date/
  status, no `PlaceholderPage`.

- [ ] **Step 1: Write a failing frontend test, then implement**

```text
it('reloads Workers and TimeEntries from their real APIs, approves a
   time entry, and displays the server-computed labor cost') {}
```

- [ ] **Step 2: Run frontend gates, review diff, commit**

```bash
cd /Users/clopezg/nexora-group-trackD-wf/frontend
npm run typecheck && npm run lint && npm test -- --run && npm run build
```

### Task 3: Daily Site Reports + Quality + Safety (NXR-REQ-0081/0082/0083/0084)

**Files:**
- Create: `backend/app/models/site_report.py` (`DailySiteReport` — project,
  date, weather, workforce summary, activities performed, equipment used,
  materials, incidents, observations, author, approval state, evidence
  references via Task 1's `Evidence` FK)
- Create: `backend/app/models/quality.py` (`QualityInspection`,
  `NonConformance`, `CorrectiveAction` — responsible user, due date,
  closure, evidence)
- Create: `backend/app/models/safety.py` (`SafetyObservation`,
  `SafetyIncident` — severity, responsible, corrective actions, evidence,
  closure)
- Create: matching Alembic revision (down_revision = Task 1's revision,
  merge `feat/nexora-greenfield` first to get the real revision ID —
  do not guess it)
- Create: repositories/services/routes/schemas for all three domains
  following the established layout
- Modify additively: `backend/app/main.py`, `backend/app/models/__init__.py`,
  `backend/app/repositories/permission_repository.py`
- Create: `backend/tests/test_site_reports.py`,
  `backend/tests/test_quality.py`, `backend/tests/test_safety.py`
- Create: `frontend/src/features/site/DailyReportsPage.tsx`,
  `frontend/src/features/quality/QualityPage.tsx`,
  `frontend/src/features/safety/SafetyPage.tsx` (+ services/types), real
  UI, no `PlaceholderPage`
- Modify: `frontend/src/app/routes.tsx`

**Interfaces:**
- Consumes: Task 1's `Evidence`/`Document` entities (photos/attachments),
  company/project scoping, RBAC, design system.
- Produces: daily report/inspection/non-conformance/corrective-action/
  safety-observation/incident IDs and their approval/closure states.

- [ ] **Step 1: Merge latest `feat/nexora-greenfield` first (to pick up Task 1's Evidence entity), resolve additively**

```bash
git merge --no-ff feat/nexora-greenfield
```

- [ ] **Step 2: Write failing tests for the acceptance behaviors below, then implement**

```text
test_daily_site_report_requires_project_id_at_domain_and_db_level:
  A report without project_id is rejected (this is inherently
  PROJECT-scoped, unlike Track D's GENERAL/PROJECT-optional resources).
test_non_conformance_requires_corrective_action_before_closure:
  Closing a NonConformance with no CorrectiveAction attached is rejected.
test_safety_incident_severity_drives_required_fields:
  A HIGH-severity incident without a responsible user assigned is
  rejected; a LOW-severity observation is not required to have one.
test_company_access_blocks_cross_company_quality_resource:
  A user scoped to company A gets 403 for a company B QualityInspection ID.
```

- [ ] **Step 3: Run full gates, review diff, commit**

```bash
./.venv/bin/pytest -q
./.venv/bin/alembic heads   # must stay one head
npm run typecheck && npm run lint && npm test -- --run && npm run build
```

### Task 4: RFI + Submittals (NXR-REQ-0085/0086)

**Files:**
- Create: `backend/app/models/rfi.py` (`RequestForInformation` — company-
  scoped number sequence reusing the existing `NumberSequence` service,
  project, WBS, subject, question, response, responsible, dates, status)
- Create: `backend/app/models/submittal.py` (`Submittal` — revision,
  project/WBS, optional supplier/contract reference into Track C,
  review status, approval/rejection, dates, evidence)
- Create: matching Alembic revision (down_revision = Task 1's revision;
  if Task 3 has already merged into `feat/nexora-greenfield` by the time
  this task starts, chain onto Task 3's head instead — check the real
  current head, do not assume)
- Create: repositories/services/routes/schemas for both domains
- Modify additively: `backend/app/main.py`, `backend/app/models/__init__.py`,
  `backend/app/repositories/permission_repository.py`
- Create: `backend/tests/test_rfi.py`, `backend/tests/test_submittals.py`
- Create: `frontend/src/features/rfi/RfiPage.tsx`,
  `frontend/src/features/submittals/SubmittalsPage.tsx` (+ services/
  types), real UI, no `PlaceholderPage`
- Modify: `frontend/src/app/routes.tsx`

**Interfaces:**
- Consumes: Task 1's `Evidence`/`Document` entities, the existing
  `NumberSequence` service (same one AP/AR/Procurement already use — do
  not invent a second numbering scheme), Track C's Supplier/Contract
  entities (optional reference on Submittal), company/project scoping,
  RBAC.
- Produces: RFI/Submittal IDs and their status lifecycles.

- [ ] **Step 1: Merge latest `feat/nexora-greenfield` first, resolve additively**

```bash
git merge --no-ff feat/nexora-greenfield
```

- [ ] **Step 2: Write failing tests for the acceptance behaviors below, then implement**

```text
test_rfi_number_sequence_is_company_scoped:
  Two companies can each issue their first RFI without a unique-constraint
  collision (same pattern as Track A's per-company document numbering).
test_submittal_requires_response_before_approval:
  Approving a Submittal with no reviewer response recorded is rejected.
test_company_access_blocks_cross_company_rfi:
  A user scoped to company A gets 403 for a company B RFI ID.
```

- [ ] **Step 3: Run full gates, review diff, commit**

```bash
./.venv/bin/pytest -q
./.venv/bin/alembic heads   # must stay one head
npm run typecheck && npm run lint && npm test -- --run && npm run build
```

### Task 5: Combined verification and traceability recount

**Files:**
- Verify only: all files touched by Tasks 1-4 once integrated on
  `feat/nexora-greenfield`
- Modify only if evidence warrants it: `docs/PROGRESS.md`,
  `docs/REQUIREMENTS_TRACEABILITY.md`, `docs/DEFERRED.md`

**Interfaces:**
- Consumes: the fully integrated Documents/Evidence/Site/Quality/Safety/
  RFI/Submittals/Workforce-UI system.
- Produces: one reproducible integration head and an honest traceability
  update for NXR-REQ-0073/0075/0076/0077/0078/0079/0081/0082/0083/0084/
  0085/0086.

- [ ] **Step 1: Verify git topology, one Alembic head, fresh-install upgrade**

```bash
git status
git log --graph --decorate --oneline -20
./.venv/bin/alembic heads
./.venv/bin/alembic upgrade head   # on a fresh disposable database
```

- [ ] **Step 2: Run complete backend/frontend verification from the integration worktree**

```bash
./.venv/bin/pytest -q
./.venv/bin/python -m compileall -q app tests
npm run typecheck && npm run lint && npm test -- --run && npm run build
```

- [ ] **Step 3: Recount `docs/REQUIREMENTS_TRACEABILITY.md` row-by-row against its own summary (same method as Task 7 of the prior plan) and update `docs/DEFERRED.md`/`docs/PROGRESS.md` honestly — only IMPLEMENTED/IN_PROGRESS states supported by real evidence, never inflate to VERIFIED**
