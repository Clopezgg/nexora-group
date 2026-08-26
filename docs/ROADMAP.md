# Roadmap

Ver `CLAUDE.md` en la raíz para las reglas permanentes del proyecto.

## Fase 0/1 — Bootstrap greenfield (completada)

- Monorepo `frontend/` (React + Vite + TS) y `backend/` (FastAPI + PostgreSQL).
- Auth real (login/logout/me) con Argon2id y sesiones persistidas en DB.
- Bootstrap de Administrator inicial vía variables de entorno.
- RBAC base (7 roles) sin policies completas todavía.
- App shell (Sidebar/Topbar/Content) con todas las rutas del roadmap, la
  mayoría en `EmptyState` hasta implementarse.
- Dashboard inicial calculado desde DB (sin datos ficticios).
- `ActiveUIContext` (proyecto activo en la UI), independiente de
  `OperationScope`.
- `/healthz`, `/readyz`, Docker local, CI, tests mínimos.

## Transición de infraestructura — Render → Azure (completada)

- Plataforma oficial pasó de Render a Microsoft Azure (decisión definitiva del
  usuario). `render.yaml` eliminado.
- Infraestructura como código en Bicep (`infra/`): Static Web Apps, Container
  Apps, PostgreSQL Flexible Server, Blob Storage, Key Vault, Monitor/App
  Insights/Log Analytics. Ver `infra/README.md`.
- Backend adaptado: carga de secretos desde Key Vault en producción
  (`app/integrations/azure_keyvault.py`), evidencias vía Blob Storage
  (`app/integrations/azure_blob.py`, `EVIDENCE_BACKEND=azure_blob`),
  telemetría opcional vía Application Insights.
- CI/CD: `.github/workflows/deploy-azure.yml` (OIDC, what-if en PRs, deploy
  manual/aprobado en `main`).
- Ningún recurso de Azure fue provisionado en esta fase: solo se validó con
  `az bicep build` y `az deployment sub what-if` (sin costo). El primer
  deploy real queda pendiente de que el usuario configure los secrets del
  repo y apruebe el environment `production`.
- Pendiente heredado: ver `docs/DEFERRED.md` (`DEFERRED-FINAL-DOCKER-001`).

## Próximas fases

Cada fase se define por un objetivo explícito entregado por el usuario. No se
anticipa alcance no solicitado.
