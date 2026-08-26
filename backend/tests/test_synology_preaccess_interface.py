from __future__ import annotations

import io
from pathlib import Path
from types import SimpleNamespace

import pytest

from backend.app.storage import (
    MockBinaryStore,
    SMBSourceConfig,
    SMBSourceStore,
    SourceCapabilities,
    SourcePage,
    StorageHealth,
    StorageLocator,
    StorageStat,
    StorageTarget,
    create_binary_store,
)
from backend.app.storage.factory import create_external_source_store
from backend.app.storage.path_policy import normalize_relative_path
from backend.app.storage.errors import StorageError, StorageErrorCode


class FakeSource:
    def __init__(self, files: dict[str, bytes] | None = None):
        self.files = files or {"root/report.txt": b"synthetic report"}
        self.modified = {path: "v1" for path in self.files}
        self.server_ids = {path: f"id:{path}" for path in self.files}
        self.open_count = 0
        self.mutate_on_open = False
        self.fail_names: set[str] = set()

    def _stat(self, path: str) -> StorageStat:
        if path not in self.files:
            raise FileNotFoundError(path)
        locator = StorageLocator("synthetic-source", "synthetic", path)
        return StorageStat(locator, len(self.files[path]), modified_at=self.modified[path], server_file_id=self.server_ids[path])

    def health(self):
        return StorageHealth("HEALTHY", "synthetic-source")

    def capabilities(self):
        return SourceCapabilities()

    def stat(self, locator):
        return self._stat(locator.relative_path)

    def open_read(self, locator, *, offset=None, length=None):
        self.open_count += 1
        if self.mutate_on_open:
            self.modified[locator.relative_path] = "v2"
        data = self.files[locator.relative_path]
        start = offset or 0
        return io.BytesIO(data[start:] if length is None else data[start:start + length])

    def list(self, prefix, *, cursor=None, max_entries_per_page=100):
        base = prefix.relative_path.rstrip("/") + "/"
        names = sorted(path[len(base):] for path in self.files if path.startswith(base) and "/" not in path[len(base):])
        start = 0 if cursor is None else int(cursor.removeprefix("opaque:"))
        selected = names[start:start + max_entries_per_page]
        failed = len([name for name in selected if name in self.fail_names])
        complete = start + len(selected) >= len(names) and failed == 0
        return SourcePage([self._stat(f"{prefix.relative_path.rstrip('/')}/{name}") for name in selected if name not in self.fail_names], None if complete else f"opaque:{start + len(selected)}", complete, failed, ("ENTRY_STAT_FAILED",) if failed else (), len(selected))


def secure_config(**overrides):
    values = {
        "server": "synology.invalid",
        "share": "AMEC",
        "username": "readonly",
        "password": "synthetic-only-placeholder",
    }
    values.update(overrides)
    return SMBSourceConfig(**values)


def test_external_source_is_not_a_managed_write_store():
    source = SMBSourceStore(secure_config())
    mutation_names = ("write_temporary", "finalize", "mkdirs", "cleanup_temporary", "rename", "remove", "delete", "create", "append")
    assert all(not hasattr(source, name) for name in mutation_names)
    assert not isinstance(source, MockBinaryStore)


def test_external_capabilities_are_read_only_and_secure():
    capabilities = SMBSourceStore(secure_config()).capabilities()
    assert capabilities == SourceCapabilities()
    assert capabilities.read and capabilities.stat and capabilities.list and capabilities.range_read
    assert not capabilities.write_new and not capabilities.mkdir and not capabilities.safe_finalize
    assert not capabilities.atomic_or_safe_rename_with_no_replace and not capabilities.delete and not capabilities.writeback
    assert capabilities.signing_required and capabilities.encryption_required
    assert not capabilities.anonymous and not capabilities.guest


def test_managed_factory_remains_write_capable(tmp_path: Path, monkeypatch):
    settings = SimpleNamespace(storage_provider="mock", app_env="TEST", mock_systems_root=str(tmp_path))
    monkeypatch.setattr("backend.app.storage.factory.get_settings", lambda: settings)
    managed = create_binary_store()
    assert isinstance(managed, MockBinaryStore)
    assert hasattr(managed, "write_temporary") and hasattr(managed, "finalize")


def test_external_factory_returns_dedicated_read_only_runtime(monkeypatch):
    settings = SimpleNamespace(
        smb_external_server="synthetic.invalid",
        smb_external_port=445,
        smb_external_share="synthetic",
        smb_external_root="root",
        smb_external_username="synthetic-readonly",
        smb_external_password="synthetic-placeholder",
        smb_external_auth_mode="ntlm",
        smb_external_require_signing=True,
        smb_external_require_encryption=True,
        smb_operation_timeout_seconds=1,
    )
    monkeypatch.setattr("backend.app.storage.factory.get_settings", lambda: settings)
    source = create_external_source_store()
    assert isinstance(source, SMBSourceStore)
    assert not isinstance(source, MockBinaryStore)
    assert not hasattr(source, "write_temporary")


@pytest.mark.parametrize("field,value", [
    ("require_signing", False),
    ("require_encryption", False),
    ("anonymous", True),
    ("guest", True),
    ("auth_mode", "anonymous"),
    ("operation_timeout_seconds", 0),
])
def test_external_security_contract_rejects_unsafe_configuration(field, value):
    with pytest.raises(Exception):
        SMBSourceConfig(**{**secure_config().__dict__, field: value})


@pytest.mark.parametrize("bad_path", [
    "../escape.txt", "/absolute.txt", "\\\\server\\share\\x.txt", "C:/drive.txt", "a/../../escape.txt",
    "a\x00b.txt", "a\n b.txt", "CON", "folder/PRN.txt", "folder/AUX", "folder/NUL", "folder/COM1.txt",
    "folder/LPT1", "folder/..", "", ":alternate", "\\absolute", "/rooted",
])
def test_source_paths_are_rejected_before_provider_use(bad_path):
    with pytest.raises(Exception):
        normalize_relative_path(bad_path)


def test_source_root_confinement_prefixes_only_safe_relative_paths():
    source = SMBSourceStore(secure_config(root="AMEC/Projects"))
    unc = source._unc("PRJ-001/report.pdf")
    assert unc == r"\\synology.invalid\AMEC\AMEC\Projects\PRJ-001\report.pdf"
    with pytest.raises(Exception):
        source._unc("../outside")


class FakeRaw:
    def __init__(self, data=b"0123456789", fail_on_read=False):
        self.data = data
        self.position = 0
        self.read_calls = []
        self.closed = False
        self.fail_on_read = fail_on_read

    def seek(self, offset):
        self.position = offset

    def read(self, size=-1):
        self.read_calls.append(size)
        if self.fail_on_read:
            raise TimeoutError("synthetic timeout")
        result = self.data[self.position:] if size < 0 else self.data[self.position:self.position + size]
        self.position += len(result)
        return result

    def close(self):
        self.closed = True


class FakeSMBClient:
    def __init__(self, names=None, stat_failures=None, raw=None):
        self.names = names or ["z.txt", "a.txt", "m.txt"]
        self.stat_failures = set(stat_failures or ())
        self.raw = raw or FakeRaw()
        self.stat_kwargs = []
        self.open_kwargs = []

    def listdir(self, path, **kwargs):
        return list(self.names)

    def stat(self, path, **kwargs):
        self.stat_kwargs.append(kwargs)
        if path.rsplit(chr(92), 1)[-1] in self.stat_failures:
            raise PermissionError("access_denied")
        return SimpleNamespace(st_size=10, st_mtime="m1")

    def open_file(self, path, **kwargs):
        self.open_kwargs.append(kwargs)
        return self.raw


def source_with_client(client):
    source = SMBSourceStore(secure_config())
    source._smbclient = client
    return source


def test_real_adapter_fake_client_bounded_page():
    source = source_with_client(FakeSMBClient())
    page = source.list(StorageTarget("smb-external-source", "AMEC", "root"), max_entries_per_page=2)
    assert [item.locator.relative_path for item in page.items] == ["root/a.txt", "root/m.txt"]
    assert page.cursor == "v1:2" and not page.complete
    assert page.entries_examined == 2


def test_real_adapter_fake_client_stat_failure_is_incomplete():
    source = source_with_client(FakeSMBClient(names=["a.txt", "bad.txt"], stat_failures={"bad.txt"}))
    page = source.list(StorageTarget("smb-external-source", "AMEC", "root"))
    assert not page.complete and page.failed_entry_count == 1 and page.cursor is None
    assert "ENTRY_STAT_FAILED" in page.issues


def test_real_adapter_fake_client_invalid_cursor_is_rejected():
    source = source_with_client(FakeSMBClient())
    with pytest.raises(StorageError) as error:
        source.list(StorageTarget("smb-external-source", "AMEC", "root"), cursor="bad")
    assert error.value.code == StorageErrorCode.PATH_INVALID


def test_cursor_does_not_skip_failed_entry():
    client = FakeSMBClient(names=["a.txt", "bad.txt", "c.txt"], stat_failures={"bad.txt"})
    source = source_with_client(client)
    page = source.list(StorageTarget("smb-external-source", "AMEC", "root"), max_entries_per_page=2)
    assert page.cursor is None
    assert page.failed_entry_count == 1


def test_smb_source_open_read_is_not_eager_full_length():
    raw = FakeRaw(b"0123456789")
    source = source_with_client(FakeSMBClient(raw=raw))
    locator = StorageLocator("smb-external-source", "AMEC", "root/file.bin")
    with source.open_read(locator, offset=2, length=6) as stream:
        assert raw.read_calls == []
        assert stream.read(3) == b"234"
        assert stream.read(3) == b"567"
        assert stream.read(1) == b""
        with pytest.raises(StorageError, match="explicit chunk"):
            stream.read()
    assert raw.closed


def test_smb_source_open_read_maps_and_closes_read_failure():
    raw = FakeRaw(fail_on_read=True)
    source = source_with_client(FakeSMBClient(raw=raw))
    stream = source.open_read(StorageLocator("smb-external-source", "AMEC", "root/file.bin"), length=3)
    with pytest.raises(Exception) as error:
        stream.read(1)
    assert isinstance(error.value, StorageError)
    assert error.value.code == StorageErrorCode.TIMEOUT
    assert raw.closed


def test_external_health_does_not_expose_raw_endpoint_components():
    source = source_with_client(FakeSMBClient())
    health = source.health()
    rendered = repr(health.detail)
    assert "synology.invalid" not in rendered and "AMEC" not in rendered and "root" not in rendered
    assert "endpoint_fingerprint" in health.detail and health.detail["security"]["encryption_required"]


def test_real_adapter_passes_security_kwargs_to_fake_client():
    client = FakeSMBClient()
    source = source_with_client(client)
    source.stat(StorageLocator("smb-external-source", "AMEC", "root/a.txt"))
    assert client.stat_kwargs[-1]["encrypt"] is True
    assert client.stat_kwargs[-1]["port"] == 445


def test_real_adapter_has_no_write_methods():
    source = source_with_client(FakeSMBClient())
    assert all(not hasattr(source, name) for name in ("write", "delete", "mkdir", "rename", "remove"))
