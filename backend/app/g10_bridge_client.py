"""Synthetic-only bridge host client for isolated G10 technical readiness."""

from __future__ import annotations

import base64
import hashlib
import json
import mimetypes
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from .schemas.bridge_intake import BridgePackageIn
from .services.bridge_intake import canonical_signature_payload
from .storage.external import StableSourceRead
from .storage.proposal_source_tree import LOGICAL_ROOT, SourceEntry, SourceProject, _parts, classify_project_folder


LIVE_SOURCE_IDENTITY = "QATAR_SYNOLOGY_LIVE"
LIVE_SOURCE_URI_PREFIX = "synology://qatar/"
MAX_LIVE_FILE_BYTES = 10 * 1024 * 1024


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _env_bool(name: str, default: bool = False) -> bool:
    """Parse a strict boolean environment setting.

    Bridge settings are operator supplied, so silently treating a typo as
    false would make a requested continuous sync look like a one-shot run.
    """
    raw = os.getenv(name)
    if raw is None:
        return default
    value = raw.strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be a boolean")


def _sync_interval_seconds() -> int:
    raw = os.getenv("G10_SYNC_INTERVAL_SECONDS", "300")
    try:
        interval = int(raw)
    except ValueError as exc:
        raise ValueError("G10_SYNC_INTERVAL_SECONDS must be an integer") from exc
    if interval < 5 or interval > 86400:
        raise ValueError("G10_SYNC_INTERVAL_SECONDS must be between 5 and 86400")
    return interval


def _project_id_map() -> dict[str, str]:
    raw = os.getenv("G10_PROJECT_ID_MAP_JSON", "{}")
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("G10_PROJECT_ID_MAP_JSON must be valid JSON") from exc
    if not isinstance(value, dict):
        raise ValueError("G10_PROJECT_ID_MAP_JSON must be an object")
    result: dict[str, str] = {}
    for key, project_id in value.items():
        if not isinstance(key, str) or not isinstance(project_id, str) or not project_id.strip():
            raise ValueError("G10_PROJECT_ID_MAP_JSON values must be non-empty strings")
        result[key.strip()] = project_id.strip()
    if os.getenv("G10_PROJECT_ID"):
        result.setdefault("454", os.environ["G10_PROJECT_ID"])
    return result


def _live_attempt_id(source_path_snapshot: str, source_version_token: str) -> str:
    """Return a stable idempotency key for one source version.

    The former random attempt id caused every polling pass to create a new
    intake event for unchanged bytes.  Including the bounded URI and the
    source version token makes retries and later polling passes converge while
    a changed file receives a new event.
    """
    material = f"{source_path_snapshot}\0{source_version_token}".encode("utf-8")
    return f"qatar-{hashlib.sha256(material).hexdigest()}"


class QatarSynologySourceReader:
    """Read-only bounded source reader for the Qatar bridge host.

    This class is intentionally usable only on the host that can reach the
    NAS. It has no write methods and never runs in the Azure API container.
    """

    def __init__(self, *, server: str, share: str, root: str = LOGICAL_ROOT, username: str, password: str, port: int = 445, max_file_bytes: int = MAX_LIVE_FILE_BYTES, max_entries: int = 100000, timeout_seconds: float = 15):
        if not server or not share or not username or not password:
            raise ValueError("Qatar Synology server, share, and read-only credentials are required")
        if not root or root.startswith(("/", "\\")) or ".." in root.split("/") or "\\" in root or ":" in root:
            raise ValueError("Qatar Synology root must be a bounded relative path")
        if max_file_bytes <= 0 or max_entries <= 0 or not 1 <= port <= 65535:
            raise ValueError("Invalid Qatar Synology reader limits")
        self.server, self.share, self.root = server, share, "/".join(_parts(root.strip("/\\")))
        self.username, self.password, self.port = username, password, port
        self.max_file_bytes, self.max_entries = max_file_bytes, max_entries
        self.timeout_seconds = timeout_seconds
        self._smbclient = None
        self._connection_cache: dict = {}

    def _client(self):
        if self._smbclient is None:
            try:
                import smbclient  # type: ignore
            except ImportError as exc:
                raise RuntimeError("SMB_PROTOCOL_UNAVAILABLE") from exc
            self._smbclient = smbclient
            smbclient.register_session(
                self.server,
                username=self.username,
                password=self.password,
                port=self.port,
                auth_protocol=os.getenv("QATAR_SYNOLOGY_AUTH_MODE", "ntlm").lower(),
                connection_timeout=self.timeout_seconds,
                require_signing=os.getenv("QATAR_SYNOLOGY_REQUIRE_SIGNING", "true").lower() == "true",
                encrypt=os.getenv("QATAR_SYNOLOGY_REQUIRE_ENCRYPTION", "true").lower() == "true",
                connection_cache=self._connection_cache,
            )
        return self._smbclient

    def _unc(self, relative: str = "") -> str:
        safe = relative.strip("/\\") if relative else ""
        if safe:
            _parts(safe)
        suffix = "/".join(part for part in (self.root, safe) if part).replace("/", "\\")
        return f"\\\\{self.server}\\{self.share}\\{suffix}"

    def _kwargs(self) -> dict:
        return {
            "username": self.username,
            "password": self.password,
            "port": self.port,
            "connection_timeout": self.timeout_seconds,
            "connection_cache": self._connection_cache,
        }

    def children(self, relative: str = "") -> list[SourceEntry]:
        if relative:
            _parts(relative)
        entries: list[SourceEntry] = []
        client = self._client()
        for item in client.scandir(self._unc(relative), **self._kwargs()):
            if getattr(item, "is_symlink", lambda: False)():
                raise RuntimeError("SYNOLOGY_SYMLINK_REJECTED")
            info = item.stat(follow_symlinks=False)
            is_directory = bool(item.is_dir(follow_symlinks=False))
            is_file = bool(item.is_file(follow_symlinks=False))
            if not (is_directory or is_file):
                raise RuntimeError("SYNOLOGY_SPECIAL_FILE_REJECTED")
            path = f"{relative}/{item.name}" if relative else item.name
            _parts(path)
            entries.append(SourceEntry(path, item.name, is_directory, int(getattr(info, "st_size", 0)), int(getattr(info, "st_mtime_ns", 0))))
            if len(entries) > self.max_entries:
                raise RuntimeError("SYNOLOGY_ENTRY_LIMIT_EXCEEDED")
        return sorted(entries, key=lambda entry: (not entry.is_directory, entry.name, entry.relative_path))

    def discover(self) -> list[SourceProject]:
        return [project for entry in self.children() if entry.is_directory if (project := classify_project_folder(entry.name)) is not None]

    def inventory(self, project_folder: str) -> list[SourceEntry]:
        project = classify_project_folder(project_folder)
        if project is None or len(_parts(project_folder)) != 1:
            raise RuntimeError("SYNOLOGY_PROJECT_PATH_INVALID")
        pending = [project_folder]
        entries: list[SourceEntry] = []
        while pending:
            directory = pending.pop()
            for entry in self.children(directory):
                entries.append(entry)
                if entry.is_directory:
                    pending.append(entry.relative_path)
                if len(entries) > self.max_entries:
                    raise RuntimeError("SYNOLOGY_ENTRY_LIMIT_EXCEEDED")
        return entries

    def capture(self, relative: str, *, attempts: int = 2) -> StableSourceRead:
        parts = _parts(relative)
        if len(parts) < 2 or classify_project_folder(parts[0]) is None:
            raise RuntimeError("SYNOLOGY_FILE_OUTSIDE_PROJECT")
        if not 1 <= attempts <= 3:
            raise ValueError("Capture attempts must be between one and three")
        client = self._client()
        for attempt in range(attempts):
            with client.open_file(self._unc(relative), mode="rb", buffering=0, **self._kwargs()) as stream:
                before = client.stat(self._unc(relative), **self._kwargs())
                if int(before.st_size) > self.max_file_bytes:
                    raise RuntimeError("LIVE_FILE_REQUIRES_CHUNKED_TRANSPORT")
                digest = hashlib.sha256()
                chunks: list[bytes] = []
                size = 0
                for chunk in iter(lambda: stream.read(min(1024 * 1024, self.max_file_bytes - size + 1)), b""):
                    size += len(chunk)
                    if size > self.max_file_bytes:
                        raise RuntimeError("LIVE_FILE_REQUIRES_CHUNKED_TRANSPORT")
                    digest.update(chunk)
                    chunks.append(chunk)
                after = client.stat(self._unc(relative), **self._kwargs())
            value = b"".join(chunks)
            if size == int(before.st_size) and int(getattr(before, "st_mtime_ns", 0)) == int(getattr(after, "st_mtime_ns", 0)) and digest.hexdigest() == _sha(value):
                return StableSourceRead(value, size, digest.hexdigest(), str(getattr(before, "st_mtime_ns", 0)), str(getattr(after, "st_mtime_ns", 0)))
            if attempt + 1 == attempts:
                raise RuntimeError("SYNOLOGY_SOURCE_CHANGED_DURING_CAPTURE")
        raise AssertionError("unreachable")

    def close(self):
        if self._smbclient is not None:
            reset = getattr(self._smbclient, "reset_connection_cache", None)
            if reset:
                reset(connection_cache=self._connection_cache)
        self._connection_cache = {}
        self._smbclient = None


class QuickConnectSynologySourceReader:
    """Read-only Synology File Station reader over DSM HTTPS.

    QuickConnect exposes the same bounded source contract as the SMB reader
    without making the Azure application a NAS client.  This reader belongs on
    the signed bridge runtime: it logs in to File Station, lists only the
    configured logical root, downloads bounded file bytes, and logs out.  No
    write-capable File Station API is called.
    """

    _API_PATH = "/webapi/entry.cgi"

    def __init__(
        self,
        *,
        base_url: str,
        account: str,
        password: str,
        root: str = LOGICAL_ROOT,
        max_file_bytes: int = MAX_LIVE_FILE_BYTES,
        max_entries: int = 100000,
        timeout_seconds: float = 30,
        client: httpx.Client | None = None,
    ):
        if not base_url or not account or not password:
            raise ValueError("Synology QuickConnect URL and read-only credentials are required")
        if not root or root.startswith(("/", "\\")) or ".." in root.split("/") or "\\" in root or ":" in root:
            raise ValueError("Synology root must be a bounded relative path")
        if max_file_bytes <= 0 or max_entries <= 0 or timeout_seconds <= 0:
            raise ValueError("Invalid Synology QuickConnect reader limits")
        self.base_url = base_url.rstrip("/")
        self.account = account
        self.password = password
        self.root = "/".join(_parts(root.strip("/\\")))
        self.max_file_bytes = max_file_bytes
        self.max_entries = max_entries
        self.timeout_seconds = timeout_seconds
        self._client = client or httpx.Client(timeout=timeout_seconds, follow_redirects=True)
        self._owns_client = client is None
        self._sid: str | None = None

    @staticmethod
    def _truthy(value: Any) -> bool:
        return value is True or value == 1 or (isinstance(value, str) and value.lower() in {"1", "true", "yes"})

    @staticmethod
    def _mtime_ns(value: Any) -> int:
        """Normalize DSM mtime (normally epoch seconds) to nanoseconds."""
        try:
            numeric = float(value or 0)
        except (TypeError, ValueError):
            return 0
        if numeric < 0:
            return 0
        if numeric < 10**12:
            return int(numeric * 1_000_000_000)
        if numeric < 10**15:
            return int(numeric * 1_000_000)
        if numeric < 10**18:
            return int(numeric * 1_000)
        return int(numeric)

    def _absolute(self, relative: str = "") -> str:
        if relative:
            parts = _parts(relative)
        else:
            parts = []
        return "/" + "/".join(part for part in (self.root, *parts) if part)

    def _api(self, method: str, *, version: int, **params: Any) -> dict[str, Any]:
        query = {"api": params.pop("api", "SYNO.FileStation.List"), "version": version, "method": method, **params}
        if self._sid:
            query["_sid"] = self._sid
        try:
            response = self._client.get(f"{self.base_url}{self._API_PATH}", params=query)
            response.raise_for_status()
            body = response.json()
        except httpx.HTTPError as exc:
            raise RuntimeError("SYNOLOGY_QUICKCONNECT_HTTP_ERROR") from exc
        except (ValueError, TypeError) as exc:
            raise RuntimeError("SYNOLOGY_QUICKCONNECT_INVALID_RESPONSE") from exc
        if not isinstance(body, dict) or not body.get("success"):
            code = body.get("error", {}).get("code") if isinstance(body, dict) else None
            raise RuntimeError(f"SYNOLOGY_QUICKCONNECT_API_ERROR:{code or 'UNKNOWN'}")
        return body

    def _login(self) -> None:
        if self._sid:
            return
        body = self._api(
            "login",
            version=7,
            api="SYNO.API.Auth",
            account=self.account,
            passwd=self.password,
            session="FileStation",
            format="sid",
        )
        sid = body.get("data", {}).get("sid") if isinstance(body.get("data"), dict) else None
        if not isinstance(sid, str) or not sid:
            raise RuntimeError("SYNOLOGY_QUICKCONNECT_SESSION_MISSING")
        self._sid = sid

    def _list(self, absolute_path: str) -> list[dict[str, Any]]:
        self._login()
        body = self._api(
            "list",
            version=2,
            api="SYNO.FileStation.List",
            folder_path=absolute_path,
            recursive="false",
            # File Station expects this value as a JSON array.  A comma
            # separated string is accepted but silently drops metadata on
            # some DSM versions, leaving files without a bounded size.
            additional=json.dumps(["size", "time", "real_path", "perm"], separators=(",", ":")),
        )
        data = body.get("data") if isinstance(body.get("data"), dict) else {}
        files = data.get("files") if isinstance(data, dict) else []
        if not isinstance(files, list):
            raise RuntimeError("SYNOLOGY_QUICKCONNECT_INVALID_LIST")
        return [item for item in files if isinstance(item, dict)]

    def _entry(self, relative: str, item: dict[str, Any]) -> SourceEntry:
        name = item.get("name")
        if not isinstance(name, str) or not name or "/" in name or "\\" in name:
            raise RuntimeError("SYNOLOGY_INVALID_ENTRY_NAME")
        is_directory = self._truthy(item.get("isdir"))
        if self._truthy(item.get("islink")) or self._truthy(item.get("is_symlink")):
            raise RuntimeError("SYNOLOGY_SYMLINK_REJECTED")
        additional = item.get("additional") if isinstance(item.get("additional"), dict) else {}
        raw_size = item.get("size") if item.get("size") is not None else additional.get("size")
        if not is_directory and raw_size is None:
            raise RuntimeError("SYNOLOGY_FILE_METADATA_MISSING")
        try:
            size = int(raw_size or 0)
        except (TypeError, ValueError) as exc:
            raise RuntimeError("SYNOLOGY_INVALID_FILE_SIZE") from exc
        if size < 0:
            raise RuntimeError("SYNOLOGY_INVALID_FILE_SIZE")
        path = f"{relative}/{name}" if relative else name
        _parts(path)
        raw_mtime = item.get("mtime")
        if raw_mtime is None:
            raw_time = additional.get("time")
            raw_mtime = raw_time.get("mtime") if isinstance(raw_time, dict) else None
        return SourceEntry(path, name, is_directory, size, self._mtime_ns(raw_mtime))

    def children(self, relative: str = "") -> list[SourceEntry]:
        if relative:
            _parts(relative)
        entries = [self._entry(relative, item) for item in self._list(self._absolute(relative))]
        if len(entries) > self.max_entries:
            raise RuntimeError("SYNOLOGY_ENTRY_LIMIT_EXCEEDED")
        return sorted(entries, key=lambda entry: (not entry.is_directory, entry.name, entry.relative_path))

    def discover(self) -> list[SourceProject]:
        return [project for entry in self.children() if entry.is_directory
                if (project := classify_project_folder(entry.name)) is not None]

    def inventory(self, project_folder: str) -> list[SourceEntry]:
        project = classify_project_folder(project_folder)
        if project is None or len(_parts(project_folder)) != 1:
            raise RuntimeError("SYNOLOGY_PROJECT_PATH_INVALID")
        pending = [project_folder]
        entries: list[SourceEntry] = []
        while pending:
            directory = pending.pop()
            for entry in self.children(directory):
                entries.append(entry)
                if entry.is_directory:
                    pending.append(entry.relative_path)
                if len(entries) > self.max_entries:
                    raise RuntimeError("SYNOLOGY_ENTRY_LIMIT_EXCEEDED")
        return entries

    def _stat(self, relative: str) -> SourceEntry:
        parts = _parts(relative)
        if len(parts) < 2 or classify_project_folder(parts[0]) is None:
            raise RuntimeError("SYNOLOGY_FILE_OUTSIDE_PROJECT")
        parent = "/".join(parts[:-1])
        name = parts[-1]
        matches = [entry for entry in self.children(parent) if entry.name == name]
        if len(matches) != 1 or matches[0].is_directory:
            raise RuntimeError("SYNOLOGY_FILE_NOT_FOUND")
        return matches[0]

    def _download(self, relative: str) -> bytes:
        self._login()
        params = {
            "api": "SYNO.FileStation.Download",
            "version": 2,
            "method": "download",
            "path": self._absolute(relative),
            "mode": "open",
            "_sid": self._sid,
        }
        try:
            response = self._client.get(f"{self.base_url}{self._API_PATH}", params=params)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise RuntimeError("SYNOLOGY_QUICKCONNECT_DOWNLOAD_ERROR") from exc
        content_length = response.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > self.max_file_bytes:
                    raise RuntimeError("LIVE_FILE_REQUIRES_CHUNKED_TRANSPORT")
            except ValueError:
                pass
        content = response.content
        content_type = response.headers.get("content-type", "").lower()
        if "json" in content_type:
            try:
                body = response.json()
            except ValueError:
                body = None
            if isinstance(body, dict) and not body.get("success", True):
                code = body.get("error", {}).get("code") if isinstance(body.get("error"), dict) else None
                raise RuntimeError(f"SYNOLOGY_QUICKCONNECT_API_ERROR:{code or 'UNKNOWN'}")
        if len(content) > self.max_file_bytes:
            raise RuntimeError("LIVE_FILE_REQUIRES_CHUNKED_TRANSPORT")
        return content

    def capture(self, relative: str, *, attempts: int = 2) -> StableSourceRead:
        _parts(relative)
        if not 1 <= attempts <= 3:
            raise ValueError("Capture attempts must be between one and three")
        for attempt in range(attempts):
            before = self._stat(relative)
            # File Station may use chunked transfer encoding and omit a
            # Content-Length header.  The bounded source contract must make
            # this decision from the authoritative listing metadata before
            # downloading any bytes.
            if before.size > self.max_file_bytes:
                raise RuntimeError("LIVE_FILE_REQUIRES_CHUNKED_TRANSPORT")
            content = self._download(relative)
            after = self._stat(relative)
            digest = _sha(content)
            if before.size == len(content) == after.size and before.modified_ns == after.modified_ns:
                return StableSourceRead(content, len(content), digest, str(before.modified_ns), str(after.modified_ns))
            if attempt + 1 == attempts:
                raise RuntimeError("SYNOLOGY_SOURCE_CHANGED_DURING_CAPTURE")
        raise AssertionError("unreachable")

    def close(self) -> None:
        if self._sid:
            try:
                self._api("logout", version=7, api="SYNO.API.Auth", session="FileStation")
            except RuntimeError:
                pass
            self._sid = None
        if self._owns_client:
            self._client.close()


def _live_token() -> str:
    # Keep the SMB reader importable for offline inventory/contract tests. The
    # Azure identity SDK is needed only on the bridge host when publishing.
    from azure.identity import CertificateCredential, ManagedIdentityCredential

    if os.getenv("BRIDGE_CERTIFICATE_PATH"):
        credential = CertificateCredential(
            tenant_id=os.environ["BRIDGE_TENANT_ID"],
            client_id=os.environ["BRIDGE_CLIENT_ID"],
            certificate_path=os.environ["BRIDGE_CERTIFICATE_PATH"],
            password=os.getenv("BRIDGE_CERTIFICATE_PASSWORD") or None,
        )
    else:
        credential = ManagedIdentityCredential(client_id=os.environ["BRIDGE_MI_CLIENT_ID"])
    return credential.get_token(f"api://{os.environ['BRIDGE_API_CLIENT_ID']}/.default").token


def _make_live_reader() -> QatarSynologySourceReader | QuickConnectSynologySourceReader:
    transport = os.getenv("QATAR_SYNOLOGY_TRANSPORT", "").strip().upper()
    if transport in {"QUICKCONNECT", "FILESTATION", "HTTPS"} or os.getenv("SYNOLOGY_BASE_URL"):
        return QuickConnectSynologySourceReader(
            base_url=os.environ["SYNOLOGY_BASE_URL"],
            account=os.environ["SYNOLOGY_ACCOUNT"],
            password=os.environ["SYNOLOGY_PASSWORD"],
            root=os.getenv("SYNOLOGY_ROOT", LOGICAL_ROOT),
            max_file_bytes=int(os.getenv("G10_MAX_LIVE_FILE_BYTES", str(MAX_LIVE_FILE_BYTES))),
        )
    return QatarSynologySourceReader(
        server=os.environ["QATAR_SYNOLOGY_SERVER"],
        share=os.environ["QATAR_SYNOLOGY_SHARE"],
        root=os.getenv("QATAR_SYNOLOGY_ROOT", LOGICAL_ROOT),
        username=os.environ["QATAR_SYNOLOGY_USERNAME"],
        password=os.environ["QATAR_SYNOLOGY_PASSWORD"],
        port=int(os.getenv("QATAR_SYNOLOGY_PORT", "445")),
        max_file_bytes=int(os.getenv("G10_MAX_LIVE_FILE_BYTES", str(MAX_LIVE_FILE_BYTES))),
    )


def sync_live_once(reader: QatarSynologySourceReader) -> dict[str, object]:
    """Capture and publish one bounded Synology snapshot.

    The returned counters are deliberately machine-readable so the bridge
    supervisor can record each pass without logging source content.
    """
    projects = reader.discover()
    project_ids = _project_id_map()
    unmapped = sorted(
        project.number
        for project in projects
        if not (project_ids.get(str(project.number)) or project_ids.get(project.folder_name))
    )
    if unmapped and _env_bool("G10_REQUIRE_ALL_PROJECT_MAPPINGS", False):
        raise RuntimeError(
            "LIVE_PROJECT_MAPPING_INCOMPLETE:" + ",".join(str(number) for number in unmapped)
        )
    field_definition_id = os.environ["G10_FIELD_DEFINITION_ID"]
    token = _live_token()
    private_key = Ed25519PrivateKey.from_private_bytes(
        base64.b64decode(os.environ["BRIDGE_SIGNING_PRIVATE_KEY_B64"], validate=True)
    )
    sent = 0
    skipped = 0
    skipped_oversize = 0
    for project in projects:
        # Number keys are the canonical operator contract; accepting the exact
        # folder name also lets an operator map names containing spaces without
        # changing the source reader or URI policy.
        project_id = project_ids.get(str(project.number)) or project_ids.get(project.folder_name)
        if not project_id:
            skipped += 1
            continue
        for entry in reader.inventory(project.folder_name):
            if entry.is_directory:
                continue
            try:
                read = reader.capture(entry.relative_path)
            except RuntimeError as exc:
                # The bridge contract deliberately bounds one signed package.
                # Keep the project discovery pass alive when an older draft
                # contains a larger archive/CAD export; supported files from
                # that project still become draft sources and the bounded
                # omission is reported in the machine result.
                if str(exc) == "LIVE_FILE_REQUIRES_CHUNKED_TRANSPORT":
                    skipped_oversize += 1
                    continue
                raise
            snapshot = f"{LIVE_SOURCE_URI_PREFIX}{LOGICAL_ROOT}/{entry.relative_path}"
            source_version_token = f"{read.before_modified_at}:{read.sha256}"
            payload = BridgePackageIn(
                # Stable ids make retries and continuous polling idempotent;
                # changed bytes produce a new source version and therefore a
                # new event.
                attempt_id=_live_attempt_id(snapshot, source_version_token),
                source_identity=LIVE_SOURCE_IDENTITY,
                source_path_snapshot=snapshot,
                size_bytes=read.size,
                mtime_utc=datetime.fromtimestamp(int(read.before_modified_at) / 1_000_000_000, timezone.utc).isoformat().replace("+00:00", "Z"),
                payload_sha256=read.sha256,
                payload_b64=base64.b64encode(read.content).decode(),
                signature_b64="pending",
                source_version_token=source_version_token,
                correlation_id=f"qatar-bridge-{project.number}-{read.sha256[:16]}",
                source_mode="NEW_UNKNOWN_SOURCE",
                scope_type="PROJECT",
                scope_id=project_id,
                project_id=project_id,
                field_definition_id=field_definition_id,
                field_raw_value=project.folder_name,
                source_filename=entry.name,
                mime_type=mimetypes.guess_type(entry.name)[0] or "application/octet-stream",
            )
            payload = payload.model_copy(
                update={"signature_b64": base64.b64encode(private_key.sign(canonical_signature_payload(payload))).decode()}
            )
            response = httpx.post(
                os.environ["G10_API_URL"].rstrip("/") + "/api/source-intake/bridge/packages",
                headers={"Authorization": f"Bearer {token}"},
                json=payload.model_dump(),
                timeout=30,
            )
            if response.status_code >= 400:
                # Keep bridge logs useful without ever logging package bytes,
                # credentials, bearer tokens, or Synology paths.
                try:
                    detail = response.json().get("detail", {})
                    code = detail.get("code") if isinstance(detail, dict) else None
                    error_class = detail.get("storage_error_class") if isinstance(detail, dict) else None
                except (ValueError, TypeError):
                    code, error_class = None, None
                suffix = f":{error_class}" if error_class else ""
                raise RuntimeError(f"LIVE_BRIDGE_POST_FAILED:{response.status_code}:{code or 'UNKNOWN'}{suffix}")
            sent += 1
    return {
        "source_identity": LIVE_SOURCE_IDENTITY,
        "logical_root": LOGICAL_ROOT,
        "projects_discovered": len(projects),
        "projects_unmapped": unmapped,
        "packages_sent": sent,
        "projects_skipped_without_mapping": skipped,
        "files_skipped_oversize": skipped_oversize,
        "synology_write_count": 0,
    }


def run_live() -> None:
    """Run one pass by default, or poll the same bounded root continuously."""
    reader = _make_live_reader()
    continuous = _env_bool("G10_CONTINUOUS_SYNC", False)
    interval = _sync_interval_seconds() if continuous else None
    try:
        while True:
            print(json.dumps(sync_live_once(reader), sort_keys=True), flush=True)
            if not continuous:
                return
            time.sleep(interval)
    finally:
        reader.close()


def main() -> None:
    if os.getenv("G10_BRIDGE_MODE", "SYNTHETIC").upper() == "LIVE":
        run_live()
        return
    fixture_path = Path(os.getenv("G10_BRIDGE_FIXTURE_PATH", "/workspace/backend/app/fixtures/g10_bridge_fixture.txt"))
    before = fixture_path.stat()
    content = fixture_path.read_bytes()
    after = fixture_path.stat()
    before_hash = _sha(content)
    if before.st_size != after.st_size or before.st_mtime_ns != after.st_mtime_ns or before_hash != _sha(fixture_path.read_bytes()):
        raise RuntimeError("G10_SOURCE_MUTATION_DETECTED")

    private_key = Ed25519PrivateKey.from_private_bytes(base64.b64decode(os.environ["BRIDGE_SIGNING_PRIVATE_KEY_B64"], validate=True))
    attempt_id = os.getenv("G10_ATTEMPT_ID", f"g10-{uuid4().hex}")
    project_id = os.environ["G10_PROJECT_ID"]
    field_definition_id = os.environ["G10_FIELD_DEFINITION_ID"]
    payload = BridgePackageIn(
        attempt_id=attempt_id,
        source_identity="QATAR_SYNOLOGY_SYNTHETIC_FIXTURE",
        source_path_snapshot="synthetic://qatar-synology/g10_bridge_fixture.txt",
        size_bytes=len(content),
        mtime_utc=datetime.fromtimestamp(after.st_mtime, timezone.utc).isoformat().replace("+00:00", "Z"),
        payload_sha256=before_hash,
        payload_b64=base64.b64encode(content).decode(),
        signature_b64="pending",
        source_version_token=f"g10-fixture-{before.st_mtime_ns}",
        correlation_id=f"g10-bridge-{attempt_id}",
        scope_type="PROJECT",
        scope_id=project_id,
        project_id=project_id,
        field_definition_id=field_definition_id,
        field_raw_value="SYNTHETIC_BRIDGE_CANDIDATE",
        source_filename=fixture_path.name,
        mime_type="text/plain",
    )
    payload = payload.model_copy(update={"signature_b64": base64.b64encode(private_key.sign(canonical_signature_payload(payload))).decode()})
    from azure.identity import ManagedIdentityCredential

    token = ManagedIdentityCredential(client_id=os.environ["BRIDGE_MI_CLIENT_ID"]).get_token(f"api://{os.environ['BRIDGE_API_CLIENT_ID']}/.default").token
    response = httpx.post(
        os.environ["G10_API_URL"].rstrip("/") + "/api/source-intake/bridge/packages",
        headers={"Authorization": f"Bearer {token}"},
        json=payload.model_dump(),
        timeout=30,
    )
    body = response.json() if response.content else {}
    print(json.dumps({
        "http_status": response.status_code,
        "result": body.get("result"),
        "attempt_id": attempt_id,
        "package_sha256": before_hash,
        "source_hash_before_after_equal": True,
        "source_mtime_before_after_equal": before.st_mtime_ns == after.st_mtime_ns,
        "source_size_before_after_equal": before.st_size == after.st_size,
        "verified_assertion_created": body.get("verified_assertion_created"),
        "projection_created": body.get("projection_created"),
        "error_code": (body.get("detail") or {}).get("code") if isinstance(body.get("detail"), dict) else None,
    }, sort_keys=True))
    response.raise_for_status()


if __name__ == "__main__":
    main()
