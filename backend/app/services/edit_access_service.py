"""Secondary confirmation for mutations of persisted data.

This is not an authentication replacement. Every protected route still performs
normal session/RBAC/company checks. The capability is short-lived, session-bound
and has a finite server-side use count.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.edit_access import EditAccessCapability


def _restore_padding(value: str) -> str:
    return value + "=" * (-len(value) % 4)


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(_restore_padding(value).encode("ascii"))


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _session_fingerprint(session_token: str, settings: Settings) -> str:
    return hmac.new(
        settings.secret_key.encode("utf-8"), session_token.encode("utf-8"), hashlib.sha256
    ).hexdigest()


def verify_pin(pin: str, settings: Settings) -> bool:
    # Bound hostile payload size, but permit strong password-manager generated
    # re-authentication credentials used as the production fallback PIN.
    if not settings.edit_access_configured or not pin or len(pin) > 256:
        return False
    try:
        salt = _b64decode(settings.edit_access_token_salt)
        expected = _b64decode(settings.edit_access_token_digest)
    except (ValueError, UnicodeEncodeError):
        return False
    candidate = hashlib.pbkdf2_hmac(
        "sha256", pin.encode("utf-8"), salt, settings.edit_access_pbkdf2_iterations
    )
    return hmac.compare_digest(candidate, expected)


def issue_capability(
    *, user_id: uuid.UUID, session_token: str, settings: Settings
) -> tuple[str, int]:
    expires_at = int(time.time()) + settings.edit_access_ttl_seconds
    payload = {
        "sub": str(user_id),
        "sid": _session_fingerprint(session_token, settings),
        "jti": str(uuid.uuid4()),
        "exp": expires_at,
        "purpose": "edit-access",
    }
    raw_payload = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    encoded_payload = _b64encode(raw_payload)
    signature = hmac.new(
        settings.secret_key.encode("utf-8"), encoded_payload.encode("ascii"), hashlib.sha256
    ).digest()
    return f"{encoded_payload}.{_b64encode(signature)}", expires_at


def _verified_claims(
    token: str | None, *, session_token: str | None, settings: Settings
) -> dict | None:
    if not token or not session_token or "." not in token:
        return None
    encoded_payload, encoded_signature = token.split(".", 1)
    expected_signature = hmac.new(
        settings.secret_key.encode("utf-8"), encoded_payload.encode("ascii"), hashlib.sha256
    ).digest()
    if not hmac.compare_digest(encoded_signature, _b64encode(expected_signature)):
        return None
    try:
        raw_payload = base64.urlsafe_b64decode(_restore_padding(encoded_payload))
        payload = json.loads(raw_payload.decode("utf-8"))
        expires_at = int(payload["exp"])
        uuid.UUID(str(payload["sub"]))
        uuid.UUID(str(payload["jti"]))
        supplied_sid = str(payload["sid"])
    except (KeyError, TypeError, ValueError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    if payload.get("purpose") != "edit-access":
        return None
    if not hmac.compare_digest(supplied_sid, _session_fingerprint(session_token, settings)):
        return None
    if expires_at < int(time.time()):
        return None
    return payload


def verify_capability(
    token: str | None, *, session_token: str | None, settings: Settings
) -> bool:
    return _verified_claims(token, session_token=session_token, settings=settings) is not None


def persist_capability(
    db: Session,
    *,
    token: str,
    session_token: str,
    user_id: uuid.UUID,
    settings: Settings,
) -> EditAccessCapability:
    claims = _verified_claims(token, session_token=session_token, settings=settings)
    if claims is None or uuid.UUID(str(claims["sub"])) != user_id:
        raise ValueError("Capability de edición inválido")
    row = EditAccessCapability(
        id=uuid.UUID(str(claims["jti"])),
        user_id=user_id,
        expires_at=datetime.fromtimestamp(int(claims["exp"]), tz=timezone.utc),
        uses_remaining=max(1, settings.edit_access_max_uses),
    )
    db.add(row)
    db.flush()
    return row


def consume_capability(
    db: Session,
    token: str | None,
    *,
    session_token: str | None,
    settings: Settings,
) -> bool:
    claims = _verified_claims(token, session_token=session_token, settings=settings)
    if claims is None:
        return False
    jti = uuid.UUID(str(claims["jti"]))
    user_id = uuid.UUID(str(claims["sub"]))
    row = db.execute(
        select(EditAccessCapability)
        .where(EditAccessCapability.id == jti, EditAccessCapability.user_id == user_id)
        .with_for_update()
    ).scalar_one_or_none()
    if row is None or row.uses_remaining <= 0:
        return False
    now = datetime.now(timezone.utc)
    expires_at = row.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < now:
        return False
    row.uses_remaining -= 1
    row.last_used_at = now
    db.flush()
    return True
