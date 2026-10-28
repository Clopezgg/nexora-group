# NEXORA GROUP — Fases 9–15: certificación técnica

Fecha: 2026-10-06
Base auditada: `main` @ `2ca980446654f3c92e3ddb1e8f55d847ef073968`

## Alcance

Este documento no inventa implementación. Las capacidades de Fases 9–14 ya existen en `main`; esta rama las somete a una nueva verificación conjunta antes de cerrar el bloque. Fase 15 exige además evidencia de infraestructura y producción real.

| Fase | Alcance | Estado de implementación | Evidencia requerida para cierre |
|---|---|---|---|
| 9 | Assets + equipment + maintenance | Implementado | backend + frontend + migraciones + E2E/invariantes |
| 10 | Construction site + quality + safety + documents | Implementado | backend + frontend + E2E de journeys críticos |
| 11 | Approvals + SoD + audit | Implementado | RBAC/SoD + audit append-only + approval workflow |
| 12 | Reports + dashboards + traceability | Implementado | reporting APIs + exports + balance/integrity checks |
| 13 | End-to-end integration | Implementado | Critical Journey sobre PostgreSQL + Azurite + frontend real |
| 14 | Security + concurrency + performance | Implementado | CI security gates + race/concurrency suites + migration/build checks |
| 15 | Production certification | Condicionado | deployment Azure del SHA certificado + production smoke |

## Reglas de cierre

1. No se considera una fase `VERIFIED` por existencia de código solamente.
2. No se rebajan gates para conseguir verde.
3. Un deployment de producción no se simula ni se declara sin evidencia real.
4. Los bloqueos externos de Azure deben permanecer explícitos hasta contar con autorización/credenciales válidas.

## Gates que deben quedar verdes

- Backend completo
- Frontend: typecheck, lint, tests y build
- E2E crítico, accessibility y visual
- Docker Compose smoke
- Alembic: exactamente un head y upgrade limpio
- Azure Bicep compile/what-if
- Security gates existentes
- PR fusionado a `main`
- Para Fase 15: deployment real, health/ready, smoke autenticado y revisión de servicios Azure

## Observación importante

La certificación de Fase 15 no se obtiene únicamente con CI. `docs/DEFERRED.md` establece expresamente que el release final requiere deployment Azure y smoke de producción. Mientras esa evidencia externa no exista, Fase 15 permanece abierta aunque los gates de código estén verdes.
