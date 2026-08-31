"""Cliente real de Azure Blob Storage para el backend de evidencias.

Producción usa Azure Blob con Managed Identity. Desarrollo/E2E puede apuntar
explícitamente a un emulador compatible mediante
`AZURE_STORAGE_CONNECTION_STRING`; esto permite probar uploads reales contra
Azurite sin introducir un backend falso ni persistencia local en la app.
"""

from app.core.config import Settings


class EvidenceStorageNotConfigured(RuntimeError):
    pass


def get_evidence_container_client(settings: Settings):
    if settings.evidence_backend != "azure_blob":
        raise EvidenceStorageNotConfigured(
            f"evidence_backend={settings.evidence_backend!r}: configura "
            "EVIDENCE_BACKEND=azure_blob para habilitar el almacenamiento de evidencias."
        )

    from azure.storage.blob import BlobServiceClient

    if settings.azure_storage_connection_string:
        if settings.is_production:
            raise EvidenceStorageNotConfigured(
                "AZURE_STORAGE_CONNECTION_STRING no se admite en producción; usa Managed Identity."
            )
        service_client = BlobServiceClient.from_connection_string(
            settings.azure_storage_connection_string
        )
        container_client = service_client.get_container_client(settings.evidence_container_name)
        from azure.core.exceptions import ResourceExistsError

        try:
            container_client.create_container()
        except ResourceExistsError:
            pass
        return container_client

    if not settings.azure_storage_account_name:
        raise EvidenceStorageNotConfigured(
            "AZURE_STORAGE_ACCOUNT_NAME no está configurado."
        )

    from azure.identity import DefaultAzureCredential

    account_url = f"https://{settings.azure_storage_account_name}.blob.core.windows.net"
    credential_kwargs: dict[str, str] = {}
    if settings.azure_client_id:
        # UAMI determinista: sin esto DefaultAzureCredential no sabe cual de
        # las identidades asignadas usar cuando hay mas de una.
        credential_kwargs["managed_identity_client_id"] = settings.azure_client_id
    credential = DefaultAzureCredential(**credential_kwargs)
    service_client = BlobServiceClient(account_url=account_url, credential=credential)
    return service_client.get_container_client(settings.evidence_container_name)


def evidence_storage_is_reachable(settings: Settings) -> tuple[bool, str | None]:
    """Best-effort readiness probe for the private evidence container.

    Returns (ok, detail). Never raises, never exposes credentials/URL. Used by
    /readyz so the Container App is not reported healthy when
    EVIDENCE_BACKEND=azure_blob but the managed identity cannot reach Blob
    Storage. A single bounded retry absorbs eventual RBAC propagation right
    after a deploy without adding sleeps to the hot path.
    """
    if settings.evidence_backend != "azure_blob":
        return True, None
    last_detail: str | None = None
    for attempt in range(2):
        try:
            container_client = get_evidence_container_client(settings)
            container_client.get_container_properties()
            return True, None
        except Exception as exc:  # noqa: BLE001 - readiness nunca debe romper
            last_detail = type(exc).__name__
            if attempt == 0:
                import time as _time

                _time.sleep(0.5)
    return False, last_detail


def delete_blob_if_exists(container_client, blob_key: str) -> None:
    """Delete a compensation target without failing if it is already gone."""
    from azure.core.exceptions import ResourceNotFoundError

    try:
        container_client.delete_blob(blob_key)
    except ResourceNotFoundError:
        pass
