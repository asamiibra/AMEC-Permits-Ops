"""Bounded, non-extracting ZIP observation reader.

The reader never writes archive members to a filesystem.  Callers receive
observations and explicitly request bounded bytes for a single file.
"""

from __future__ import annotations

import hashlib
import io
import mimetypes
import os
import posixpath
import stat
import unicodedata
import zipfile
from dataclasses import dataclass
from collections.abc import Callable
from pathlib import PurePosixPath


class ArchiveSafetyError(ValueError):
    pass


@dataclass(frozen=True)
class ArchivePolicy:
    max_entries: int = 1000
    max_files: int = 500
    max_total_bytes: int = 250 * 1024 * 1024
    max_entry_bytes: int = 50 * 1024 * 1024
    max_compression_ratio: float = 1000.0
    allow_nested_archives: bool = False


@dataclass(frozen=True)
class ArchiveEntryObservation:
    ordinal: int
    original_relative_path: str
    normalized_safe_path: str
    is_dir: bool
    size_bytes: int
    compressed_size: int
    sha256: str | None
    media_type: str | None
    _info: zipfile.ZipInfo
    _archive: "BoundedZipReader"

    def read_bytes(self) -> bytes:
        if self.is_dir:
            return b""
        return self._archive.read(self._info)


def _safe_path(raw: str) -> str:
    if not raw or "\x00" in raw:
        raise ArchiveSafetyError("archive path is empty or contains NUL")
    raw = raw.replace("\\", "/")
    if raw.startswith("/") or raw.startswith("//") or raw.startswith("\\"):
        raise ArchiveSafetyError(f"absolute or UNC archive path rejected: {raw!r}")
    if len(raw) >= 2 and raw[1] == ":":
        raise ArchiveSafetyError(f"drive-qualified archive path rejected: {raw!r}")
    normalized = unicodedata.normalize("NFC", raw)
    parts: list[str] = []
    for part in PurePosixPath(normalized).parts:
        if part in ("", "."):
            continue
        if part == "..":
            raise ArchiveSafetyError(f"traversal archive path rejected: {raw!r}")
        parts.append(part)
    if not parts:
        raise ArchiveSafetyError(f"archive path normalizes empty: {raw!r}")
    return "/".join(parts)


class BoundedZipReader:
    def __init__(self, payload: bytes, policy: ArchivePolicy | None = None):
        self.payload = payload
        self.policy = policy or ArchivePolicy()
        self.archive_sha256 = hashlib.sha256(payload).hexdigest()
        self._zip = zipfile.ZipFile(io.BytesIO(payload))
        self._observations: list[ArchiveEntryObservation] | None = None

    def observations(self) -> list[ArchiveEntryObservation]:
        if self._observations is not None:
            return self._observations
        infos = self._zip.infolist()
        if len(infos) > self.policy.max_entries:
            raise ArchiveSafetyError("archive entry limit exceeded")
        seen: set[str] = set()
        seen_casefold: set[str] = set()
        seen_count = 0
        total = 0
        result: list[ArchiveEntryObservation] = []
        for ordinal, info in enumerate(infos, start=1):
            normalized = _safe_path(info.filename)
            key = normalized.casefold()
            if normalized in seen or key in seen_casefold:
                raise ArchiveSafetyError(f"duplicate or case-colliding archive path: {info.filename!r}")
            seen.add(normalized)
            seen_casefold.add(key)
            is_dir = info.is_dir() or info.filename.endswith(("/", "\\"))
            mode = (info.external_attr >> 16) & 0xFFFF
            if stat.S_ISLNK(mode) or stat.S_ISDIR(mode) and not is_dir:
                raise ArchiveSafetyError(f"symlink or invalid directory entry rejected: {info.filename!r}")
            if info.flag_bits & 0x1:
                raise ArchiveSafetyError("encrypted ZIP entries are unsupported")
            if not is_dir:
                seen_count += 1
                if seen_count > self.policy.max_files:
                    raise ArchiveSafetyError("archive file limit exceeded")
                if info.file_size > self.policy.max_entry_bytes:
                    raise ArchiveSafetyError("archive member size limit exceeded")
                if info.compress_size == 0 and info.file_size:
                    raise ArchiveSafetyError("invalid compressed-size metadata")
                if info.compress_size and info.file_size / info.compress_size > self.policy.max_compression_ratio:
                    raise ArchiveSafetyError("suspicious archive compression ratio")
                total += info.file_size
                if total > self.policy.max_total_bytes:
                    raise ArchiveSafetyError("archive total-size limit exceeded")
                suffix = os.path.splitext(normalized)[1].lower()
                if not self.policy.allow_nested_archives and suffix in {".zip", ".tar", ".gz", ".tgz", ".7z", ".rar"}:
                    raise ArchiveSafetyError("nested archive member rejected")
            result.append(ArchiveEntryObservation(ordinal, info.filename, normalized, is_dir, info.file_size, info.compress_size, None, mimetypes.guess_type(normalized)[0], info, self))
        self._observations = result
        return result

    def read(self, info: zipfile.ZipInfo) -> bytes:
        if info.file_size > self.policy.max_entry_bytes:
            raise ArchiveSafetyError("archive member size limit exceeded")
        digest = hashlib.sha256()
        chunks: list[bytes] = []
        count = 0
        with self._zip.open(info, "r") as stream:
            while True:
                chunk = stream.read(min(1024 * 1024, self.policy.max_entry_bytes - count + 1))
                if not chunk:
                    break
                count += len(chunk)
                if count > self.policy.max_entry_bytes:
                    raise ArchiveSafetyError("archive member expanded beyond limit")
                digest.update(chunk)
                chunks.append(chunk)
        if count != info.file_size:
            raise ArchiveSafetyError("archive member size changed during read")
        return b"".join(chunks)

    def observations_with_hashes(self, *, exclude: Callable[[str], bool] | None = None) -> list[ArchiveEntryObservation]:
        result = []
        for observation in self.observations():
            if exclude and exclude(observation.normalized_safe_path):
                continue
            if observation.is_dir:
                result.append(observation)
                continue
            payload = observation.read_bytes()
            result.append(ArchiveEntryObservation(observation.ordinal, observation.original_relative_path, observation.normalized_safe_path, False, observation.size_bytes, observation.compressed_size, hashlib.sha256(payload).hexdigest(), observation.media_type, observation._info, self))
        return result
