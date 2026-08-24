import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document_type import DocumentType
from app.models.number_sequence import NumberSequence


def next_document_number(db: Session, *, company_id: uuid.UUID, document_type_code: str) -> str:
    """Concurrency-safe: nunca MAX()+1. Bloquea la fila (company_id,
    document_type_code, year) con SELECT ... FOR UPDATE dentro de la
    transacción del caller antes de incrementar, así que dos requests
    concurrentes nunca reciben el mismo número. El caller es responsable de
    hacer commit/rollback de la transacción (ver PostingService)."""
    year = datetime.now(timezone.utc).year

    document_type = db.execute(
        select(DocumentType).where(DocumentType.code == document_type_code)
    ).scalar_one_or_none()
    if document_type is None:
        raise ValueError(f"DocumentType '{document_type_code}' no existe")

    sequence = db.execute(
        select(NumberSequence)
        .where(
            NumberSequence.company_id == company_id,
            NumberSequence.document_type_code == document_type_code,
            NumberSequence.year == year,
        )
        .with_for_update()
    ).scalar_one_or_none()

    if sequence is None:
        sequence = NumberSequence(
            company_id=company_id,
            document_type_code=document_type_code,
            year=year,
            current_value=0,
        )
        db.add(sequence)
        db.flush()
        sequence = db.execute(
            select(NumberSequence).where(NumberSequence.id == sequence.id).with_for_update()
        ).scalar_one()

    sequence.current_value += 1
    db.flush()

    return f"{document_type.number_prefix}-{year}-{sequence.current_value:06d}"
