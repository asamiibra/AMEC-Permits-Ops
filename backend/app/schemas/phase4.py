from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Phase4Model(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class SourceChangeEventIn(Phase4Model):
    event_id: str
    scan_id_or_observation_group: str
    source_surface: str
    source_artifact_id_or_locator: str
    source_version_id: str | None = None
    source_version_token: str
    source_collection_role_if_applicable: str | None = None
    event_type: str
    observed_size: int | None = Field(default=None, ge=0)
    observed_mtime: str | None = None
    previous_observation_id: str | None = None
    origin: str = "CONTROLLED_SYNTHETIC"
    correlation_id: str
    observed_at: str
    stability_state: str = "STABLE"
    observation_count: int = Field(default=1, ge=1)
    stability_window_seconds: int = Field(default=0, ge=0)
    content_identity_proof: dict[str, Any] = Field(default_factory=dict)


class EvidenceEnvelopeIn(Phase4Model):
    root_event_id: str
    source_artifact_id: str
    source_version_id: str | None = None
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


class ClassificationEnvelopeIn(Phase4Model):
    envelope_id: str
    root_event_id: str
    document_version_id: str | None = None
    source_mode: str
    classifier_version: str = "rules-only-v1"
    rules_version: str = "phase4-rules-v1"
    taxonomy_revision: str = "phase3c-taxonomy-v6c"
    module_truth_contract_sha: str
    corpus_app_contract_sha: str
    axes_json: dict[str, Any]


class ReviewDecisionIn(Phase4Model):
    decision_id: str
    classification_envelope_id: str
    decision: str
    actor_id: str
    capability: str
    scope_type: str
    scope_id: str
    record_version: int = Field(default=1, ge=1)
    idempotency_key: str
    corrections_json: list[dict[str, Any]] = Field(default_factory=list)


class PromotionIn(Phase4Model):
    review_decision_id: str
    verified_assertion_id: str
    idempotency_key: str


class ProjectionRequest(Phase4Model):
    projection_id: str
    verified_assertion_id: str
    target_domain: str
    target_entity_type: str
    target_entity_id: str
    operation: str
    precondition_version: str
    idempotency_key: str
    root_event_id: str | None = None
    correlation_id: str
    plan_json: dict[str, Any] = Field(default_factory=dict)


class ReviewQueueFilter(Phase4Model):
    scope_type: str | None = None
    scope_id: str | None = None
