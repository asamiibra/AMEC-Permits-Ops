from __future__ import annotations

from dataclasses import dataclass, field
from io import BufferedIOBase
from typing import BinaryIO, Protocol


@dataclass(frozen=True)
class StorageTarget:
    provider_id: str
    share_id: str
    relative_path: str


@dataclass(frozen=True)
class StorageLocator(StorageTarget):
    layout_version: str = "1"

    def serialized(self) -> str:
        return f"storage://{self.provider_id}/{self.share_id}/{self.relative_path}"


@dataclass(frozen=True)
class StorageStat:
    locator: StorageLocator
    size: int
    sha256: str | None = None
    modified_at: str | None = None
    server_file_id: str | None = None


@dataclass(frozen=True)
class StorageCapabilities:
    read: bool = True
    write_new: bool = True
    mkdir: bool = True
    list: bool = True
    stat: bool = True
    safe_finalize: bool = True
    atomic_or_safe_rename_with_no_replace: bool = True
    range_read: bool = False
    acl_metadata: bool = False
    dsm_api: bool = False


@dataclass(frozen=True)
class StorageHealth:
    state: str
    provider_id: str
    latency_ms: float | None = None
    detail: dict = field(default_factory=dict)


@dataclass(frozen=True)
class StoragePage:
    items: list[StorageStat]
    cursor: str | None = None


@dataclass(frozen=True)
class TemporaryObject:
    locator: StorageLocator
    operation_id: str
    expected_size: int
    expected_sha256: str


class BinaryStorePort(Protocol):
    def health(self) -> StorageHealth: ...
    def capabilities(self) -> StorageCapabilities: ...
    def stat(self, locator: StorageLocator) -> StorageStat: ...
    def open_read(self, locator: StorageLocator, *, offset: int | None = None, length: int | None = None) -> BinaryIO: ...
    def write_temporary(self, target: StorageTarget, content: BinaryIO, *, operation_id: str, expected_size: int, expected_sha256: str) -> TemporaryObject: ...
    def finalize(self, temporary: TemporaryObject, final_target: StorageTarget) -> StorageLocator: ...
    def mkdirs(self, target_prefix: StorageTarget) -> None: ...
    def list(self, prefix: StorageTarget, *, cursor: str | None = None) -> StoragePage: ...
    def cleanup_temporary(self, temporary: TemporaryObject) -> None: ...

