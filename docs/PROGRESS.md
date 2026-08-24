# NEXORA GROUP — Progress Log

Bitácora viva de integración. Cada entrada corresponde a un track
integrado a `feat/nexora-greenfield`, con evidencia real, nunca
aspiracional. No se reemplazan entradas anteriores, se agregan.

## Rúbrica — avance real acumulado

Bootstrap / Platform baseline: **5% / 5%** (commit `62c56eb`, verificado).

Todo lo demás: **0% acumulado formalmente** hasta que un track aterrice
con evidencia (ver `docs/REQUIREMENTS_TRACEABILITY.md` para el detalle
pieza por pieza — varios requisitos están `IN_PROGRESS` pero ningún
bloque de la rúbrica se marca completo todavía).

## Entradas

### 2026-08-24 — Arranque de la ORDEN MAESTRA

- `CLAUDE.md` actualizado con los pilares, invariantes contables, rúbrica
  fija y las dos excepciones de autorización.
- `docs/MASTER_PLAN.md` creado: tracks, orden de ejecución, dependencias.
- `docs/REQUIREMENTS_TRACEABILITY.md` creado: 124 requisitos (`NXR-REQ-0001`
  a `NXR-REQ-0124`), estado inicial derivado honestamente del código ya
  existente (bootstrap + IaC Azure) — 0 `VERIFIED`, 30 `IN_PROGRESS`, 92
  `NOT_STARTED`, 2 `BLOCKED_EXTERNAL` (despliegue de producción, gated por
  `CLAUDE.md` §11.1).
- Próximo: Track 1 (Foundation: core platform, master data, identity/RBAC
  ampliado, chart of accounts, posting engine, GL, OperationScope) y
  Track F (Experience: design system ampliado, navegación empresarial)
  lanzados en paralelo.
