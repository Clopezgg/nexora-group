import hashlib
import logging
import re
import unicodedata
import uuid
from collections.abc import Iterable

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.domain.errors import (
    EvidenceStorageAccessError,
    EvidenceStorageAuthError,
    EvidenceStorageTemporaryError,
    EvidenceTooLargeError,
    UnsupportedEvidenceMimeTypeError,
)
from app.integrations.azure_blob import delete_blob_if_exists, get_evidence_container_client
from app.models.evidence import EVIDENCE_ALLOWED_MIME_TYPES, Evidence
from app.repositories import evidence_repository

"""Evidence upload/download service (CONSTRUCTION CONTROL).

Evidence is stored only in Azure Blob Storage (or the explicitly configured
Azurite-compatible development backend). The application never fabricates a
public URL and never persists evidence payloads to local disk.
"""

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


# ISO-BMFF `ftyp` brands que identifican una imagen HEIC/HEIF real. Bytes
# 4-8 == b"ftyp", bytes 8-12 == brand. iOS a veces manda content-type vacio o
# application/octet-stream para estas fotos, asi que la firma es la unica
# fuente de verdad. NO se hace conversion nativa (sin pillow-heif); solo se
# valida y se almacena tal cual -- normalizacion a JPEG queda DEFERRED.
_HEIC_BRANDS = {b"heic", b"heix", b"hevc", b"hevx"}
_HEIF_BRANDS = {b"mif1", b"heif", b"msf1", b"mif2"}


def _detect_heif_mime(content: bytes) -> str | None:
    if len(content) < 12 or content[4:8] != b"ftyp":
        return None
    brand = content[8:12]
    if brand in _HEIC_BRANDS:
        return "image/heic"
    if brand in _HEIF_BRANDS:
        return "image/heif"
    return None


def _detect_mime(content: bytes) -> str | None:
    """Return the MIME type implied by the file's magic bytes, or None."""
    if content.startswith(b"%PDF-"):
        return "application/pdf"
    if content.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if len(content) >= 12 and content.startswith(b"RIFF") and content[8:12] == b"WEBP":
        return "image/webp"
    return _detect_heif_mime(content)


def _resolve_and_validate_mime(mime_type: str, content: bytes) -> str:
    """Reconcile the declared MIME with the real signature.

    iOS uploads frequently arrive with an empty or ``application/octet-stream``
    content-type (notably for HEIC/HEIF). In that case the magic bytes decide.
    In every case the stored MIME must match the real signature, so a spoofed
    ``Content-Type`` can never smuggle a disallowed payload through.
    """
    detected = _detect_mime(content)
    declared = (mime_type or "").strip().lower()
    if declared in ("", "application/octet-stream") and detected is not None:
        return detected
    if detected is None or detected != declared:
        raise UnsupportedEvidenceMimeTypeError(
            "el contenido del archivo no coincide con un tipo de evidencia permitido "
            "(PDF, JPEG, PNG, WEBP, HEIC, HEIF)"
        )
    return detected


def _raise_classified_storage_error(exc: Exception, *, operation: str, correlation_id: str | None) -> None:
    """Map an Azure SDK exception onto a NEXORA structured storage error.

    The root cause (exception type + message) is logged with the correlationId;
    the client only ever sees the generic user message and HTTP 503. Never
    leaks credentials, tokens, SAS or the storage URL.
    """
    from azure.core.exceptions import (
        ClientAuthenticationError,
        HttpResponseError,
        ServiceRequestError,
        ServiceResponseError,
    )

    logger.error(
        "evidence.storage.error operation=%s type=%s correlationId=%s cause=%s",
        operation,
        type(exc).__name__,
        correlation_id,
        str(exc).splitlines()[0][:300] if str(exc) else "",
    )

    if isinstance(exc, ClientAuthenticationError):
        raise EvidenceStorageAuthError() from exc
    if isinstance(exc, HttpResponseError):
        code = getattr(exc, "status_code", None)
        if code == 403:
            raise EvidenceStorageAccessError() from exc
        if code is not None and code >= 500:
            raise EvidenceStorageTemporaryError() from exc
        raise
    if isinstance(exc, (ServiceRequestError, ServiceResponseError)):
        raise EvidenceStorageTemporaryError() from exc
    raise


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
    correlation_id: str | None = None,
) -> Evidence:
    size_bytes = len(content)
    max_bytes = _max_size_bytes()
    if size_bytes == 0:
        raise EvidenceTooLargeError("el archivo está vacío (0 bytes)")
    if size_bytes > max_bytes:
        raise EvidenceTooLargeError(
            f"el archivo ({size_bytes} bytes) excede el límite configurado "
            f"({max_bytes} bytes / {get_settings().max_evidence_mb} MB)"
        )

    resolved_mime = _resolve_and_validate_mime(mime_type, content)
    if resolved_mime not in EVIDENCE_ALLOWED_MIME_TYPES:
        raise UnsupportedEvidenceMimeTypeError(
            f"mime_type {resolved_mime!r} no permitido. Tipos permitidos: "
            f"{', '.join(EVIDENCE_ALLOWED_MIME_TYPES)}"
        )
    mime_type = resolved_mime
    content_hash = hashlib.sha256(content).hexdigest()

    settings = get_settings()
    try:
        container_client = get_evidence_container_client(settings)
    except Exception as exc:  # noqa: BLE001 - se re-clasifica o re-lanza
        _raise_classified_storage_error(
            exc, operation="acquire_client", correlation_id=correlation_id
        )

    safe_filename = normalize_filename(filename)
    blob_key = f"{company_id}/{uuid.uuid4()}-{safe_filename}"

    from azure.storage.blob import ContentSettings

    try:
        container_client.upload_blob(
            name=blob_key,
            data=content,
            overwrite=False,
            content_settings=ContentSettings(content_type=mime_type),
        )
    except Exception as exc:  # noqa: BLE001 - se re-clasifica o re-lanza
        _raise_classified_storage_error(
            exc, operation="upload_blob", correlation_id=correlation_id
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
            content_hash=content_hash,
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


def download_evidence(evidence: Evidence) -> Iterable[bytes]:
    """Return a private Blob stream for an already-authorized evidence row.

    Authorization deliberately lives in the API layer because it requires the
    current principal and project grants. This function only resolves the
    configured private container and starts the Blob download; storage
    configuration errors propagate to the standard NXR-EVIDENCE-001 handler.
    """
    try:
        container_client = get_evidence_container_client(get_settings())
        downloader = container_client.download_blob(evidence.blob_key)
        return downloader.chunks()
    except Exception as exc:  # noqa: BLE001 - se re-clasifica o re-lanza
        from app.integrations.azure_blob import EvidenceStorageNotConfigured

        if isinstance(exc, EvidenceStorageNotConfigured):
            raise
        _raise_classified_storage_error(exc, operation="download_blob", correlation_id=None)


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
