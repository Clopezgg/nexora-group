# Integration Architecture — extension surface real (NXR-REQ-0096)

Cierra `NXR-REQ-0096` (bloque PLATFORM, `docs/MASTER_PLAN.md`). Este
documento **no diseña** adaptadores nuevos (SAP, un agente de IA, un
webhook receiver, etc.) — registra, con evidencia contra el código real,
qué superficie de extensión existe hoy en NEXORA para que un sistema
externo se integre, y nombra honestamente lo que todavía no existe. Ver
`docs/superpowers/specs/2026-08-25-reports-search-analytics-design.md`
para el scope ruling que define este task como documentación, no código.
En `docs/REQUIREMENTS_TRACEABILITY.md` la fila de `NXR-REQ-0096` ya
marcaba FE/E2E como `➖` (no aplica) desde antes de este task — confirma
que la matriz siempre esperó un entregable de arquitectura/documentación
aquí, no adaptadores nuevos.

## Cómo se integraría hoy un sistema externo (SAP, un agente de IA, un BI)

Hay exactamente tres superficies reales, las tres ya construidas por
tracks anteriores, ninguna nueva de este task:

### 1. La API REST misma

Todo dominio ya construido (Treasury, AP/AR, Procurement, Inventory,
Project Control, CRM, Documents/Evidence, RFI/Submittals, Site
Reports/Quality/Safety, Assets/Equipment/Workforce, Master Data) expone
un API REST real, autenticado y aislado por company —
`app/api/routes/*.py`, montado bajo `/api` en `app/main.py`. No hay un
"modo integración" separado: un adaptador externo consume exactamente los
mismos endpoints que el frontend, con la misma autorización
(`require_permission`/`assert_company_access`, `docs/RBAC.md`). Esto es
consistente con la regla de dominio "Treasury es dueño del dinero" — un
integrador no puede escribir un saldo directamente, tiene que pasar por
`treasury_service`/`posting_service` como cualquier otro cliente del API.

Formato de error real en toda la superficie: `{"error": {"code",
"message", "field", "correlationId"}}` (`app/api/error_handlers.py`) — un
adaptador externo puede parsear esto de forma uniforme sin conocer cada
dominio.

### 2. `AuditLog` como feed de eventos consultable (poll, no push)

`app/models/audit.py` (Track G, `NXR-REQ-0090`, ver `docs/AUDIT.md`) es
una tabla append-only real: `actor_user_id`, `action`
(`"<dominio>.<entidad>.<verbo>"`), `entity_type`, `entity_id`,
`company_id`, `project_id`, `before`/`after` (JSONB, solo los campos que
valen la pena auditar), `correlation_id`, `created_at`. Expuesta vía
`GET /api/audit` (`app/api/routes/audit.py`), con `companyId` obligatorio
y `entityType`/`entityId` opcionales como filtro, protegida por
`audit.log:read` + `assert_company_access`.

Un poller externo (un adaptador SAP, un agente de IA que quiere
reaccionar a "se aprobó una factura de proveedor") puede consultar este
endpoint periódicamente, ordenado por `created_at`, filtrando por
`entityType`, y tratarlo como un feed de eventos de negocio reales. Es
real hoy, pero **no** es un mecanismo de eventos diseñado para
integración: es la auditoría interna del sistema reutilizada como fuente
de verdad consultable. Limitación honesta: no todo mutation está
instrumentado todavía (`docs/AUDIT.md`/`docs/PROGRESS.md` documentan qué
rutas sí llaman a `audit_service.record` hoy — `ap.py`, `approvals.py`,
`procurement.py`, `treasury.py` — y cuáles, como la creación de una
`Company` en `master_data.py`, todavía no).

### 3. `Notification` como superficie de eventos por usuario

`app/models/notification.py` (Track G, `NXR-REQ-0091/0092`) es una
entidad in-app real por usuario (`recipient_user_id`, `type`, `title`,
`body`, `entity_type`/`entity_id` opcional, `read_at`), expuesta vía
`GET /api/notifications` y `POST /api/notifications/{id}/read`
(`app/api/routes/notifications.py`). No pertenece a una company —la
propiedad se verifica contra el usuario autenticado, no
`assert_company_access` (mismo patrón que cualquier recurso "propio" del
usuario). Hoy se crea en los mismos puntos donde se crea/decide un
`ApprovalRequest` (Workflow/SoD, `NXR-REQ-0087/0088/0089`). Un
integrador que actúa "como" un usuario autenticado (login real, misma
cookie de sesión) puede leer su propia bandeja de notificaciones igual
que el frontend — no es un mecanismo de integración dedicado, es la
misma superficie que ya usa `NotificationBell` en el frontend.

## Autenticación: solo sesión de usuario, hoy

`app/api/deps.py::get_current_user` lee una cookie de sesión
(`nexora_session`, `app/core/config.py::session_cookie_name`) y resuelve
contra `Session`/`User` en PostgreSQL (`app/services/auth_service.py`,
TTL vía `session_ttl_days`). **No existe** ningún mecanismo de
autenticación distinto — verificado contra el código real, no hay API
key, no hay client credentials / OAuth2 client_credentials, no hay
service account. Un adaptador externo que hoy quisiera integrarse tendría
que autenticarse como un usuario real (`POST /api/auth/login`) y guardar
la cookie de sesión igual que un navegador — no hay una identidad
"sistema" distinguible de una identidad "persona" en el audit trail
(`actor_user_id` siempre apunta, cuando existe, a un `User` real).

## Lo que NO existe todavía (groundwork honesto, no diseñado en este task)

Estos son huecos reales del sistema hoy, no una lista de features a
construir por este task — quedan documentados como groundwork futuro
para cuando un integrador real (SAP, un agente de IA con permisos
delegados, un BI) lo necesite:

- **Sin mecanismo de webhook/push.** Todo lo de arriba es poll: un
  integrador externo tiene que preguntar (`GET /api/audit`,
  `GET /api/notifications`) en vez de que NEXORA le avise. No hay cola,
  no hay `NOTIFY`/`LISTEN` de PostgreSQL expuesto, no hay ningún broker
  (consistente con CLAUDE.md §3 — "sin colas salvo que se decida
  explícitamente lo contrario").
- **Sin autenticación de servicio distinta al login de usuario.** No hay
  API key, no hay client_credentials OAuth2, no hay service account con
  su propio scope de permisos. Cualquier integración hoy se hace "como"
  un usuario humano con su propio rol/RBAC.
- **Sin rate limiting.** Ningún middleware ni dependencia limita
  requests por IP/usuario/token hoy — verificado (`grep` sobre `app/` sin
  resultados para rate limiting). Un poller mal configurado puede
  saturar la API igual que cualquier otro cliente.
- **Cobertura de `AuditLog` parcial.** Varios dominios (Master Data,
  RFI/Submittals, Site Reports/Quality/Safety, entre otros) todavía no
  llaman a `audit_service.record` en sus rutas de escritura — un poller
  de `AuditLog` no ve el 100% de las mutaciones del sistema todavía (ver
  `DEFERRED-FINAL-014` en `docs/PROGRESS.md`).
- **Sin versión de contrato de API explícita.** No hay `/api/v1/` ni
  ningún header de versión — un cambio de forma en una respuesta hoy
  rompería a cualquier integrador sin aviso previo.

Ninguno de estos puntos se resuelve en este task — construirlos
requeriría una decisión de arquitectura explícita (qué mecanismo de
push, qué modelo de autenticación de servicio) que el scope ruling de
este plan deliberadamente no autoriza a decidir de forma especulativa.
