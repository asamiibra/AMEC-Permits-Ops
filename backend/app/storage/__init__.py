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
from .port import ReadOnlySourcePort, SourceCapabilities, SourcePage
from .smb import SMBSourceConfig, SMBSourceStore
from .external import (
    BoundedEnumeration,
    ContentBudgetExceeded,
    OperationDeadlineExceeded,
    ReadBudgetState,
    SourceChangedDuringImport,
    SourceReadBudgets,
    SourceStabilityTracker,
    StabilityObservation,
    StabilityPolicy,
    StabilityState,
    classify_path_change,
    enumerate_bounded,
    read_bounded_content,
    run_with_deadline,
)

__all__ = [
    "BinaryStorePort",
    "DocumentStorageService",
    "create_binary_store",
    "ReadOnlySourcePort",
    "SourceCapabilities",
    "SourcePage",
    "SMBSourceConfig",
    "SMBSourceStore",
    "SourceReadBudgets",
    "SourceStabilityTracker",
    "StabilityObservation",
    "StabilityPolicy",
    "StabilityState",
    "BoundedEnumeration",
    "ContentBudgetExceeded",
    "OperationDeadlineExceeded",
    "ReadBudgetState",
    "SourceChangedDuringImport",
    "classify_path_change",
    "enumerate_bounded",
    "read_bounded_content",
    "run_with_deadline",
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
