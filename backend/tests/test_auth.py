from tests.conftest import BOOTSTRAP_ADMIN_EMAIL, BOOTSTRAP_ADMIN_PASSWORD


def test_bootstrap_admin_created_on_fresh_database(client):
    response = client.post(
        "/api/auth/login",
        json={"email": BOOTSTRAP_ADMIN_EMAIL, "password": BOOTSTRAP_ADMIN_PASSWORD},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == BOOTSTRAP_ADMIN_EMAIL
    assert "Administrator" in body["roles"]


def test_login_with_invalid_password_returns_401(client):
    response = client.post(
        "/api/auth/login",
        json={"email": BOOTSTRAP_ADMIN_EMAIL, "password": "wrong-password"},
    )
    assert response.status_code == 401


def test_login_with_unknown_email_returns_401(client):
    response = client.post(
        "/api/auth/login",
        json={"email": "nadie@nexora.group", "password": "whatever"},
    )
    assert response.status_code == 401


def test_me_without_session_returns_401(client):
    response = client.get("/api/auth/me")
    assert response.status_code == 401


def test_me_after_login_returns_current_user(client):
    login_response = client.post(
        "/api/auth/login",
        json={"email": BOOTSTRAP_ADMIN_EMAIL, "password": BOOTSTRAP_ADMIN_PASSWORD},
    )
    assert login_response.status_code == 200

    me_response = client.get("/api/auth/me")
    assert me_response.status_code == 200
    assert me_response.json()["email"] == BOOTSTRAP_ADMIN_EMAIL


def test_logout_invalidates_session(client):
    client.post(
        "/api/auth/login",
        json={"email": BOOTSTRAP_ADMIN_EMAIL, "password": BOOTSTRAP_ADMIN_PASSWORD},
    )
    logout_response = client.post("/api/auth/logout")
    assert logout_response.status_code == 204

    me_response = client.get("/api/auth/me")
    assert me_response.status_code == 401


def test_account_locks_after_max_failed_login_attempts(client, db_session):
    """NXR-REQ-0008: sin este guard, un atacante podía intentar
    contraseñas indefinidamente contra la misma cuenta."""
    from app.core.config import get_settings

    settings = get_settings()
    for _ in range(settings.max_login_attempts):
        client.post(
            "/api/auth/login",
            json={"email": BOOTSTRAP_ADMIN_EMAIL, "password": "wrong-password"},
        )

    locked_even_with_correct_password = client.post(
        "/api/auth/login",
        json={"email": BOOTSTRAP_ADMIN_EMAIL, "password": BOOTSTRAP_ADMIN_PASSWORD},
    )
    assert locked_even_with_correct_password.status_code == 423, locked_even_with_correct_password.text


def test_successful_login_resets_failed_attempts(client, db_session):
    from app.models.user import User

    client.post(
        "/api/auth/login",
        json={"email": BOOTSTRAP_ADMIN_EMAIL, "password": "wrong-password"},
    )
    client.post(
        "/api/auth/login",
        json={"email": BOOTSTRAP_ADMIN_EMAIL, "password": "wrong-password"},
    )
    success = client.post(
        "/api/auth/login",
        json={"email": BOOTSTRAP_ADMIN_EMAIL, "password": BOOTSTRAP_ADMIN_PASSWORD},
    )
    assert success.status_code == 200, success.text

    db_session.expire_all()
    user = db_session.query(User).filter(User.email == BOOTSTRAP_ADMIN_EMAIL).one()
    assert user.failed_login_attempts == 0
    assert user.locked_until is None


def test_lockout_expires_after_lockout_window(client, db_session):
    from datetime import datetime, timedelta, timezone

    from app.models.user import User

    user = db_session.query(User).filter(User.email == BOOTSTRAP_ADMIN_EMAIL).one()
    user.failed_login_attempts = 5
    user.locked_until = datetime.now(timezone.utc) - timedelta(minutes=1)
    db_session.commit()

    response = client.post(
        "/api/auth/login",
        json={"email": BOOTSTRAP_ADMIN_EMAIL, "password": BOOTSTRAP_ADMIN_PASSWORD},
    )
    assert response.status_code == 200, response.text


def test_csrf_guard_rejects_a_mismatched_origin(client):
    response = client.post(
        "/api/auth/login",
        json={"email": BOOTSTRAP_ADMIN_EMAIL, "password": BOOTSTRAP_ADMIN_PASSWORD},
        headers={"Origin": "https://attacker.example"},
    )
    assert response.status_code == 403, response.text
    assert response.json()["error"]["code"] == "NXR-AUTH-001"


def test_csrf_guard_allows_the_configured_frontend_origin(client):
    response = client.post(
        "/api/auth/login",
        json={"email": BOOTSTRAP_ADMIN_EMAIL, "password": BOOTSTRAP_ADMIN_PASSWORD},
        headers={"Origin": "http://localhost:5173"},
    )
    assert response.status_code == 200, response.text
