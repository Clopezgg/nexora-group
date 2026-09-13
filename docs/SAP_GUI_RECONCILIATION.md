# SAP workstation reconciliation

Base inspected: `774a8985c25a0f117e69de7ad70ac726396e2a74` (origin/main).
Source PR #135: `origin/fix/nexora-final-certification-closure`, inspected by
three-dot diff; no merge or bulk cherry-pick of its backend history.

| Source change | Classification | Resolution |
|---|---|---|
| SapWorkstation and eight shell components, typed ThemeAnatomy, JPL mapping | ALREADY_IN_MAIN | Extend existing composition |
| AppLayout.css contiguous bars, mobile wrapping, popup layers | VALID_SAP_UNIQUE | Ported, retain scoped presentation |
| themes.css metrics, density, responsive records and dark fixes | VALID_SAP_UNIQUE | Ported, reconciled against original JPL |
| Signature legend-style card title in that CSS | WRONG | JPL has a 25px band; replaced with measured band |
| Rounded folder tabs without diagonal shoulder | SUPERSEDED | Reconstructed diagonal shoulder from JPL geometry |
| ThemeProvider authoritative save response/cache ordering | VALID_SAP_UNIQUE | Ported; preserves a newer in-flight preview |
| ThemeSettingsCard family/variant transition | VALID_SAP_UNIQUE | Ported to avoid stale variant during family transition |
| CompanySettingsPage enterprise/financial setup changes | CONFLICTING | Excluded: not a presentation-only SAP slice |
| SAP theme/visual tests, critical browsers, browser projects | TEST_ONLY | Ported and strengthened; full default coverage retained |
| Other backend, finance, migrations and workflow changes in #135 | Out of scope | No port |

## Implementation constraints

Measurements and unsupported reference states are recorded in
[SAP_GUI_REFERENCE_MEASUREMENTS.md](SAP_GUI_REFERENCE_MEASUREMENTS.md).
The user's 28–30px desktop and 40px mobile field targets supersede the JPL's
18px original fields. Grids, keyboard interaction and Horizon variants use
Nexora's existing typed anatomy contract because this JPL cannot establish
those measurements. No proprietary images are bundled.

Canonical acceptance scenes: General Ledger (`/finanzas/contabilidad`),
Project Cockpit (`/proyectos/cockpit`), Inventory (`/abastecimiento/inventario`).
The test database is isolated and populated through real APIs. Financial test
records never enter production. Acceptance requires opening all 36 primary
images, not just recording a Playwright pass.
