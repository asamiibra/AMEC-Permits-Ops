"""Fail-closed path policy for synthetic certification fixtures.

The policy is component-based rather than filename-based so future files,
versions, and stream canaries remain outside business ingestion.
"""

from __future__ import annotations

from collections.abc import Iterable


_INVENTORY_COMPONENT = "proposalops-inventory"
_CERTIFICATION_ROOT = ("proposalops_certification", "phase3b_0_4")


class FixturePathExcludedError(ValueError):
    """Raised before a controlled synthetic fixture can reach business I/O."""

    code = "SOURCE_EXCLUDED_SYNTHETIC_FIXTURE_OR_INVENTORY"


def normalized_source_path(value: str | None) -> tuple[str, ...]:
    """Normalize supported POSIX/SMB path representations to components."""

    if not value or not isinstance(value, str):
        return ()
    normalized = value.replace("\\", "/").strip("/")
    return tuple(part.casefold() for part in normalized.split("/") if part not in {"", "."})


def is_fixture_excluded_path(value: str | None) -> bool:
    """Return true for controlled inventory or certification-root paths."""

    parts = normalized_source_path(value)
    if _INVENTORY_COMPONENT in parts:
        return True
    return any(parts[index : index + len(_CERTIFICATION_ROOT)] == _CERTIFICATION_ROOT for index in range(len(parts)))


def ensure_fixture_path_allowed(value: str | None) -> None:
    """Fail closed at a canonical storage/path boundary."""

    if is_fixture_excluded_path(value):
        raise FixturePathExcludedError(FixturePathExcludedError.code)


def filter_fixture_excluded_paths(values: Iterable[str]) -> tuple[list[str], list[str]]:
    """Split source paths deterministically into eligible and excluded lists."""

    eligible: list[str] = []
    excluded: list[str] = []
    for value in values:
        (excluded if is_fixture_excluded_path(value) else eligible).append(value)
    return eligible, excluded
