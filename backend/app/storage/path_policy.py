from __future__ import annotations

import re
import unicodedata
from pathlib import PurePosixPath

from .errors import StorageError, StorageErrorCode

_RESERVED_WINDOWS_NAMES = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}
_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")


def normalize_filename(filename: str, *, max_length: int = 240) -> str:
    """Return one safe Windows/SMB-compatible component.

    Original filenames remain business metadata; this value is only the
    physical component used by the provider.
    """
    if not filename or not isinstance(filename, str):
        raise StorageError(StorageErrorCode.NAME_INVALID, "A filename is required")
    value = unicodedata.normalize("NFC", filename).replace("\\", "/").split("/")[-1]
    value = _CONTROL_CHARS.sub("_", value).strip()
    value = value.rstrip(" .")
    if not value or value in {".", ".."}:
        raise StorageError(StorageErrorCode.NAME_INVALID, "The filename is invalid")
    stem = value.rsplit(".", 1)[0].upper()
    if stem in _RESERVED_WINDOWS_NAMES:
        raise StorageError(StorageErrorCode.NAME_INVALID, "The filename uses a reserved Windows device name")
    if len(value) > max_length:
        suffix = value.rsplit(".", 1)[-1] if "." in value else ""
        keep = max_length - (len(suffix) + 1 if suffix else 0)
        value = value[:max(1, keep)] + (("." + suffix) if suffix else "")
    return value


def normalize_relative_path(relative_path: str, *, max_component_length: int = 240, max_total_length: int = 900) -> str:
    if not relative_path or not isinstance(relative_path, str):
        raise StorageError(StorageErrorCode.PATH_INVALID, "A relative storage path is required")
    if "\x00" in relative_path or relative_path.startswith(("/", "\\")) or ":" in relative_path:
        raise StorageError(StorageErrorCode.PATH_INVALID, "Absolute or alternate storage paths are not allowed")
    value = unicodedata.normalize("NFC", relative_path).replace("\\", "/")
    parts = [part for part in PurePosixPath(value).parts if part not in {""}]
    if any(part in {".", ".."} or _CONTROL_CHARS.search(part) for part in parts):
        raise StorageError(StorageErrorCode.PATH_INVALID, "Path traversal is not allowed")
    safe_parts = [normalize_filename(part, max_length=max_component_length) for part in parts]
    result = "/".join(safe_parts)
    if not result or len(result) > max_total_length:
        raise StorageError(StorageErrorCode.PATH_INVALID, "The storage path is too long")
    return result

