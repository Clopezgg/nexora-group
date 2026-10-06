# NEXORA GROUP — Phase 0 System Baseline

**Date:** 2026-10-05  
**Baseline branch:** `main`  
**Baseline SHA:** `2ca980446654f3c92e3ddb1e8f55d847ef073968`

## Purpose

Phase 0 is the diagnostic and freeze gate before transactional reconstruction. It does not promote historical claims to verified status and it does not permit new product features to bypass the canonical transaction model.

## Canonical source of truth

- Production branch: `main`.
- Current baseline is the remote `main` SHA recorded above.
- Historical branches and historical certification text are evidence only.
- A capability is not considered verified merely because it is implemented or because a historical CI run was green.

## Current repository findings

1. `main` is protected, but the branch metadata currently reports required status-check enforcement as `off`. Phase 0 therefore treats merge-gate enforcement as an unresolved governance issue rather than assuming protection is sufficient.
2. The repository contains multiple non-main branches. They must be reconciled by comparing their unique commits with `main` before any deletion is considered. Phase 0 does not delete branches blindly.
3. PR #154 (`birthday-invitation-2026`) is unrelated to the NEXORA ERP product boundary. It is not part of the ERP release stream and must not be merged into `main`.
4. `docs/REQUIREMENTS_TRACEABILITY.md` still contains historical overlays and an implementation-heavy status model. Phase 0 freezes the rule that `IMPLEMENTED` and `VERIFIED` are different states; no requirement is promoted without current evidence.
5. `docs/DEFERRED.md` correctly distinguishes a zero known functional backlog from release certification. This distinction is retained.
6. `docs/PRODUCTION_READINESS.md` contains historical certification chronology. It must not be treated as proof for the current `main` SHA unless the exact SHA, CI, deployment and production evidence match.
7. `docs/AGENT_HANDOFF.md` contains the correct architectural invariants and release-gate principles, but its historical PR #112 closeout section is not evidence for the current baseline. Current work must use the SHA above as authority.
8. The inventory documentation explicitly acknowledges that inventory project issues record project actuals but leave the actual accounting posting to the accounting track. This is a critical integration seam to be audited in Phase 1+ rather than assumed to be end-to-end.

## Phase 0 freeze rules

Until the transactional correction phases are completed:

- Do not add unrelated features to the ERP release branch.
- Do not declare `100%`, `production ready`, or `VERIFIED` from documentation alone.
- Do not create parallel financial posting engines.
- Do not invent financial master data, FX rules, evidence, accounts or ownership semantics.
- Preserve fail-closed behavior where business policy is undefined.
- Treat Project, Treasury, Accounting, Inventory, Procurement, AP/AR and Contract flows as one connected transaction system.
- Every later correction must be validated against the same canonical baseline and then against the resulting branch state.

## Phase 0 exit criteria

Phase 0 is considered complete only when the baseline is explicitly recorded, the release boundary is frozen, unrelated work is excluded from the ERP release stream, and the following phases can begin from a known SHA without relying on historical claims.

The next phase must begin with the transactional/domain model and authoritative relationships, not with new UI features.
