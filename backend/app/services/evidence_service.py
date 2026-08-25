import uuid

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.domain.errors import EvidenceTooLargeError, UnsupportedEvidenceMimeTypeError
from app.integrations.azure_blob import get_evidence_container_client
from app.models.evidence import EVIDENCE_ALLOWED_MIME_TYPES, Evidence
from app.repositories import evidence_repository

"""Evidence upload (bloque CONSTRUCTION CONTROL, orden maestra §79,
docs/DOCUMENTS_EVIDENCE.md). Regla "no mocks presentados como
funcionalidad real": este servicio SOLO crea una fila `Evidence` después de
un upload real y exitoso contra Azure Blob Storage. Si el storage no está
configurado, `get_evidence_container_client` lanza
`EvidenceStorageNotConfigured` (RuntimeError real, registrado en
error_handlers.py como 503 NXR-EVIDENCE-001) -- nunca se fabrica una URL ni
una fila falsa. MIME type y tamaño se validan ANTES de tocar el cliente de
Blob, para no gastar una llamada de red en un archivo que de todos modos se
va a rechazar."""


def _max_size_bytes() -> int:
    return get_settings().max_evidence_mb * 1024 * 1024


def upload_evidence(
    db: Session,
    *,
    company_id: uuid.UUID,
    uploaded_by: uuid.UUID,
    filename: str,
    mime_type: str,
    content: bytes,
    category: str | None = None,
    entity_type: str | None = None,
    entity_id: uuid.UUID | None = None,
) -> Evidence:
    if mime_type not in EVIDENCE_ALLOWED_MIME_TYPES:
        raise UnsupportedEvidenceMimeTypeError(
            f"mime_type {mime_type!r} no permitido. Tipos permitidos: "
            f"{', '.join(EVIDENCE_ALLOWED_MIME_TYPES)}"
        )

    size_bytes = len(content)
    max_bytes = _max_size_bytes()
    if size_bytes == 0:
        raise EvidenceTooLargeError("el archivo está vacío (0 bytes)")
    if size_bytes > max_bytes:
        raise EvidenceTooLargeError(
            f"el archivo ({size_bytes} bytes) excede el límite configurado "
            f"({max_bytes} bytes / {get_settings().max_evidence_mb} MB)"
        )

    settings = get_settings()
    # Puede lanzar EvidenceStorageNotConfigured -- se deja propagar tal cual,
    # nunca se atrapa aquí para fabricar una respuesta de éxito falsa.
    container_client = get_evidence_container_client(settings)

    blob_key = f"{company_id}/{uuid.uuid4()}-{filename}"

    from azure.storage.blob import ContentSettings

    container_client.upload_blob(
        name=blob_key,
        data=content,
        overwrite=False,
        content_settings=ContentSettings(content_type=mime_type),
    )

    evidence = evidence_repository.create_evidence(
        db,
        company_id=company_id,
        blob_key=blob_key,
        original_filename=filename,
        mime_type=mime_type,
        size_bytes=size_bytes,
        uploaded_by=uploaded_by,
        category=category,
        entity_type=entity_type,
        entity_id=entity_id,
    )
    db.commit()
    db.refresh(evidence)
    return evidence


def get_evidence(db: Session, evidence_id: uuid.UUID) -> Evidence | None:
    return evidence_repository.get_evidence(db, evidence_id)


def list_evidence(
    db: Session,
    *,
    company_id: uuid.UUID,
    entity_type: str | None = None,
    entity_id: uuid.UUID | None = None,
) -> list[Evidence]:
    return evidence_repository.list_evidence(
        db, company_id=company_id, entity_type=entity_type, entity_id=entity_id
    )
