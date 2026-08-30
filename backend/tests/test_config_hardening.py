import pytest

from app.core.config import Settings


_BASE_PRODUCTION = {
    "app_env": "production",
    "secret_key": "s" * 32,
    "edit_access_token_salt": "test-salt",
    "edit_access_token_digest": "test-digest",
}


def test_production_requires_https_frontend_origin():
    with pytest.raises(ValueError, match="FRONTEND_URL must be an exact HTTPS origin"):
        Settings(**_BASE_PRODUCTION, frontend_url="http://example.com")


def test_production_rejects_frontend_origin_with_path():
    with pytest.raises(ValueError, match="FRONTEND_URL must be an exact HTTPS origin"):
        Settings(**_BASE_PRODUCTION, frontend_url="https://example.com/app")


def test_production_accepts_exact_https_frontend_origin():
    settings = Settings(**_BASE_PRODUCTION, frontend_url="https://example.com")
    assert settings.frontend_url == "https://example.com"
