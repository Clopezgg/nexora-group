import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.evidence import Evidence


def create_evidence(
    db: Session,
    *,
    company_id: uuid.UUID,
    blob_key: str,
    original_filename: str,
    mime_type: str,
    size_bytes: int,
    uploaded_by: uuid.UUID,
    category: str | None = None,
    entity_type: str | None = None,
    entity_id: uuid.UUID | None = None,
    content_hash: str | None = None,
    derived_blob_key: str | None = None,
    derived_mime_type: str | None = None,
) -> Evidence:
    evidence = Evidence(
        company_id=company_id,
        blob_key=blob_key,
        original_filename=original_filename,
        mime_type=mime_type,
        size_bytes=size_bytes,
        uploaded_by=uploaded_by,
        category=category,
        entity_type=entity_type,
        entity_id=entity_id,
        content_hash=content_hash,
        derived_blob_key=derived_blob_key,
        derived_mime_type=derived_mime_type,
    )
    db.add(evidence)
    db.flush()
    return evidence


def get_evidence(db: Session, evidence_id: uuid.UUID) -> Evidence | None:
    return db.get(Evidence, evidence_id)


def list_evidence(
    db: Session,
    *,
    company_id: uuid.UUID,
    entity_type: str | None = None,
    entity_id: uuid.UUID | None = None,
    offset: int = 0,
    limit: int = 50,
) -> list[Evidence]:
    stmt = select(Evidence).where(Evidence.company_id == company_id)
    if entity_type is not None:
        stmt = stmt.where(Evidence.entity_type == entity_type)
    if entity_id is not None:
        stmt = stmt.where(Evidence.entity_id == entity_id)
    stmt = stmt.order_by(Evidence.created_at.desc(), Evidence.id.asc()).offset(offset).limit(limit)
    return list(db.execute(stmt).scalars())
