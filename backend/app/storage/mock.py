from __future__ import annotations

import hashlib
import io
import shutil
import time
from pathlib import Path
from typing import BinaryIO

from .errors import StorageError, StorageErrorCode
from .path_policy import normalize_relative_path
from .port import BinaryStorePort, StorageCapabilities, StorageHealth, StorageLocator, StoragePage, StorageStat, StorageTarget, TemporaryObject


class MockBinaryStore(BinaryStorePort):
    """Filesystem-backed provider for isolated unit tests only.

    It implements the same temporary/read-back/finalize protocol as the SMB
    provider. It is intentionally not selected by production configuration.
    """

    def __init__(self, root: str | Path, *, provider_id: str = "mock-test", share_id: str = "test", root_prefix: str = ""):
        self.root = Path(root).resolve()
        self.provider_id = provider_id
        self.share_id = share_id
        self.root_prefix = normalize_relative_path(root_prefix) if root_prefix else ""

    def _path(self, relative_path: str, *, allow_missing: bool = True) -> Path:
        safe = normalize_relative_path(relative_path)
        path = (self.root / safe).resolve()
        if self.root not in path.parents and path != self.root:
            raise StorageError(StorageErrorCode.PATH_INVALID, "The storage path escapes the approved root")
        if not allow_missing and not path.exists():
            raise StorageError(StorageErrorCode.OBJECT_NOT_FOUND, "The storage object was not found")
        return path

    def _locator(self, path: str) -> StorageLocator:
        return StorageLocator(self.provider_id, self.share_id, normalize_relative_path(path))

    def health(self) -> StorageHealth:
        started = time.perf_counter()
        try:
            self.root.mkdir(parents=True, exist_ok=True)
            return StorageHealth("HEALTHY", self.provider_id, (time.perf_counter() - started) * 1000, {"synthetic": True})
        except OSError as exc:
            return StorageHealth("UNAVAILABLE", self.provider_id, (time.perf_counter() - started) * 1000, {"error": type(exc).__name__})

    def capabilities(self) -> StorageCapabilities:
        return StorageCapabilities(range_read=True)

    def stat(self, locator: StorageLocator) -> StorageStat:
        path = self._path(locator.relative_path, allow_missing=False)
        stat = path.stat()
        return StorageStat(locator, stat.st_size, self._hash(path), modified_at=str(stat.st_mtime))

    @staticmethod
    def _hash(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def open_read(self, locator: StorageLocator, *, offset: int | None = None, length: int | None = None) -> BinaryIO:
        path = self._path(locator.relative_path, allow_missing=False)
        stream = path.open("rb")
        if offset:
            stream.seek(offset)
        if length is None:
            return stream
        return io.BytesIO(stream.read(length))

    def write_temporary(self, target: StorageTarget, content: BinaryIO, *, operation_id: str, expected_size: int, expected_sha256: str) -> TemporaryObject:
        directory = self._path(target.relative_path)
        directory.mkdir(parents=True, exist_ok=True)
        temp_name = f".uploading-{operation_id}"
        path = directory / temp_name
        digest = hashlib.sha256()
        size = 0
        try:
            with path.open("xb") as destination:
                for chunk in iter(lambda: content.read(1024 * 1024), b""):
                    destination.write(chunk)
                    digest.update(chunk)
                    size += len(chunk)
                destination.flush()
            if size != expected_size or digest.hexdigest() != expected_sha256:
                raise StorageError(StorageErrorCode.INTEGRITY_MISMATCH, "Input stream did not match its declared digest")
            locator = self._locator(f"{target.relative_path}/{temp_name}")
            return TemporaryObject(locator, operation_id, size, expected_sha256)
        except FileExistsError as exc:
            raise StorageError(StorageErrorCode.CONFLICT, "The upload operation already has a temporary object") from exc
        except StorageError:
            path.unlink(missing_ok=True)
            raise
        except OSError as exc:
            path.unlink(missing_ok=True)
            raise StorageError(StorageErrorCode.UNAVAILABLE, "Temporary storage write failed", retryable=True) from exc

    def finalize(self, temporary: TemporaryObject, final_target: StorageTarget) -> StorageLocator:
        source = self._path(temporary.locator.relative_path, allow_missing=False)
        final = self._path(final_target.relative_path)
        final.parent.mkdir(parents=True, exist_ok=True)
        if final.exists():
            existing = self.stat(self._locator(final_target.relative_path))
            if existing.size == temporary.expected_size and existing.sha256 == temporary.expected_sha256:
                source.unlink(missing_ok=True)
                return existing.locator
            raise StorageError(StorageErrorCode.CONFLICT, "The immutable final object already exists")
        try:
            source.rename(final)
        except OSError as exc:
            raise StorageError(StorageErrorCode.UNAVAILABLE, "Finalization failed", retryable=True) from exc
        return self._locator(final_target.relative_path)

    def mkdirs(self, target_prefix: StorageTarget) -> None:
        self._path(target_prefix.relative_path).mkdir(parents=True, exist_ok=True)

    def list(self, prefix: StorageTarget, *, cursor: str | None = None) -> StoragePage:
        directory = self._path(prefix.relative_path, allow_missing=False)
        items = [self.stat(self._locator(str(path.relative_to(self.root)))) for path in sorted(directory.iterdir()) if path.is_file()]
        return StoragePage(items)

    def cleanup_temporary(self, temporary: TemporaryObject) -> None:
        try:
            self._path(temporary.locator.relative_path, allow_missing=False).unlink()
        except StorageError as exc:
            if exc.code != StorageErrorCode.OBJECT_NOT_FOUND:
                raise

