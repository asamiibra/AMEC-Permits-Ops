from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ClassifierV2Model(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


L0SourceMode = Literal[
    "EXISTING_KNOWN_SOURCE",
    "NEW_UNKNOWN_SOURCE",
    "MODIFIED_KNOWN_SOURCE",
    "MOVE_RENAME_CANDIDATE",
]


class ClassifierV2Request(ClassifierV2Model):
    fixture_id: str = Field(min_length=1, max_length=160)
    source_artifact_id: str = Field(min_length=1, max_length=500)
    source_version_token: str = Field(min_length=1, max_length=160)
    source_mode: L0SourceMode
    scope_type: str = Field(min_length=1, max_length=80)
    scope_id: str = Field(min_length=1, max_length=160)
    correlation_id: str = Field(min_length=1, max_length=160)
    evidence_ids: list[str] = Field(default_factory=list, min_length=1, max_length=32)
    document_type_hint: str | None = Field(default=None, max_length=120)
    discipline_hint: str | None = Field(default=None, max_length=120)
    candidate_entity_id: str | None = Field(default=None, max_length=160)
    previous_source_version_token: str | None = Field(default=None, max_length=160)
    contradiction_families: list[str] = Field(default_factory=list, max_length=16)
    out_of_scope: bool = False
    secret_exclude: bool = False
    missing_candidate: bool = False


class DocumentEvidenceEnvelope(ClassifierV2Model):
    """Phase5 naming layer over the immutable Phase4 evidence contract."""

    root_event_id: str
    source_artifact_id: str
    source_version_token: str
    source_surface: str
    evidence_envelope_sha256: str
    document_intelligence_runtime_version: str = "deterministic-parser-v1"
    runtime_sha256: str
    capability_id: str
    handler_parser_identity: str
    metering_json: dict[str, Any] = Field(default_factory=dict)
    warnings_json: list[Any] = Field(default_factory=list)
    content_retention_class: str = "METADATA_ONLY"
    unsupported_capability_state: str | None = None
    evidence_json: dict[str, Any] = Field(default_factory=dict)


class Phase5ReviewDecisionIn(ClassifierV2Model):
    decision_id: str = Field(min_length=1, max_length=160)
    classification_envelope_id: str = Field(min_length=1, max_length=36)
    decision: Literal["ACCEPT", "CORRECT", "DEFER", "MARK_OUT_OF_SCOPE", "RESOLVE_RELATIONSHIP"]
    actor_id: str = Field(min_length=1, max_length=200)
    capability: str = Field(min_length=1, max_length=160)
    scope_type: str = Field(min_length=1, max_length=80)
    scope_id: str = Field(min_length=1, max_length=160)
    record_version: int = Field(default=1, ge=1)
    idempotency_key: str = Field(min_length=1, max_length=200)
    corrections_json: list[dict[str, Any]] = Field(default_factory=list)


class Phase5PromotionIn(ClassifierV2Model):
    review_decision_id: str = Field(min_length=1, max_length=36)
    verified_assertion_id: str = Field(min_length=1, max_length=36)
    idempotency_key: str = Field(min_length=1, max_length=200)


class Phase5ProjectionIn(ClassifierV2Model):
    projection_id: str = Field(min_length=1, max_length=160)
    verified_assertion_id: str = Field(min_length=1, max_length=36)
    target_domain: str = Field(min_length=1, max_length=80)
    target_entity_type: str = Field(min_length=1, max_length=100)
    target_entity_id: str = Field(min_length=1, max_length=160)
    operation: str = Field(min_length=1, max_length=80)
    precondition_version: str = Field(min_length=1, max_length=160)
    idempotency_key: str = Field(min_length=1, max_length=200)
    root_event_id: str | None = Field(default=None, max_length=36)
    correlation_id: str = Field(min_length=1, max_length=160)
    plan_json: dict[str, Any] = Field(default_factory=dict)
