# Nexora Group

Plataforma administrativa greenfield de Nexora Group: tesorería, proyectos y
operaciones. Ver `CLAUDE.md` para las reglas permanentes del proyecto y
`docs/ROADMAP.md` para el estado por fases.

Stack: React + TypeScript + Vite (frontend) y FastAPI + PostgreSQL (backend).
Sin Frappe, sin ERPNext, sin código heredado.

## Estructura

```
frontend/   React + Vite + TS
backend/    FastAPI + SQLAlchemy + Alembic
docs/       Documentación y roadmap
scripts/    Scripts de desarrollo local
```

## Requisitos

- Node.js 22+
- Python 3.12+
- PostgreSQL 16 (local, vía Homebrew, o Docker)

## Desarrollo local

1. Copia `.env.example` a `backend/.env` y completa los valores (al menos
   `DATABASE_URL`; opcionalmente `BOOTSTRAP_ADMIN_EMAIL`/`BOOTSTRAP_ADMIN_PASSWORD`
   para crear el primer usuario Administrator).
2. Backend:

   ```bash
   ./scripts/dev-backend.sh
   ```

   Crea el virtualenv si no existe, instala dependencias, aplica las
   migraciones de Alembic y levanta `uvicorn` en `http://localhost:8000`.

3. Frontend (en otra terminal):

   ```bash
   ./scripts/dev-frontend.sh
   ```

   Levanta Vite en `http://localhost:5173`, con proxy de `/api` hacia el
   backend.

### Con Docker

```bash
docker compose up
```

Levanta PostgreSQL y el backend (aplica migraciones automáticamente al
arrancar). El frontend se sigue ejecutando con Vite localmente.

## Verificación

Backend:

```bash
cd backend && source .venv/bin/activate
pytest -q
```

Frontend:

```bash
cd frontend
npm run typecheck && npm run lint && npm run test && npm run build
```

## Deploy

`render.yaml` define un Web Service (backend, Docker) y un Static Site
(frontend) sobre el plan Free de Render, más una base PostgreSQL gestionada.
Tras el primer deploy, completa manualmente en el dashboard de Render:

- `FRONTEND_URL` en el servicio backend (para CORS).
- `VITE_API_BASE_URL` en el sitio estático (URL pública del backend + `/api`),
  y vuelve a disparar un build del frontend.
- `BOOTSTRAP_ADMIN_EMAIL` / `BOOTSTRAP_ADMIN_PASSWORD` en el backend, para el
  primer login de Administrator.
