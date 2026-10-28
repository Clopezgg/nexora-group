# NEXORA — Render Free + Supabase Free

Decisión del propietario: 2026-10-28. Este es el destino nuevo. Azure se conserva
para compatibilidad y recuperación manual; su workflow ya no se activa en push/PR.
No se han creado servicios ni migrado datos mediante esta preparación.

## Arquitectura

- Un Web Service Docker **Free** de Render sirve React y FastAPI en el mismo
  origen HTTPS. El frontend usa `/api`, conservando cookies first-party en Safari.
- Supabase PostgreSQL guarda datos, sesiones y auditoría; Supabase Storage guarda
  evidencias privadas mediante S3. No se guardan adjuntos en el disco de Render.
- NEXORA conserva su autenticación y RBAC. No se activa Supabase Auth ni se envían
  credenciales S3/Postgres al navegador. El acceso a evidencias sigue pasando por API.
- Pool SQLAlchemy acotado a 3 conexiones + 2 adicionales, un worker Uvicorn.

## 1. Supabase

Crear un proyecto Free dedicado a NEXORA. Guardar el password de PostgreSQL en
el gestor de secretos. Preferir una región próxima a Render.

En **Connect**, copiar la URL **Session pooler, puerto 5432** (compatible con IPv4).
Usar `postgresql+psycopg://` —también se normalizan `postgres://`/`postgresql://`—,
password escapado como URL y `?sslmode=require&connect_timeout=10`.
No usar el pooler transaccional 6543 para este despliegue/migraciones.

Usar un proyecto vacío para instalación nueva. Alembic crea las tablas de NEXORA
en public y usa extensiones PostgreSQL como btree_gist. **Desactivar la Data API
del proyecto**: la aplicación usa conexión SQL directa y su propio RBAC; no debe
exponer estas tablas por REST/GraphQL con una clave pública. No habilitar acceso
anónimo al esquema de negocio. El servicio necesita permisos de migración; separar
rol de migración/runtime es una mejora posterior antes de operar en producción.

En Storage crear bucket `evidence`, **Public desactivado**, límite de archivo
al menos 25 MB y MIME acordes con PDF/JPEG/PNG/WEBP/HEIC/HEIF. No crear políticas
de lectura o escritura pública. Activar S3 y generar Access Key ID + Secret Access
Key. Copiar endpoint y región exactamente como aparecen en Supabase.
Las claves S3 de servidor tienen privilegios amplios: nunca usar prefijo VITE_.

## 2. Render

Una vez que estos cambios estén publicados en GitHub, crear un Blueprint desde
el repositorio/rama que los contiene usando `render.yaml`. El blueprint contiene
**solo un servicio Free**; no crea una DB Render, discos ni servicios pagados.
Auto-deploy está desactivado para controlar releases.

Completar las variables secretas desde Render Environment:

| Variable | Valor |
|---|---|
| APP_ENV | production |
| FRONTEND_URL | Origen HTTPS real asignado por Render, sin slash final ni /api |
| DATABASE_URL | URL Session pooler Supabase, SSL y connect_timeout |
| SECRET_KEY | Generada por Blueprint; conservarla estable |
| EVIDENCE_BACKEND | supabase |
| EVIDENCE_CONTAINER_NAME | evidence |
| SUPABASE_S3_ENDPOINT | Endpoint HTTPS completo terminado en /storage/v1/s3 |
| SUPABASE_S3_REGION | Región copiada de Supabase |
| SUPABASE_S3_ACCESS_KEY_ID | Clave S3 de servidor |
| SUPABASE_S3_SECRET_ACCESS_KEY | Secreto S3 de servidor |
| EDIT_ACCESS_REQUIRED | true |
| EDIT_ACCESS_TOKEN_SALT / DIGEST | Generados con el procedimiento siguiente |
| BOOTSTRAP_ADMIN_EMAIL / PASSWORD | Administrador inicial, solo para instalación vacía |

Si el hostname no se conoce al iniciar el Blueprint, completar FRONTEND_URL al
obtener la URL de Render y volver a desplegar. No inventar un dominio ni usar `*`.
No configurar AZURE_KEY_VAULT_URI, AZURE_STORAGE_ACCOUNT_NAME ni
APPLICATIONINSIGHTS_CONNECTION_STRING en el nuevo servicio.

Para generar Protected Edit, ejecutar localmente este código Python (solicita la
credencial sin mostrarla; la salida contiene salt y digest, no el PIN):

```python
import base64, getpass, hashlib, secrets
pin = getpass.getpass('Credencial de edición: ')
if not pin or pin != getpass.getpass('Repetir: '):
    raise SystemExit('Las credenciales no coinciden o están vacías')
salt = secrets.token_bytes(32)
digest = hashlib.pbkdf2_hmac('sha256', pin.encode(), salt, 250_000)
encode = lambda b: base64.urlsafe_b64encode(b).decode().rstrip('=')
print('EDIT_ACCESS_TOKEN_SALT=' + encode(salt))
print('EDIT_ACCESS_TOKEN_DIGEST=' + encode(digest))
```

El contenedor compila React, instala Python, aplica `alembic upgrade head` y
arranca Uvicorn en `$PORT`. Si una migración falla, no arranca la aplicación.
El check `/api/readyz` exige DB y acceso al bucket. Usar siempre el Dockerfile
de raíz **Dockerfile.render**, no backend/Dockerfile que solo empaqueta la API.

## 3. Migración desde Azure: procedimiento pendiente de ejecución

Para conservar datos existentes, **no arrancar como sistema vacío y luego mezclar
manualmente registros financieros**. Mantener Azure accesible hasta verificar el destino.

1. Inventariar versión Alembic de origen, recuentos de tablas, compañías, saldos,
   facturas, pagos, evidencias y hashes. Crear backup comprobado y copia de blobs.
2. Crear destino Supabase dedicado, sin tráfico. Restaurar tablas/datos de NEXORA
   y `alembic_version` con herramientas PostgreSQL, sin reemplazar esquemas
   administrados `auth`, `storage` o roles internos de Supabase. No ejecutar
   `scripts/db_restore.sh` contra Supabase: ese script intenta borrar la DB destino.
3. Copiar originales y derivados de Blob al bucket privado conservando **exactamente
   blob_key y derived_blob_key**. Los IDs y hashes de Evidence no cambian. Verificar
   tamaño y SHA-256 por archivo. Cambiar de proveedor no copia automáticamente bytes.
4. Ejecutar migraciones pendientes desde la revisión restaurada. No hacer stamp
   head para ocultar incompatibilidades ni reejecutar migraciones destructivas históricas.
5. Probar lectura completa, comprobantes históricos, login y permisos; comparar
   GL, tesorería, AP/AR, planes y auditoría contra origen.
6. Congelar escrituras durante el corte final, aplicar delta consistente de DB y
   blobs, verificar nuevamente y dirigir usuarios a Render. Conservar rollback.

El rol/grants del dump y las extensiones deben revisarse contra el proyecto real
antes de proporcionar un comando de restauración definitivo. Un backup de DB no
respalda por sí solo los adjuntos. No enviar passwords ni claves por chat.

## 4. Aceptación del despliegue

- `/api/healthz` y `/api/readyz`: 200; `/api/version` disponible.
- `/`, ruta directa `/proyectos` y verificación de comprobante sirven el SPA;
  API desconocida y asset inexistente devuelven 404, no index.html.
- Login/logout/relogin real en Safari y Chrome, cookies HttpOnly/Secure.
- Empresa visible, proyectos y totales consistentes con origen.
- Subir/descargar PDF e imagen, generar voucher con evidencia privada.
- Solicitud sin permiso: rechazada por backend; URL pública del bucket: no accesible.
- Protected Edit sigue exigido para acciones sensibles.
- Reiniciar/redeploy Render y comprobar persistencia de datos y adjuntos.
- Contrastar el SHA desplegado, ejecutar E2E y suite PostgreSQL antes de declarar listo.

## Límites gratuitos y estado

Render Free suspende por inactividad; Supabase Free limita DB/Storage/tráfico y
puede pausar proyectos con poca actividad. No se promete servicio continuo ni
capacidad de producción. Mantener backups externos de datos y adjuntos.
No agregar pings artificiales para eludir suspensión. Un único contenedor puede
necesitar más memoria al generar PDFs/HEIC; medir con archivos reales.

La preparación local no demuestra acceso a las cuentas ni migración completada.
Quedan pendientes credenciales/configuración de los proyectos, prueba real S3/DB,
build Docker en entorno con Docker, despliegue y smoke del destino.

### Verificación local de esta preparación (2026-10-28)

- Ruff: pasa. 37 tests dirigidos de backend: pasan (adaptador S3 probado con
  Stubber, sin red; no es una prueba del proyecto Supabase).
- Frontend: typecheck, lint, 263 tests y build `/api`: pasan.
- FastAPI con el build real: root, ruta de proyecto, asset JS, health/version
  responden; API/asset desconocidos conservan 404. Smoke sin lifespan ni DB.
- Alembic: un head `eb8ce8e18b2d`; no se aplicaron migraciones a Supabase.
- YAML comprobado localmente; pendiente validación por Render y build Docker.
- Cambios locales en rama `feat/render-supabase`; aún no publicados en GitHub.

Referencias oficiales:
- https://render.com/docs/blueprint-spec
- https://render.com/docs/free
- https://supabase.com/docs/guides/database/connecting-to-postgres
- https://supabase.com/docs/guides/storage/s3/authentication
- https://supabase.com/docs/guides/storage/s3/compatibility
