import pytest

from app.core.config import Settings
from azure.core.exceptions import ResourceNotFoundError

from app.integrations.azure_blob import (
    EvidenceStorageNotConfigured,
    delete_blob_if_exists,
    get_evidence_container_client,
)


def test_raises_when_backend_is_none():
    settings = Settings(evidence_backend="none")
    with pytest.raises(EvidenceStorageNotConfigured):
        get_evidence_container_client(settings)


def test_raises_when_azure_blob_backend_missing_account_name():
    settings = Settings(evidence_backend="azure_blob", azure_storage_account_name=None)
    with pytest.raises(EvidenceStorageNotConfigured):
        get_evidence_container_client(settings)


def test_delete_blob_is_idempotent_when_blob_is_already_gone():
    class MissingBlobContainer:
        def delete_blob(self, blob_key: str):
            raise ResourceNotFoundError("already gone")

    delete_blob_if_exists(MissingBlobContainer(), "company/missing.pdf")
