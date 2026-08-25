from __future__ import annotations

import io

import pytest

from backend.app.storage import SMBSourceConfig, SMBSourceStore, StorageError, StorageLocator, SourceReadBudgets, ContentBudgetExceeded, read_bounded_content
from backend.tests.test_synology_preaccess_interface import FakeSource


class Raw:
    def __init__(self, data=b"abcdef"):
        self.data = data
        self.position = 0
        self.closed = False

    def seek(self, offset):
        self.position = offset

    def read(self, size=-1):
        value = self.data[self.position:] if size < 0 else self.data[self.position:self.position + size]
        self.position += len(value)
        return value

    def close(self):
        self.closed = True


class Client:
    def __init__(self):
        self.open_calls = 0
        self.raw = Raw()

    def open_file(self, *args, **kwargs):
        self.open_calls += 1
        return self.raw


def config(**overrides):
    values = {"server": "synthetic.invalid", "share": "AMEC", "username": "readonly", "password": "synthetic-placeholder"}
    values.update(overrides)
    return SMBSourceConfig(**values)


def locator():
    return StorageLocator("smb-external-source", "AMEC", "root/file.bin")


def test_direct_open_without_explicit_length_rejected():
    client = Client()
    source = SMBSourceStore(config())
    source._smbclient = client
    with pytest.raises(StorageError, match="explicit total length"):
        source.open_read(locator())
    assert client.open_calls == 0


def test_direct_oversize_open_rejected_before_fake_open():
    client = Client()
    source = SMBSourceStore(config(max_single_read_bytes=4))
    source._smbclient = client
    with pytest.raises(StorageError, match="maximum single read"):
        source.open_read(locator(), length=5)
    assert client.open_calls == 0


def test_max_single_read_bytes_must_be_positive():
    with pytest.raises(StorageError, match="maximum single read"):
        config(max_single_read_bytes=0)


def test_explicit_bounded_open_works():
    client = Client()
    source = SMBSourceStore(config(max_single_read_bytes=6))
    source._smbclient = client
    with source.open_read(locator(), offset=1, length=3) as stream:
        assert stream.read(3) == b"bcd"
    assert client.open_calls == 1 and client.raw.closed


def test_zero_length_direct_open_is_safe():
    client = Client()
    source = SMBSourceStore(config())
    source._smbclient = client
    with source.open_read(locator(), length=0) as stream:
        assert stream.read(1) == b""
    assert client.open_calls == 0


def test_helper_file_budget_remains_effective():
    source = FakeSource({"root/large.bin": b"12345"})
    with pytest.raises(ContentBudgetExceeded):
        read_bounded_content(source, StorageLocator("synthetic-source", "synthetic", "root/large.bin"), SourceReadBudgets(max_file_bytes=4))
    assert source.open_count == 0


def test_helper_total_run_budget_remains_effective():
    source = FakeSource({"root/a": b"1234", "root/b": b"5678"})
    budgets = SourceReadBudgets(max_file_bytes=8, max_total_content_bytes_per_run=6)
    from backend.app.storage import ReadBudgetState
    state = ReadBudgetState(budgets)
    read_bounded_content(source, StorageLocator("synthetic-source", "synthetic", "root/a"), budgets, budget_state=state)
    with pytest.raises(ContentBudgetExceeded):
        read_bounded_content(source, StorageLocator("synthetic-source", "synthetic", "root/b"), budgets, budget_state=state)
