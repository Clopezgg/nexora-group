"""Carga de secretos desde Azure Key Vault hacia variables de entorno."""

import os

_SECRET_TO_ENV_VAR = {
    "database-url": "DATABASE_URL",
    "secret-key": "SECRET_KEY",
    "bootstrap-admin-password": "BOOTSTRAP_ADMIN_PASSWORD",
    "edit-access-token-salt": "EDIT_ACCESS_TOKEN_SALT",
    "edit-access-token-digest": "EDIT_ACCESS_TOKEN_DIGEST",
}
_OPTIONAL_SECRETS = {"edit-access-token-salt", "edit-access-token-digest"}


def load_secrets_from_key_vault(vault_uri: str) -> None:
    from azure.core.exceptions import ResourceNotFoundError
    from azure.identity import DefaultAzureCredential
    from azure.keyvault.secrets import SecretClient

    client = SecretClient(vault_url=vault_uri, credential=DefaultAzureCredential())

    for secret_name, env_var in _SECRET_TO_ENV_VAR.items():
        if os.environ.get(env_var):
            continue
        try:
            secret = client.get_secret(secret_name)
        except ResourceNotFoundError:
            if secret_name in _OPTIONAL_SECRETS:
                # Safe fail-closed: the API keeps serving, but protected edits
                # remain unavailable until the owner configures both secrets.
                continue
            raise
        if secret.value:
            os.environ[env_var] = secret.value
