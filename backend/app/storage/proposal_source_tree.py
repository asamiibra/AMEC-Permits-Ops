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
from datetime import datetime
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from .errors import StorageError, StorageErrorCode
from .external import SourceChangedDuringImport, StableSourceRead
from .port import StorageCapabilities
from ..models import DocumentVersion

LOGICAL_ROOT = "Tenders/1- Proposal/2026"
PILOT_FOLDER = "454 - Al Watan Center"


@dataclass(frozen=True)
class SourceEntry:
    relative_path: str
    name: str
    is_directory: bool
    size: int
    modified_ns: int
    capture_status: str = "PRESENT"
    failure_reason: str | None = None
    source_version_token: str | None = None


@dataclass(frozen=True)
class SourceProject:
    number: int
    folder_name: str
    discovery_class: str


class ProposalSourceProvider(Protocol):
    """Logical source contract shared by mounted and bridge-backed sources."""

    def discover(self) -> list[SourceProject]: ...
    def inventory(self, project_folder: str) -> list[SourceEntry]: ...
    def capture(self, relative_path: str, *, attempts: int = 2) -> StableSourceRead: ...


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


LIVE_SOURCE_URI_PREFIX = "synology://qatar/"


class BridgeProposalSourceProvider:
    """Reconstruct the Proposal source tree from bridge-captured versions.

    The Azure application never contacts Synology.  The bridge receiver has
    already verified the source package and persisted the bytes through the
    canonical binary store; this provider only reads that durable record.
    """

    def __init__(self, db: Session, *, max_file_bytes: int = 128 * 1024 * 1024, max_entries: int = 100000):
        if max_file_bytes <= 0 or max_entries <= 0:
            raise ValueError("Source limits must be positive")
        self.db = db
        self.max_file_bytes = max_file_bytes
        self.max_entries = max_entries

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None

    @staticmethod
    def _relative_path(version: DocumentVersion) -> str | None:
        metadata = version.metadata_json or {}
        relative = metadata.get("source_relative_path")
        if isinstance(relative, str) and relative:
            return relative
        snapshot = metadata.get("source_path_snapshot") or version.source_path_or_reference
        if isinstance(snapshot, str) and snapshot.startswith(LIVE_SOURCE_URI_PREFIX):
            logical = snapshot.removeprefix(LIVE_SOURCE_URI_PREFIX)
            prefix = LOGICAL_ROOT + "/"
            if logical.startswith(prefix):
                return logical.removeprefix(prefix)
        return None

    @staticmethod
    def _modified_ns(version: DocumentVersion) -> int:
        metadata = version.metadata_json or {}
        raw = metadata.get("source_modified_ns") or metadata.get("source_mtime_ns")
        if isinstance(raw, int):
            return raw
        if isinstance(raw, str) and raw.isdigit():
            return int(raw)
        raw = metadata.get("source_modified_at") or metadata.get("source_mtime_utc")
        if isinstance(raw, str):
            try:
                return int(datetime.fromisoformat(raw.replace("Z", "+00:00")).timestamp() * 1_000_000_000)
            except ValueError:
                pass
        return 0

    def _current_versions(self) -> dict[str, DocumentVersion]:
        rows = self.db.scalars(
            select(DocumentVersion)
            .where(DocumentVersion.source_system == "QATAR_SOURCE_INTAKE_BRIDGE")
            .order_by(DocumentVersion.ingested_at, DocumentVersion.version_number)
        ).all()
        current: dict[str, DocumentVersion] = {}
        for row in rows:
            relative = self._relative_path(row)
            metadata = row.metadata_json or {}
            if not relative or metadata.get("source_presence_state", "PRESENT") != "PRESENT":
                continue
            try:
                parts = _parts(relative)
            except StorageError:
                continue
            if len(parts) < 2 or classify_project_folder(parts[0]) is None:
                continue
            prior = current.get(relative)
            if prior is None or row.version_number >= prior.version_number:
                current[relative] = row
        if len(current) > self.max_entries:
            raise StorageError(StorageErrorCode.QUOTA_OR_SPACE, "Source entry limit exceeded")
        return current

    def _latest_scan(self, project_folder: str):
        """Return the latest completed scan for this exact source folder."""
        from ..models import ProposalSourceScan
        project = classify_project_folder(project_folder)
        if project is None:
            return None
        rows = self.db.scalars(
            select(ProposalSourceScan)
            .where(ProposalSourceScan.project_number == str(project.number), ProposalSourceScan.status == "COMPLETED")
            .order_by(ProposalSourceScan.completed_at.desc(), ProposalSourceScan.created_at.desc())
        ).all()
        return rows[0] if rows else None

    def discover(self) -> list[SourceProject]:
        projects: dict[str, SourceProject] = {}
        from ..models import ProposalSourceScan, ProposalSourceScanEntry
        for scan in self.db.scalars(select(ProposalSourceScan).where(ProposalSourceScan.status == "COMPLETED")).all():
            for entry in self.db.scalars(select(ProposalSourceScanEntry).where(ProposalSourceScanEntry.scan_id == scan.id)).all():
                folder = entry.relative_path.split("/", 1)[0]
                project = classify_project_folder(folder)
                if project is not None:
                    projects[folder] = project
        for relative in self._current_versions():
            folder = relative.split("/", 1)[0]
            project = classify_project_folder(folder)
            if project is not None:
                projects[folder] = project
        return sorted(projects.values(), key=lambda item: (item.number, item.folder_name))

    def inventory(self, project_folder: str) -> list[SourceEntry]:
        project = classify_project_folder(project_folder)
        if project is None or len(_parts(project_folder)) != 1:
            raise StorageError(StorageErrorCode.PATH_INVALID, "Project is outside the discovery rule")
        versions = {
            relative: version
            for relative, version in self._current_versions().items()
            if relative == project_folder or relative.startswith(project_folder + "/")
        }
        scan = self._latest_scan(project_folder)
        if not versions and scan is None:
            raise FileNotFoundError("SOURCE_PROJECT_NOT_FOUND")
        entries: dict[str, SourceEntry] = {}
        if scan is not None:
            from ..models import ProposalSourceScanEntry
            for scan_entry in self.db.scalars(select(ProposalSourceScanEntry).where(ProposalSourceScanEntry.scan_id == scan.id)).all():
                relative = scan_entry.relative_path
                if relative == project_folder or relative.startswith(project_folder + "/"):
                    parts = _parts(relative)
                    entries[relative] = SourceEntry(relative, parts[-1], scan_entry.entry_type == "DIRECTORY", scan_entry.size_bytes, 0, scan_entry.capture_status, scan_entry.failure_reason, scan_entry.source_version_token)
        for relative, version in versions.items():
            parts = _parts(relative)
            metadata = version.metadata_json or {}
            entries[relative] = SourceEntry(
                relative_path=relative,
                name=parts[-1],
                is_directory=bool(metadata.get("source_is_directory", False)),
                size=int(version.file_size or 0),
                modified_ns=self._modified_ns(version),
                capture_status=str(metadata.get("capture_status") or "CAPTURED"),
                failure_reason=metadata.get("failure_reason"),
                source_version_token=metadata.get("source_version_token"),
            )
            for index in range(1, len(parts)):
                directory = "/".join(parts[:index])
                entries.setdefault(directory, SourceEntry(directory, parts[index - 1], True, 0, 0))
        if len(entries) > self.max_entries:
            raise StorageError(StorageErrorCode.QUOTA_OR_SPACE, "Source entry limit exceeded")
        return sorted(entries.values(), key=lambda item: (not item.is_directory, item.name, item.relative_path))

    def capture(self, relative_path: str, *, attempts: int = 2) -> StableSourceRead:
        _parts(relative_path)
        if not 1 <= attempts <= 3:
            raise ValueError("Capture attempts must be between one and three")
        version = self._current_versions().get(relative_path)
        if version is None:
            raise FileNotFoundError("SOURCE_FILE_NOT_FOUND")
        metadata = version.metadata_json or {}
        if metadata.get("source_is_directory"):
            raise StorageError(StorageErrorCode.PATH_INVALID, "Directories cannot be captured as files")
        if version.file_size > self.max_file_bytes:
            raise StorageError(StorageErrorCode.QUOTA_OR_SPACE, "Source file size limit exceeded")
        try:
            if version.source_path_or_reference.startswith("storage://"):
                from .service import DocumentStorageService
                from .factory import create_binary_store
                with DocumentStorageService(create_binary_store()).read_verified(version) as stream:
                    content = stream.read(self.max_file_bytes + 1)
            elif version.synthetic_content is not None:
                content = version.synthetic_content
            else:
                raise StorageError(StorageErrorCode.UNAVAILABLE, "Bridge-captured bytes are unavailable")
        except StorageError:
            raise
        except Exception as exc:
            raise StorageError(StorageErrorCode.UNAVAILABLE, "Bridge-captured bytes could not be read", retryable=True) from exc
        if len(content) > self.max_file_bytes:
            raise StorageError(StorageErrorCode.QUOTA_OR_SPACE, "Source file size limit exceeded")
        digest = hashlib.sha256(content).hexdigest()
        if len(content) != version.file_size or digest != version.sha256:
            raise StorageError(StorageErrorCode.INTEGRITY_MISMATCH, "Bridge-captured bytes failed hash verification")
        modified = str(self._modified_ns(version))
        return StableSourceRead(content, len(content), digest, modified, modified)
