from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración centralizada leída desde variables de entorno."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    app_name: str = "Nexora Group"
    database_url: str = "postgresql+psycopg://nexora:nexora@localhost:5432/nexora_dev"
    secret_key: str = "dev-secret-key-change-me"
    frontend_url: str = "http://localhost:5173"

    bootstrap_admin_email: str | None = None
    bootstrap_admin_password: str | None = None

    evidence_backend: str = "none"
    max_evidence_mb: int = 25

    session_cookie_name: str = "nexora_session"
    session_ttl_days: int = 7

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
