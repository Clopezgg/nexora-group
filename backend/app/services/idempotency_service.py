import hashlib
import json
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.errors import IdempotencyConflictError
from app.models.idempotency import IdempotencyRecord


def _hash_payload(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass
class IdempotencyOutcome:
    record: IdempotencyRecord
    is_replay: bool


def begin(
    db: Session, *, key: str, command: str, payload: dict[str, Any]
) -> IdempotencyOutcome:
    """INV-IDEM-001/002. Misma key + mismo payload -> replay del resultado ya
    completado. Misma key + payload distinto -> IdempotencyConflictError
    (mapeado a 409 en la capa API). Key nueva -> crea un registro PENDING que
    el caller debe completar con `complete()`."""
    payload_hash = _hash_payload(payload)
    existing = db.execute(
        select(IdempotencyRecord).where(IdempotencyRecord.key == key)
    ).scalar_one_or_none()

    if existing is not None:
        if existing.payload_hash != payload_hash:
            raise IdempotencyConflictError(
                f"Idempotency-Key '{key}' ya se usó con un payload distinto"
            )
        return IdempotencyOutcome(record=existing, is_replay=existing.status == "COMPLETED")

    record = IdempotencyRecord(
        key=key, command=command, payload_hash=payload_hash, status="PENDING"
    )
    db.add(record)
    db.flush()
    return IdempotencyOutcome(record=record, is_replay=False)


def complete(
    db: Session,
    record: IdempotencyRecord,
    *,
    result: dict[str, Any],
    entity_type: str | None = None,
    entity_id=None,
) -> None:
    record.status = "COMPLETED"
    record.result = result
    record.entity_type = entity_type
    record.entity_id = entity_id
    db.flush()
