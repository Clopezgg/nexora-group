# SAP GUI Theme Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add SAP GUI Signature and Tradeshow as a fifth, presentation-only Theme Engine family that changes Nexora's global anatomy while preserving routes, permissions, data, and business behavior.

**Architecture:** Extend the existing typed `ThemePreset` with one centralized `ThemeAnatomy` record and expose the selected anatomy as DOM datasets. Reuse the existing router, permission-filtered navigation, business components, preferences cascade, and design-system DOM; add SAP-specific shell chrome and isolated CSS under `data-nx-family='sap-gui'`.

**Tech Stack:** React 19, TypeScript, Vite, CSS custom properties, React Router, Testing Library/Vitest, Playwright.

**Spec:** User-provided “NEXORA GROUP — ORDEN MAESTRA DE IMPLEMENTACIÓN / SAP GUI COMO QUINTA FAMILIA COMPLETA DEL THEME ENGINE”, validated against `~/Downloads/sap-widgets.jpl`.

## Global Constraints

- Theme changes presentation only; no financial, permission, scope, workflow, API, or persistence-contract behavior changes.
- IDs are permanently `sap-gui-signature` and `sap-gui-tradeshow`; family order ends with `sap-gui`.
- The JPL is read-only visual evidence; no SAP runtime, SAP backend, SAPUI5, rasterized application surfaces, or invented actions.
- Existing user edits in `backend/tests/conftest.py` and untracked `-a` remain untouched.
- Work stays on synchronized `main`, then is committed, pushed, CI-verified, and reconciled with `origin/main` as explicitly authorized.

---

### Task 1: Typed anatomy and SAP presets

**Files:** `frontend/src/theme/themes.ts`, `frontend/src/theme/ThemeProvider.tsx`, `frontend/tests/themeEngine.test.ts`

- [ ] Add failing tests for family order, stable SAP IDs, compact defaults, distinct Signature/Tradeshow anatomy, and compiled SAP tokens.
- [ ] Run `npm test -- themeEngine.test.ts` and confirm failures are caused by the missing family/presets.
- [ ] Add `ThemeAnatomy`, SAP family traits/presets, exported family order/labels, and compiled chrome tokens.
- [ ] Set `data-nx-anatomy` and `data-nx-sap-variant` from the active preset; remove the SAP variant dataset for non-SAP themes.
- [ ] Rerun the directed test to green.

### Task 2: Explicit entry confirmation and structural preview

**Files:** `frontend/src/features/settings/ThemeSettingsCard.tsx`, `frontend/src/features/settings/ThemeSettingsCard.css`, `frontend/tests/ThemeSettingsCard.test.tsx`

- [ ] Add failing interaction tests for family ordering, confirmation/cancel/accept, one-time entry behavior, variant switching, exit behavior, save, company default, reload, preview cancellation, and legacy families.
- [ ] Run the directed test and verify expected failures.
- [ ] Implement the design-system modal flow without mutating draft/preview before acceptance; default accepted entry to Signature and compact density.
- [ ] Render a dedicated SAP miniature with title bar, menu bar, command toolbar, permission-neutral tree, screen, tabs, table, field, button, panel/dialog sample, and status bar.
- [ ] Rerun the directed tests to green.

### Task 3: Global SAP shell anatomy

**Files:** `frontend/src/layouts/AppLayout.tsx`, `frontend/src/layouts/Topbar.tsx`, `frontend/src/layouts/Sidebar.tsx`, `frontend/src/layouts/NavList.tsx`, `frontend/src/layouts/AppLayout.css`, `frontend/tests/AppShell.test.tsx`

- [ ] Add failing shell tests proving SAP chrome is present for saved Signature/Tradeshow and absent for non-SAP themes.
- [ ] Run the directed shell tests and verify expected failures.
- [ ] Add SAP-only title/menu/command/status chrome with real current company/project/period/user/protected-edit/search/navigation/logout actions.
- [ ] Reuse `filterNavGroups` and existing `NavLink` routes; expose the desktop list as an accessible expandable tree and retain the existing responsive drawer.
- [ ] Rerun directed shell tests to green.

### Task 4: Global component anatomy and responsive adaptation

**Files:** `frontend/src/theme/themes.css`, `frontend/src/layouts/AppLayout.css`, `frontend/src/features/settings/ThemeSettingsCard.css`

- [ ] Add isolated `data-nx-family='sap-gui'` rules for page frames, headers, panels/cards, forms, buttons, tables, tabs, dialogs/drawers/popovers, badges, charts, focus, toolbars, and status chrome.
- [ ] Encode real Signature/Tradeshow differences with `data-nx-sap-variant`, not palette alone.
- [ ] Add desktop/tablet/mobile breakpoints with collapsing menubar, drawer navigation, safe table overflow, and touch-safe mobile controls.
- [ ] Run directed unit tests plus typecheck after the stylesheet integration.

### Task 5: Persistence, documentation, and route smoke

**Files:** `backend/tests/test_theme_preferences.py`, `frontend/e2e/theme-engine.spec.ts` (or the existing matching E2E file), `docs/THEME_ENGINE.md`

- [ ] Characterize the existing free-string preference contract with both SAP IDs; avoid backend production changes or migrations unless the test proves validation blocks them.
- [ ] Add stable E2E coverage for confirmation, both variants, non-SAP isolation, and representative real routes using structural assertions rather than fragile screenshots.
- [ ] Document JPL provenance, React/CSS recreation, presentation-only boundary, confirmation/persistence cascade, responsive behavior, and accessibility adaptations.
- [ ] Run directed backend and E2E tests.

### Task 6: Full verification and integration

**Files:** all changed files only

- [ ] Run the Impeccable detector once on changed UI targets and correct relevant findings.
- [ ] Run frontend typecheck, lint, full Vitest suite, production build, directed backend preference tests, E2E theme smoke, and `git diff --check`.
- [ ] Inspect `git diff`, `git status`, and confirm only intended files are staged; exclude `backend/tests/conftest.py` and `-a`.
- [ ] Commit coherently and push `main`; if direct push is rejected, create only `feat/sap-gui-theme-engine`, push one PR, repair CI, merge, and fast-forward local `main`.
- [ ] Verify GitHub CI is green and `git rev-parse HEAD` equals `git rev-parse origin/main` at the feature SHA.
