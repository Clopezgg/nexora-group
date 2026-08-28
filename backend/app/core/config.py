import os
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

    # Confirmación secundaria para modificar/eliminar información ya guardada.
    # Nunca se conserva el PIN en texto plano. El digest por defecto corresponde
    # a la clave empresarial configurada para esta instancia y puede rotarse por
    # variables de entorno sin tocar el frontend.
    edit_access_required: bool = True
    edit_access_token_salt: str = "fYyyYqkKw3wA1_gSBsp6Yw=="
    edit_access_token_digest: str = "fpyQturFHSsqW1An4hKXeUJOe4wdMjuRTvepcSKOfag="
    edit_access_pbkdf2_iterations: int = 250_000
    edit_access_ttl_seconds: int = 600
    edit_access_max_attempts: int = 5
    edit_access_window_seconds: int = 900

    # "none" (por defecto) | "azure_blob". Ver app/integrations/azure_blob.py.
    evidence_backend: str = "none"
    evidence_container_name: str = "evidence"
    max_evidence_mb: int = 25

    # Azure Key Vault: si está definido y app_env=production, get_settings()
    # sobreescribe DATABASE_URL/SECRET_KEY/BOOTSTRAP_ADMIN_PASSWORD desde el
    # vault antes de construir Settings. Ver app/integrations/azure_keyvault.py.
    azure_key_vault_uri: str | None = None

    # Azure Blob Storage (evidence_backend=azure_blob).
    azure_storage_account_name: str | None = None

    # Azure Monitor / Application Insights. Vacío = telemetría desactivada.
    applicationinsights_connection_string: str | None = None

    session_cookie_name: str = "nexora_session"
    session_ttl_days: int = 7

    # NXR-REQ-0008 (brute-force lockout).
    max_login_attempts: int = 5
    lockout_minutes: int = 15

    # NXR-REQ-0107 (app-layer rate limiting, independiente de Azure Front
    # Door/WAF). Por IP, no por cuenta -- el lockout de arriba ya protege
    # una cuenta conocida; esto protege contra fuerza bruta distribuida
    # entre muchas cuentas o ruido/DoS desde un mismo origen.
    login_rate_limit_max_attempts: int = 20
    login_rate_limit_window_seconds: int = 60

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    # Solo se intenta contactar Key Vault en producción: en local/dev/tests no
    # hay credenciales Azure disponibles y no debe bloquear el arranque.
    if os.environ.get("APP_ENV") == "production" and os.environ.get("AZURE_KEY_VAULT_URI"):
        from app.integrations.azure_keyvault import load_secrets_from_key_vault

        load_secrets_from_key_vault(os.environ["AZURE_KEY_VAULT_URI"])

    return Settings()
