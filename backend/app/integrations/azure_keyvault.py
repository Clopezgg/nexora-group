"""Carga de secretos desde Azure Key Vault hacia variables de entorno.

Se usa solo en producción (ver app/core/config.py). En local/dev/tests las
variables de entorno normales siguen siendo la única fuente de configuración.
"""

import os

_SECRET_TO_ENV_VAR = {
    "database-url": "DATABASE_URL",
    "secret-key": "SECRET_KEY",
    "bootstrap-admin-password": "BOOTSTRAP_ADMIN_PASSWORD",
}


def load_secrets_from_key_vault(vault_uri: str) -> None:
    from azure.identity import DefaultAzureCredential
    from azure.keyvault.secrets import SecretClient

    client = SecretClient(vault_url=vault_uri, credential=DefaultAzureCredential())

    for secret_name, env_var in _SECRET_TO_ENV_VAR.items():
        if os.environ.get(env_var):
            # La variable de entorno explícita (p.ej. inyectada por Container Apps
            # vía secretRef) tiene prioridad sobre volver a pedirla al vault.
            continue
        secret = client.get_secret(secret_name)
        if secret.value:
            os.environ[env_var] = secret.value
