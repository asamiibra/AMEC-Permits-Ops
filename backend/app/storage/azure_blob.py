from __future__ import annotations

import hashlib
import io
import time
from dataclasses import dataclass
from typing import BinaryIO

from .errors import StorageError, StorageErrorCode
from .path_policy import normalize_relative_path
from .port import (
    BinaryStorePort,
    StorageCapabilities,
    StorageHealth,
    StorageLocator,
    StoragePage,
    StorageStat,
    StorageTarget,
    TemporaryObject,
)


@dataclass(frozen=True)
class AzureBlobConfig:
    account_url: str
    container: str
    managed_identity_client_id: str
    provider_id: str = "azure-blob"


class AzureBlobBinaryStore(BinaryStorePort):
    """Durable managed-artifact store backed by private Azure Blob Storage.

    The Azure SDK and credential are loaded only when this provider is selected.
    Production uses ``DefaultAzureCredential`` with the dedicated runtime UAMI;
    no account key or connection string is accepted by this adapter.
    """

    def __init__(self, config: AzureBlobConfig):
        if not config.account_url or not config.container or not config.managed_identity_client_id:
            raise StorageError(StorageErrorCode.CONFIGURATION_ERROR, "Azure Blob account, container and UAMI are required")
        self.config = config
        try:
            from azure.identity import DefaultAzureCredential
            from azure.storage.blob import BlobServiceClient
        except ImportError as exc:
            raise StorageError(StorageErrorCode.CONFIGURATION_ERROR, "Azure Blob dependencies are not installed") from exc
        try:
            credential = DefaultAzureCredential(managed_identity_client_id=config.managed_identity_client_id)
            self._container = BlobServiceClient(config.account_url, credential=credential).get_container_client(config.container)
        except Exception as exc:
            raise StorageError(StorageErrorCode.CONFIGURATION_ERROR, "Azure Blob client initialization failed") from exc

    def _locator(self, relative_path: str) -> StorageLocator:
        return StorageLocator(self.config.provider_id, self.config.container, normalize_relative_path(relative_path))

    def _blob(self, relative_path: str):
        return self._container.get_blob_client(normalize_relative_path(relative_path))

    @staticmethod
    def _map_error(exc: Exception, message: str = "Azure Blob operation failed") -> StorageError:
        status = getattr(exc, "status_code", None)
        if status == 404:
            return StorageError(StorageErrorCode.OBJECT_NOT_FOUND, "The Azure Blob object was not found")
        if status == 409:
            return StorageError(StorageErrorCode.CONFLICT, "The Azure Blob object already exists")
        if status in {401, 403}:
            return StorageError(StorageErrorCode.ACCESS_DENIED, "Azure Blob access was denied")
        if status in {408, 429} or "timeout" in str(exc).lower():
            return StorageError(StorageErrorCode.TIMEOUT, "The Azure Blob operation timed out", retryable=True)
        return StorageError(StorageErrorCode.UNAVAILABLE, message, retryable=True, details={"exception": type(exc).__name__})

    def health(self) -> StorageHealth:
        started = time.perf_counter()
        try:
            self._container.get_container_properties()
            return StorageHealth("HEALTHY", self.config.provider_id, (time.perf_counter() - started) * 1000, {"durable": True, "managed_identity": True})
        except Exception as exc:
            mapped = self._map_error(exc)
            return StorageHealth("UNAVAILABLE", self.config.provider_id, (time.perf_counter() - started) * 1000, {"error_class": mapped.code.value})

    def capabilities(self) -> StorageCapabilities:
        return StorageCapabilities(range_read=True, atomic_or_safe_rename_with_no_replace=True)

    def stat(self, locator: StorageLocator) -> StorageStat:
        try:
            props = self._blob(locator.relative_path).get_blob_properties()
            metadata = props.metadata or {}
            return StorageStat(locator, int(props.size), sha256=metadata.get("sha256"), modified_at=str(props.last_modified or ""))
        except Exception as exc:
            raise self._map_error(exc, "Azure Blob stat failed") from exc

    def open_read(self, locator: StorageLocator, *, offset: int | None = None, length: int | None = None) -> BinaryIO:
        try:
            stream = self._blob(locator.relative_path).download_blob(offset=offset, length=length)
            return io.BytesIO(stream.readall())
        except Exception as exc:
            raise self._map_error(exc, "Azure Blob read failed") from exc

    def write_temporary(self, target: StorageTarget, content: BinaryIO, *, operation_id: str, expected_size: int, expected_sha256: str) -> TemporaryObject:
        relative = f"{target.relative_path.rstrip('/')}/.proposalops/tmp/.uploading-{operation_id}"
        temporary = TemporaryObject(self._locator(relative), operation_id, expected_size, expected_sha256)
        digest = hashlib.sha256()
        data = io.BytesIO()
        size = 0
        for chunk in iter(lambda: content.read(1024 * 1024), b""):
            data.write(chunk)
            digest.update(chunk)
            size += len(chunk)
        if size != expected_size or digest.hexdigest() != expected_sha256:
            raise StorageError(StorageErrorCode.INTEGRITY_MISMATCH, "Azure Blob input stream failed declared size/hash verification")
        try:
            data.seek(0)
            self._blob(relative).upload_blob(data, overwrite=False, metadata={"sha256": expected_sha256, "size": str(size)})
            return temporary
        except Exception as exc:
            mapped = self._map_error(exc, "Azure Blob temporary write failed")
            if mapped.code == StorageErrorCode.CONFLICT:
                try:
                    existing = self.stat(temporary.locator)
                    if existing.size == size and existing.sha256 == expected_sha256:
                        return temporary
                except StorageError:
                    pass
            raise mapped from exc

    def finalize(self, temporary: TemporaryObject, final_target: StorageTarget) -> StorageLocator:
        final_locator = self._locator(final_target.relative_path)
        try:
            try:
                existing = self.stat(final_locator)
                if existing.size == temporary.expected_size and existing.sha256 == temporary.expected_sha256:
                    self.cleanup_temporary(temporary)
                    return existing.locator
                raise StorageError(StorageErrorCode.CONFLICT, "The immutable Azure Blob already exists with different bytes")
            except StorageError as exc:
                if exc.code != StorageErrorCode.OBJECT_NOT_FOUND:
                    raise
            payload = self._blob(temporary.locator.relative_path).download_blob().readall()
            self._blob(final_locator.relative_path).upload_blob(io.BytesIO(payload), overwrite=False, metadata={"sha256": temporary.expected_sha256, "size": str(temporary.expected_size)})
            self.cleanup_temporary(temporary)
            return final_locator
        except StorageError:
            raise
        except Exception as exc:
            raise self._map_error(exc, "Azure Blob finalization failed") from exc

    def mkdirs(self, target_prefix: StorageTarget) -> None:
        # Blob containers are flat; prefix directories are virtual.
        return None

    def list(self, prefix: StorageTarget, *, cursor: str | None = None) -> StoragePage:
        try:
            prefix_value = normalize_relative_path(prefix.relative_path).rstrip("/")
            items = [
                StorageStat(
                    self._locator(blob.name),
                    int(blob.size or 0),
                    sha256=(blob.metadata or {}).get("sha256"),
                    modified_at=str(blob.last_modified or ""),
                )
                for blob in self._container.list_blobs(name_starts_with=prefix_value)
            ]
            return StoragePage(items)
        except Exception as exc:
            raise self._map_error(exc, "Azure Blob listing failed") from exc

    def cleanup_temporary(self, temporary: TemporaryObject) -> None:
        try:
            self._blob(temporary.locator.relative_path).delete_blob(delete_snapshots="include")
        except Exception as exc:
            mapped = self._map_error(exc, "Azure Blob temporary cleanup failed")
            if mapped.code != StorageErrorCode.OBJECT_NOT_FOUND:
                raise mapped from exc
