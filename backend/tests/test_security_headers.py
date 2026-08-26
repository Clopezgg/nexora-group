from app.core.config import get_settings


def test_security_headers_present_on_a_normal_response(client):
    response = client.get("/readyz")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert response.headers["content-security-policy"] == "default-src 'none'; frame-ancestors 'none'"
    assert "strict-transport-security" not in {k.lower() for k in response.headers.keys()}


def test_security_headers_present_even_on_csrf_rejection(client):
    """Security headers must apply to every response, including error
    paths from other middleware -- not only the happy path."""
    response = client.post(
        "/api/master-data/companies",
        json={"name": "x"},
        headers={"Origin": "https://attacker.example"},
    )
    assert response.status_code == 403, response.text
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"


def test_docs_endpoint_never_gets_the_strict_csp(client):
    """A strict default-src 'none' CSP would break Swagger UI's real CDN
    script/style loading -- /docs and /redoc are deliberately exempt."""
    response = client.get("/docs")
    assert response.status_code == 200, response.text
    assert "content-security-policy" not in {k.lower() for k in response.headers.keys()}


def test_hsts_only_present_in_production(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "app_env", "production")
    response = client.get("/readyz")
    assert "strict-transport-security" in {k.lower() for k in response.headers.keys()}
