import hashlib
import json
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
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


def _resolve_existing(existing: IdempotencyRecord, *, key: str, payload_hash: str) -> IdempotencyOutcome:
    if existing.payload_hash != payload_hash:
        raise IdempotencyConflictError(
            f"Idempotency-Key '{key}' ya se usó con un payload distinto"
        )
    return IdempotencyOutcome(record=existing, is_replay=existing.status == "COMPLETED")


def begin(
    db: Session, *, key: str, command: str, payload: dict[str, Any]
) -> IdempotencyOutcome:
    """INV-IDEM-001/002. Misma key + mismo payload -> replay del resultado ya
    completado. Misma key + payload distinto -> IdempotencyConflictError
    (mapeado a 409 en la capa API). Key nueva -> crea un registro PENDING que
    el caller debe completar con `complete()`.

    Dos requests concurrentes con la MISMA key pueden ambas ver
    `existing is None` antes de que cualquiera haga commit de su INSERT
    -- `key` es `unique=True` (constraint real), así que la segunda
    inserción siempre choca, pero sin manejar esa colisión el caller que
    pierde la carrera recibía un `IntegrityError` sin capturar en vez
    del replay esperado (el punto entero de una idempotency key es que
    un caller concurrente/reintentado reciba la MISMA respuesta exitosa,
    nunca un error de integridad de datos) -- encontrado con una prueba
    de concurrencia real (`tests/test_concurrency.py`). Se resuelve
    igual que `numbering_service.next_document_number`: SAVEPOINT
    alrededor del INSERT, y si choca, un SELECT ... FOR UPDATE sobre la
    key ya existente -- eso bloquea hasta que la transacción del
    ganador termine (commit libera el lock), momento en el que su
    registro ya está COMPLETED de verdad, no a medio terminar."""
    payload_hash = _hash_payload(payload)
    existing = db.execute(
        select(IdempotencyRecord).where(IdempotencyRecord.key == key)
    ).scalar_one_or_none()

    if existing is not None:
        return _resolve_existing(existing, key=key, payload_hash=payload_hash)

    savepoint = db.begin_nested()
    try:
        record = IdempotencyRecord(
            key=key, command=command, payload_hash=payload_hash, status="PENDING"
        )
        db.add(record)
        db.flush()
        savepoint.commit()
    except IntegrityError:
        savepoint.rollback()
        existing = db.execute(
            select(IdempotencyRecord).where(IdempotencyRecord.key == key).with_for_update()
        ).scalar_one()
        return _resolve_existing(existing, key=key, payload_hash=payload_hash)

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
