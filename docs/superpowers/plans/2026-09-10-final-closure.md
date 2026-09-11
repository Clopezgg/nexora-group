# NEXORA Final Closure Implementation Plan

> **For agentic workers:** Execute inline against the current `origin/main`; preserve unrelated local files.

**Goal:** Correct and verify demonstrable defects from the final-closure order without trusting historical claims.

**Architecture:** Extend the existing canonical services, reporting authority, active-company store, and append-only inventory ledger. Keep SAP as presentation over the same ERP services and do not create parallel financial authorities.

**Tech Stack:** FastAPI, SQLAlchemy, PostgreSQL, React, TypeScript, TanStack Query, Vitest, Pytest, Vite.

**Spec:** `AGENTS.md` and the user-provided final-closure order.

## Global Constraints

- Treasury remains the sole owner of real cash.
- `effective_date` governs economic reporting; `posted_at` remains technical audit time.
- Only `POSTED` and `REVERSED` documents affect effective balances.
- Active company comes from `useActiveCompany()`; no silent screen-local company fallback.
- Goods receipt and physical count operations remain atomic and append-only.

### Work units

- [x] Capture current Git/origin baseline and inspect repository authority.
- [x] Correct report date/status filtering and Treasury balance status filtering; add regression coverage.
- [x] Remove local active-company authorities from AP, AR, Treasury, and Supplier Invoice Flows.
- [x] Make goods receipt child stock writes participate in the parent transaction.
- [x] Snapshot physical-count expected quantity from the locked backend ledger and make approval single-use.
- [x] Continue the forensic audit for contract/AP/AR/procurement/assets/SAP/Azure and verify each remaining correction before closure.
- [x] Run full regression, inspect diff, update traceability, and only then determine whether GitHub/Azure operations are available and authorized.
