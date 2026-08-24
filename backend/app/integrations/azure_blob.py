"""Cliente real de Azure Blob Storage para el backend de evidencias.

Regla del proyecto: "no mocks presentados como funcionalidad real". Este
módulo no simula un upload exitoso si falta configuración: falla explícito
con EvidenceStorageNotConfigured. No hay todavía endpoints que lo llamen
(el feature de evidencias es de una fase posterior); esto deja la base de
almacenamiento lista y con no filesystem persistente, como exige CLAUDE.md.
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
    if not settings.azure_storage_account_name:
        raise EvidenceStorageNotConfigured(
            "AZURE_STORAGE_ACCOUNT_NAME no está configurado."
        )

    from azure.identity import DefaultAzureCredential
    from azure.storage.blob import BlobServiceClient

    account_url = f"https://{settings.azure_storage_account_name}.blob.core.windows.net"
    service_client = BlobServiceClient(account_url=account_url, credential=DefaultAzureCredential())
    return service_client.get_container_client(settings.evidence_container_name)
