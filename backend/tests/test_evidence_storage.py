import pytest

from app.core.config import Settings
from app.integrations.azure_blob import EvidenceStorageNotConfigured, get_evidence_container_client


def test_raises_when_backend_is_none():
    settings = Settings(evidence_backend="none")
    with pytest.raises(EvidenceStorageNotConfigured):
        get_evidence_container_client(settings)


def test_raises_when_azure_blob_backend_missing_account_name():
    settings = Settings(evidence_backend="azure_blob", azure_storage_account_name=None)
    with pytest.raises(EvidenceStorageNotConfigured):
        get_evidence_container_client(settings)
