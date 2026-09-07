"""Persistence seams for the Phase 4 corpus-to-application integration.

These records are lineage and workflow records.  The existing Document,
FieldObservation, VerifiedAssertion, Work, Issue, Notification, and Audit
entities remain authoritative for their respective domains.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, utcnow


def _id() -> str:
    return str(uuid4())


class Phase4SourceChangeEvent(Base):
    __tablename__ = "phase4_source_change_events"
    __table_args__ = (UniqueConstraint("event_id", name="uq_phase4_source_event_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    event_id: Mapped[str] = mapped_column(String(160), nullable=False)
    scan_id_or_observation_group: Mapped[str] = mapped_column(String(160), nullable=False)
    source_surface: Mapped[str] = mapped_column(String(80), nullable=False)
    source_artifact_id_or_locator: Mapped[str] = mapped_column(String(500), nullable=False)
    source_version_id: Mapped[str | None] = mapped_column(String(160))
    source_version_token: Mapped[str] = mapped_column(String(160), nullable=False)
    source_collection_role_if_applicable: Mapped[str | None] = mapped_column(String(120))
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    observed_size: Mapped[int | None] = mapped_column(Integer)
    observed_mtime: Mapped[str | None] = mapped_column(String(80))
    previous_observation_id: Mapped[str | None] = mapped_column(String(160))
    origin: Mapped[str] = mapped_column(String(40), nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(160), nullable=False)
    observed_at: Mapped[str] = mapped_column(String(80), nullable=False)
    stability_state: Mapped[str] = mapped_column(String(40), nullable=False)
    observation_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    stability_window_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    content_identity_proof: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    immutable_payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    record_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[Any] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class Phase4DocumentEvidenceEnvelope(Base):
    __tablename__ = "phase4_document_evidence_envelopes"
    __table_args__ = (UniqueConstraint("evidence_envelope_sha256", name="uq_phase4_evidence_envelope_sha"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    root_event_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    source_artifact_id: Mapped[str] = mapped_column(String(500), nullable=False)
    source_version_id: Mapped[str | None] = mapped_column(String(160))
    source_version_token: Mapped[str] = mapped_column(String(160), nullable=False)
    source_surface: Mapped[str] = mapped_column(String(80), nullable=False)
    evidence_envelope_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    document_intelligence_runtime_version: Mapped[str] = mapped_column(String(100), nullable=False)
    runtime_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    capability_id: Mapped[str] = mapped_column(String(160), nullable=False)
    handler_parser_identity: Mapped[str] = mapped_column(String(200), nullable=False)
    metering_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    warnings_json: Mapped[list[Any]] = mapped_column(JSON, default=list, nullable=False)
    content_retention_class: Mapped[str] = mapped_column(String(80), nullable=False)
    unsupported_capability_state: Mapped[str | None] = mapped_column(String(120))
    evidence_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[Any] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class Phase4ClassificationEnvelope(Base):
    __tablename__ = "phase4_classification_envelopes"
    __table_args__ = (UniqueConstraint("envelope_id", name="uq_phase4_classification_envelope_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    envelope_id: Mapped[str] = mapped_column(String(160), nullable=False)
    root_event_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    document_version_id: Mapped[str | None] = mapped_column(String(36), index=True)
    source_mode: Mapped[str] = mapped_column(String(60), nullable=False)
    classifier_version: Mapped[str] = mapped_column(String(100), nullable=False)
    rules_version: Mapped[str] = mapped_column(String(100), nullable=False)
    taxonomy_revision: Mapped[str] = mapped_column(String(100), nullable=False)
    module_truth_contract_sha: Mapped[str] = mapped_column(String(64), nullable=False)
    corpus_app_contract_sha: Mapped[str] = mapped_column(String(64), nullable=False)
    axes_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    immutable_result_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    record_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="PENDING_REVIEW")
    created_at: Mapped[Any] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class Phase4ReviewDecision(Base):
    __tablename__ = "phase4_review_decisions"
    __table_args__ = (UniqueConstraint("decision_id", name="uq_phase4_review_decision_id"), UniqueConstraint("idempotency_key", name="uq_phase4_review_decision_idempotency"))

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    decision_id: Mapped[str] = mapped_column(String(160), nullable=False)
    classification_envelope_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    decision: Mapped[str] = mapped_column(String(40), nullable=False)
    actor_id: Mapped[str] = mapped_column(String(200), nullable=False)
    capability: Mapped[str] = mapped_column(String(160), nullable=False)
    scope_type: Mapped[str] = mapped_column(String(80), nullable=False)
    scope_id: Mapped[str] = mapped_column(String(160), nullable=False)
    record_version: Mapped[int] = mapped_column(Integer, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)
    corrections_json: Mapped[list[Any]] = mapped_column(JSON, default=list, nullable=False)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[Any] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class Phase4ClassifierCorrectionEvent(Base):
    __tablename__ = "phase4_classifier_correction_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    source_version: Mapped[str] = mapped_column(String(160), nullable=False)
    classification_envelope_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    axis: Mapped[str] = mapped_column(String(80), nullable=False)
    old_value_json: Mapped[Any] = mapped_column(JSON, nullable=True)
    new_value_json: Mapped[Any] = mapped_column(JSON, nullable=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    reviewer: Mapped[str] = mapped_column(String(200), nullable=False)
    evidence_ids_json: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    classifier_version: Mapped[str] = mapped_column(String(100), nullable=False)
    rules_version: Mapped[str] = mapped_column(String(100), nullable=False)
    taxonomy_revision: Mapped[str] = mapped_column(String(100), nullable=False)
    module_truth_contract_sha: Mapped[str] = mapped_column(String(64), nullable=False)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[Any] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class Phase4ProjectionPlan(Base):
    __tablename__ = "phase4_projection_plans"
    __table_args__ = (UniqueConstraint("idempotency_key", name="uq_phase4_projection_plan_idempotency"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    verified_assertion_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    target_domain: Mapped[str] = mapped_column(String(80), nullable=False)
    target_entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    target_entity_id: Mapped[str] = mapped_column(String(160), nullable=False)
    precondition_version: Mapped[str] = mapped_column(String(160), nullable=False)
    plan_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)
    result: Mapped[str] = mapped_column(String(40), nullable=False, default="PLANNED")
    created_at: Mapped[Any] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class Phase4ProjectionReceipt(Base):
    __tablename__ = "phase4_projection_receipts"
    __table_args__ = (UniqueConstraint("projection_id", name="uq_phase4_projection_id"), UniqueConstraint("idempotency_key", name="uq_phase4_projection_idempotency"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    projection_id: Mapped[str] = mapped_column(String(160), nullable=False)
    root_event_id: Mapped[str | None] = mapped_column(String(36), index=True)
    verified_assertion_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    module_truth_contract_sha: Mapped[str] = mapped_column(String(64), nullable=False)
    corpus_app_contract_sha: Mapped[str] = mapped_column(String(64), nullable=False)
    target_domain: Mapped[str] = mapped_column(String(80), nullable=False)
    target_entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    target_entity_id: Mapped[str] = mapped_column(String(160), nullable=False)
    operation: Mapped[str] = mapped_column(String(80), nullable=False)
    precondition_version: Mapped[str] = mapped_column(String(160), nullable=False)
    postcondition_version: Mapped[str] = mapped_column(String(160), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)
    result: Mapped[str] = mapped_column(String(40), nullable=False)
    created_ids_json: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    updated_ids_json: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    work_ids_json: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    issue_ids_json: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    notification_ids_json: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    audit_ids_json: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    failure_or_review_reason: Mapped[str | None] = mapped_column(Text)
    correlation_id: Mapped[str] = mapped_column(String(160), nullable=False)
    created_at: Mapped[Any] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class Phase4VerifiedAssertionBridge(Base):
    __tablename__ = "phase4_verified_assertion_bridges"
    __table_args__ = (UniqueConstraint("bridge_id", name="uq_phase4_bridge_id"), UniqueConstraint("idempotency_key", name="uq_phase4_bridge_idempotency"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    bridge_id: Mapped[str] = mapped_column(String(160), nullable=False)
    classification_envelope_id: Mapped[str] = mapped_column(String(36), nullable=False)
    review_decision_id: Mapped[str] = mapped_column(String(36), nullable=False)
    verified_assertion_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    strategy: Mapped[str] = mapped_column(String(80), nullable=False)
    lineage_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[Any] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
