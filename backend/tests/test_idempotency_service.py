import pytest

from app.domain.errors import IdempotencyConflictError
from app.services import idempotency_service


def test_same_key_and_payload_replays_completed_result(db_session):
    """INV-IDEM-001."""
    outcome = idempotency_service.begin(
        db_session, key="k1", command="create_remittance", payload={"amount": 100}
    )
    assert outcome.is_replay is False
    idempotency_service.complete(
        db_session, outcome.record, result={"id": "abc"}, entity_type="remittance"
    )
    db_session.commit()

    replay = idempotency_service.begin(
        db_session, key="k1", command="create_remittance", payload={"amount": 100}
    )
    assert replay.is_replay is True
    assert replay.record.result == {"id": "abc"}


def test_same_key_different_payload_conflicts(db_session):
    """INV-IDEM-002."""
    idempotency_service.begin(db_session, key="k2", command="create_remittance", payload={"amount": 100})
    db_session.commit()

    with pytest.raises(IdempotencyConflictError):
        idempotency_service.begin(
            db_session, key="k2", command="create_remittance", payload={"amount": 200}
        )


def test_pending_replay_is_not_marked_completed(db_session):
    outcome = idempotency_service.begin(db_session, key="k3", command="cmd", payload={"a": 1})
    db_session.commit()
    assert outcome.is_replay is False

    still_pending = idempotency_service.begin(db_session, key="k3", command="cmd", payload={"a": 1})
    assert still_pending.is_replay is False
