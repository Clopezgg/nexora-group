# E2E / Critical Journey (NXR-REQ-0112 / NXR-REQ-0113)

Real Playwright suite, driven against a real backend + real frontend +
real PostgreSQL — never mocked. Runs in its own database (`nexora_e2e`),
never the dev DB (`nexora_dev`) or the pytest DB (`nexora_test_*`), and
its own ports (backend `8010`, frontend `5175`) so it never collides with
a manually-running dev server.

## Prerequisites

- PostgreSQL running locally with a `nexora` role that can create
  databases (same role the backend/pytest already use).
- Backend virtualenv already set up (`backend/.venv`).
- `npx playwright install chromium` run once (downloads the browser
  binary — this repo does not commit it).

## Running

```bash
cd frontend
npm run test:e2e
```

`playwright.config.ts` handles everything else:

1. `webServer[0]` drops and recreates `nexora_e2e` (fresh database every
   run — this also exercises the real "fresh install" migration path),
   runs `alembic upgrade head` against the empty database (same as
   `backend/Dockerfile`'s `CMD`), then starts `uvicorn` on port 8010
   against it, with `FRONTEND_URL` set to the E2E frontend origin (so
   CORS and the CSRF Origin guard both accept it) and a real bootstrap
   admin (`admin@nexora.group` / `NexoraAdmin123!`) created on first
   boot.
2. `webServer[1]` runs `vite` on port 5175, proxying `/api` to the E2E
   backend.
3. Playwright waits for both to be ready (`/readyz` and the frontend
   root) before running any test.

The Approval Inbox step needs a real second user (INV-SOD-001 forbids a
submitter deciding their own approval) — created via the real
`POST /api/master-data/users` endpoint (DEFERRED-FINAL-015), same as any
other admin action in this journey.

## Why some steps are API calls, not clicks

Several backend capabilities are deliberately backend-only (no dedicated
screen yet) — documented as such in
`docs/REQUIREMENTS_TRACEABILITY.md` (e.g. Stock Ledger receive/issue/
transfer/return, RFQ/Quotation creation before Bid Comparison existed,
Service Entry, Three-Way Match). The Critical Journey still exercises the
real backend for those steps via `page.request` (same session cookie as
the browser context, so it's still testing real authorization/company
isolation, not a separate unauthenticated client) instead of skipping
them or inventing UI that doesn't exist.

## Debugging a failure

```bash
npx playwright show-report e2e-report
```

Traces and screenshots are captured only on failure (`retain-on-failure`,
`only-on-failure`).
