# Backup / Restore — NXR-REQ-0109

Este documento define la estrategia verificable de recuperación de NEXORA. No asume que una aplicación sana equivale a un backup sano: el restore se prueba de forma independiente.

## Backup lógico probado

Los scripts autoritativos son:

```bash
./scripts/db_backup.sh <nombre_db> <archivo_salida.dump>
./scripts/db_restore.sh <archivo.dump> <nombre_db_destino>
```

Usan `pg_dump --format=custom` y `pg_restore`. El restore se realiza siempre sobre una base nueva/vacía; nunca se usa como mecanismo para sobrescribir silenciosamente una base productiva viva.

`backend/tests/test_backup_restore.py` ejecuta un ciclo real contra PostgreSQL:

1. crea una base de origen;
2. aplica `alembic upgrade head`;
3. siembra datos mediante repositorios/servicios reales, incluido un asiento de Treasury;
4. genera el dump;
5. restaura a una base destino independiente;
6. comprueba revision Alembic, credenciales/hash, datos críticos e integridad `SUM(debit)==SUM(credit)`.

Ese test forma parte de la suite backend completa; una regresión del procedimiento lógico de backup/restore falla en CI.

## Azure Database for PostgreSQL

La infraestructura Bicep despliega PostgreSQL Flexible Server 16. La configuración autoritativa vive en `infra/modules/postgres.bicep` y actualmente establece:

- almacenamiento: 32 GB;
- backup automático de Azure: **7 días** (`backupRetentionDays: 7`);
- geo-redundant backup: deshabilitado;
- high availability: deshabilitado en el entorno económico actual;
- acceso de Azure Services mediante la regla definida por IaC.

Los cambios de retención, HA, red o SKU deben realizarse por Bicep/PR y validarse con `what-if`; no se documentan valores distintos de los que realmente declara IaC.

## RPO / RTO

No se inventa un SLA de negocio. Hay dos niveles distintos:

| Mecanismo | RPO/RTO técnico documentado |
|---|---|
| `pg_dump` / `pg_restore` | RPO = instante del último dump disponible. En el dataset automatizado de prueba, restore local tarda segundos; no extrapolar ese tiempo a producción. |
| Azure Flexible Server | RPO/RTO dependen de la capacidad PITR/backup del servicio, el volumen real y el procedimiento de recuperación. La retención configurada por IaC es 7 días. Un SLA empresarial en minutos/horas debe aprobarse y medirse antes de prometerlo contractualmente. |

La ausencia de un SLA comercial explícito no invalida el mecanismo técnico de backup. Si NEXORA GROUP define posteriormente un RPO/RTO empresarial, el tier/HA/retención deberán ajustarse para cumplirlo y medirse mediante un simulacro controlado.

## Procedimiento de recuperación

Ante un incidente de base de datos:

1. detener o aislar escrituras si continuar escribiendo aumenta el daño;
2. determinar el punto de recuperación objetivo;
3. restaurar a un destino nuevo, nunca sobre el origen;
4. aplicar/verificar Alembic en el destino;
5. comprobar login y configuración crítica;
6. reconciliar contabilidad (`debit == credit`), AP/AR/Treasury y conteos esenciales;
7. validar `/api/readyz` contra el destino restaurado;
8. ejecutar smoke autenticado;
9. cambiar la aplicación al destino únicamente después de la verificación;
10. conservar evidencia/auditoría del incidente y del punto restaurado.

## Blob Storage / Evidence

Los documentos y Evidence viven en Azure Blob Storage privado cuando `EVIDENCE_BACKEND` está configurado. El original no se sustituye por previews derivados. La estrategia de continuidad de Storage se gobierna por configuración de Azure y debe tratarse separadamente del dump PostgreSQL: restaurar la DB sin los blobs asociados no constituye recuperación completa de Evidence.

La integridad de cada Evidence puede contrastarse con su `content_hash` SHA-256 persistido. Los enlaces company/project y los permisos siguen siendo autoritativos después de una restauración.

## Seguridad del backup

- Los dumps pueden contener datos sensibles y deben tratarse como secretos operativos.
- No se suben dumps al repositorio Git.
- No se imprimen contraseñas/connection strings en logs.
- Un restore de validación usa un destino aislado y credenciales controladas.
- El backup no es una vía para saltar auditoría ni para reescribir movimientos financieros históricos.

## Alcance futuro opcional

- geo-redundant backup;
- HA zonal;
- réplica/DR multi-región;
- retención superior a 7 días;
- simulacros periódicos con RTO medido sobre volumen productivo.

Estas mejoras se activan cuando el SLA/riesgo del negocio lo requiera. La arquitectura actual no debe declarar capacidades multi-región o tiempos de recuperación que no estén configurados y medidos.
