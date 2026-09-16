"""Read-only mounted source-tree adapter; destinations use DocumentStorageService.

No source write API exists here. The configured physical root must correspond
exactly to the allowlisted logical root. Folder names never become business
facts. This adapter is not wired to a production route until source-workspace
permissions and durable sync have been implemented and qualified.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import re
import stat

from .errors import StorageError, StorageErrorCode
from .external import SourceChangedDuringImport, StableSourceRead
from .port import StorageCapabilities

LOGICAL_ROOT = "Tenders/1- Proposal/2026"
PILOT_FOLDER = "454 - Al Watan Center"


@dataclass(frozen=True)
class SourceEntry:
    relative_path: str
    name: str
    is_directory: bool
    size: int
    modified_ns: int


@dataclass(frozen=True)
class SourceProject:
    number: int
    folder_name: str
    discovery_class: str


def classify_project_folder(name: str) -> SourceProject | None:
    match = re.match(r"^([0-9]{1,9})(?=$|[\s-])", name)
    if not match:
        return None
    number = int(match[1])
    if name == PILOT_FOLDER:
        return SourceProject(number, name, "PROPOSALS_V1_ACTIVE_PILOT")
    if number >= 520:
        return SourceProject(number, name, "DRAFT_SOURCE_PROJECT")
    return None


def _parts(path: str, *, root_allowed=False) -> list[str]:
    if path == "" and root_allowed:
        return []
    if not isinstance(path, str) or not path or path.startswith("/") or "\\" in path or ":" in path:
        raise StorageError(StorageErrorCode.PATH_INVALID, "A bounded relative source path is required")
    parts = path.split("/")
    if len(path) > 4096 or len(parts) > 64 or any(p in {"", ".", ".."} or any(ord(c) < 32 or ord(c) == 127 for c in p) for p in parts):
        raise StorageError(StorageErrorCode.PATH_INVALID, "Invalid source path")
    # Do not normalize Unicode, trim, URL-decode, or invoke a shell.
    return parts


class MountedProposalSource:
    """POSIX dirfd walk rejects symlinks at every boundary, including read races."""
    def __init__(self, physical_root: str | Path, *, max_file_bytes=128 * 1024 * 1024, max_entries=100000):
        if max_file_bytes <= 0 or max_entries <= 0:
            raise ValueError("Source limits must be positive")
        root = Path(physical_root)
        if not root.is_absolute():
            raise StorageError(StorageErrorCode.CONFIGURATION_ERROR, "An explicit absolute source root is required")
        self.max_file_bytes = max_file_bytes
        self.max_entries = max_entries
        # Source root is configured by server, never by a file/download request.
        self._fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)

    def close(self):
        if self._fd is not None:
            os.close(self._fd)
            self._fd = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def capabilities(self):
        return StorageCapabilities(read=True, write_new=False, mkdir=False, list=True,
                                   stat=True, safe_finalize=False,
                                   atomic_or_safe_rename_with_no_replace=False)

    def _open(self, relative_path: str, *, directory=False):
        parts = _parts(relative_path, root_allowed=directory)
        if self._fd is None:
            raise StorageError(StorageErrorCode.UNAVAILABLE, "Source adapter is closed")
        fd = os.dup(self._fd)
        try:
            for i, component in enumerate(parts):
                flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
                if i < len(parts) - 1 or directory:
                    flags |= os.O_DIRECTORY
                next_fd = os.open(component, flags, dir_fd=fd)
                os.close(fd)
                fd = next_fd
            mode = os.fstat(fd).st_mode
            if (directory and not stat.S_ISDIR(mode)) or (not directory and not stat.S_ISREG(mode)):
                raise StorageError(StorageErrorCode.PATH_INVALID, "Source must be a regular file or directory")
            return fd
        except Exception:
            os.close(fd)
            raise

    def children(self, relative_path="") -> list[SourceEntry]:
        fd = self._open(relative_path, directory=True)
        try:
            entries = []
            with os.scandir(fd) as directory:
                for item in directory:
                    path = f"{relative_path}/{item.name}" if relative_path else item.name
                    _parts(path)
                    info = item.stat(follow_symlinks=False)
                    if not (stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode)):
                        raise StorageError(StorageErrorCode.PATH_INVALID, "Symlinks and special source files are not allowed")
                    entries.append(SourceEntry(path, item.name, stat.S_ISDIR(info.st_mode), info.st_size, info.st_mtime_ns))
                    if len(entries) > self.max_entries:
                        raise StorageError(StorageErrorCode.QUOTA_OR_SPACE, "Source entry limit exceeded")
            return sorted(entries, key=lambda e: (not e.is_directory, e.name))
        finally:
            os.close(fd)

    def discover(self) -> list[SourceProject]:
        return [project for entry in self.children() if entry.is_directory
                if (project := classify_project_folder(entry.name)) is not None]

    def inventory(self, project_folder: str) -> list[SourceEntry]:
        if classify_project_folder(project_folder) is None or len(_parts(project_folder)) != 1:
            raise StorageError(StorageErrorCode.PATH_INVALID, "Project is outside the discovery rule")
        pending = [project_folder]
        entries = []
        while pending:
            directory = pending.pop()
            for entry in self.children(directory):
                entries.append(entry)
                if len(entries) > self.max_entries:
                    raise StorageError(StorageErrorCode.QUOTA_OR_SPACE, "Source entry limit exceeded")
                if entry.is_directory:
                    pending.append(entry.relative_path)
        return entries

    @staticmethod
    def _identity(info):
        return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns

    def _read_once(self, relative_path: str) -> StableSourceRead:
        fd = self._open(relative_path)
        try:
            before = os.fstat(fd)
            if before.st_size > self.max_file_bytes:
                raise StorageError(StorageErrorCode.QUOTA_OR_SPACE, "Source file size limit exceeded")
            chunks = []
            size = 0
            hasher = hashlib.sha256()
            while True:
                chunk = os.read(fd, min(1024 * 1024, self.max_file_bytes - size + 1))
                if not chunk:
                    break
                size += len(chunk)
                if size > self.max_file_bytes:
                    raise StorageError(StorageErrorCode.QUOTA_OR_SPACE, "Source file size limit exceeded")
                hasher.update(chunk)
                chunks.append(chunk)
            after = os.fstat(fd)
            check_fd = self._open(relative_path)
            try:
                path_after = os.fstat(check_fd)
            finally:
                os.close(check_fd)
            if size != before.st_size or self._identity(before) != self._identity(after) or self._identity(before) != self._identity(path_after):
                raise SourceChangedDuringImport("source changed during capture")
            return StableSourceRead(b"".join(chunks), size, hasher.hexdigest(), str(before.st_mtime_ns), str(after.st_mtime_ns))
        finally:
            os.close(fd)

    def capture(self, relative_path: str, *, attempts=2) -> StableSourceRead:
        parts = _parts(relative_path)
        if len(parts) < 2 or classify_project_folder(parts[0]) is None:
            raise StorageError(StorageErrorCode.PATH_INVALID, "File is outside an eligible source project")
        if not 1 <= attempts <= 3:
            raise ValueError("Capture attempts must be between one and three")
        for attempt in range(attempts):
            try:
                return self._read_once(relative_path)
            except SourceChangedDuringImport:
                if attempt + 1 == attempts:
                    raise
        raise AssertionError("unreachable")
