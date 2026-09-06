def test_healthz(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readyz(client):
    response = client.get("/readyz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_version_exposes_real_build_metadata_no_auth_required(client):
    """ORDEN MAESTRA §21: /api/version permite certificar
    origin/main == CI == imagen backend == build frontend == producción."""
    response = client.get("/api/version")
    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {"gitSha", "buildTime", "environment"}
    assert body["gitSha"]
    assert body["buildTime"]
    assert body["environment"]


def test_version_never_leaks_secrets(client):
    response = client.get("/api/version")
    body = response.json()
    forbidden = ("secret", "password", "token", "key", "database_url")
    dumped = str(body).lower()
    for word in forbidden:
        assert word not in dumped
