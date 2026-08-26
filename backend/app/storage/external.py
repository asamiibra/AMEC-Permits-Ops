"""External/source-root read helpers with mutation detection."""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from enum import StrEnum
from typing import Callable

from .port import ReadOnlySourcePort, SourcePage, StorageLocator, StorageStat, StorageTarget


class SourceChangedDuringImport(RuntimeError):
    code = "SOURCE_CHANGED_DURING_IMPORT"


@dataclass(frozen=True)
class StableSourceRead:
    content: bytes
    size: int
    sha256: str
    before_modified_at: str | None
    after_modified_at: str | None


def read_stable_source(store: ReadOnlySourcePort, locator: StorageLocator) -> StableSourceRead:
    """Compatibility wrapper that still uses the bounded source-read path.

    Callers should prefer ``read_bounded_content`` when they need explicit
    per-run budgets.  This wrapper intentionally cannot call ``read()`` on a
    provider stream without a bounded length.
    """
    budgets = SourceReadBudgets()
    content, before, digest = read_bounded_content(store, locator, budgets)
    after = store.stat(locator)
    return StableSourceRead(content, len(content), digest, before.modified_at, after.modified_at)


class StabilityState(StrEnum):
    DETECTED = "DETECTED"
    WAITING_FOR_STABILITY = "WAITING_FOR_STABILITY"
    READY_FOR_BOUNDED_READ = "READY_FOR_BOUNDED_READ"
    STABILITY_TIMEOUT = "STABILITY_TIMEOUT"


class ContentBudgetExceeded(RuntimeError):
    code = "CONTENT_READ_BLOCKED_BUDGET"


class OperationDeadlineExceeded(TimeoutError):
    code = "OPERATION_DEADLINE_EXCEEDED"


@dataclass(frozen=True)
class SourceReadBudgets:
    max_file_bytes: int = 10 * 1024 * 1024
    max_total_content_bytes_per_run: int = 50 * 1024 * 1024
    max_files_with_content_per_run: int = 100
    max_runtime_seconds: float = 60
    max_parallelism: int = 1
    max_entries_per_page: int = 100
    max_entries_per_run: int = 500

    def __post_init__(self) -> None:
        values = (self.max_file_bytes, self.max_total_content_bytes_per_run, self.max_files_with_content_per_run, self.max_runtime_seconds, self.max_parallelism, self.max_entries_per_page, self.max_entries_per_run)
        if any(value <= 0 for value in values):
            raise ValueError("source budgets must be positive")
        if self.max_parallelism != 1:
            raise ValueError("Synology preaccess requires max_parallelism=1")


@dataclass
class ReadBudgetState:
    budgets: SourceReadBudgets
    total_content_bytes: int = 0
    files_with_content: int = 0

    def reserve(self, expected_bytes: int) -> None:
        if expected_bytes > self.budgets.max_file_bytes or self.files_with_content >= self.budgets.max_files_with_content_per_run or self.total_content_bytes + expected_bytes > self.budgets.max_total_content_bytes_per_run:
            raise ContentBudgetExceeded("CONTENT_READ_BLOCKED_BUDGET")
        self.files_with_content += 1
        self.total_content_bytes += expected_bytes


def run_with_deadline(operation: Callable[[], object], timeout_seconds: float) -> object:
    """Run synchronously and fail closed after the operation returns.

    Python threads cannot safely kill an arbitrary SMB operation.  The SMB
    adapter therefore does not use this helper; it relies on smbclient's
    transport/session timeout.  A future hard-stop implementation must move
    the operation into a killable fetcher process or container.
    """
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")
    started = time.monotonic()
    result = operation()
    if time.monotonic() - started > timeout_seconds:
        raise OperationDeadlineExceeded("source operation exceeded its deadline")
    return result


@dataclass(frozen=True)
class StabilityObservation:
    size: int
    modified_at: str | None
    version_token: str | None = None
    server_file_id: str | None = None

    @classmethod
    def from_stat(cls, stat: StorageStat) -> "StabilityObservation":
        return cls(stat.size, stat.modified_at, stat.sha256, stat.server_file_id)

    def identity_token(self) -> tuple:
        return self.size, self.modified_at, self.version_token, self.server_file_id


@dataclass(frozen=True)
class StabilityPolicy:
    required_stable_observations: int = 2
    observation_interval_seconds: float = 1
    maximum_wait_seconds: float = 60

    def __post_init__(self) -> None:
        if self.required_stable_observations < 2 or self.observation_interval_seconds < 0 or self.maximum_wait_seconds <= 0:
            raise ValueError("invalid stability policy")


class SourceStabilityTracker:
    def __init__(self, policy: StabilityPolicy, *, clock: Callable[[], float] = time.monotonic):
        self.policy = policy
        self.clock = clock
        self.state = StabilityState.DETECTED
        self._last: StabilityObservation | None = None
        self._stable_count = 0
        self._started_at: float | None = None
        self._last_observed_at: float | None = None
        self._terminal = False

    @property
    def stable_count(self) -> int:
        return self._stable_count

    def observe(self, observation: StabilityObservation | None) -> StabilityState:
        now = self.clock()
        if self._started_at is None:
            self._started_at = now
        if self._terminal:
            return self.state
        if observation is None:
            self.state = StabilityState.DETECTED
            self._last = None
            self._stable_count = 0
            self._last_observed_at = None
            return self.state
        if now - self._started_at > self.policy.maximum_wait_seconds:
            self.state = StabilityState.STABILITY_TIMEOUT
            self._terminal = True
            return self.state
        if self._last is None or self._last.identity_token() != observation.identity_token():
            self.state = StabilityState.DETECTED
            self._stable_count = 1
            self._last = observation
            self._last_observed_at = now
            return self.state
        if self._last_observed_at is not None and now - self._last_observed_at < self.policy.observation_interval_seconds:
            self.state = StabilityState.WAITING_FOR_STABILITY
            return self.state
        self._stable_count += 1
        self._last = observation
        self._last_observed_at = now
        self.state = StabilityState.READY_FOR_BOUNDED_READ if self._stable_count >= self.policy.required_stable_observations else StabilityState.WAITING_FOR_STABILITY
        return self.state


def classify_path_change(previous: StabilityObservation, current: StabilityObservation, *, content_hash_equal: bool) -> str:
    if previous.identity_token() == current.identity_token():
        return "UNCHANGED"
    if content_hash_equal:
        return "MOVE_RENAME_CANDIDATE"
    return "SOURCE_CHANGED_REVIEW_REQUIRED"


@dataclass(frozen=True)
class BoundedEnumeration:
    items: list[StorageStat]
    cursor: str | None
    complete: bool
    failed_entry_count: int
    entries_seen: int
    issues: tuple[str, ...] = ()


def enumerate_bounded(source: ReadOnlySourcePort, prefix: StorageTarget, budgets: SourceReadBudgets) -> BoundedEnumeration:
    items: list[StorageStat] = []
    cursor: str | None = None
    entries_seen = 0
    while entries_seen < budgets.max_entries_per_run:
        page_size = min(budgets.max_entries_per_page, budgets.max_entries_per_run - entries_seen)
        page: SourcePage = source.list(prefix, cursor=cursor, max_entries_per_page=page_size)
        items.extend(page.items)
        entries_seen += len(page.items) + page.failed_entry_count
        if page.failed_entry_count or page.complete:
            return BoundedEnumeration(items, page.cursor, page.complete, page.failed_entry_count, entries_seen, page.issues)
        if not page.cursor or page.cursor == cursor:
            return BoundedEnumeration(items, page.cursor, False, page.failed_entry_count, entries_seen, page.issues)
        cursor = page.cursor
    return BoundedEnumeration(items, cursor, False, 0, entries_seen)


def read_bounded_content(source: ReadOnlySourcePort, locator: StorageLocator, budgets: SourceReadBudgets, *, budget_state: ReadBudgetState | None = None, started_at: float | None = None, clock: Callable[[], float] = time.monotonic) -> tuple[bytes, StorageStat, str]:
    started = started_at if started_at is not None else clock()
    before = source.stat(locator)
    if budget_state is not None:
        budget_state.reserve(before.size)
    elif before.size > budgets.max_file_bytes:
        raise ContentBudgetExceeded("CONTENT_READ_BLOCKED_BUDGET")
    with source.open_read(locator, offset=0, length=before.size) as stream:
        content = bytearray()
        while True:
            if clock() - started > budgets.max_runtime_seconds:
                raise ContentBudgetExceeded("CONTENT_READ_BLOCKED_BUDGET")
            chunk = stream.read(min(1024 * 1024, budgets.max_file_bytes - len(content) + 1))
            if not chunk:
                break
            content.extend(chunk)
            if len(content) > budgets.max_file_bytes:
                raise ContentBudgetExceeded("CONTENT_READ_BLOCKED_BUDGET")
    after = source.stat(locator)
    if before.size != after.size or before.modified_at != after.modified_at or before.server_file_id != after.server_file_id:
        raise SourceChangedDuringImport("source changed during bounded read")
    if len(content) != before.size:
        raise SourceChangedDuringImport("source read length differed from source stat")
    return bytes(content), before, hashlib.sha256(content).hexdigest()
