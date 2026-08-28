import base64
import hashlib
import os

from app.core.config import get_settings
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


def test_edit_pin_is_hashed_and_capability_is_signed_and_tamper_proof():
    settings = get_settings()
    old_salt = settings.edit_access_token_salt
    old_digest = settings.edit_access_token_digest
    old_ttl = settings.edit_access_ttl_seconds
    test_pin = "246810"
    try:
        _configure_test_pin(settings, test_pin)
        assert edit_access_service.verify_pin(test_pin, settings)
        assert not edit_access_service.verify_pin("000000", settings)

        import uuid

        capability, expires_at = edit_access_service.issue_capability(
            user_id=uuid.uuid4(), settings=settings
        )
        assert expires_at > 0
        assert edit_access_service.verify_capability(capability, settings)

        payload, signature = capability.split(".", 1)
        replacement = "A" if signature[-1] != "A" else "B"
        assert not edit_access_service.verify_capability(
            f"{payload}.{signature[:-1]}{replacement}", settings
        )

        settings.edit_access_ttl_seconds = -1
        expired, _ = edit_access_service.issue_capability(user_id=uuid.uuid4(), settings=settings)
        assert not edit_access_service.verify_capability(expired, settings)
    finally:
        settings.edit_access_token_salt = old_salt
        settings.edit_access_token_digest = old_digest
        settings.edit_access_ttl_seconds = old_ttl


def test_edit_guard_requires_unlock_then_allows_request_to_reach_route(client):
    settings = get_settings()
    old_required = settings.edit_access_required
    old_salt = settings.edit_access_token_salt
    old_digest = settings.edit_access_token_digest
    test_pin = "864209"
    try:
        settings.edit_access_required = True
        _configure_test_pin(settings, test_pin)

        login = client.post(
            "/api/auth/login",
            json={"email": BOOTSTRAP_ADMIN_EMAIL, "password": BOOTSTRAP_ADMIN_PASSWORD},
        )
        assert login.status_code == 200, login.text

        import uuid

        missing_capability = client.patch(
            f"/api/master-data/companies/{uuid.uuid4()}/profile",
            json={"legalName": "Test"},
        )
        assert missing_capability.status_code == 428

        wrong = client.post("/api/edit-access/verify", json={"token": "111111"})
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
    finally:
        settings.edit_access_required = old_required
        settings.edit_access_token_salt = old_salt
        settings.edit_access_token_digest = old_digest
