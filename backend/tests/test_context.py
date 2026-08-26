from tests.conftest import BOOTSTRAP_ADMIN_EMAIL, BOOTSTRAP_ADMIN_PASSWORD


def _login(client):
    client.post(
        "/api/auth/login",
        json={"email": BOOTSTRAP_ADMIN_EMAIL, "password": BOOTSTRAP_ADMIN_PASSWORD},
    )


def test_get_context_requires_auth(client):
    response = client.get("/api/context")
    assert response.status_code == 401


def test_get_context_defaults_to_no_active_project(client):
    _login(client)
    response = client.get("/api/context")
    assert response.status_code == 200
    assert response.json() == {"activeProjectId": None, "activeProjectName": None}


def test_set_context_with_unknown_project_returns_400(client):
    _login(client)
    response = client.put(
        "/api/context", json={"activeProjectId": "00000000-0000-0000-0000-000000000000"}
    )
    assert response.status_code == 400
