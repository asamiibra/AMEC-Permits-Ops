from __future__ import annotations

import hashlib
import io
import itertools
import time
from dataclasses import dataclass
from typing import BinaryIO

from .errors import StorageError, StorageErrorCode
from .path_policy import normalize_relative_path
from .external import run_with_deadline
from .port import BinaryStorePort, ReadOnlySourcePort, SourceCapabilities, SourcePage, StorageCapabilities, StorageHealth, StorageLocator, StoragePage, StorageStat, StorageTarget, TemporaryObject


@dataclass(frozen=True)
class SMBConfig:
    server: str
    share: str
    username: str
    password: str
    port: int = 445
    provider_id: str = "smb"
    root: str = ""
    auth_mode: str = "ntlm"
    require_signing: bool = False
    require_encryption: bool = False
    connect_timeout_seconds: float = 10
    operation_timeout_seconds: float = 60
    environment: str = "DEV"


@dataclass(frozen=True)
class SMBSourceConfig:
    server: str
    share: str
    username: str
    password: str
    port: int = 445
    provider_id: str = "smb-external-source"
    root: str = ""
    auth_mode: str = "ntlm"
    require_signing: bool = True
    require_encryption: bool = True
    anonymous: bool = False
    guest: bool = False
    operation_timeout_seconds: float = 60

    def __post_init__(self) -> None:
        if not all((self.server, self.share, self.username, self.password)):
            raise StorageError(StorageErrorCode.CONFIGURATION_ERROR, "External source credentials are required")
        if self.auth_mode.lower() not in {"ntlm", "kerberos", "negotiate"}:
            raise StorageError(StorageErrorCode.CONFIGURATION_ERROR, "Unsupported external source authentication mode")
        if self.anonymous or self.guest:
            raise StorageError(StorageErrorCode.CONFIGURATION_ERROR, "Anonymous and guest external source access are forbidden")
        if not self.require_signing or not self.require_encryption:
            raise StorageError(StorageErrorCode.CONFIGURATION_ERROR, "External source signing and encryption are required")
        if self.operation_timeout_seconds <= 0:
            raise StorageError(StorageErrorCode.CONFIGURATION_ERROR, "External source operation timeout must be positive")


class SMBSourceStore(ReadOnlySourcePort):
    """Read-only SMB source implementation; never a managed write provider."""

    def __init__(self, config: SMBSourceConfig):
        self.config = config
        self._smbclient = None
        self._connection_cache: dict = {}

    def _client(self):
        if self._smbclient is None:
            try:
                import smbclient  # type: ignore
            except ImportError as exc:
                raise StorageError(StorageErrorCode.CONFIGURATION_ERROR, "The pinned smbprotocol dependency is not installed") from exc
            self._smbclient = smbclient
            try:
                smbclient.register_session(self.config.server, username=self.config.username, password=self.config.password, port=self.config.port, auth_protocol=self.config.auth_mode.lower(), connection_timeout=self.config.operation_timeout_seconds, require_signing=True, encrypt=True, connection_cache=self._connection_cache)
            except Exception as exc:
                raise self._map_error(exc, "External source authentication failed") from exc
        return self._smbclient

    def _session_kwargs(self) -> dict:
        return {"username": self.config.username, "password": self.config.password, "port": self.config.port, "encrypt": True, "connection_timeout": self.config.operation_timeout_seconds, "connection_cache": self._connection_cache}

    def _unc(self, relative_path: str) -> str:
        raw = relative_path.strip("/\\") if relative_path else ""
        safe = normalize_relative_path(raw) if raw and raw != "." else ""
        configured_root = normalize_relative_path(self.config.root.strip("/\\")) if self.config.root else ""
        if configured_root and safe != configured_root and not safe.startswith(configured_root + "/"):
            safe = f"{configured_root}/{safe}" if safe else configured_root
        windows_safe = safe.replace("/", chr(92))
        suffix = f"{chr(92)}{windows_safe}" if safe else ""
        return f"{chr(92) * 2}{self.config.server}{chr(92)}{self.config.share}{suffix}"

    @staticmethod
    def _map_error(exc: Exception, message: str = "External source operation failed") -> StorageError:
        text = str(exc).lower()
        name = type(exc).__name__.lower()
        if "timeout" in text or "timeout" in name:
            return StorageError(StorageErrorCode.TIMEOUT, "The external source operation timed out", retryable=True)
        if any(token in text for token in ("logon_failure", "bad_password", "access_denied", "permission")):
            return StorageError(StorageErrorCode.AUTH_FAILED if "logon" in text or "password" in text else StorageErrorCode.ACCESS_DENIED, "External source access was denied")
        if any(token in text for token in ("bad_network_name", "not_found", "file_not_found", "object_name_not_found", "no such file")):
            return StorageError(StorageErrorCode.OBJECT_NOT_FOUND, "The external source object was not found")
        return StorageError(StorageErrorCode.UNAVAILABLE, message, retryable=True, details={"exception": type(exc).__name__})

    def _run(self, operation):
        try:
            return run_with_deadline(operation, self.config.operation_timeout_seconds)
        except StorageError:
            raise
        except TimeoutError as exc:
            raise StorageError(StorageErrorCode.TIMEOUT, "The external source operation timed out", retryable=True) from exc
        except Exception as exc:
            raise self._map_error(exc) from exc

    def health(self) -> StorageHealth:
        started = time.perf_counter()
        try:
            info = self._run(lambda: self._client().stat(self._unc(self.config.root or "."), **self._session_kwargs()))
            connection = next(iter(self._connection_cache.values()), None)
            return StorageHealth("HEALTHY", self.config.provider_id, (time.perf_counter() - started) * 1000, {"server": self.config.server, "port": self.config.port, "share": self.config.share, "auth_mode": self.config.auth_mode.lower(), "negotiated_dialect": str(getattr(connection, "dialect", None)) if connection else None, "signing_required": True, "encryption_required": True, "root_stat_size": int(getattr(info, "st_size", 0))})
        except StorageError as exc:
            return StorageHealth("UNAVAILABLE", self.config.provider_id, (time.perf_counter() - started) * 1000, {"error_class": exc.code.value})

    def capabilities(self) -> SourceCapabilities:
        return SourceCapabilities()

    def stat(self, locator: StorageLocator) -> StorageStat:
        info = self._run(lambda: self._client().stat(self._unc(locator.relative_path), **self._session_kwargs()))
        return StorageStat(locator, int(info.st_size), modified_at=str(getattr(info, "st_mtime", "")))

    def open_read(self, locator: StorageLocator, *, offset: int | None = None, length: int | None = None) -> BinaryIO:
        stream = self._run(lambda: self._client().open_file(self._unc(locator.relative_path), mode="rb", buffering=0, **self._session_kwargs()))
        if offset:
            self._run(lambda: stream.seek(offset))
        if length is None:
            return stream
        return self._run(lambda: io.BytesIO(stream.read(length)))

    def list(self, prefix: StorageTarget, *, cursor: str | None = None, max_entries_per_page: int = 100) -> SourcePage:
        if max_entries_per_page <= 0:
            raise StorageError(StorageErrorCode.CONFIGURATION_ERROR, "max_entries_per_page must be positive")
        if cursor is None:
            start = 0
        elif cursor.startswith("v1:") and cursor[3:].isdigit():
            start = int(cursor[3:])
        else:
            raise StorageError(StorageErrorCode.PATH_INVALID, "Invalid source continuation cursor")

        def enumerate_bounded():
            names = self._client().listdir(self._unc(prefix.relative_path.rstrip("/")), **self._session_kwargs())
            return list(itertools.islice(names, start, start + max_entries_per_page + 1))

        names = self._run(enumerate_bounded)
        truncated = len(names) > max_entries_per_page
        if truncated:
            names = names[:max_entries_per_page]
        items: list[StorageStat] = []
        failures = 0
        issues: list[str] = []
        base = prefix.relative_path.rstrip("/")
        for name in names:
            try:
                items.append(self.stat(StorageLocator(prefix.provider_id, prefix.share_id, f"{base}/{name}")))
            except StorageError:
                failures += 1
                issues.append("ENTRY_STAT_FAILED")
        complete = not truncated and failures == 0
        next_cursor = f"v1:{start + len(names)}" if not complete else None
        return SourcePage(items, next_cursor, complete, failures, tuple(issues), len(names))


class SMBBinaryStore(BinaryStorePort):
    """Application-managed SMB2/SMB3 binary store.

    The optional ``smbprotocol`` dependency is imported lazily so fixture-only
    development and unit tests do not need an SMB server. No business module
    should import this class directly; use the provider factory/service seam.
    """

    def __init__(self, config: SMBConfig):
        if not config.server or not config.share or not config.username or not config.password:
            raise StorageError(StorageErrorCode.CONFIGURATION_ERROR, "SMB server, share and service credentials are required")
        if config.auth_mode.lower() not in {"ntlm", "kerberos", "negotiate"}:
            raise StorageError(StorageErrorCode.CONFIGURATION_ERROR, "Unsupported SMB authentication mode")
        self.config = config
        self._smbclient = None
        self._connection_cache: dict = {}
        self._auth_fingerprint = (config.server, config.port, config.username, config.auth_mode.lower(), config.require_signing, config.require_encryption)

    @property
    def provider_id(self) -> str:
        return self.config.provider_id

    def _client(self):
        if self._smbclient is None:
            try:
                import smbclient  # type: ignore
            except ImportError as exc:
                raise StorageError(StorageErrorCode.CONFIGURATION_ERROR, "The pinned smbprotocol dependency is not installed") from exc
            self._smbclient = smbclient
            try:
                kwargs = {
                    "username": self.config.username,
                    "password": self.config.password,
                    "port": self.config.port,
                    "auth_protocol": self.config.auth_mode.lower(),
                    "connection_timeout": self.config.connect_timeout_seconds,
                    "require_signing": self.config.require_signing,
                    "encrypt": True if self.config.require_encryption else None,
                    "connection_cache": self._connection_cache,
                }
                smbclient.register_session(self.config.server, **kwargs)
            except Exception as exc:
                raise self._map_error(exc, "SMB authentication failed") from exc
        return self._smbclient

    def _session_kwargs(self) -> dict:
        """Keep every smbclient operation on this provider's port/session.

        smbclient's process cache is keyed by server/port, but a path-only
        operation otherwise defaults to TCP/445. Passing the explicit context
        prevents a non-standard test port from silently changing endpoints
        and keeps credentials/security requirements scoped to this provider.
        """
        return {
            "username": self.config.username,
            "password": self.config.password,
            "port": self.config.port,
            "encrypt": True if self.config.require_encryption else None,
            "connection_timeout": self.config.connect_timeout_seconds,
            "connection_cache": self._connection_cache,
        }

    def rotate_credentials(self, *, username: str, password: str) -> None:
        """Invalidate this provider's pooled session before credential rotation."""
        if self._smbclient is not None:
            reset = getattr(self._smbclient, "reset_connection_cache", None)
            if reset:
                reset(connection_cache=self._connection_cache)
        self._connection_cache = {}
        self.config = SMBConfig(**{**self.config.__dict__, "username": username, "password": password})
        self._smbclient = None

    def _unc(self, relative_path: str) -> str:
        raw = relative_path.strip("/\\") if relative_path else ""
        safe = normalize_relative_path(raw) if raw and raw != "." else ""
        configured_root = self.config.root.strip("/\\") if self.config.root else ""
        if configured_root:
            configured_root = normalize_relative_path(configured_root)
            if safe != configured_root and not safe.startswith(configured_root + "/"):
                safe = f"{configured_root}/{safe}" if safe else configured_root
        windows_safe = safe.replace("/", "\\")
        suffix = f"\\{windows_safe}" if safe else ""
        return f"\\\\{self.config.server}\\{self.config.share}{suffix}"

    @staticmethod
    def _map_error(exc: Exception, message: str = "SMB operation failed") -> StorageError:
        text = str(exc).lower()
        name = type(exc).__name__.lower()
        if "timeout" in text or "timeout" in name:
            return StorageError(StorageErrorCode.TIMEOUT, "The storage operation timed out", retryable=True)
        if any(token in text for token in ("logon_failure", "bad_password", "access_denied", "permission")):
            return StorageError(StorageErrorCode.AUTH_FAILED if "logon" in text or "password" in text else StorageErrorCode.ACCESS_DENIED, "SMB access was denied")
        if any(token in text for token in ("bad_network_name", "not_found", "file_not_found", "object_name_not_found", "no such file", "0xc0000034")):
            return StorageError(StorageErrorCode.OBJECT_NOT_FOUND, "The SMB object or share was not found")
        if any(token in text for token in ("disk_full", "quota", "no_space")):
            return StorageError(StorageErrorCode.QUOTA_OR_SPACE, "The SMB storage has insufficient space")
        if any(token in text for token in ("sharing_violation", "lock")):
            return StorageError(StorageErrorCode.LOCKED, "The SMB object is locked")
        return StorageError(StorageErrorCode.UNAVAILABLE, message, retryable=True, details={"exception": type(exc).__name__})

    def health(self) -> StorageHealth:
        started = time.perf_counter()
        try:
            client = self._client()
            client.stat(self._unc(self.config.root or "."), **self._session_kwargs())
            connection = next(iter(self._connection_cache.values()), None)
            dialect = getattr(connection, "dialect", None)
            dialect_name = {514: "SMB_2_0_2", 528: "SMB_2_1", 770: "SMB_3_0", 771: "SMB_3_0_2", 785: "SMB_3_1_1"}.get(dialect, str(dialect) if dialect is not None else None)
            return StorageHealth("HEALTHY", self.config.provider_id, (time.perf_counter() - started) * 1000, {
                "server": self.config.server,
                "port": self.config.port,
                "share": self.config.share,
                "auth_mode": self.config.auth_mode.lower(),
                "negotiated_dialect": dialect_name,
                "signing_required": bool(getattr(connection, "require_signing", self.config.require_signing)),
                "encryption_required": self.config.require_encryption,
            })
        except StorageError as exc:
            state = "AUTH_FAILED" if exc.code == StorageErrorCode.AUTH_FAILED else "UNAVAILABLE"
            return StorageHealth(state, self.config.provider_id, (time.perf_counter() - started) * 1000, {"error_class": exc.code.value})
        except Exception as exc:
            mapped = self._map_error(exc)
            return StorageHealth("UNAVAILABLE", self.config.provider_id, (time.perf_counter() - started) * 1000, {"error_class": mapped.code.value})

    def capabilities(self) -> StorageCapabilities:
        return StorageCapabilities(range_read=True, atomic_or_safe_rename_with_no_replace=True)

    def stat(self, locator: StorageLocator) -> StorageStat:
        try:
            info = self._client().stat(self._unc(locator.relative_path), **self._session_kwargs())
            return StorageStat(locator, int(info.st_size), modified_at=str(getattr(info, "st_mtime", "")))
        except StorageError:
            raise
        except Exception as exc:
            raise self._map_error(exc, "SMB stat failed") from exc

    def open_read(self, locator: StorageLocator, *, offset: int | None = None, length: int | None = None) -> BinaryIO:
        try:
            stream = self._client().open_file(self._unc(locator.relative_path), mode="rb", buffering=0, **self._session_kwargs())
            if offset:
                stream.seek(offset)
            if length is None:
                return stream
            return io.BytesIO(stream.read(length))
        except StorageError:
            raise
        except Exception as exc:
            raise self._map_error(exc, "SMB read failed") from exc

    def write_temporary(self, target: StorageTarget, content: BinaryIO, *, operation_id: str, expected_size: int, expected_sha256: str) -> TemporaryObject:
        temp_relative = f"{target.relative_path}/.proposalops/tmp/.uploading-{operation_id}"
        temporary = TemporaryObject(self._locator(temp_relative), operation_id, expected_size, expected_sha256)
        created_by_this_attempt = False
        try:
            client = self._client()
            client.makedirs(self._unc(f"{target.relative_path}/.proposalops/tmp"), exist_ok=True, **self._session_kwargs())
            # A retry with the same durable operation may resume an already
            # complete temporary object. A different payload is a conflict;
            # never overwrite or delete another attempt's bytes.
            try:
                with client.open_file(self._unc(temp_relative), mode="rb", buffering=0, **self._session_kwargs()) as existing:
                    existing_digest = hashlib.sha256()
                    existing_size = 0
                    for chunk in iter(lambda: existing.read(1024 * 1024), b""):
                        existing_digest.update(chunk)
                        existing_size += len(chunk)
                if existing_size == expected_size and existing_digest.hexdigest() == expected_sha256:
                    return temporary
                raise StorageError(StorageErrorCode.CONFLICT, "The operation temporary object contains different bytes")
            except StorageError as exc:
                if exc.code != StorageErrorCode.OBJECT_NOT_FOUND:
                    raise
            except Exception as raw_exc:
                mapped = self._map_error(raw_exc, "Temporary object probe failed")
                if mapped.code != StorageErrorCode.OBJECT_NOT_FOUND:
                    raise mapped from raw_exc
            digest = hashlib.sha256()
            size = 0
            with client.open_file(self._unc(temp_relative), mode="xb", buffering=0, **self._session_kwargs()) as destination:
                created_by_this_attempt = True
                for chunk in iter(lambda: content.read(1024 * 1024), b""):
                    destination.write(chunk)
                    digest.update(chunk)
                    size += len(chunk)
                destination.flush()
            if size != expected_size or digest.hexdigest() != expected_sha256:
                self.cleanup_temporary(TemporaryObject(self._locator(temp_relative), operation_id, size, expected_sha256))
                raise StorageError(StorageErrorCode.INTEGRITY_MISMATCH, "SMB input stream failed declared size/hash verification")
            return TemporaryObject(self._locator(temp_relative), operation_id, size, expected_sha256)
        except StorageError:
            raise
        except Exception as exc:
            if created_by_this_attempt:
                try:
                    self.cleanup_temporary(temporary)
                except Exception:
                    pass
            raise self._map_error(exc, "SMB temporary write failed") from exc

    def _locator(self, relative_path: str) -> StorageLocator:
        return StorageLocator(self.config.provider_id, self.config.share, normalize_relative_path(relative_path))

    def finalize(self, temporary: TemporaryObject, final_target: StorageTarget) -> StorageLocator:
        destination = self._unc(final_target.relative_path)
        source = self._unc(temporary.locator.relative_path)
        try:
            parent = final_target.relative_path.rsplit("/", 1)[0]
            if parent:
                self._client().makedirs(self._unc(parent), exist_ok=True, **self._session_kwargs())
            try:
                existing = self.stat(self._locator(final_target.relative_path))
                if existing.size == temporary.expected_size:
                    with self.open_read(existing.locator) as stream:
                        digest = hashlib.sha256(stream.read()).hexdigest()
                    if digest == temporary.expected_sha256:
                        self.cleanup_temporary(temporary)
                        return existing.locator
                raise StorageError(StorageErrorCode.CONFLICT, "The immutable final object already exists with different bytes")
            except StorageError as existing_error:
                if existing_error.code != StorageErrorCode.OBJECT_NOT_FOUND:
                    raise
            # smbclient.rename exposes ReplaceIfExists=false as the safe
            # default. Never fall back to an overwrite disposition.
            # smbclient.rename hard-codes replace_if_exists=False; do not
            # pass an overwrite disposition through this immutable path.
            self._client().rename(source, destination, **self._session_kwargs())
            return self._locator(final_target.relative_path)
        except Exception as exc:
            mapped = self._map_error(exc, "SMB finalization failed")
            if mapped.code == StorageErrorCode.OBJECT_NOT_FOUND:
                raise mapped from exc
            raise mapped from exc

    def mkdirs(self, target_prefix: StorageTarget) -> None:
        try:
            self._client().makedirs(self._unc(target_prefix.relative_path), exist_ok=True, **self._session_kwargs())
        except Exception as exc:
            raise self._map_error(exc, "SMB directory creation failed") from exc

    def list(self, prefix: StorageTarget, *, cursor: str | None = None) -> StoragePage:
        try:
            items = []
            base = prefix.relative_path.rstrip("/")
            for name in self._client().listdir(self._unc(base), **self._session_kwargs()):
                relative = f"{base}/{name}"
                try:
                    items.append(self.stat(self._locator(relative)))
                except StorageError:
                    continue
            return StoragePage(items)
        except StorageError:
            raise
        except Exception as exc:
            raise self._map_error(exc, "SMB listing failed") from exc

    def cleanup_temporary(self, temporary: TemporaryObject) -> None:
        try:
            self._client().remove(self._unc(temporary.locator.relative_path), **self._session_kwargs())
        except Exception as exc:
            mapped = self._map_error(exc, "SMB temporary cleanup failed")
            if mapped.code != StorageErrorCode.OBJECT_NOT_FOUND:
                raise mapped from exc
