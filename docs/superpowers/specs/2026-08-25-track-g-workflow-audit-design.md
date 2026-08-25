# Track G: Workflow / Approvals / Audit / Notifications — Design

Status: approved by user (scope-fork question answered via AskUserQuestion;
sectioned design presented and not objected to; user's standing autonomy
order for this session directs no further pause between design and
implementation — see Ruling below).

## Goal

Close NXR-REQ-0087 through 0096 (`docs/REQUIREMENTS_TRACEABILITY.md`,
PLATFORM block): Workflow engine, Approval Inbox, Segregation of Duties,
Audit, Notifications. This is the first track to build a real audit
mechanism — `DEFERRED-FINAL-014` (no audit-log mechanism exists anywhere
in the codebase yet) is this track's first job.

## Ruling: scope boundary (the core design decision)

**Track G does NOT build a generic state-machine framework that existing
domains migrate onto.** Every domain across Tracks 1/A/B/C/D/E/
construction-control already has its own status field and
service-layer transition guards (AP invoice DRAFT→APPROVED, Submittal
SUBMITTED→UNDER_REVIEW→APPROVED/REJECTED, NonConformance open/closed,
etc.) — all independently reviewed and tested. Rewriting them onto a new
generic engine would be a large, risky, low-value refactor of
already-correct code, and would compete with domain-owned invariants
(Treasury owns money, Posting Engine is the sole path to GL debits/
credits) that are enforced by dedicated services on purpose.

Instead, Track G builds three shared, cross-cutting services that
domains **opt into**, keeping their own transition logic exactly as
built:

1. **Audit trail** (`AuditLog`) — a shared append-only log any service
   calls into explicitly.
2. **Approval Inbox** (`ApprovalRequest`) — a shared entity any domain
   creates when it needs a human decision; the domain still owns its own
   state transition, `ApprovalRequest` just gives one queryable inbox
   surface across domains and centralizes Segregation of Duties.
3. **Notifications** (`Notification`) — a shared entity created at the
   same event points as the above two.

Cost if this ruling is wrong: a future need for genuinely configurable,
admin-editable workflows (business users defining new approval chains
without code changes) would require a second effort later. Given nothing
in the brief or `docs/MASTER_PLAN.md` asks for admin-configurable
workflows today, this is accepted.

**Correction discovered during planning:** Foundation already reserved
an `ApprovalPolicy` skeleton table (`backend/app/models/approval_policy.py`)
with a docstring explicitly naming Track G as its owner, and nothing
references it yet. Track G extends this existing table (adds
`entity_type`, `requires_third_role`) instead of inventing a parallel
policy concept — see the Approval Inbox section below.

## Components

### 1. Audit trail

**Model** `AuditLog` (append-only — no service ever UPDATEs or DELETEs a
row, same discipline as `AccountingDocument`):
- `id`, `actor_user_id` (FK, nullable for system actions), `action` (str,
  e.g. `"ap.supplier_invoice.approve"`), `entity_type`, `entity_id`,
  `before` (JSONB, nullable), `after` (JSONB, nullable), `company_id`
  (FK), `project_id` (FK, nullable), `correlation_id` (str), `created_at`.
- Never store secrets/full financial credentials in `before`/`after` —
  callers pass only the fields worth auditing, not a raw model dump.

**Integration pattern**: `audit_service.record(db, actor_user_id=...,
action=..., entity_type=..., entity_id=..., company_id=..., before=...,
after=..., project_id=None, correlation_id=...)`, called explicitly —
matching the existing house style of `assert_company_access`/
`assert_evidence_belongs_to_company`, not a hidden SQLAlchemy event
hook. `correlation_id` is generated once per HTTP request (middleware)
and threaded through.

**Call site is the route layer, not the service layer.** Verified
against the real codebase (`backend/app/api/routes/ap.py:92-105`):
`assert_company_access` is already called in the route handler, using
`user` (from `require_permission`) and the entity resolved there —
service functions like `ap_service.approve_supplier_invoice(db,
invoice_id=...)` don't receive `actor_user_id` today and this task does
not add it to any existing service signature (that would be exactly the
large, risky refactor of already-tested code the scope Ruling above
rejects). Instead, each instrumented route calls `audit_service.record`
right after its service call succeeds, using the `user.id` and resolved
entity it already has — same layer, same pattern as
`assert_company_access`, zero service-signature changes.

**Rollout is incremental, not all-domains-at-once**: Task 1 builds the
model/service/API (`GET /api/audit` filtered by entity/company/actor/
date) and instruments Financial Core (Treasury/AP/AR) and Procurement
first — the highest-audit-value domains — with real tests proving audit
rows are created on real mutations. Every other domain's instrumentation
is tracked honestly as `NOT_STARTED`/`IN_PROGRESS` per requirement, never
implied complete. `docs/AUDIT.md` documents the call pattern so later
tracks (or a dedicated follow-up task) can close the remaining domains
without guessing.

### 2. Approval Inbox

**`ApprovalPolicy` already exists** as a reserved skeleton
(`backend/app/models/approval_policy.py`, from Foundation/Track 1):
`id`, `company_id`, `name`, `description`, `active`. Its own docstring
says explicitly: "el motor de workflow completo ... es responsabilidad
del Track G ... esta tabla solo reserva dónde va a vivir la política."
Nothing references it yet (verified: no FK, no service touches it) — it
is genuinely unused, not half-built. Track G extends this table rather
than creating a parallel policy concept: add `entity_type: str` (which
domain/entity this policy governs, e.g. `"ap.supplier_invoice"`),
`requires_third_role: bool` (default `False`).

**Model** `ApprovalRequest`:
- `id`, `policy_id` (FK to `ApprovalPolicy`, nullable — a request can
  exist without a matching policy row for domains that haven't defined
  one yet), `entity_type`, `entity_id`, `company_id`, `project_id`
  (nullable), `module` (str, e.g. `"ap"`, `"construction"`),
  `requested_by` (FK), `assigned_to` (FK, nullable) / `assigned_role`
  (str, nullable — one of the two is set), `status`
  (`PENDING`/`APPROVED`/`REJECTED`/`CANCELLED`), `priority`
  (`LOW`/`NORMAL`/`HIGH`), `amount` (Decimal, nullable — for
  filtering/display only, never authoritative), `comment` (str,
  nullable, set on decision), `decided_by` (FK, nullable), `decided_at`
  (nullable), `created_at`.

**Flow**: a domain service creates an `ApprovalRequest` instead of (or
alongside) flipping its own status directly to a state that needs
approval — e.g. AP's "submit for payment approval" creates one row
instead of directly transitioning to `APPROVED`. The Approval Inbox API
(`GET /api/approvals?assignedToMe=true&module=...&priority=...`,
`POST /api/approvals/{id}/decide`) is generic across all domains. On
`decide`, a small per-module adapter function (registered by each
domain, e.g. `{"ap.supplier_invoice": ap_service.apply_approval_decision}`)
is called back into to perform the domain's own transition — the
`ApprovalRequest` never mutates domain state directly. This keeps each
domain's transition logic as the single source of truth for its own
invariants.

**Segregation of Duties**: enforced centrally in `decide()`:
`requested_by != decided_by` always (422 `NXR-WORKFLOW-001` if violated).
When the resolved `ApprovalPolicy.requires_third_role` is `True`, `decide()`
additionally checks the *executor* (the user who later performs the
approved action, e.g. releases payment) differs from both — this is
scoped to AP payment approval and Submittal decisions initially (the
brief's two most concrete SoD-sensitive flows, each getting a real
`ApprovalPolicy` row seeded in the migration), not retrofitted to every
domain in this task.

### 3. Notifications

**Model** `Notification`:
- `id`, `recipient_user_id` (FK), `type` (str, e.g.
  `"approval.assigned"`, `"approval.decided"`, `"budget.exceeded"`),
  `title`, `body`, `entity_type` (nullable), `entity_id` (nullable),
  `read_at` (nullable), `created_at`.

**Trigger points** (in this task's scope): `ApprovalRequest` creation
(notify `assigned_to`), `ApprovalRequest` decision (notify
`requested_by`). A small, named set of financial/project alerts from the
brief — budget threshold exceeded (Project Control), AP invoice overdue
— reusing existing domain read paths, not a new alerting engine.

**API/UI**: `GET /api/notifications?unreadOnly=true`,
`POST /api/notifications/{id}/read`, a bell icon + dropdown in
`AppLayout` (existing design system), real unread count.

## Data flow (approval example)

```
AP service: supplier invoice ready for payment
  → creates ApprovalRequest(entity_type="ap.supplier_invoice", ...)
  → creates Notification(recipient=assigned_to, type="approval.assigned")

Approver: GET /api/approvals?assignedToMe=true → sees it
  → POST /api/approvals/{id}/decide {"decision": "APPROVED"}
    → SoD check (requested_by != decided_by)
    → calls back: ap_service.apply_approval_decision(invoice_id, "APPROVED")
      → AP's own state machine transitions the invoice (unchanged logic)
    → AuditLog row: action="approval.decide", before/after on ApprovalRequest
    → Notification(recipient=requested_by, type="approval.decided")
```

## Testing

Real TDD per component, same house pattern as every prior track:
- Audit: a mutation in an instrumented domain creates exactly one
  `AuditLog` row with correct `before`/`after`; company isolation on
  `GET /api/audit`.
- Approval Inbox: SoD rejection (`requested_by == decided_by` → 422);
  double-decision is rejected (idempotent-safe, can't approve twice);
  a decided `ApprovalRequest` correctly triggers the domain's real
  transition (verified against the domain's own model state after
  decide, not just the `ApprovalRequest` row).
- Notifications: created on the real trigger points; unread count and
  mark-read work; company isolation (a user never sees another
  company's notification).

## Out of scope (explicit, not hidden)

- Generic/admin-configurable state machines (see Ruling above).
- Email/push notifications — in-app only, as the brief specifies.
- Retrofitting audit instrumentation to every existing domain in this
  task — incremental, honestly tracked.
- A generic "workflow designer" UI.

## Files (indicative — final list belongs in the implementation plan)

Backend: `app/models/audit.py`, `app/models/approval.py`,
`app/models/notification.py`, matching Alembic revision,
`app/services/audit_service.py`, `app/services/approval_service.py`,
`app/services/notification_service.py`, `app/api/routes/audit.py`,
`app/api/routes/approvals.py`, `app/api/routes/notifications.py`, a
correlation-id middleware, per-module approval-decision adapters wired
into `ap_service.py`/`submittal_service.py` initially.

Frontend: `features/audit/AuditLogPage.tsx`,
`features/approvals/ApprovalInboxPage.tsx`, a notifications bell
component in `AppLayout`, services/types for all three.

Docs: `docs/AUDIT.md` (instrumentation pattern for future domains),
`docs/PROGRESS.md`/`docs/REQUIREMENTS_TRACEABILITY.md` updates.
