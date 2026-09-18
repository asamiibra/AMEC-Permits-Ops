from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class BridgePackageIn(BaseModel):
    """Signed, bounded package submitted by the dedicated source bridge."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    attempt_id: str = Field(min_length=8, max_length=160)
    source_identity: str = Field(min_length=1, max_length=160)
    source_path_snapshot: str = Field(min_length=1, max_length=700)
    size_bytes: int = Field(ge=0, le=10_485_760)
    mtime_utc: str = Field(min_length=1, max_length=80)
    payload_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    payload_b64: str = Field(min_length=1, max_length=14_000_000)
    signature_b64: str = Field(min_length=1, max_length=512)
    source_version_token: str = Field(min_length=1, max_length=160)
    correlation_id: str = Field(min_length=1, max_length=160)
    source_mode: Literal[
        "EXISTING_KNOWN_SOURCE",
        "NEW_UNKNOWN_SOURCE",
        "MODIFIED_KNOWN_SOURCE",
        "MOVE_RENAME_CANDIDATE",
    ] = "NEW_UNKNOWN_SOURCE"
    scope_type: Literal["PROJECT", "ENTITY", "AMEC"] = "PROJECT"
    scope_id: str = Field(min_length=1, max_length=160)
    project_id: str = Field(min_length=1, max_length=36)
    field_definition_id: str = Field(min_length=1, max_length=36)
    field_raw_value: str = Field(min_length=1, max_length=4000)
    source_filename: str = Field(default="synthetic-bridge-fixture.bin", min_length=1, max_length=300)
    mime_type: str = Field(default="application/octet-stream", min_length=1, max_length=120)
    # Optional scan binding.  Package signatures cover these fields so a
    # receiver can distinguish a complete enumeration from received payloads.
    scan_id: str | None = Field(default=None, max_length=160)
    scan_status: Literal["IN_PROGRESS", "COMPLETED", "INCOMPLETE", "FAILED"] | None = None
    scan_source_root: str | None = Field(default=None, max_length=700)
    scan_project_identity: str | None = Field(default=None, max_length=200)
    scan_entry_type: Literal["FILE", "DIRECTORY"] = "FILE"
    scan_entry_size_bytes: int | None = Field(default=None, ge=0)
    scan_entry_mtime_token: str | None = Field(default=None, max_length=160)
    scan_capture_status: str | None = Field(default=None, max_length=40)
    scan_failure_reason: str | None = Field(default=None, max_length=500)
    scan_manifest_hash: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    scan_counts: dict[str, int] = Field(default_factory=dict)


class BridgeScanEntryIn(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    relative_path: str = Field(min_length=1, max_length=700)
    entry_type: Literal["FILE", "DIRECTORY"]
    size_bytes: int = Field(default=0, ge=0)
    mtime_token: str | None = Field(default=None, max_length=160)
    sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    capture_status: str = Field(default="PENDING", max_length=40)
    failure_reason: str | None = Field(default=None, max_length=500)
    source_version_token: str | None = Field(default=None, max_length=160)


class BridgeScanIn(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    scan_id: str = Field(min_length=8, max_length=160)
    source_identity: str = Field(min_length=1, max_length=160)
    source_root: str = Field(min_length=1, max_length=700)
    source_project_identity: str = Field(min_length=1, max_length=200)
    project_number: str = Field(min_length=1, max_length=50)
    status: Literal["COMPLETED", "INCOMPLETE", "FAILED"]
    started_at: str = Field(min_length=1, max_length=80)
    completed_at: str | None = Field(default=None, max_length=80)
    entries: list[BridgeScanEntryIn] = Field(default_factory=list, max_length=100000)
    counts: dict[str, int] = Field(default_factory=dict)
    manifest_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    signature_b64: str = Field(min_length=1, max_length=512)
