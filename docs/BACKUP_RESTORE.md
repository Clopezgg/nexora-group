# Backup / Restore — NXR-REQ-0109

Cierra `NXR-REQ-0109` (`docs/PRODUCTION_READINESS.md`, bloque 4:
"estrategia, retención, point-in-time recovery si el tier lo permite,
RPO/RTO documentados, al menos una prueba real de restore en destino no
productivo"). Este documento describe lo que existe **hoy, probado
localmente contra PostgreSQL real** — no un plan a futuro.

## Estrategia

Backup lógico vía `pg_dump --format=custom` (comprimido, restaurable
selectivamente con `pg_restore` si algún día hace falta). Restore
siempre a un destino **nuevo y vacío** (`dropdb`/`createdb` antes de
`pg_restore`) — una restauración de desastre real nunca sobrescribe una
base de datos con datos existentes.

Scripts reales, ejecutables directamente:

```bash
# Backup
./scripts/db_backup.sh <nombre_db> <archivo_salida.dump>

# Restore (siempre a un destino nuevo)
./scripts/db_restore.sh <archivo.dump> <nombre_db_destino>
```

Ambos scripts son exactamente lo que ejecuta
`backend/tests/test_backup_restore.py` — el test es también su único
ejercicio real, así que una regresión en cualquiera de los dos falla
ahí primero, no en un desastre real.

## Prueba real de restore (NXR-REQ-0109, requisito explícito)

`backend/tests/test_backup_restore.py` ejecuta, contra PostgreSQL real
(no mockeado, no simulado):

1. Crea una base `nexora_backup_source_*` vacía, `alembic upgrade head`
   sobre ella (mismo camino de fresh-install que `NXR-REQ-0106`).
2. Siembra datos reales a través de la capa de repositorio/servicio real
   (`company_repository`, `account_repository`, `treasury_service` —
   nunca un `INSERT` crudo): una company, su chart of accounts, una
   cuenta de tesorería, una remesa CENTRAL real posteada (`L 75,000.00`,
   `AccountingDocument`/`JournalLine` reales), y un usuario Administrator
   real con su hash Argon2id real.
3. `./scripts/db_backup.sh` sobre esa base.
4. `./scripts/db_restore.sh` a una base `nexora_backup_target_*`
   completamente nueva.
5. Verifica, contra la base restaurada:
   - **migrations/state**: `alembic current` reporta el mismo head.
   - **login**: el hash de password restaurado es idéntico byte a byte
     al original, y `verify_password()` (la misma función que usa
     `auth_service.login()` en producción) acepta la contraseña en
     texto plano contra él.
   - **datos críticos**: la company sembrada existe con el mismo nombre.
   - **integridad contable**: `SUM(debit_amount) == SUM(credit_amount)`
     sobre `journal_lines` en la base restaurada, y ese total es
     exactamente el monto real de la remesa sembrada — no "hay datos",
     sino "son los mismos datos, con la misma integridad de partida
     doble".

Ejecutar bajo demanda: `pytest tests/test_backup_restore.py -v` (ya
forma parte de la suite completa, `pytest -q`).

## RPO / RTO

**Contexto actual: solo DEV local, sin Azure desplegado todavía**
(`NXR-REQ-0116-0118` — Bicep escrito, sin desplegar). Los valores de
abajo son los que aplican **hoy** a este entorno; se revisan cuando
exista una Azure Database for PostgreSQL Flexible Server real.

| Entorno | RPO (pérdida máxima aceptable) | RTO (tiempo máximo de recuperación) | Mecanismo |
|---|---|---|---|
| DEV local (hoy) | Desde el último `db_backup.sh` manual | Minutos (restore local es rápido: `< 10s` para el volumen de datos actual, medido por el test) | `pg_dump`/`pg_restore` manual, bajo demanda |
| Azure DEV (cuando exista, `NXR-REQ-0118`) | Definido por el backup automático de Azure Database for PostgreSQL Flexible Server (point-in-time recovery, retención configurable en el módulo Bicep `infra/modules/postgres.bicep`) | Definido por el tiempo de restore de Azure PITR + re-deploy de Container Apps apuntando a la instancia restaurada | Azure PITR nativo + este mismo procedimiento de verificación (migrations/login/datos/integridad) aplicado contra el restore de Azure |
| Producción (futuro, tras confirmación puntual de despliegue real) | Igual a Azure DEV, ajustado según el SLA de negocio que se decida | Igual a Azure DEV | Igual, con retención más larga |

**No se declara un RPO/RTO de producción específico en minutos/horas
todavía** porque no hay una Azure Database for PostgreSQL real
desplegada contra la cual medirlo honestamente — inventar un número
sin evidencia violaría `CLAUDE.md` (no fabricar datos/certificaciones).
Cuando `NXR-REQ-0118` se despliegue, este documento se actualiza con el
RPO/RTO real medido contra esa instancia, siguiendo el mismo
procedimiento de verificación que ya existe aquí (no un procedimiento
nuevo — el mismo).

## Retención

DEV local: sin política automática todavía (backups manuales bajo
demanda vía `db_backup.sh`). Azure Database for PostgreSQL Flexible
Server soporta retención configurable de backups automáticos (7-35
días) vía el parámetro `backupRetentionDays` — a fijar en
`infra/modules/postgres.bicep` cuando se decida el SLA real antes del
primer despliegue a Azure DEV.

## Qué NO cubre este documento todavía

- Point-in-time recovery real (requiere Azure Database for PostgreSQL
  Flexible Server desplegado — `NXR-REQ-0118`, `BLOCKED_EXTERNAL` por
  la suscripción UNAH deshabilitada al momento de escribir esto).
- Backup/restore de Azure Blob Storage (evidencia/documentos) — Azure
  Storage tiene su propia estrategia de redundancia (`infra/modules/
  storage.bicep`); no hay evidencia real todavía porque no hay Storage
  Account desplegado.
- Disaster recovery multi-región — explícitamente fuera de alcance
  (`docs/MASTER_PLAN.md`: "sin arquitectura multi-region si no es
  necesaria").
