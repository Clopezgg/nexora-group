import base64
import hashlib
import os
import secrets

from app.core.config import get_settings
from app.models.edit_access import EditAccessEvent
from app.services import edit_access_service
from tests.conftest import BOOTSTRAP_ADMIN_EMAIL, BOOTSTRAP_ADMIN_PASSWORD


def _configure_test_pin(settings, pin: str) -> None:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        pin.encode("utf-8"),
        salt,
        settings.edit_access_pbkdf2_iterations,
    )
    settings.edit_access_token_salt = base64.urlsafe_b64encode(salt).decode("ascii")
    settings.edit_access_token_digest = base64.urlsafe_b64encode(digest).decode("ascii")


def test_edit_pin_is_hashed_and_capability_is_signed_tamper_proof_and_session_bound():
    settings = get_settings()
    old_salt = settings.edit_access_token_salt
    old_digest = settings.edit_access_token_digest
    old_ttl = settings.edit_access_ttl_seconds
    test_pin = secrets.token_urlsafe(12)
    wrong_pin = secrets.token_urlsafe(12)
    session_token = secrets.token_urlsafe(24)
    try:
        _configure_test_pin(settings, test_pin)
        assert edit_access_service.verify_pin(test_pin, settings)
        assert not edit_access_service.verify_pin(wrong_pin, settings)

        import uuid

        capability, expires_at = edit_access_service.issue_capability(
            user_id=uuid.uuid4(), session_token=session_token, settings=settings
        )
        assert expires_at > 0
        assert edit_access_service.verify_capability(
            capability, session_token=session_token, settings=settings
        )
        assert not edit_access_service.verify_capability(
            capability, session_token=secrets.token_urlsafe(24), settings=settings
        )

        payload, signature = capability.split(".", 1)
        replacement = "A" if signature[-1] != "A" else "B"
        assert not edit_access_service.verify_capability(
            f"{payload}.{signature[:-1]}{replacement}",
            session_token=session_token,
            settings=settings,
        )

        settings.edit_access_ttl_seconds = -1
        expired, _ = edit_access_service.issue_capability(
            user_id=uuid.uuid4(), session_token=session_token, settings=settings
        )
        assert not edit_access_service.verify_capability(
            expired, session_token=session_token, settings=settings
        )
    finally:
        settings.edit_access_token_salt = old_salt
        settings.edit_access_token_digest = old_digest
        settings.edit_access_ttl_seconds = old_ttl


def test_edit_guard_requires_unlock_then_allows_request_to_reach_route(client, db_session):
    settings = get_settings()
    old_required = settings.edit_access_required
    old_salt = settings.edit_access_token_salt
    old_digest = settings.edit_access_token_digest
    old_max_uses = settings.edit_access_max_uses
    test_pin = secrets.token_urlsafe(12)
    wrong_pin = secrets.token_urlsafe(12)
    try:
        settings.edit_access_required = True
        settings.edit_access_max_uses = 1
        _configure_test_pin(settings, test_pin)

        login = client.post(
            "/api/auth/login",
            json={"email": BOOTSTRAP_ADMIN_EMAIL, "password": BOOTSTRAP_ADMIN_PASSWORD},
        )
        assert login.status_code == 200, login.text

        # ActiveUIContext changes only navigation state. Selecting a project must
        # remain possible without unlocking business-data editing.
        context_update = client.put("/api/context", json={"activeProjectId": None})
        assert context_update.status_code == 200, context_update.text

        import uuid

        missing_capability = client.patch(
            f"/api/master-data/companies/{uuid.uuid4()}/profile",
            json={"legalName": "Test"},
        )
        assert missing_capability.status_code == 428

        wrong = client.post("/api/edit-access/verify", json={"token": wrong_pin})
        assert wrong.status_code == 403

        unlocked = client.post("/api/edit-access/verify", json={"token": test_pin})
        assert unlocked.status_code == 200, unlocked.text
        body = unlocked.json()
        assert body["capability"]
        assert body["expiresAt"] > 0

        reached_route = client.patch(
            f"/api/master-data/companies/{uuid.uuid4()}/profile",
            json={"legalName": "Test"},
            headers={"X-Nexora-Edit-Access": body["capability"]},
        )
        # The random company does not exist. 404 proves the request passed the
        # edit gate and reached the normal authenticated/RBAC route.
        assert reached_route.status_code == 404, reached_route.text
        exhausted = client.patch(
            f"/api/master-data/companies/{uuid.uuid4()}/profile",
            json={"legalName": "Test"},
            headers={"X-Nexora-Edit-Access": body["capability"]},
        )
        assert exhausted.status_code == 428, exhausted.text
        outcomes = [
            (row.success, row.outcome)
            for row in db_session.query(EditAccessEvent)
            .filter(EditAccessEvent.outcome.like("MUTATION_%"))
            .order_by(EditAccessEvent.created_at)
            .all()
        ]
        assert (False, "MUTATION_DENIED") in outcomes
        assert (True, "MUTATION_ALLOWED") in outcomes
    finally:
        settings.edit_access_required = old_required
        settings.edit_access_token_salt = old_salt
        settings.edit_access_token_digest = old_digest
        settings.edit_access_max_uses = old_max_uses


def test_edit_access_rate_limit_locks_repeated_failures(client):
    settings = get_settings()
    old_salt = settings.edit_access_token_salt
    old_digest = settings.edit_access_token_digest
    old_attempts = settings.edit_access_max_attempts
    old_window = settings.edit_access_window_seconds
    valid_pin = secrets.token_urlsafe(12)
    try:
        settings.edit_access_max_attempts = 2
        settings.edit_access_window_seconds = 60
        _configure_test_pin(settings, valid_pin)
        login = client.post(
            "/api/auth/login",
            json={"email": BOOTSTRAP_ADMIN_EMAIL, "password": BOOTSTRAP_ADMIN_PASSWORD},
        )
        assert login.status_code == 200, login.text

        first = client.post(
            "/api/edit-access/verify", json={"token": secrets.token_urlsafe(12)}
        )
        assert first.status_code == 403, first.text
        locked = client.post(
            "/api/edit-access/verify", json={"token": secrets.token_urlsafe(12)}
        )
        assert locked.status_code == 429, locked.text
        still_locked = client.post(
            "/api/edit-access/verify", json={"token": valid_pin}
        )
        assert still_locked.status_code == 429, still_locked.text
    finally:
        settings.edit_access_token_salt = old_salt
        settings.edit_access_token_digest = old_digest
        settings.edit_access_max_attempts = old_attempts
        settings.edit_access_window_seconds = old_window
