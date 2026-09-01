import uuid
from datetime import datetime
from typing import Literal

from pydantic import model_validator

from app.models.document import DOCUMENT_CATEGORIES
from app.schemas.base import CamelModel


class EvidenceResponse(CamelModel):
    id: uuid.UUID
    company_id: uuid.UUID
    blob_key: str
    original_filename: str
    mime_type: str
    size_bytes: int
    category: str | None
    entity_type: str | None
    entity_id: uuid.UUID | None
    content_hash: str | None = None
    # §28: si el original no es renderizable (HEIC/HEIF), `derived_mime_type`
    # indica el formato del JPEG derivado que sirve `/evidence/{id}/render`.
    derived_mime_type: str | None = None
    uploaded_by: uuid.UUID
    created_at: datetime


class DocumentVersionResponse(CamelModel):
    id: uuid.UUID
    document_id: uuid.UUID
    version_number: int
    evidence_id: uuid.UUID
    status: str
    notes: str | None
    uploaded_by: uuid.UUID
    created_at: datetime


class DocumentCreateRequest(CamelModel):
    company_id: uuid.UUID
    scope: Literal["CENTRAL", "GENERAL", "PROJECT"] = "GENERAL"
    project_id: uuid.UUID | None = None
    category: str
    title: str
    description: str | None = None
    evidence_id: uuid.UUID

    @model_validator(mode="after")
    def category_must_be_known(self) -> "DocumentCreateRequest":
        if self.category not in DOCUMENT_CATEGORIES:
            raise ValueError(
                f"category debe ser una de: {', '.join(DOCUMENT_CATEGORIES)}"
            )
        return self


class DocumentVersionCreateRequest(CamelModel):
    evidence_id: uuid.UUID
    notes: str | None = None


class DocumentResponse(CamelModel):
    id: uuid.UUID
    company_id: uuid.UUID
    scope: str
    project_id: uuid.UUID | None
    category: str
    title: str
    description: str | None
    status: str
    current_version: DocumentVersionResponse | None = None
