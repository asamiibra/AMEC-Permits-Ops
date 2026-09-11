from __future__ import annotations

from typing import Literal

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
