import logging
import re
import unicodedata
import uuid

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.domain.errors import EvidenceTooLargeError, UnsupportedEvidenceMimeTypeError
from app.integrations.azure_blob import delete_blob_if_exists, get_evidence_container_client
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

logger = logging.getLogger(__name__)


def _max_size_bytes() -> int:
    return get_settings().max_evidence_mb * 1024 * 1024


async def read_bounded_upload(upload, *, max_bytes: int | None = None) -> bytes:
    """Read at most max+1 bytes so rejection never requires buffering the full upload."""
    effective_max = _max_size_bytes() if max_bytes is None else max_bytes
    content = bytearray()
    while len(content) <= effective_max:
        remaining = effective_max + 1 - len(content)
        chunk = await upload.read(min(64 * 1024, remaining))
        if not chunk:
            break
        content.extend(chunk)
        if len(content) > effective_max:
            raise EvidenceTooLargeError(
                f"el archivo excede el límite configurado ({effective_max} bytes)"
            )
    if not content:
        raise EvidenceTooLargeError("el archivo está vacío (0 bytes)")
    return bytes(content)


def normalize_filename(filename: str) -> str:
    normalized = unicodedata.normalize("NFKC", filename).replace("\\", "/")
    basename = normalized.rsplit("/", 1)[-1]
    basename = re.sub(r"(?i)%(?:0[0-9a-f]|1[0-9a-f]|7f)", "", basename)
    basename = "".join(char for char in basename if not unicodedata.category(char).startswith("C"))
    basename = basename.strip().lstrip(".").strip()
    return basename[:255] or "archivo"


def _content_matches_mime(content: bytes, mime_type: str) -> bool:
    signatures = {
        "application/pdf": lambda value: value.startswith(b"%PDF-"),
        "image/jpeg": lambda value: value.startswith(b"\xff\xd8\xff"),
        "image/png": lambda value: value.startswith(b"\x89PNG\r\n\x1a\n"),
        "image/webp": lambda value: len(value) >= 12
        and value.startswith(b"RIFF")
        and value[8:12] == b"WEBP",
    }
    return signatures[mime_type](content)


def _compensate_uploaded_blob(container_client, blob_key: str) -> None:
    try:
        delete_blob_if_exists(container_client, blob_key)
    except Exception:
        logger.exception("could not compensate evidence blob %s", blob_key)


def compensate_evidence_blob(blob_key: str) -> None:
    try:
        container_client = get_evidence_container_client(get_settings())
    except Exception:
        logger.exception("could not acquire storage client to compensate evidence blob %s", blob_key)
        return
    _compensate_uploaded_blob(container_client, blob_key)


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
    commit: bool = True,
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
    if not _content_matches_mime(content, mime_type):
        raise UnsupportedEvidenceMimeTypeError(
            f"el contenido del archivo no coincide con mime_type {mime_type!r}"
        )

    settings = get_settings()
    # Puede lanzar EvidenceStorageNotConfigured -- se deja propagar tal cual,
    # nunca se atrapa aquí para fabricar una respuesta de éxito falsa.
    container_client = get_evidence_container_client(settings)

    safe_filename = normalize_filename(filename)
    blob_key = f"{company_id}/{uuid.uuid4()}-{safe_filename}"

    from azure.storage.blob import ContentSettings

    container_client.upload_blob(
        name=blob_key,
        data=content,
        overwrite=False,
        content_settings=ContentSettings(content_type=mime_type),
    )

    try:
        evidence = evidence_repository.create_evidence(
            db,
            company_id=company_id,
            blob_key=blob_key,
            original_filename=safe_filename,
            mime_type=mime_type,
            size_bytes=size_bytes,
            uploaded_by=uploaded_by,
            category=category,
            entity_type=entity_type,
            entity_id=entity_id,
        )
        if commit:
            db.commit()
            db.refresh(evidence)
        else:
            db.flush()
        return evidence
    except Exception:
        db.rollback()
        _compensate_uploaded_blob(container_client, blob_key)
        raise


def get_evidence(db: Session, evidence_id: uuid.UUID) -> Evidence | None:
    return evidence_repository.get_evidence(db, evidence_id)


def list_evidence(
    db: Session,
    *,
    company_id: uuid.UUID,
    entity_type: str | None = None,
    entity_id: uuid.UUID | None = None,
    offset: int = 0,
    limit: int = 50,
) -> list[Evidence]:
    return evidence_repository.list_evidence(
        db,
        company_id=company_id,
        entity_type=entity_type,
        entity_id=entity_id,
        offset=offset,
        limit=limit,
    )
