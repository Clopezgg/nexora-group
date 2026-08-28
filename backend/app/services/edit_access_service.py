"""Secondary confirmation for mutations of persisted data.

This is intentionally *not* an authentication replacement. Every protected
route still performs the normal session/RBAC/company checks. The capability is
an additional short-lived confirmation required for PUT/PATCH/DELETE requests
and is cryptographically bound to the authenticated session that requested it.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
import uuid

from app.core.config import Settings


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value.encode("ascii"))


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _restore_padding(value: str) -> str:
    return value + "=" * (-len(value) % 4)


def _session_fingerprint(session_token: str, settings: Settings) -> str:
    return hmac.new(
        settings.secret_key.encode("utf-8"),
        session_token.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def verify_pin(pin: str, settings: Settings) -> bool:
    if not pin or len(pin) > 32:
        return False
    salt = _b64decode(settings.edit_access_token_salt)
    expected = _b64decode(settings.edit_access_token_digest)
    candidate = hashlib.pbkdf2_hmac(
        "sha256",
        pin.encode("utf-8"),
        salt,
        settings.edit_access_pbkdf2_iterations,
    )
    return hmac.compare_digest(candidate, expected)


def issue_capability(
    *, user_id: uuid.UUID, session_token: str, settings: Settings
) -> tuple[str, int]:
    expires_at = int(time.time()) + settings.edit_access_ttl_seconds
    payload = {
        "sub": str(user_id),
        "sid": _session_fingerprint(session_token, settings),
        "exp": expires_at,
        "purpose": "edit-access",
    }
    raw_payload = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    encoded_payload = _b64encode(raw_payload)
    signature = hmac.new(
        settings.secret_key.encode("utf-8"),
        encoded_payload.encode("ascii"),
        hashlib.sha256,
    ).digest()
    return f"{encoded_payload}.{_b64encode(signature)}", expires_at


def verify_capability(
    token: str | None, *, session_token: str | None, settings: Settings
) -> bool:
    if not token or not session_token or "." not in token:
        return False
    encoded_payload, encoded_signature = token.split(".", 1)
    expected_signature = hmac.new(
        settings.secret_key.encode("utf-8"),
        encoded_payload.encode("ascii"),
        hashlib.sha256,
    ).digest()
    try:
        supplied_signature = base64.urlsafe_b64decode(_restore_padding(encoded_signature))
        raw_payload = base64.urlsafe_b64decode(_restore_padding(encoded_payload))
        payload = json.loads(raw_payload.decode("utf-8"))
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
        return False
    if not hmac.compare_digest(supplied_signature, expected_signature):
        return False
    if payload.get("purpose") != "edit-access":
        return False
    try:
        expires_at = int(payload["exp"])
        uuid.UUID(str(payload["sub"]))
        supplied_session_fingerprint = str(payload["sid"])
    except (KeyError, TypeError, ValueError):
        return False
    if not hmac.compare_digest(
        supplied_session_fingerprint,
        _session_fingerprint(session_token, settings),
    ):
        return False
    return expires_at >= int(time.time())
