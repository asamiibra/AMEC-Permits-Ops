from backend.app.storage.azure_blob import AzureBlobBinaryStore, AzureBlobConfig
from backend.app.storage.errors import StorageErrorCode
from backend.app.storage.port import StorageLocator


def test_azure_blob_store_exposes_provider_identity():
    store = AzureBlobBinaryStore.__new__(AzureBlobBinaryStore)
    store.config = AzureBlobConfig(
        account_url="https://storage.example",
        container="managed-artifacts",
        managed_identity_client_id="88888888-8888-4888-8888-888888888888",
    )

    assert store.provider_id == "azure-blob"


def test_azure_blob_store_resolves_legacy_unicode_filename_locator():
    class Missing:
        def download_blob(self, **_):
            error = RuntimeError("not found")
            error.status_code = 404
            raise error

    class Present:
        def download_blob(self, **_):
            class Stream:
                @staticmethod
                def readall():
                    return b"arabic filename bytes"
            return Stream()

    class Blob:
        def __init__(self, name):
            self.name = name

    class Container:
        def get_blob_client(self, name):
            return Missing() if "????" in name else Present()

        def list_blobs(self, *, name_starts_with):
            return [Blob(name_starts_with + "اسم الملف.pdf")]

    store = AzureBlobBinaryStore.__new__(AzureBlobBinaryStore)
    store.config = AzureBlobConfig(
        account_url="https://storage.example",
        container="managed-artifacts",
        managed_identity_client_id="88888888-8888-4888-8888-888888888888",
    )
    store._container = Container()
    locator = StorageLocator(
        "azure-blob",
        "managed-artifacts",
        "proposal-sources/p/documents/document/version/????.pdf",
    )

    with store.open_read(locator) as stream:
        assert stream.read() == b"arabic filename bytes"
