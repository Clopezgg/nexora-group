# Documents / Evidence — Track D (Construction Control)

Fundación del bloque CONSTRUCTION CONTROL (orden maestra §77-79,
`docs/MASTER_PLAN.md` fila "Documents / Evidence / Progress / Site /
Quality"). Cubre `NXR-REQ-0077` (Documents + Azure Blob), `NXR-REQ-0078`
(Document Versioning) y `NXR-REQ-0079` (Evidence validado MIME/tamaño).
Daily Site Report/Quality/Safety/RFI/Submittals (`NXR-REQ-0081`-`0086`,
tareas posteriores del mismo plan) construyen sus propias entidades sobre
esta base — no se reinventa el pipeline de subida de archivos.

## Dos entidades, dos responsabilidades

- **`Evidence`** (`app/models/evidence.py`): metadata REAL de un archivo ya
  subido a Azure Blob Storage vía `app/integrations/azure_blob.py`
  (`get_evidence_container_client`). Es el único punto de entrada al
  storage — nada en el sistema sube un archivo sin pasar por
  `evidence_service.upload_evidence`. Columnas: `company_id`, `blob_key`
  (único), `original_filename`, `mime_type`, `size_bytes`, `category`
  (etiqueta libre, ver abajo), `entity_type`/`entity_id` (enlace
  polimórfico informativo, ver abajo), `uploaded_by`, `created_at`.
- **`Document` / `DocumentVersion`** (`app/models/document.py`): el objeto
  de negocio versionado ("Plano estructural nivel 3", "Contrato de
  subcontratista"). Un `Document` nunca existe sin al menos una
  `DocumentVersion`; cada versión apunta a una fila `Evidence` distinta.
  `Document` nunca apunta a Blob Storage directamente.

Evidence es de propósito general — una foto de avance de obra, un PDF de
contrato, una foto de un incidente de seguridad, todo pasa por la misma
tabla `evidence` y el mismo endpoint `POST /api/evidence`. `Document` es
específicamente para objetos versionados con historial; un adjunto simple
(una foto de avance, un archivo de una orden de mantenimiento) no necesita
un `Document` — se referencia el `Evidence` directamente.

## Attachment contract (para Tasks 3/4 y cualquier dominio futuro)

**Regla por defecto — adjunto único**: cualquier entidad de dominio que
necesita UN adjunto (foto, PDF, firma) declara su propia columna:

```python
evidence_id: Mapped[uuid.UUID | None] = mapped_column(
    UUID(as_uuid=True), ForeignKey("evidence.id", ondelete="SET NULL"), nullable=True
)
```

Este es el patrón real ya aplicado en este mismo track:
`ProgressRecord.evidence_id` (antes `evidence_ref: str` de texto libre,
ahora una FK real — `app/models/progress.py`). Mismo patrón que Track A dio
a `SupplierInvoice`/`Supplier` y a `CustomerInvoice.customer_id` (FK real,
nunca texto libre).

**Validación obligatoria antes de persistir**: cualquier servicio que
reciba un `evidence_id` del cliente DEBE validar que pertenece a la misma
`company_id` que la entidad dueña, usando el helper ya existente:

```python
from app.services.financial_validation_service import assert_evidence_belongs_to_company

assert_evidence_belongs_to_company(db, evidence_id=payload.evidence_id, company_id=company_id)
```

(Pese al nombre del módulo — heredado de Track A —, es el punto central
donde viven TODOS los helpers `assert_X_belongs_to_company` de FKs
cross-dominio del sistema; `Customer` de Track E ya sigue el mismo patrón.)
Esto lanza `InvalidFinancialReferenceError` → HTTP 422 `NXR-FINANCIAL-001`
si el `evidence_id` no existe o pertenece a otra compañía — el rechazo
ocurre ANTES de cualquier `db.add`/`db.flush` de la entidad dueña.

**Adjuntos múltiples — tabla de unión**: si una entidad necesita VARIOS
adjuntos (p.ej. una `DailySiteReport` con 10 fotos), no se agregan 10
columnas `evidence_id`. Se crea una tabla de unión propia del dominio
dueño, por ejemplo:

```python
class DailySiteReportPhoto(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "daily_site_report_photos"
    daily_site_report_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("daily_site_reports.id", ondelete="CASCADE"), nullable=False
    )
    evidence_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evidence.id", ondelete="RESTRICT"), nullable=False
    )
```

Cada fila de la tabla de unión también se valida con
`assert_evidence_belongs_to_company` antes de insertarse. Este es el mismo
patrón usado en todo el sistema para relaciones N:M reales (p.ej.
`RfqSupplier`, `SupplierQuotationLine`) — nunca se inventa un patrón nuevo.

**Lo que `Evidence.entity_type`/`entity_id` NO es**: son columnas
informativas de conveniencia (para responder "¿para qué se subió este
archivo?" al momento del upload, útil para listar `GET
/api/evidence?entityType=...&entityId=...`), sin FK real de PostgreSQL
(la tabla destino varía según el caso de uso y Postgres no soporta una FK
contra múltiples tablas). **No son el contrato de adjunto autoritativo.**
Cualquier dominio que necesite integridad referencial real usa la columna
`evidence_id` tipada descrita arriba, nunca confía solo en
`entity_type`/`entity_id` para garantizar que un adjunto existe o
pertenece a la compañía correcta.

## Versionado inmutable (`DOCUMENT_VERSION_STATUSES`)

Subir una nueva versión de un `Document` (`POST
/api/documents/{id}/versions`):

1. Valida que el `Document` está `ACTIVE` (no `ARCHIVED`) —
   `InvalidDocumentStateError`, `NXR-DOCUMENT-001`, HTTP 409 si no.
2. Valida que el nuevo `evidence_id` pertenece a la misma compañía
   (`assert_evidence_belongs_to_company`).
3. Marca la `DocumentVersion` `ACTIVE` actual como `SUPERSEDED` — **nunca**
   se hace `UPDATE`/`DELETE` sobre una versión ya creada, ni siquiera para
   corregirla. Corrección = subir una versión nueva.
4. Crea una fila `DocumentVersion` nueva con `version_number = anterior + 1`
   y `status = ACTIVE`.

**No hay columna `Document.current_version_id`** — se evitó
deliberadamente una FK circular `documents.current_version_id →
document_versions.id → documents.id` (mismo criterio que Track E usó para
evitar ciclos en `customers → leads → opportunities`). El "current version
pointer" se deriva de la única `DocumentVersion` en estado `ACTIVE` por
documento, garantizado a nivel de PostgreSQL por el índice único parcial:

```sql
CREATE UNIQUE INDEX uq_document_versions_one_active_per_document
  ON document_versions (document_id) WHERE status = 'ACTIVE';
```

`Document.current_version` (propiedad Python, `app/models/document.py`) y
el campo `currentVersion` en `DocumentResponse` exponen este puntero
derivado — nunca puede haber dos versiones `ACTIVE` simultáneas para el
mismo documento, ni bajo escritura concurrente.

## Validación de Evidence: MIME allowlist + tamaño (NXR-REQ-0079)

`evidence_service.upload_evidence` valida, **antes** de llamar a
`get_evidence_container_client()` (nunca se gasta una llamada de red en un
archivo que de todos modos se va a rechazar):

1. **MIME type** contra el allowlist `EVIDENCE_ALLOWED_MIME_TYPES`
   (`app/models/evidence.py`): `application/pdf`, `image/jpeg`,
   `image/png`, `image/webp`. Cualquier otro tipo (`.exe`, `.zip`, etc.) →
   `UnsupportedEvidenceMimeTypeError`, HTTP 422, `NXR-EVIDENCE-002`.
2. **Tamaño** contra `settings.max_evidence_mb` (default 25 MB, variable de
   entorno `MAX_EVIDENCE_MB`). Un archivo vacío o que excede el límite →
   `EvidenceTooLargeError`, HTTP 422, `NXR-EVIDENCE-003`.

## Storage failure contract (regla "no mocks presentados como funcionalidad real")

Si `EVIDENCE_BACKEND` no está en `azure_blob` (o `AZURE_STORAGE_ACCOUNT_NAME`
falta), `get_evidence_container_client()` lanza
`EvidenceStorageNotConfigured` (`app/integrations/azure_blob.py`, ya
existía antes de este track). Este track registra esa excepción en
`app/api/error_handlers.py` como un **503 real**, código `NXR-EVIDENCE-001`
— nunca un `200` con una URL de blob fabricada. Esto ocurre DESPUÉS de la
validación de MIME/tamaño (para que un archivo inválido siempre falle por
la razón correcta, incluso con storage configurado) pero ANTES de crear
cualquier fila `Evidence` — sin upload real a Blob, nunca hay fila
`Evidence`.

## API

- `POST /api/evidence` (multipart/form-data: `companyId`, `category?`,
  `entityType?`, `entityId?`, `file`) → `EvidenceResponse` (201). Requiere
  permiso `document.evidence:create`.
- `GET /api/evidence?companyId=&entityType=&entityId=` → lista. Requiere
  `document.evidence:read`.
- `GET /api/evidence/{id}` → una fila. Requiere `document.evidence:read`.
- `POST /api/documents` (JSON: `companyId`, `scope`, `projectId?`,
  `category`, `title`, `description?`, `evidenceId`) → crea `Document` +
  `DocumentVersion` v1 en la misma transacción. Requiere
  `document.document:create`.
- `GET /api/documents?companyId=&projectId=` → lista con `currentVersion`
  embebido. Requiere `document.document:read`.
- `GET /api/documents/{id}` → un documento. Requiere `document.document:read`.
- `GET /api/documents/{id}/versions` → historial completo, orden
  descendente. Requiere `document.document:read`.
- `POST /api/documents/{id}/versions` (JSON: `evidenceId`, `notes?`) → nueva
  versión (ver "Versionado inmutable" arriba). Requiere
  `document.document:version`.

**Fuera de alcance de este task (deuda documentada, no oculta)**: no existe
todavía un endpoint de *descarga* del archivo real (`GET
/api/evidence/{id}/download` con SAS token de Azure Blob de corta
duración) — el frontend actual solo sube y lista metadata. Un track de
Hardening posterior debe agregarlo antes de considerar el módulo
"VERIFIED" end-to-end.

## RBAC

Recursos nuevos: `document.document` (`create`/`read`/`version`) y
`document.evidence` (`create`/`read`), ver
`app/repositories/permission_repository.py`. Otorgados a `Administrator`
(todos, `ANY`), `Project Manager` (`create`/`read`/`version`/`create`
evidence, `OWN`), `Project Controller`/`Auditor`/`Viewer` (solo `read`).
