# Pendientes diferidos

Bugs o verificaciones no bloqueantes, documentados en vez de ocultados
(regla de `CLAUDE.md`: "Bugs no bloqueantes pueden diferirse, pero deben
quedar documentados"). Deben resolverse/certificarse antes de declarar el
proyecto al 100% (FINAL HARDENING).

## DEFERRED-FINAL-DOCKER-001

**Qué falta:** verificación en vivo de `docker compose up` (Postgres +
backend vía Docker Compose).

**Por qué está diferido:** Docker no estaba instalado en la máquina donde se
construyó la Fase 0/1. El flujo completo (migraciones, auth, dashboard) se
verificó igualmente end-to-end usando PostgreSQL 16 nativo (Homebrew) en vez
de Docker, así que la aplicación en sí está probada — lo que falta es
confirmar que `docker-compose.yml` y `backend/Dockerfile` funcionan tal cual
están escritos.

**Cómo certificarlo:** en una máquina con Docker instalado, ejecutar
`docker compose up` desde la raíz del repo y confirmar que:
- Postgres arranca y queda healthy.
- El backend arranca, aplica `alembic upgrade head` y responde en
  `/healthz`/`/readyz`.
- El login (`POST /api/auth/login`) funciona contra la base del contenedor.

**Estado:** pendiente. Debe resolverse en FINAL HARDENING antes del 100%.
