"""External/source-root read helpers with mutation detection."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from .port import BinaryStorePort, StorageLocator
from .fixture_exclusion import ensure_fixture_path_allowed


class SourceChangedDuringImport(RuntimeError):
    code = "SOURCE_CHANGED_DURING_IMPORT"


@dataclass(frozen=True)
class StableSourceRead:
    content: bytes
    size: int
    sha256: str
    before_modified_at: str | None
    after_modified_at: str | None


def read_stable_source(store: BinaryStorePort, locator: StorageLocator) -> StableSourceRead:
    ensure_fixture_path_allowed(locator.relative_path)
    before = store.stat(locator)
    with store.open_read(locator) as stream:
        content = stream.read()
    after = store.stat(locator)
    if before.size != after.size or before.modified_at != after.modified_at:
        raise SourceChangedDuringImport("external source changed during SMB read")
    return StableSourceRead(content, len(content), hashlib.sha256(content).hexdigest(), before.modified_at, after.modified_at)
