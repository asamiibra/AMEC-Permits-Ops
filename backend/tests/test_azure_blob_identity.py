from backend.app.storage.azure_blob import AzureBlobBinaryStore, AzureBlobConfig


def test_azure_blob_store_exposes_provider_identity():
    store = AzureBlobBinaryStore.__new__(AzureBlobBinaryStore)
    store.config = AzureBlobConfig(
        account_url="https://storage.example",
        container="managed-artifacts",
        managed_identity_client_id="88888888-8888-4888-8888-888888888888",
    )

    assert store.provider_id == "azure-blob"
