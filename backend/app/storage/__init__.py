"""Provider-neutral document binary storage.

Business modules should depend on :mod:`backend.app.storage`, never on an SMB
client or a Synology-specific adapter.  The package deliberately keeps the
legacy synthetic adapter available for existing fixture-only workflows while
the production path is selected explicitly through configuration.
"""

from .errors import StorageError, StorageErrorCode
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
from .mock import MockBinaryStore
from .smb import SMBConfig, SMBBinaryStore
from .service import DocumentStorageService, StoredVersion
from .factory import create_binary_store

__all__ = [
    "BinaryStorePort",
    "DocumentStorageService",
    "create_binary_store",
    "MockBinaryStore",
    "SMBConfig",
    "SMBBinaryStore",
    "StoredVersion",
    "StorageCapabilities",
    "StorageError",
    "StorageErrorCode",
    "StorageHealth",
    "StorageLocator",
    "StoragePage",
    "StorageStat",
    "StorageTarget",
    "TemporaryObject",
]
