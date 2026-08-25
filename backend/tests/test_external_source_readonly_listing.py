from __future__ import annotations

import pytest

from backend.app.storage import SourceReadBudgets, StorageTarget, enumerate_bounded
from backend.tests.test_synology_preaccess_interface import FakeSource


def prefix():
    return StorageTarget("synthetic-source", "synthetic", "root")


def test_page_result_is_bounded_and_continuable():
    source = FakeSource({f"root/{index:03d}": b"x" for index in range(7)})
    result = source.list(prefix(), max_entries_per_page=3)
    assert len(result.items) == 3
    assert result.complete is False
    assert result.cursor and not result.cursor.isdigit()
    assert result.failed_entry_count == 0


def test_complete_page_has_no_cursor():
    source = FakeSource({"root/001": b"x"})
    result = source.list(prefix(), max_entries_per_page=3)
    assert result.complete is True
    assert result.cursor is None


def test_failed_stat_is_never_reported_complete():
    source = FakeSource({"root/001": b"x", "root/002": b"y"})
    source.fail_names.add("002")
    result = source.list(prefix(), max_entries_per_page=3)
    assert result.failed_entry_count == 1
    assert result.complete is False
    assert result.issues == ("ENTRY_STAT_FAILED",)
    assert result.entries_examined == 2


def test_run_budget_stops_before_unbounded_tree_walk():
    source = FakeSource({f"root/{index:03d}": b"x" for index in range(50)})
    result = enumerate_bounded(source, prefix(), SourceReadBudgets(max_entries_per_page=4, max_entries_per_run=7))
    assert result.entries_seen <= 7
    assert result.complete is False


def test_listing_does_not_recurse_into_nested_directories():
    source = FakeSource({"root/top.txt": b"x", "root/nested/deep.txt": b"y"})
    result = source.list(prefix(), max_entries_per_page=10)
    assert [item.locator.relative_path for item in result.items] == ["root/top.txt"]


@pytest.mark.parametrize("limit", [1, 2, 5, 10, 25])
def test_page_limit_is_honored_for_each_local_policy_value(limit):
    source = FakeSource({f"root/{index:03d}": b"x" for index in range(30)})
    result = source.list(prefix(), max_entries_per_page=limit)
    assert len(result.items) <= limit
