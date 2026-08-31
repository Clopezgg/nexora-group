import os
from functools import lru_cache
from urllib.parse import urlparse

from pydantic import model_validator
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
    # El PIN nunca se conserva en texto plano y tampoco existe un digest/salt
    # válido dentro del repositorio. Producción debe inyectarlos mediante
    # variables de entorno/secretRef o Azure Key Vault.
    edit_access_required: bool = True
    edit_access_token_salt: str = ""
    edit_access_token_digest: str = ""
    edit_access_pbkdf2_iterations: int = 250_000
    edit_access_ttl_seconds: int = 600
    edit_access_max_attempts: int = 5
    edit_access_window_seconds: int = 900
    edit_access_max_uses: int = 5

    # "none" (por defecto) | "azure_blob". Ver app/integrations/azure_blob.py.
    evidence_backend: str = "none"
    evidence_container_name: str = "evidence"
    max_evidence_mb: int = 25

    azure_key_vault_uri: str | None = None
    azure_storage_account_name: str | None = None
    # clientId de la User Assigned Managed Identity del Container App. Se pasa
    # explicitamente a DefaultAzureCredential para que, cuando el contenedor
    # tenga mas de una identidad asignada (o el IMDS no infiera cual usar),
    # la autenticacion contra Blob Storage sea determinista. Lo inyecta el
    # Bicep (infra/modules/containerapps.bicep) como AZURE_CLIENT_ID.
    azure_client_id: str | None = None
    # Solo para desarrollo/E2E con un emulador compatible (Azurite). Producción
    # sigue usando Managed Identity + `azure_storage_account_name`; nunca se
    # necesita ni se commitea una connection string productiva.
    azure_storage_connection_string: str | None = None
    applicationinsights_connection_string: str | None = None

    session_cookie_name: str = "nexora_session"
    session_ttl_days: int = 7

    max_login_attempts: int = 5
    lockout_minutes: int = 15
    login_rate_limit_max_attempts: int = 20
    login_rate_limit_window_seconds: int = 60

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def edit_access_configured(self) -> bool:
        return bool(self.edit_access_token_salt.strip() and self.edit_access_token_digest.strip())

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        if not self.is_production:
            return self
        if self.secret_key == "dev-secret-key-change-me" or len(self.secret_key) < 32:
            raise ValueError("SECRET_KEY must be a unique value of at least 32 characters in production")
        if self.edit_access_required and not self.edit_access_configured:
            raise ValueError(
                "EDIT_ACCESS_TOKEN_SALT and EDIT_ACCESS_TOKEN_DIGEST are required in production"
            )

        # FRONTEND_URL is both the CORS allow-origin and the CSRF Origin
        # authority. In production it must therefore be one exact HTTPS
        # origin, never a path, wildcard-like value or cleartext URL.
        frontend = urlparse(self.frontend_url)
        if (
            frontend.scheme != "https"
            or not frontend.netloc
            or frontend.path
            or frontend.params
            or frontend.query
            or frontend.fragment
            or frontend.username
            or frontend.password
        ):
            raise ValueError(
                "FRONTEND_URL must be an exact HTTPS origin without path, query, fragment, or credentials in production"
            )
        return self


@lru_cache
def get_settings() -> Settings:
    if os.environ.get("APP_ENV") == "production" and os.environ.get("AZURE_KEY_VAULT_URI"):
        from app.integrations.azure_keyvault import load_secrets_from_key_vault

        load_secrets_from_key_vault(os.environ["AZURE_KEY_VAULT_URI"])

    return Settings()
