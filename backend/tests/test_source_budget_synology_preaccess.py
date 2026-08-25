from __future__ import annotations

import io

import pytest

from backend.app.storage import (
    ContentBudgetExceeded,
    ReadBudgetState,
    SourceReadBudgets,
    StorageLocator,
    read_bounded_content,
)

from backend.tests.test_synology_preaccess_interface import FakeSource


def test_default_content_budgets_are_frozen_and_positive():
    budgets = SourceReadBudgets()
    assert budgets.max_file_bytes > 0
    assert budgets.max_total_content_bytes_per_run >= budgets.max_file_bytes
    assert budgets.max_files_with_content_per_run > 0
    assert budgets.max_parallelism == 1


def test_oversized_object_is_rejected_before_open():
    source = FakeSource({"root/large.bin": b"12345"})
    with pytest.raises(ContentBudgetExceeded, match="CONTENT_READ_BLOCKED_BUDGET"):
        read_bounded_content(source, StorageLocator("synthetic-source", "synthetic", "root/large.bin"), SourceReadBudgets(max_file_bytes=4))
    assert source.open_count == 0


def test_cumulative_byte_budget_is_reserved_before_second_open():
    source = FakeSource({"root/a": b"1234", "root/b": b"5678"})
    budgets = SourceReadBudgets(max_file_bytes=8, max_total_content_bytes_per_run=6)
    state = ReadBudgetState(budgets)
    locator = StorageLocator("synthetic-source", "synthetic", "root/a")
    read_bounded_content(source, locator, budgets, budget_state=state)
    with pytest.raises(ContentBudgetExceeded, match="CONTENT_READ_BLOCKED_BUDGET"):
        read_bounded_content(source, StorageLocator("synthetic-source", "synthetic", "root/b"), budgets, budget_state=state)
    assert source.open_count == 1


def test_file_count_budget_is_explicit():
    source = FakeSource({"root/a": b"1", "root/b": b"2"})
    budgets = SourceReadBudgets(max_files_with_content_per_run=1)
    state = ReadBudgetState(budgets)
    read_bounded_content(source, StorageLocator("synthetic-source", "synthetic", "root/a"), budgets, budget_state=state)
    with pytest.raises(ContentBudgetExceeded, match="CONTENT_READ_BLOCKED_BUDGET"):
        read_bounded_content(source, StorageLocator("synthetic-source", "synthetic", "root/b"), budgets, budget_state=state)


def test_short_read_is_not_reported_as_success():
    source = FakeSource({"root/a": b"1234"})
    source.open_read = lambda locator, **kwargs: io.BytesIO(b"12")
    with pytest.raises(Exception, match="source read length"):
        read_bounded_content(source, StorageLocator("synthetic-source", "synthetic", "root/a"), SourceReadBudgets())


def test_source_change_during_read_is_not_reported_as_success():
    source = FakeSource({"root/a": b"1234"})
    source.mutate_on_open = True
    with pytest.raises(Exception, match="changed during bounded read"):
        read_bounded_content(source, StorageLocator("synthetic-source", "synthetic", "root/a"), SourceReadBudgets())


def test_incremental_hash_is_returned_only_after_full_bounded_read():
    source = FakeSource({"root/a": b"1234"})
    content, stat, digest = read_bounded_content(source, StorageLocator("synthetic-source", "synthetic", "root/a"), SourceReadBudgets())
    assert content == b"1234" and stat.size == 4 and len(digest) == 64


def test_negative_budget_configuration_is_rejected():
    with pytest.raises(ValueError):
        SourceReadBudgets(max_file_bytes=0)


def test_preaccess_parallelism_above_one_rejected():
    with pytest.raises(ValueError, match="max_parallelism=1"):
        SourceReadBudgets(max_parallelism=2)
