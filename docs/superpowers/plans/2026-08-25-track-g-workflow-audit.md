# Track G: Workflow / Approvals / Audit / Notifications Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close NXR-REQ-0087 through 0096 (PLATFORM block): a real
append-only audit trail, a cross-domain Approval Inbox with Segregation
of Duties, and in-app Notifications — as three shared services existing
and future domains opt into, without rewriting any domain's own
already-tested state-transition logic.

**Architecture:** Task 1 builds the Audit trail (model, service, API,
`correlation_id` dependency) and instruments Treasury/AP/AR/Procurement
at the route layer — the same layer `assert_company_access` already
lives at, so no existing service function signature changes. Task 2
extends the already-reserved-but-unused `ApprovalPolicy` skeleton table
and adds `ApprovalRequest` (generic inbox, SoD enforcement, per-module
decision adapters for AP payment approval and Submittal decisions).
Task 3 adds Notifications, triggered at Task 2's approval-request
creation/decision points. Task 4 is combined verification and
traceability recount, same method as the two plans this session already
used.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2, Alembic, PostgreSQL
16, Pytest, React, TypeScript, Vite, TanStack Query, Vitest/RTL — same
stack and house conventions as every prior track.

**Spec:** `docs/superpowers/specs/2026-08-25-track-g-workflow-audit-design.md`,
`docs/MASTER_PLAN.md`, `docs/REQUIREMENTS_TRACEABILITY.md`, `CLAUDE.md`.

## Global Constraints

- Company isolation (`assert_company_access`, from
  `app.services.permission_service`) on every new resource, called at
  the route layer with the pattern verified in
  `backend/app/api/routes/ap.py:92-105`: resolve the entity, then
  `assert_company_access(db, user_id=user.id, resource=..., action=...,
  company_id=<entity>.company_id)`, then call the service.
- PostgreSQL is the only persistence; no in-memory or
  filesystem-persistent state.
- `AuditLog` is append-only: no service, route, or migration may
  `UPDATE` or `DELETE` a row after insert. Never store secrets or full
  financial credentials in `before`/`after`.
- Do not add `actor_user_id` (or any new parameter) to any existing
  service function in `ap_service.py`, `ar_service.py`,
  `treasury_service.py`, or `procurement_service.py`. Audit calls live
  in the route handler, which already has `user` and the resolved
  entity — same layer as `assert_company_access`.
- Do not create a second `ApprovalPolicy`-shaped table. Extend
  `backend/app/models/approval_policy.py` (currently unused, reserved
  for this track) rather than defining a parallel concept.
- Every domain slice follows domain → DB → Alembic → repository →
  service → API → permission → frontend → test, updates
  `docs/PROGRESS.md`/`docs/REQUIREMENTS_TRACEABILITY.md` honestly
  (`IMPLEMENTED`/`IN_PROGRESS`/`NOT_STARTED`, never `VERIFIED`).
- No GL posting, no Treasury cash movement — this track does not touch
  money.
- Reuse existing patterns: RBAC (`require_permission`), the design
  system, TanStack Query conventions. Error responses follow the
  existing `{"error": {"code": "NXR-...", "message": ..., "field":
  ..., "correlationId": ...}}` shape via
  `backend/app/api/error_handlers.py`.
- Test database: this worktree needs its own isolated Postgres database
  (per `backend/tests/conftest.py`'s per-worktree naming, added this
  session) — `CREATE DATABASE nexora_test_<sanitized_worktree_dirname>;`
  before running pytest here for the first time.

---

### Task 1: Audit trail foundation (NXR-REQ-0090)

**Files:**
- Create: `backend/app/models/audit.py` (`AuditLog`)
- Create: `backend/alembic/versions/<rev>_add_audit_log.py` — down_revision
  is `feat/nexora-greenfield`'s real current head; run `alembic heads`
  first and use that value, do not guess it
- Create: `backend/app/repositories/audit_repository.py`
- Create: `backend/app/services/audit_service.py`
- Create: `backend/app/api/deps_correlation.py` (correlation-id
  dependency)
- Create: `backend/app/api/routes/audit.py`
- Modify: `backend/app/main.py` (register `audit.router`)
- Modify: `backend/app/models/__init__.py` (export `AuditLog`)
- Modify: `backend/app/repositories/permission_repository.py` (add
  `audit.log` permission grants)
- Modify: `backend/app/api/routes/ap.py` — instrument
  `approve_supplier_invoice` (the route at line ~92) and
  `pay_supplier_invoice`
- Modify: `backend/app/api/routes/treasury.py` — instrument the
  remittance-approval and cash-closing-approval routes (read the file
  first for exact function/route names — do not guess)
- Modify: `backend/app/api/routes/procurement.py` — instrument the
  purchase-order-approval route (read the file first for the exact
  route name)
- Test: `backend/tests/test_audit.py`
- Test: `backend/tests/test_ap_ar.py` (extend — one new test asserting
  an `AuditLog` row exists after a real AP approval)
- Create: `frontend/src/features/audit/AuditLogPage.tsx`,
  `frontend/src/services/auditService.ts`, `frontend/src/types/audit.ts`
- Modify: `frontend/src/app/routes.tsx`, `frontend/src/app/navigation.ts`
  (add `/plataforma/auditoria` — check `navigation.ts` first for
  whether a Platform/Plataforma section already exists; if not, add one
  following the existing section pattern)
- Create: `docs/AUDIT.md` (instrumentation pattern for future domains)

**Interfaces:**
- Consumes: `app.services.permission_service.assert_company_access`,
  `require_permission`; `app.api.deps.get_db`, `get_current_user`.
- Produces: `audit_service.record(db, *, actor_user_id: uuid.UUID,
  action: str, entity_type: str, entity_id: uuid.UUID, company_id:
  uuid.UUID, project_id: uuid.UUID | None = None, before: dict | None =
  None, after: dict | None = None, correlation_id: str) -> AuditLog` —
  Task 2 and Task 3 call this directly on `ApprovalRequest`/
  `Notification` mutations. `get_correlation_id(...)` FastAPI dependency
  — Task 2/3's routes reuse it.

- [ ] **Step 1: Check the real current Alembic head**

```bash
cd backend
./.venv/bin/alembic heads
```

Record the printed revision id — call it `<head>` below.

- [ ] **Step 2: Write the failing model/migration test**

```python
# backend/tests/test_audit.py
import uuid

from app.models.audit import AuditLog
from tests.helpers import create_company, login_admin


def test_audit_log_is_append_only_and_records_actor_and_entity(client, db_session):
    login_admin(client)
    company = create_company(client)

    from app.services import audit_service

    row = audit_service.record(
        db_session,
        actor_user_id=uuid.uuid4(),
        action="test.create",
        entity_type="test_entity",
        entity_id=uuid.uuid4(),
        company_id=uuid.UUID(company["id"]),
        before=None,
        after={"status": "CREATED"},
        correlation_id="corr-1",
    )
    db_session.commit()

    fetched = db_session.get(AuditLog, row.id)
    assert fetched is not None
    assert fetched.action == "test.create"
    assert fetched.after == {"status": "CREATED"}
    assert fetched.company_id == uuid.UUID(company["id"])
```

- [ ] **Step 3: Run it to confirm it fails (module doesn't exist yet)**

Run: `./.venv/bin/pytest tests/test_audit.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.models.audit'`

- [ ] **Step 4: Create the `AuditLog` model**

```python
# backend/app/models/audit.py
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import UUIDPrimaryKeyMixin

# Append-only: no service/route ever UPDATEs or DELETEs a row after
# insert. Deliberately does NOT use TimestampMixin (its onupdate would
# make "updated_at" a lie for a table that must never update).


class AuditLog(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "audit_logs"

    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(150), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True
    )
    before: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    after: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    correlation_id: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
```

- [ ] **Step 5: Create the repository and service**

```python
# backend/app/repositories/audit_repository.py
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit import AuditLog


def create(db: Session, **kwargs) -> AuditLog:
    row = AuditLog(**kwargs)
    db.add(row)
    db.flush()
    return row


def list_for_company(
    db: Session,
    *,
    company_id: uuid.UUID,
    entity_type: str | None = None,
    entity_id: uuid.UUID | None = None,
    actor_user_id: uuid.UUID | None = None,
) -> list[AuditLog]:
    stmt = select(AuditLog).where(AuditLog.company_id == company_id)
    if entity_type is not None:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
    if entity_id is not None:
        stmt = stmt.where(AuditLog.entity_id == entity_id)
    if actor_user_id is not None:
        stmt = stmt.where(AuditLog.actor_user_id == actor_user_id)
    stmt = stmt.order_by(AuditLog.created_at.desc())
    return list(db.execute(stmt).scalars())
```

```python
# backend/app/services/audit_service.py
import uuid

from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.repositories import audit_repository


def record(
    db: Session,
    *,
    actor_user_id: uuid.UUID | None,
    action: str,
    entity_type: str,
    entity_id: uuid.UUID,
    company_id: uuid.UUID,
    correlation_id: str,
    project_id: uuid.UUID | None = None,
    before: dict | None = None,
    after: dict | None = None,
) -> AuditLog:
    return audit_repository.create(
        db,
        actor_user_id=actor_user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        company_id=company_id,
        project_id=project_id,
        before=before,
        after=after,
        correlation_id=correlation_id,
    )
```

- [ ] **Step 6: Generate and inspect the Alembic revision**

```bash
./.venv/bin/alembic revision --autogenerate -m "add audit log"
```

Open the generated file, confirm `down_revision = "<head>"` (from Step
1), confirm it only creates `audit_logs` (no unrelated diff — if
autogenerate picked up unrelated drift from another in-progress
worktree's uncommitted model changes, trim the migration to just this
table).

- [ ] **Step 7: Run the model test**

Run: `./.venv/bin/alembic upgrade head` then
`./.venv/bin/pytest tests/test_audit.py -v`
Expected: PASS

- [ ] **Step 8: Add the correlation-id dependency**

```python
# backend/app/api/deps_correlation.py
import uuid

from fastapi import Header


def get_correlation_id(x_correlation_id: str | None = Header(default=None)) -> str:
    return x_correlation_id or str(uuid.uuid4())
```

- [ ] **Step 9: Write the failing route-instrumentation test**

```python
# backend/tests/test_ap_ar.py — add to the existing file
def test_approving_supplier_invoice_creates_audit_log_entry(client, db_session):
    login_admin(client)
    company, _bank, expense, payable, supplier = _setup_ap(client)
    invoice = client.post(
        "/api/ap/supplier-invoices",
        json={
            "companyId": company["id"],
            "supplierId": supplier["id"],
            "invoiceNumber": "A-AUD-1",
            "scope": "GENERAL",
            "expenseAccountId": expense["id"],
            "payableAccountId": payable["id"],
            "currencyCode": "HNL",
            "amount": "100.00",
            "invoiceDate": "2026-01-10",
            "dueDate": "2026-02-10",
        },
    ).json()

    client.post(f"/api/ap/supplier-invoices/{invoice['id']}/approve")

    from app.models.audit import AuditLog
    from sqlalchemy import select

    rows = db_session.execute(
        select(AuditLog).where(
            AuditLog.entity_type == "ap.supplier_invoice",
            AuditLog.entity_id == uuid.UUID(invoice["id"]),
        )
    ).scalars().all()
    assert len(rows) == 1
    assert rows[0].action == "ap.supplier_invoice.approve"
    assert rows[0].after["status"] == "APPROVED"
```

Add `import uuid` at the top of `test_ap_ar.py` if not already present
(check first).

- [ ] **Step 10: Run it to confirm it fails**

Run: `./.venv/bin/pytest tests/test_ap_ar.py::test_approving_supplier_invoice_creates_audit_log_entry -v`
Expected: FAIL — 0 rows found.

- [ ] **Step 11: Instrument the AP approve route**

```python
# backend/app/api/routes/ap.py — modify approve_supplier_invoice
def approve_supplier_invoice(
    invoice_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("ap.supplier_invoice", "approve")),
    correlation_id: str = Depends(get_correlation_id),
) -> SupplierInvoiceResponse:
    invoice = _resolve_invoice(db, invoice_id)
    assert_company_access(
        db,
        user_id=user.id,
        resource="ap.supplier_invoice",
        action="approve",
        company_id=invoice.company_id,
    )
    before_status = invoice.status
    invoice = ap_service.approve_supplier_invoice(db, invoice_id=invoice_id)
    audit_service.record(
        db,
        actor_user_id=user.id,
        action="ap.supplier_invoice.approve",
        entity_type="ap.supplier_invoice",
        entity_id=invoice.id,
        company_id=invoice.company_id,
        project_id=invoice.project_id,
        before={"status": before_status},
        after={"status": invoice.status},
        correlation_id=correlation_id,
    )
    db.commit()
    return SupplierInvoiceResponse.model_validate(invoice, from_attributes=True)
```

Add the two new imports at the top of `ap.py`:
`from app.api.deps_correlation import get_correlation_id` and
`from app.services import audit_service`.

- [ ] **Step 12: Run the test to confirm it passes**

Run: `./.venv/bin/pytest tests/test_ap_ar.py::test_approving_supplier_invoice_creates_audit_log_entry -v`
Expected: PASS

- [ ] **Step 13: Repeat Steps 9-12's pattern for `pay_supplier_invoice`
      (ap.py), the Treasury remittance-approval and cash-closing-approval
      routes (treasury.py — read the file first to get exact route/
      function names, do not guess), and the Procurement purchase-order
      approval route (procurement.py — same)**

Each gets its own focused test in the same shape as Step 9 (one
`AuditLog` row, correct `action`/`entity_type`/`after`), its own RED
run, its own instrumentation, its own GREEN run. Do not batch these
into one giant untested change — one route, one test, one commit each
or a small logical group per file.

- [ ] **Step 14: Build the Audit API and permissions**

```python
# backend/app/api/routes/audit.py
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.repositories import audit_repository
from app.schemas.audit import AuditLogResponse
from app.services.permission_service import assert_company_access, require_permission

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=list[AuditLogResponse])
def list_audit_logs(
    company_id: uuid.UUID,
    entity_type: str | None = None,
    entity_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    user=Depends(require_permission("audit.log", "read")),
) -> list[AuditLogResponse]:
    assert_company_access(
        db, user_id=user.id, resource="audit.log", action="read", company_id=company_id
    )
    rows = audit_repository.list_for_company(
        db, company_id=company_id, entity_type=entity_type, entity_id=entity_id
    )
    return [AuditLogResponse.model_validate(r, from_attributes=True) for r in rows]
```

```python
# backend/app/schemas/audit.py
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.base import CamelModel


class AuditLogResponse(CamelModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    actor_user_id: uuid.UUID | None
    action: str
    entity_type: str
    entity_id: uuid.UUID
    company_id: uuid.UUID
    project_id: uuid.UUID | None
    before: dict | None
    after: dict | None
    correlation_id: str
    created_at: datetime
```

Check `app/schemas/base.py` for the real `CamelModel` base class name
before using it — every other schema module in this codebase imports
it, confirm the import path matches (e.g. `backend/app/schemas/ap.py`'s
own import line) and adjust if the actual name differs.

Register the router in `main.py` (`app.include_router(audit.router,
prefix="/api")`, additive, alongside the existing includes) and export
`AuditLog` from `models/__init__.py`. Add permission grants in
`permission_repository.py`: `("audit.log", "read", "Ver bitácora de
auditoría")` in `_BASE_PERMISSIONS`, and grant `SCOPE_OWN` read to
Administrator/Auditor/Finance Manager (mirror the existing grant style
for a read-only cross-cutting permission — check how `document.evidence`
read grants are structured for the exact role list to copy).

- [ ] **Step 15: Write a company-isolation test for the Audit API**

```python
# backend/tests/test_audit.py — add
def test_company_access_blocks_cross_company_audit_log(client, db_session):
    login_admin(client)
    company_a = create_company(client, name="Auditoria A")
    company_b = create_company(client, name="Auditoria B")

    user = create_user_with_role(
        db_session, email="auditor-b@nexora.group", role_name="Auditor"
    )
    db_session.add(UserCompanyAccess(user_id=user.id, company_id=company_b["id"]))
    db_session.commit()
    login_as(client, email="auditor-b@nexora.group")

    response = client.get(f"/api/audit?companyId={company_a['id']}")
    assert response.status_code == 403, response.text
    assert response.json()["error"]["code"] == "NXR-PERM-001"
```

Add the needed imports (`UserCompanyAccess` from `app.models.permission`,
`create_user_with_role`, `login_as` from `tests.helpers`) at the top of
`test_audit.py`.

- [ ] **Step 16: Run it, confirm RED then GREEN**

Run: `./.venv/bin/pytest tests/test_audit.py -v`
Confirm it fails before the Auditor role actually has only `SCOPE_OWN`
(not `SCOPE_ANY`) for `audit.log` — if Auditor was already granted
`SCOPE_ANY` elsewhere in this codebase's convention, use a role that
genuinely has `SCOPE_OWN` for this test to be meaningful; check
`permission_repository.py`'s existing Auditor grants first.

- [ ] **Step 17: Build the frontend AuditLogPage**

```typescript
// frontend/src/types/audit.ts
export interface AuditLogEntry {
  id: string
  actorUserId: string | null
  action: string
  entityType: string
  entityId: string
  companyId: string
  projectId: string | null
  before: Record<string, unknown> | null
  after: Record<string, unknown> | null
  correlationId: string
  createdAt: string
}
```

```typescript
// frontend/src/services/auditService.ts
import { apiFetch } from './httpClient'
import type { AuditLogEntry } from '../types/audit'

export async function listAuditLog(params: {
  companyId: string
  entityType?: string
  entityId?: string
}): Promise<AuditLogEntry[]> {
  const query = new URLSearchParams(params as Record<string, string>)
  return apiFetch(`/audit?${query.toString()}`)
}
```

Check `frontend/src/services/httpClient.ts`'s real `apiFetch` signature
before using it (confirm it returns parsed JSON directly, matching
every other service file's usage — e.g. `documentService.ts`).

Build `AuditLogPage.tsx` following `frontend/src/features/documents/DocumentsPage.tsx`'s
structure: `useActiveCompany()` for scoping, TanStack Query
`useQuery(['audit', activeCompanyId, filters], () =>
listAuditLog({...}))`, a filterable table (entity type, date range),
using the design system's `Table`/`FilterBar` components — check
`DocumentsPage.tsx` for the exact import paths and reuse them.

Register the route: add `import { AuditLogPage } from
'../features/audit/AuditLogPage'` and
`'/plataforma/auditoria': <AuditLogPage />,` to
`IMPLEMENTED_ROUTES` in `routes.tsx`, and add the nav entry to
`navigation.ts` (check whether a Platform/Plataforma section exists
first — follow whatever sectioning convention the file already uses).

- [ ] **Step 18: Write a frontend test**

```typescript
// frontend/tests/AuditLogPage.test.tsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { AuditLogPage } from '../src/features/audit/AuditLogPage'
// follow the exact test-setup wrapper (QueryClientProvider, ActiveCompanyProvider,
// etc.) used in frontend/tests/DocumentsPage.test.tsx — copy its structure

it('loads and displays real audit log entries from the API', async () => {
  vi.spyOn(globalThis, 'fetch').mockResolvedValue({
    ok: true,
    json: async () => [
      {
        id: 'a1',
        actorUserId: 'u1',
        action: 'ap.supplier_invoice.approve',
        entityType: 'ap.supplier_invoice',
        entityId: 'inv1',
        companyId: 'c1',
        projectId: null,
        before: { status: 'DRAFT' },
        after: { status: 'APPROVED' },
        correlationId: 'corr-1',
        createdAt: '2026-08-25T10:00:00Z',
      },
    ],
  } as Response)

  // render with the same provider wrapper DocumentsPage.test.tsx uses
  await waitFor(() => {
    expect(screen.getByText(/ap\.supplier_invoice\.approve/i)).toBeInTheDocument()
  })
})
```

Adjust the mock/render boilerplate to match `DocumentsPage.test.tsx`
exactly — do not invent a different test-setup pattern.

- [ ] **Step 19: Write `docs/AUDIT.md`**

Document: the `AuditLog` schema, the `audit_service.record(...)` call
signature, the route-layer-not-service-layer rule with the
`ap.py:approve_supplier_invoice` example, the list of domains
instrumented so far (Treasury/AP/AR/Procurement — name the exact
actions), and the list of domains NOT yet instrumented (Project Control,
Enterprise Resources, Commercial, Construction Control) as an explicit,
honest backlog for a future task — not hidden, not implied done.

- [ ] **Step 20: Run full gates, update docs, commit**

```bash
./.venv/bin/pytest -q
./.venv/bin/python -m compileall -q app tests
./.venv/bin/alembic heads
cd ../frontend
npm run typecheck && npm run lint && npm test -- --run && npm run build
```

Update `docs/PROGRESS.md` and `docs/REQUIREMENTS_TRACEABILITY.md` for
`NXR-REQ-0090` (Audit) — `IMPLEMENTED` only for the instrumented
domains' evidence, honestly noting which domains remain. Stage explicit
reviewed paths, commit in logical units (model+migration+service, then
each route's instrumentation, then API+frontend, then docs).

### Task 2: Approval Inbox + Segregation of Duties (NXR-REQ-0087/0088/0089)

**Files:**
- Modify: `backend/app/models/approval_policy.py` (add `entity_type`,
  `requires_third_role`)
- Create: `backend/app/models/approval_request.py` (`ApprovalRequest`)
- Create: `backend/alembic/versions/<rev>_add_approval_request.py` —
  `down_revision` is Task 1's real merged head (check `alembic heads`
  on `feat/nexora-greenfield` after Task 1 lands, do not assume)
- Create: `backend/app/repositories/approval_repository.py`
- Create: `backend/app/services/approval_service.py` (includes the
  per-module decision-adapter registry)
- Create: `backend/app/api/routes/approvals.py`
- Modify: `backend/app/main.py`, `backend/app/models/__init__.py`,
  `backend/app/repositories/permission_repository.py`
- Modify: `backend/app/services/ap_service.py` — add
  `apply_approval_decision(db, *, invoice_id, decision)` function (new
  function, does not change `approve_supplier_invoice`'s existing
  signature/behavior — it's an additional entry point the adapter calls)
- Modify: `backend/app/services/submittal_service.py` — add
  `apply_approval_decision(db, *, submittal_id, decision)` (same
  pattern; read the file first for the real existing decision function
  to delegate to)
- Test: `backend/tests/test_approvals.py`
- Create: `frontend/src/features/approvals/ApprovalInboxPage.tsx`,
  `frontend/src/services/approvalService.ts`,
  `frontend/src/types/approval.ts`
- Modify: `frontend/src/app/routes.tsx`, `frontend/src/app/navigation.ts`

**Interfaces:**
- Consumes: Task 1's `audit_service.record(...)` and
  `get_correlation_id` dependency (called on `decide()` for the
  `ApprovalRequest`'s own audit entry).
- Produces: `approval_service.create_request(db, *, policy_id:
  uuid.UUID | None, entity_type: str, entity_id: uuid.UUID, company_id:
  uuid.UUID, requested_by: uuid.UUID, module: str, assigned_to:
  uuid.UUID | None = None, assigned_role: str | None = None, priority:
  str = "NORMAL", amount: Decimal | None = None, project_id: uuid.UUID
  | None = None) -> ApprovalRequest` and `approval_service.decide(db, *,
  request_id: uuid.UUID, decided_by: uuid.UUID, decision: str, comment:
  str | None = None) -> ApprovalRequest` — Task 3 calls both to know
  when to create a `Notification`.

- [ ] **Step 1: Merge latest `feat/nexora-greenfield` into this
      worktree's branch, resolve additively, confirm the real Alembic
      head**

```bash
git merge --no-ff feat/nexora-greenfield
cd backend && ./.venv/bin/alembic heads
```

- [ ] **Step 2: Write the failing test for extending `ApprovalPolicy`**

```python
# backend/tests/test_approvals.py
import uuid

from app.models.approval_policy import ApprovalPolicy
from tests.helpers import create_company, login_admin


def test_approval_policy_has_entity_type_and_requires_third_role(client, db_session):
    login_admin(client)
    company = create_company(client)

    policy = ApprovalPolicy(
        company_id=uuid.UUID(company["id"]),
        name="AP Payment Approval",
        entity_type="ap.supplier_payment",
        requires_third_role=True,
    )
    db_session.add(policy)
    db_session.commit()
    db_session.refresh(policy)

    assert policy.entity_type == "ap.supplier_payment"
    assert policy.requires_third_role is True
```

- [ ] **Step 3: Run it, confirm it fails**

Run: `./.venv/bin/pytest tests/test_approvals.py -v`
Expected: FAIL — `TypeError: 'entity_type' is an invalid keyword argument`

- [ ] **Step 4: Extend `ApprovalPolicy`**

```python
# backend/app/models/approval_policy.py — add these two columns
    entity_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    requires_third_role: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
```

Update the file's module docstring to note Track G has now built on
this reserved skeleton (replace the "se construye después" line).

- [ ] **Step 5: Write the `ApprovalRequest` model, run
      autogenerate, verify down_revision, run the extend-policy test**

```python
# backend/app/models/approval_request.py
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class ApprovalRequest(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "approval_requests"

    policy_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("approval_policies.id", ondelete="SET NULL"), nullable=True
    )
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True
    )
    module: Mapped[str] = mapped_column(String(50), nullable=False)
    requested_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    assigned_role: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    priority: Mapped[str] = mapped_column(String(10), nullable=False, default="NORMAL")
    amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    comment: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    decided_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

```bash
./.venv/bin/alembic revision --autogenerate -m "add approval request, extend approval policy"
# open the file, confirm down_revision matches Task 1's real merged head
./.venv/bin/alembic upgrade head
./.venv/bin/pytest tests/test_approvals.py -v
```

Expected: PASS.

- [ ] **Step 6: Write the failing SoD test**

```python
# backend/tests/test_approvals.py — top of file
import uuid

import pytest
from sqlalchemy import select

from app.domain.errors import InvalidApprovalStateError, SegregationOfDutiesError
from app.models.approval_policy import ApprovalPolicy
from app.models.user import User
from app.services import approval_service
from tests.conftest import BOOTSTRAP_ADMIN_EMAIL
from tests.helpers import create_company, login_admin


def _get_admin_user(db_session) -> User:
    return db_session.execute(select(User).where(User.email == BOOTSTRAP_ADMIN_EMAIL)).scalar_one()


def test_requester_cannot_decide_their_own_approval_request(client, db_session):
    login_admin(client)
    company = create_company(client)
    admin_user = _get_admin_user(db_session)

    request = approval_service.create_request(
        db_session,
        policy_id=None,
        entity_type="test.entity",
        entity_id=uuid.uuid4(),
        company_id=uuid.UUID(company["id"]),
        requested_by=admin_user.id,
        module="test",
    )
    db_session.commit()

    with pytest.raises(SegregationOfDutiesError):
        approval_service.decide(
            db_session,
            request_id=request.id,
            decided_by=admin_user.id,
            decision="APPROVED",
        )
```

`_get_admin_user` and the shared imports at the top of the file are
reused by every test below in this task — do not redeclare them per
test.

- [ ] **Step 7: Run it, confirm it fails**

Run: `./.venv/bin/pytest tests/test_approvals.py -v`
Expected: FAIL — `ImportError` (`SegregationOfDutiesError`/
`approval_service` don't exist yet) or `AttributeError`.

- [ ] **Step 8: Add the error class and implement `approval_service`**

```python
# backend/app/domain/errors.py — add near the other Track G-owned errors
class SegregationOfDutiesError(Exception):
    """INV-WORKFLOW-001: requested_by == decided_by, or the configured
    third role wasn't distinct from both, on an ApprovalRequest decide."""


class InvalidApprovalStateError(Exception):
    """Deciding an ApprovalRequest that isn't PENDING (double-decision)."""
```

Register both in `error_handlers.py`'s `_ERROR_CODES` (additive,
alongside the existing entries):
`SegregationOfDutiesError: ("NXR-WORKFLOW-001", 422)`,
`InvalidApprovalStateError: ("NXR-WORKFLOW-002", 409)`. Add the two
imports to `error_handlers.py`'s import block.

```python
# backend/app/services/approval_service.py
import uuid
from decimal import Decimal

from sqlalchemy.orm import Session

from app.domain.errors import InvalidApprovalStateError, SegregationOfDutiesError
from app.models.approval_policy import ApprovalPolicy
from app.models.approval_request import ApprovalRequest
from app.repositories import approval_repository

# Per-module decision adapters: entity_type -> callable(db, entity_id, decision) -> None.
# Registered explicitly here rather than via a dynamic plugin mechanism —
# matches this codebase's preference for explicit over magic.
_DECISION_ADAPTERS: dict[str, "callable"] = {}


def register_decision_adapter(entity_type: str, adapter) -> None:
    _DECISION_ADAPTERS[entity_type] = adapter


def create_request(
    db: Session,
    *,
    policy_id: uuid.UUID | None,
    entity_type: str,
    entity_id: uuid.UUID,
    company_id: uuid.UUID,
    requested_by: uuid.UUID,
    module: str,
    assigned_to: uuid.UUID | None = None,
    assigned_role: str | None = None,
    priority: str = "NORMAL",
    amount: Decimal | None = None,
    project_id: uuid.UUID | None = None,
) -> ApprovalRequest:
    return approval_repository.create(
        db,
        policy_id=policy_id,
        entity_type=entity_type,
        entity_id=entity_id,
        company_id=company_id,
        project_id=project_id,
        module=module,
        requested_by=requested_by,
        assigned_to=assigned_to,
        assigned_role=assigned_role,
        priority=priority,
        amount=amount,
        status="PENDING",
    )


def decide(
    db: Session,
    *,
    request_id: uuid.UUID,
    decided_by: uuid.UUID,
    decision: str,
    comment: str | None = None,
    executed_by: uuid.UUID | None = None,
) -> ApprovalRequest:
    request = approval_repository.get_for_update(db, request_id=request_id)
    if request.status != "PENDING":
        raise InvalidApprovalStateError(
            f"ApprovalRequest {request_id} ya fue decidido (estado: {request.status})"
        )
    if request.requested_by == decided_by:
        raise SegregationOfDutiesError(
            "El solicitante no puede decidir su propia solicitud de aprobación"
        )
    policy = db.get(ApprovalPolicy, request.policy_id) if request.policy_id else None
    if policy is not None and policy.requires_third_role:
        if executed_by is not None and executed_by in (request.requested_by, decided_by):
            raise SegregationOfDutiesError(
                "Esta política exige un tercer rol distinto de solicitante y aprobador"
            )

    request.status = decision
    request.decided_by = decided_by
    request.comment = comment
    from datetime import datetime, timezone

    request.decided_at = datetime.now(timezone.utc)

    adapter = _DECISION_ADAPTERS.get(request.entity_type)
    if adapter is not None:
        adapter(db, request.entity_id, decision)

    db.flush()
    return request
```

```python
# backend/app/repositories/approval_repository.py
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.approval_request import ApprovalRequest


def create(db: Session, **kwargs) -> ApprovalRequest:
    row = ApprovalRequest(**kwargs)
    db.add(row)
    db.flush()
    return row


def get_for_update(db: Session, *, request_id: uuid.UUID) -> ApprovalRequest:
    row = db.execute(
        select(ApprovalRequest).where(ApprovalRequest.id == request_id).with_for_update()
    ).scalar_one_or_none()
    if row is None:
        raise ValueError(f"ApprovalRequest {request_id} no existe")
    return row


def list_assigned_to(
    db: Session, *, user_id: uuid.UUID, company_id: uuid.UUID, module: str | None = None
) -> list[ApprovalRequest]:
    stmt = select(ApprovalRequest).where(
        ApprovalRequest.assigned_to == user_id,
        ApprovalRequest.company_id == company_id,
        ApprovalRequest.status == "PENDING",
    )
    if module is not None:
        stmt = stmt.where(ApprovalRequest.module == module)
    return list(db.execute(stmt).scalars())
```

- [ ] **Step 9: Run the SoD test, confirm GREEN**

Run: `./.venv/bin/pytest tests/test_approvals.py -v`
Expected: PASS

- [ ] **Step 10: Write and pass the double-decision and third-role tests**

```python
# backend/tests/test_approvals.py — add
def test_deciding_an_already_decided_request_is_rejected(client, db_session):
    login_admin(client)
    company = create_company(client)
    admin_user = _get_admin_user(db_session)
    from tests.helpers import create_user_with_role

    approver = create_user_with_role(
        db_session, email="approver-g1@nexora.group", role_name="Finance Manager"
    )
    from app.models.permission import UserCompanyAccess

    db_session.add(UserCompanyAccess(user_id=approver.id, company_id=uuid.UUID(company["id"])))
    db_session.commit()

    request = approval_service.create_request(
        db_session,
        policy_id=None,
        entity_type="test.entity",
        entity_id=uuid.uuid4(),
        company_id=uuid.UUID(company["id"]),
        requested_by=admin_user.id,
        module="test",
    )
    db_session.commit()

    approval_service.decide(
        db_session, request_id=request.id, decided_by=approver.id, decision="APPROVED"
    )
    db_session.commit()

    with pytest.raises(InvalidApprovalStateError):
        approval_service.decide(
            db_session, request_id=request.id, decided_by=approver.id, decision="APPROVED"
        )


def test_third_role_required_rejects_executor_matching_requester_or_approver(client, db_session):
    login_admin(client)
    company = create_company(client)
    admin_user = _get_admin_user(db_session)
    from tests.helpers import create_user_with_role

    approver = create_user_with_role(
        db_session, email="approver-g2@nexora.group", role_name="Finance Manager"
    )
    executor = create_user_with_role(
        db_session, email="executor-g2@nexora.group", role_name="Finance Manager"
    )
    db_session.commit()

    policy = ApprovalPolicy(
        company_id=uuid.UUID(company["id"]),
        name="Three-role payment policy",
        entity_type="test.entity",
        requires_third_role=True,
    )
    db_session.add(policy)
    db_session.commit()
    db_session.refresh(policy)

    request = approval_service.create_request(
        db_session,
        policy_id=policy.id,
        entity_type="test.entity",
        entity_id=uuid.uuid4(),
        company_id=uuid.UUID(company["id"]),
        requested_by=admin_user.id,
        module="test",
    )
    db_session.commit()

    with pytest.raises(SegregationOfDutiesError):
        approval_service.decide(
            db_session,
            request_id=request.id,
            decided_by=approver.id,
            decision="APPROVED",
            executed_by=admin_user.id,
        )

    request2 = approval_service.create_request(
        db_session,
        policy_id=policy.id,
        entity_type="test.entity",
        entity_id=uuid.uuid4(),
        company_id=uuid.UUID(company["id"]),
        requested_by=admin_user.id,
        module="test",
    )
    db_session.commit()

    result = approval_service.decide(
        db_session,
        request_id=request2.id,
        decided_by=approver.id,
        decision="APPROVED",
        executed_by=executor.id,
    )
    assert result.status == "APPROVED"
```

Run RED (before `InvalidApprovalStateError`/the third-role check exist
in `approval_service.decide`) then GREEN after Step 8's implementation.

- [ ] **Step 11: Wire the AP and Submittal decision adapters**

```python
# backend/app/services/ap_service.py — add this new function, does not
# touch approve_supplier_invoice's existing signature or behavior
def apply_approval_decision(db: Session, *, invoice_id: uuid.UUID, decision: str) -> None:
    if decision == "APPROVED":
        approve_supplier_invoice(db, invoice_id=invoice_id)
    elif decision == "REJECTED":
        cancel_supplier_invoice(db, invoice_id=invoice_id)
```

Read `submittal_service.py` first for its real existing
approve/reject function names (Task 4 of the prior plan built
`Submittal` with a two-step SUBMITTED→UNDER_REVIEW→APPROVED/REJECTED
flow — use its actual function names, not invented ones) and write the
equivalent `apply_approval_decision(db, *, submittal_id, decision)`
there.

Register both adapters where the FastAPI app starts up — add to
`main.py`'s `create_app()`, after `register_error_handlers(app)`:

```python
    from app.services import approval_service, ap_service, submittal_service

    approval_service.register_decision_adapter(
        "ap.supplier_invoice", lambda db, entity_id, decision: ap_service.apply_approval_decision(
            db, invoice_id=entity_id, decision=decision
        )
    )
    approval_service.register_decision_adapter(
        "construction.submittal",
        lambda db, entity_id, decision: submittal_service.apply_approval_decision(
            db, submittal_id=entity_id, decision=decision
        ),
    )
```

- [ ] **Step 12: Write a failing end-to-end adapter test, then confirm
      it passes**

```python
# backend/tests/test_approvals.py — add
def test_deciding_ap_approval_request_transitions_the_real_invoice(client, db_session):
    from app.models.ap import SupplierInvoice
    from tests.helpers import create_user_with_role
    from tests.test_ap_ar import _setup_ap  # reuse the existing fixture-builder

    login_admin(client)
    company, _bank, expense, payable, supplier = _setup_ap(client)
    admin_user = _get_admin_user(db_session)
    invoice = client.post(
        "/api/ap/supplier-invoices",
        json={
            "companyId": company["id"],
            "supplierId": supplier["id"],
            "invoiceNumber": "A-APR-1",
            "scope": "GENERAL",
            "expenseAccountId": expense["id"],
            "payableAccountId": payable["id"],
            "currencyCode": "HNL",
            "amount": "100.00",
            "invoiceDate": "2026-01-10",
            "dueDate": "2026-02-10",
        },
    ).json()

    approver = create_user_with_role(
        db_session, email="approver-g3@nexora.group", role_name="Finance Manager"
    )
    from app.models.permission import UserCompanyAccess

    db_session.add(UserCompanyAccess(user_id=approver.id, company_id=uuid.UUID(company["id"])))
    db_session.commit()

    request = approval_service.create_request(
        db_session,
        policy_id=None,
        entity_type="ap.supplier_invoice",
        entity_id=uuid.UUID(invoice["id"]),
        company_id=uuid.UUID(company["id"]),
        requested_by=admin_user.id,
        module="ap",
    )
    db_session.commit()

    approval_service.decide(
        db_session, request_id=request.id, decided_by=approver.id, decision="APPROVED"
    )
    db_session.commit()

    refreshed = db_session.get(SupplierInvoice, uuid.UUID(invoice["id"]))
    assert refreshed.status == "APPROVED"
```

If `_setup_ap` isn't importable directly from `tests.test_ap_ar` (check
whether it's prefixed with an underscore in a way pytest's import
machinery handles fine — it should, since it's a plain module-level
function, not a fixture), inline the same four lines of setup
(company/bank/expense/payable account creation) that `_setup_ap`
performs instead — read its real body in `test_ap_ar.py` first rather
than guessing its return shape.

- [ ] **Step 13: Build the Approval Inbox API**

```python
# backend/app/api/routes/approvals.py
import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.deps_correlation import get_correlation_id
from app.repositories import approval_repository
from app.schemas.approval import ApprovalRequestResponse
from app.services import approval_service, audit_service
from app.services.permission_service import assert_company_access, require_permission

router = APIRouter(prefix="/approvals", tags=["approvals"])


class ApprovalDecisionRequest(BaseModel):
    decision: str
    comment: str | None = None


@router.get("", response_model=list[ApprovalRequestResponse])
def list_my_approvals(
    company_id: uuid.UUID,
    module: str | None = None,
    db: Session = Depends(get_db),
    user=Depends(require_permission("workflow.approval", "read")),
) -> list[ApprovalRequestResponse]:
    assert_company_access(
        db, user_id=user.id, resource="workflow.approval", action="read", company_id=company_id
    )
    rows = approval_repository.list_assigned_to(
        db, user_id=user.id, company_id=company_id, module=module
    )
    return [ApprovalRequestResponse.model_validate(r, from_attributes=True) for r in rows]


@router.post("/{request_id}/decide", response_model=ApprovalRequestResponse)
def decide_approval(
    request_id: uuid.UUID,
    body: ApprovalDecisionRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("workflow.approval", "decide")),
    correlation_id: str = Depends(get_correlation_id),
) -> ApprovalRequestResponse:
    existing = approval_repository.get_for_update(db, request_id=request_id)
    assert_company_access(
        db,
        user_id=user.id,
        resource="workflow.approval",
        action="decide",
        company_id=existing.company_id,
    )
    before_status = existing.status
    updated = approval_service.decide(
        db, request_id=request_id, decided_by=user.id, decision=body.decision, comment=body.comment
    )
    audit_service.record(
        db,
        actor_user_id=user.id,
        action="workflow.approval.decide",
        entity_type="workflow.approval_request",
        entity_id=updated.id,
        company_id=updated.company_id,
        project_id=updated.project_id,
        before={"status": before_status},
        after={"status": updated.status},
        correlation_id=correlation_id,
    )
    db.commit()
    return ApprovalRequestResponse.model_validate(updated, from_attributes=True)
```

Write `backend/app/schemas/approval.py`'s `ApprovalRequestResponse`
following the exact field-naming pattern of Task 1's
`schemas/audit.py::AuditLogResponse` (same `CamelModel` base, same
`from_attributes=True` config) — one field per `ApprovalRequest` column.

Register the router (`approvals.router`, prefix `/api`), export
`ApprovalRequest` from `models/__init__.py`, add permission grants
(`workflow.approval` read/decide) to Administrator/Project
Manager/Finance Manager per the same style as prior grants — check
which roles should plausibly decide AP/Submittal approvals and grant
`decide` only to those, `read` more broadly.

- [ ] **Step 14: Write the company-isolation and read-vs-decide
      permission tests, run RED/GREEN**

Follow Step 15's pattern from Task 1 (`test_company_access_blocks_
cross_company_audit_log`) adapted to `/api/approvals`.

- [ ] **Step 15: Build the frontend `ApprovalInboxPage`**

Follow `frontend/src/features/documents/DocumentsPage.tsx`'s structure
again: `useActiveCompany()`, TanStack Query list + a decide mutation
(approve/reject buttons, optional comment field), filters by
module/priority. `frontend/src/types/approval.ts` and
`frontend/src/services/approvalService.ts` mirror Task 1's
`audit.ts`/`auditService.ts` shape. Register `/plataforma/aprobaciones`
in `routes.tsx`/`navigation.ts`.

- [ ] **Step 16: Write a frontend test proving decide() calls the real
      API and refetches**

Follow `TimeEntriesPage.test.tsx`'s approve-flow test pattern (from the
prior plan's Task 2) — mock the API response shaped like the real
schema, click a real "Aprobar" button, assert the row's status updates
after the mocked response.

- [ ] **Step 17: Run full gates, update docs, commit**

```bash
./.venv/bin/pytest -q
./.venv/bin/alembic heads
cd ../frontend
npm run typecheck && npm run lint && npm test -- --run && npm run build
```

Update `docs/PROGRESS.md`/`docs/REQUIREMENTS_TRACEABILITY.md` for
NXR-REQ-0087 (Workflow engine — note explicitly this is the
cross-cutting-services scope, not a generic state machine, per the
spec's Ruling), 0088 (Approval Inbox), 0089 (Segregation of Duties).

### Task 3: Notifications (NXR-REQ-0092, financial/project alert wiring)

**Files:**
- Create: `backend/app/models/notification.py` (`Notification`)
- Create: `backend/alembic/versions/<rev>_add_notification.py` —
  down_revision is Task 2's real merged head
- Create: `backend/app/repositories/notification_repository.py`
- Create: `backend/app/services/notification_service.py`
- Create: `backend/app/api/routes/notifications.py`
- Modify: `backend/app/api/routes/approvals.py` — call
  `notification_service.notify(...)` after `create_request`/`decide`
  succeed (find where `ApprovalRequest` creation actually happens — if
  Task 2 only exposed `decide` via API and requests are created
  server-side by domains, add the notification call at each domain's
  request-creation call site instead; verify against Task 2's actual
  shipped code, don't assume)
- Modify: `backend/app/main.py`, `backend/app/models/__init__.py`,
  `backend/app/repositories/permission_repository.py`
- Test: `backend/tests/test_notifications.py`
- Create: `frontend/src/components/NotificationBell.tsx`,
  `frontend/src/services/notificationService.ts`,
  `frontend/src/types/notification.ts`
- Modify: `frontend/src/layouts/AppLayout.tsx` (mount the bell)

**Interfaces:**
- Consumes: Task 2's `approval_service.create_request`/`decide` call
  sites (this task's only integration point).
- Produces: `notification_service.notify(db, *, recipient_user_id:
  uuid.UUID, type: str, title: str, body: str, entity_type: str | None
  = None, entity_id: uuid.UUID | None = None) -> Notification`.

- [ ] **Step 1: Merge latest `feat/nexora-greenfield`, confirm real
      Alembic head**

- [ ] **Step 2: Write the failing model test**

```python
# backend/tests/test_notifications.py
import uuid

from app.models.notification import Notification
from tests.helpers import create_company, login_admin


def test_notification_starts_unread_and_can_be_marked_read(client, db_session):
    login_admin(client)

    from app.services import notification_service

    note = notification_service.notify(
        db_session,
        recipient_user_id=uuid.uuid4(),
        type="approval.assigned",
        title="Nueva aprobación pendiente",
        body="Tienes una factura de proveedor esperando tu aprobación",
    )
    db_session.commit()
    assert note.read_at is None

    from app.services import notification_service as ns
    ns.mark_read(db_session, notification_id=note.id)
    db_session.commit()
    db_session.refresh(note)
    assert note.read_at is not None
```

- [ ] **Step 3: Run it, confirm it fails**

Run: `./.venv/bin/pytest tests/test_notifications.py -v`
Expected: FAIL — module not found.

- [ ] **Step 4: Build the model, repository, service; run
      autogenerate; confirm the test passes**

```python
# backend/app/models/notification.py
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Notification(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "notifications"

    recipient_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(String(1000), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

```python
# backend/app/repositories/notification_repository.py
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.notification import Notification


def create(db: Session, **kwargs) -> Notification:
    row = Notification(**kwargs)
    db.add(row)
    db.flush()
    return row


def get(db: Session, *, notification_id: uuid.UUID) -> Notification:
    row = db.get(Notification, notification_id)
    if row is None:
        raise ValueError(f"Notification {notification_id} no existe")
    return row


def list_for_user(
    db: Session, *, user_id: uuid.UUID, unread_only: bool = False
) -> list[Notification]:
    stmt = select(Notification).where(Notification.recipient_user_id == user_id)
    if unread_only:
        stmt = stmt.where(Notification.read_at.is_(None))
    stmt = stmt.order_by(Notification.created_at.desc())
    return list(db.execute(stmt).scalars())


def mark_read(db: Session, *, notification_id: uuid.UUID) -> Notification:
    row = get(db, notification_id=notification_id)
    row.read_at = datetime.now(timezone.utc)
    db.flush()
    return row
```

```python
# backend/app/services/notification_service.py
import uuid

from sqlalchemy.orm import Session

from app.models.notification import Notification
from app.repositories import notification_repository


def notify(
    db: Session,
    *,
    recipient_user_id: uuid.UUID,
    type: str,
    title: str,
    body: str,
    entity_type: str | None = None,
    entity_id: uuid.UUID | None = None,
) -> Notification:
    return notification_repository.create(
        db,
        recipient_user_id=recipient_user_id,
        type=type,
        title=title,
        body=body,
        entity_type=entity_type,
        entity_id=entity_id,
    )


def mark_read(db: Session, *, notification_id: uuid.UUID) -> Notification:
    return notification_repository.mark_read(db, notification_id=notification_id)
```

```bash
./.venv/bin/alembic revision --autogenerate -m "add notification"
# verify down_revision, then:
./.venv/bin/alembic upgrade head
./.venv/bin/pytest tests/test_notifications.py -v
```

Expected: PASS.

- [ ] **Step 5: Wire notification creation into the real Approval
      Inbox call sites (read Task 2's shipped `approvals.py` and
      wherever `ApprovalRequest` rows are actually created — likely
      inside each domain service or a thin wrapper — and add exactly
      those two calls: on request creation, notify `assigned_to`; on
      `decide`, notify `requested_by`)**

Write the failing test first:

```python
# backend/tests/test_notifications.py — top of file additions
import uuid

from sqlalchemy import select

from app.models.notification import Notification
from app.models.permission import UserCompanyAccess
from app.models.user import User
from app.services import approval_service
from tests.conftest import BOOTSTRAP_ADMIN_EMAIL
from tests.helpers import create_company, create_user_with_role, login_admin


def _get_admin_user(db_session) -> User:
    return db_session.execute(select(User).where(User.email == BOOTSTRAP_ADMIN_EMAIL)).scalar_one()


def test_deciding_an_approval_request_notifies_the_requester(client, db_session):
    login_admin(client)
    company = create_company(client)
    admin_user = _get_admin_user(db_session)
    approver = create_user_with_role(
        db_session, email="approver-notify@nexora.group", role_name="Finance Manager"
    )
    db_session.add(UserCompanyAccess(user_id=approver.id, company_id=uuid.UUID(company["id"])))
    db_session.commit()

    request = approval_service.create_request(
        db_session,
        policy_id=None,
        entity_type="test.entity",
        entity_id=uuid.uuid4(),
        company_id=uuid.UUID(company["id"]),
        requested_by=admin_user.id,
        module="test",
    )
    db_session.commit()

    approval_service.decide(
        db_session, request_id=request.id, decided_by=approver.id, decision="APPROVED"
    )
    db_session.commit()

    notes = db_session.execute(
        select(Notification).where(
            Notification.recipient_user_id == admin_user.id,
            Notification.type == "approval.decided",
        )
    ).scalars().all()
    assert len(notes) == 1
```

Run it, confirm RED (no `notify()` call wired into `approval_service.decide`
yet), then implement the wiring: inside `approval_service.decide` (in
`backend/app/services/approval_service.py`, from Task 2) or at the
`/approvals/{id}/decide` route (`backend/app/api/routes/approvals.py`)
— whichever call site actually has access to both the decided request
and a live `db` session without a circular import between
`approval_service` and `notification_service` (check for that risk
first: `notification_service` should not need to import
`approval_service`, so the wiring belongs in `approval_service.decide`
or the route, not the other direction) — call
`notification_service.notify(db, recipient_user_id=updated.requested_by,
type="approval.decided", title=..., body=..., entity_type=
updated.entity_type, entity_id=updated.entity_id)` after a successful
decision. Then confirm GREEN.

- [ ] **Step 6: Build the Notifications API**

```python
# backend/app/api/routes/notifications.py
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.repositories import notification_repository
from app.schemas.notification import NotificationResponse

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationResponse])
def list_my_notifications(
    unread_only: bool = False,
    db: Session = Depends(get_db),
    current=Depends(get_current_user),
) -> list[NotificationResponse]:
    user, _roles = current
    rows = notification_repository.list_for_user(db, user_id=user.id, unread_only=unread_only)
    return [NotificationResponse.model_validate(r, from_attributes=True) for r in rows]


@router.post("/{notification_id}/read", response_model=NotificationResponse)
def mark_notification_read(
    notification_id: uuid.UUID,
    db: Session = Depends(get_db),
    current=Depends(get_current_user),
) -> NotificationResponse:
    user, _roles = current
    row = notification_repository.get(db, notification_id=notification_id)
    if row.recipient_user_id != user.id:
        from app.domain.errors import NotAuthorizedError

        raise NotAuthorizedError("No puede marcar como leída una notificación de otro usuario")
    updated = notification_repository.mark_read(db, notification_id=notification_id)
    db.commit()
    return NotificationResponse.model_validate(updated, from_attributes=True)
```

No `assert_company_access` here deliberately — a `Notification` is
scoped to its `recipient_user_id`, not a company, so ownership is
checked directly against the current user. Write
`backend/app/schemas/notification.py::NotificationResponse` following
the same `CamelModel` pattern as the two prior schemas this task built
on.

- [ ] **Step 7: Write and pass the per-user isolation test**

```python
# backend/tests/test_notifications.py — add
def test_user_cannot_mark_another_users_notification_as_read(client, db_session):
    from app.services import notification_service
    from tests.helpers import login_as

    login_admin(client)
    company = create_company(client)
    admin_user = _get_admin_user(db_session)
    other = create_user_with_role(
        db_session, email="other-notify@nexora.group", role_name="Finance Manager"
    )
    db_session.add(UserCompanyAccess(user_id=other.id, company_id=uuid.UUID(company["id"])))
    db_session.commit()

    note = notification_service.notify(
        db_session,
        recipient_user_id=admin_user.id,
        type="approval.assigned",
        title="Test",
        body="Test body",
    )
    db_session.commit()

    login_as(client, email="other-notify@nexora.group")
    response = client.post(f"/api/notifications/{note.id}/read")

    assert response.status_code == 403, response.text
    assert response.json()["error"]["code"] == "NXR-PERM-001"
```

Run RED (before the ownership check exists in the route) then GREEN
after Step 6's implementation.

- [ ] **Step 8: Build the frontend `NotificationBell` and wire it into
      `AppLayout`**

Read `frontend/src/layouts/AppLayout.tsx` first to find the topbar/
header structure and where an icon-button component would naturally
mount (look for how other topbar icons, e.g. the search/command-palette
trigger, are wired). Poll `GET /api/notifications?unreadOnly=true`
every N seconds via TanStack Query's `refetchInterval` (reuse whatever
polling convention, if any, already exists elsewhere in the codebase —
check before inventing one; if none exists, a `refetchInterval: 30000`
is a reasonable default) for the unread count badge; clicking opens a
dropdown listing recent notifications with a mark-read action per item.

- [ ] **Step 9: Write a frontend test for the bell's unread count and
      mark-read flow**

Follow the same mock-fetch-and-assert-real-DOM-update pattern as every
other frontend test this session's plans wrote.

- [ ] **Step 10: Run full gates, update docs, commit**

```bash
./.venv/bin/pytest -q
./.venv/bin/alembic heads
cd ../frontend
npm run typecheck && npm run lint && npm test -- --run && npm run build
```

Update `docs/PROGRESS.md`/`docs/REQUIREMENTS_TRACEABILITY.md` for
NXR-REQ-0092. NXR-REQ-0093-0096 (the specific financial/project alert
triggers named in the brief, e.g. budget threshold exceeded, AP invoice
overdue) are explicitly out of this task's minimal scope unless time
allows — if skipped, mark them `NOT_STARTED` honestly with a one-line
note of what's needed (which existing domain read path each alert
would reuse), not silently implied done by NXR-REQ-0092 being
`IMPLEMENTED`.

### Task 4: Combined verification and traceability recount

**Files:**
- Verify: all files touched by Tasks 1-3 once integrated on
  `feat/nexora-greenfield`
- Modify only if evidence warrants it: `docs/PROGRESS.md`,
  `docs/REQUIREMENTS_TRACEABILITY.md`, `docs/DEFERRED.md`

**Interfaces:**
- Consumes: the fully integrated Audit/Approval-Inbox/Notifications
  system.
- Produces: one reproducible integration head and an honest
  traceability update for NXR-REQ-0087 through 0096.

- [ ] **Step 1: Verify Git topology and exact modified file set**

```bash
git status
git log --graph --decorate --oneline -30
git diff --check
git diff --stat origin/feat/nexora-greenfield...HEAD
```

- [ ] **Step 2: Verify one Alembic head, upgrade path, fresh-install
      path**

```bash
./.venv/bin/alembic heads
./.venv/bin/alembic upgrade head   # on a fresh disposable database, then drop it
```

- [ ] **Step 3: Run complete backend/frontend verification from the
      integration worktree**

```bash
./.venv/bin/pytest -q
./.venv/bin/python -m compileall -q app tests
npm run typecheck && npm run lint && npm test -- --run && npm run build
```

- [ ] **Step 4: Recount `docs/REQUIREMENTS_TRACEABILITY.md` row-by-row
      against its own summary (same method used twice already this
      session: `grep -oP` the real per-row status, compare to the
      prose tally, fix any discrepancy, rewrite the summary honestly).
      Update `docs/DEFERRED.md` — resolve `DEFERRED-FINAL-014` if the
      audit rollout genuinely covers what it claims; if only partially
      instrumented, correct the wording rather than closing it
      prematurely. Continue with the highest-dependency-free next
      slice from `docs/MASTER_PLAN.md` (Reports/Search/Analytics is the
      user's named Priority 4) rather than inflating completion.**
