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
- `/healthz`, `/readyz`, Docker local, `render.yaml`, CI, tests mínimos.

## Próximas fases

Cada fase se define por un objetivo explícito entregado por el usuario. No se
anticipa alcance no solicitado.
