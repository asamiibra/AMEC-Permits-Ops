from __future__ import annotations

from enum import StrEnum


class StorageErrorCode(StrEnum):
    UNAVAILABLE = "STORAGE_UNAVAILABLE"
    TIMEOUT = "STORAGE_TIMEOUT"
    AUTH_FAILED = "STORAGE_AUTH_FAILED"
    ACCESS_DENIED = "STORAGE_ACCESS_DENIED"
    SHARE_NOT_FOUND = "STORAGE_SHARE_NOT_FOUND"
    OBJECT_NOT_FOUND = "STORAGE_OBJECT_NOT_FOUND"
    PATH_INVALID = "STORAGE_PATH_INVALID"
    NAME_INVALID = "STORAGE_NAME_INVALID"
    CONFLICT = "STORAGE_CONFLICT"
    LOCKED = "STORAGE_LOCKED"
    QUOTA_OR_SPACE = "STORAGE_QUOTA_OR_SPACE"
    INTEGRITY_MISMATCH = "STORAGE_INTEGRITY_MISMATCH"
    INTEGRITY_DRIFT = "STORAGE_INTEGRITY_DRIFT"
    PROTOCOL_ERROR = "STORAGE_PROTOCOL_ERROR"
    CONFIGURATION_ERROR = "STORAGE_CONFIGURATION_ERROR"
    UNKNOWN = "STORAGE_UNKNOWN_ERROR"


class StorageError(RuntimeError):
    """Normalized, safe-to-surface storage failure.

    ``details`` is intentionally diagnostic-only and must never contain
    credentials or raw file contents.
    """

    def __init__(self, code: StorageErrorCode | str, message: str = "", *, details: dict | None = None, retryable: bool = False):
        self.code = StorageErrorCode(code)
        self.details = details or {}
        self.retryable = retryable
        super().__init__(message or self.code.value)

