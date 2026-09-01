import base64
import hashlib
import os
import secrets
import uuid

import pytest
from pydantic import ValidationError

from app.core.config import Settings, get_settings
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


def test_edit_pin_verifies_only_against_the_configured_digest():
    """El PIN se compara SOLO contra el digest PBKDF2 configurado. Acepta
    tanto un PIN corto (p.ej. 6 dígitos) como un secreto largo."""
    settings = get_settings()
    old_salt = settings.edit_access_token_salt
    old_digest = settings.edit_access_token_digest
    for pin in ("051012", secrets.token_urlsafe(64)):
        try:
            _configure_test_pin(settings, pin)
            assert edit_access_service.verify_pin(pin, settings)
            assert not edit_access_service.verify_pin(pin + "x", settings)
        finally:
            settings.edit_access_token_salt = old_salt
            settings.edit_access_token_digest = old_digest


def test_administrator_password_is_not_accepted_as_the_edit_pin(client, db_session):
    """ORDEN MAESTRA §12/§27 — el password del Administrator NO funciona como
    PIN de Protected Edit. Son credenciales independientes; no hay fallback."""
    settings = get_settings()
    old_salt, old_digest = settings.edit_access_token_salt, settings.edit_access_token_digest
    try:
        _configure_test_pin(settings, "051012")
        from tests.helpers import login_admin

        login_admin(client)
        # El password del Administrator -> rechazado (403), no una capability.
        bad = client.post("/api/edit-access/verify", json={"token": BOOTSTRAP_ADMIN_PASSWORD})
        assert bad.status_code == 403, bad.text
        # El PIN real -> capability temporal.
        good = client.post("/api/edit-access/verify", json={"token": "051012"})
        assert good.status_code == 200, good.text
        assert good.json()["capability"]
        assert good.json()["usesRemaining"] >= 1
    finally:
        settings.edit_access_token_salt, settings.edit_access_token_digest = old_salt, old_digest


def test_edit_access_verify_is_not_configured_without_server_secrets(client, db_session):
    """Sin `EDIT_ACCESS_TOKEN_SALT`/`DIGEST` la ruta responde 503
    NOT_CONFIGURED — nunca acepta un token de respaldo."""
    settings = get_settings()
    old_salt, old_digest = settings.edit_access_token_salt, settings.edit_access_token_digest
    try:
        settings.edit_access_token_salt = ""
        settings.edit_access_token_digest = ""
        from tests.helpers import login_admin

        login_admin(client)
        r = client.post("/api/edit-access/verify", json={"token": BOOTSTRAP_ADMIN_PASSWORD})
        assert r.status_code == 503, r.text
    finally:
        settings.edit_access_token_salt, settings.edit_access_token_digest = old_salt, old_digest


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


def test_edit_guard_rejection_keeps_security_and_correlation_headers(client, db_session):
    settings = get_settings()
    old_required = settings.edit_access_required
    old_salt = settings.edit_access_token_salt
    old_digest = settings.edit_access_token_digest
    test_pin = secrets.token_urlsafe(12)
    try:
        settings.edit_access_required = True
        _configure_test_pin(settings, test_pin)
        login = client.post(
            "/api/auth/login",
            json={"email": BOOTSTRAP_ADMIN_EMAIL, "password": BOOTSTRAP_ADMIN_PASSWORD},
        )
        assert login.status_code == 200, login.text

        response = client.patch(
            f"/api/master-data/companies/{uuid.uuid4()}/profile",
            json={"legalName": "Test"},
        )

        assert response.status_code == 428, response.text
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.headers["x-frame-options"] == "DENY"
        correlation_id = response.headers["x-correlation-id"]
        assert correlation_id
        event = (
            db_session.query(EditAccessEvent)
            .filter(EditAccessEvent.outcome == "MUTATION_DENIED")
            .one()
        )
        assert event.correlation_id == correlation_id
    finally:
        settings.edit_access_required = old_required
        settings.edit_access_token_salt = old_salt
        settings.edit_access_token_digest = old_digest


def test_production_settings_reject_the_development_signing_key():
    with pytest.raises(ValidationError, match="SECRET_KEY"):
        Settings(
            app_env="production",
            secret_key="dev-secret-key-change-me",
            edit_access_required=False,
        )


def test_production_settings_require_protected_edit_server_secrets():
    with pytest.raises(ValidationError, match="EDIT_ACCESS_TOKEN"):
        Settings(
            app_env="production",
            secret_key=secrets.token_urlsafe(48),
            edit_access_required=True,
            edit_access_token_salt="",
            edit_access_token_digest="",
        )
