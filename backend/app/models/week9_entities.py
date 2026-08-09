"""Week 9 attachment, repeating-grid, and portal-derived evidence entities."""

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, utcnow


def _id() -> str:
    return str(uuid4())


class AttachmentCategoryRule(Base):
    __tablename__ = "attachment_category_rules"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    scenario_id: Mapped[str] = mapped_column(ForeignKey("scenario_configs.id"), nullable=False)
    scenario_version: Mapped[str] = mapped_column(String(40), nullable=False)
    category_code: Mapped[str] = mapped_column(String(120), nullable=False)
    portal_label_en: Mapped[str] = mapped_column(String(240), nullable=False)
    portal_label_ar: Mapped[str | None] = mapped_column(String(240))
    portal_order: Mapped[int] = mapped_column(Integer, nullable=False)
    requirement_state: Mapped[str] = mapped_column(String(40), nullable=False)
    applicability_expression_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    allowed_document_types: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    min_files: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_files: Mapped[int | None] = mapped_column(Integer)
    multiple_files_allowed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    allowed_languages: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    required_language_combination: Mapped[str | None] = mapped_column(String(30))
    allowed_mime_types: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    allowed_extensions: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    max_file_size_bytes: Mapped[int | None] = mapped_column(Integer)
    revision_policy: Mapped[str] = mapped_column(String(50), nullable=False)
    reuse_policy: Mapped[str] = mapped_column(String(60), nullable=False)
    replacement_policy: Mapped[str] = mapped_column(String(60), nullable=False)
    evidence_policy: Mapped[str] = mapped_column(String(60), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    effective_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rule_version: Mapped[str] = mapped_column(String(40), nullable=False)


class AttachmentManifestItem(Base):
    __tablename__ = "attachment_manifest_items"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    attachment_manifest_id: Mapped[str] = mapped_column(ForeignKey("attachment_manifests.id"), nullable=False)
    category_code: Mapped[str] = mapped_column(String(120), nullable=False)
    category_rule_version: Mapped[str] = mapped_column(String(40), nullable=False)
    requirement_state: Mapped[str] = mapped_column(String(40), nullable=False)
    document_id: Mapped[str | None] = mapped_column(ForeignKey("documents.id"))
    document_version_id: Mapped[str | None] = mapped_column(ForeignKey("document_versions.id"))
    file_sha256: Mapped[str | None] = mapped_column(String(64))
    logical_name: Mapped[str | None] = mapped_column(String(240))
    revision_label: Mapped[str | None] = mapped_column(String(80))
    language: Mapped[str | None] = mapped_column(String(30))
    mime_type: Mapped[str | None] = mapped_column(String(100))
    file_size_bytes: Mapped[int | None] = mapped_column(Integer)
    intended_portal_filename: Mapped[str | None] = mapped_column(String(300))
    sequence_in_category: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    reuse_group_id: Mapped[str | None] = mapped_column(String(80))
    source_reason: Mapped[str] = mapped_column(Text, nullable=False)
    validity_state: Mapped[str] = mapped_column(String(50), nullable=False)
    approval_state: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)


class AttachmentAssociationIntent(Base):
    __tablename__ = "attachment_association_intents"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    application_id: Mapped[str] = mapped_column(ForeignKey("permit_applications.id"), nullable=False)
    preparation_revision_id: Mapped[str] = mapped_column(ForeignKey("preparation_revisions.id"), nullable=False)
    attachment_manifest_item_id: Mapped[str | None] = mapped_column(ForeignKey("attachment_manifest_items.id"))
    category_code: Mapped[str] = mapped_column(String(120), nullable=False)
    document_version_id: Mapped[str] = mapped_column(ForeignKey("document_versions.id"), nullable=False)
    operation_type: Mapped[str] = mapped_column(String(40), nullable=False)
    replaces_association_id: Mapped[str | None] = mapped_column(ForeignKey("attachment_association_intents.id"))
    idempotency_key: Mapped[str] = mapped_column(String(300), unique=True, nullable=False)
    intended_portal_filename: Mapped[str] = mapped_column(String(300), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)


class AttachmentPersistenceEvidence(Base):
    __tablename__ = "attachment_persistence_evidence"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    application_id: Mapped[str] = mapped_column(ForeignKey("permit_applications.id"), nullable=False)
    preparation_revision_id: Mapped[str] = mapped_column(ForeignKey("preparation_revisions.id"), nullable=False)
    category_code: Mapped[str] = mapped_column(String(120), nullable=False)
    document_version_id: Mapped[str] = mapped_column(ForeignKey("document_versions.id"), nullable=False)
    expected_filename: Mapped[str] = mapped_column(String(300), nullable=False)
    expected_size: Mapped[int | None] = mapped_column(Integer)
    observed_filename: Mapped[str | None] = mapped_column(String(300))
    observed_size: Mapped[int | None] = mapped_column(Integer)
    observed_category_code: Mapped[str | None] = mapped_column(String(120))
    capture_method: Mapped[str] = mapped_column(String(40), nullable=False)
    pre_save_state_hash: Mapped[str | None] = mapped_column(String(64))
    post_save_state_hash: Mapped[str | None] = mapped_column(String(64))
    reopened_state_hash: Mapped[str | None] = mapped_column(String(64))
    result: Mapped[str] = mapped_column(String(50), nullable=False)
    evidence_artifact_id: Mapped[str | None] = mapped_column(String(300))
    verified_by: Mapped[str | None] = mapped_column(String(200))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AttachmentReconciliationResult(Base):
    __tablename__ = "attachment_reconciliation_results"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    preparation_revision_id: Mapped[str] = mapped_column(ForeignKey("preparation_revisions.id"), nullable=False)
    manifest_item_id: Mapped[str | None] = mapped_column(ForeignKey("attachment_manifest_items.id"))
    category_code: Mapped[str] = mapped_column(String(120), nullable=False)
    document_version_id: Mapped[str | None] = mapped_column(ForeignKey("document_versions.id"))
    expected: Mapped[Any] = mapped_column(JSON)
    observed: Mapped[Any] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[str] = mapped_column(String(30), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_id: Mapped[str | None] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class PortalStructureFingerprint(Base):
    __tablename__ = "portal_structure_fingerprints"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    preparation_revision_id: Mapped[str] = mapped_column(ForeignKey("preparation_revisions.id"), nullable=False)
    scope: Mapped[str] = mapped_column(String(50), nullable=False)
    scenario_id: Mapped[str | None] = mapped_column(ForeignKey("scenario_configs.id"))
    contract_version: Mapped[str] = mapped_column(String(40), nullable=False)
    expected_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    observed_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    expected_structure: Mapped[Any] = mapped_column(JSON)
    observed_structure: Mapped[Any] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class PortalGridRowObservation(Base):
    __tablename__ = "portal_grid_row_observations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    portal_snapshot_id: Mapped[str] = mapped_column(ForeignKey("portal_snapshots.id"), nullable=False)
    grid_code: Mapped[str] = mapped_column(String(100), nullable=False)
    portal_row_id: Mapped[str | None] = mapped_column(String(160))
    observed_sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    observed_values: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    observed_business_key: Mapped[str | None] = mapped_column(String(300))
    row_hash: Mapped[str] = mapped_column(String(64), nullable=False)


class GridReconciliationRun(Base):
    __tablename__ = "grid_reconciliation_runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    preparation_revision_id: Mapped[str] = mapped_column(ForeignKey("preparation_revisions.id"), nullable=False)
    portal_snapshot_id: Mapped[str] = mapped_column(ForeignKey("portal_snapshots.id"), nullable=False)
    grid_code: Mapped[str] = mapped_column(String(100), nullable=False)
    intended_row_count: Mapped[int] = mapped_column(Integer, nullable=False)
    observed_row_count: Mapped[int] = mapped_column(Integer, nullable=False)
    matched_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    missing_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    extra_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    mismatch_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ambiguous_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    result: Mapped[str] = mapped_column(String(40), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class GridRowReconciliationResult(Base):
    __tablename__ = "grid_row_reconciliation_results"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    run_id: Mapped[str] = mapped_column(ForeignKey("grid_reconciliation_runs.id"), nullable=False)
    canonical_row_id: Mapped[str | None] = mapped_column(String(160))
    portal_row_id: Mapped[str | None] = mapped_column(String(160))
    business_key: Mapped[str | None] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    field_diffs: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    severity: Mapped[str] = mapped_column(String(30), nullable=False)
    evidence: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)


class GridFieldDiff(Base):
    __tablename__ = "grid_field_diffs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    row_result_id: Mapped[str] = mapped_column(ForeignKey("grid_row_reconciliation_results.id"), nullable=False)
    field_code: Mapped[str] = mapped_column(String(120), nullable=False)
    expected: Mapped[Any] = mapped_column(JSON)
    observed: Mapped[Any] = mapped_column(JSON)
    normalized_expected: Mapped[Any] = mapped_column(JSON)
    normalized_observed: Mapped[Any] = mapped_column(JSON)
    tolerance_rule_version: Mapped[str | None] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(30), nullable=False)


class GridPersistenceEvidence(Base):
    __tablename__ = "grid_persistence_evidence"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    preparation_revision_id: Mapped[str] = mapped_column(ForeignKey("preparation_revisions.id"), nullable=False)
    grid_code: Mapped[str] = mapped_column(String(100), nullable=False)
    intended_state_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    post_save_snapshot_id: Mapped[str | None] = mapped_column(ForeignKey("portal_snapshots.id"))
    reopened_snapshot_id: Mapped[str | None] = mapped_column(ForeignKey("portal_snapshots.id"))
    result: Mapped[str] = mapped_column(String(50), nullable=False)
    evidence_artifact_id: Mapped[str | None] = mapped_column(String(300))
    verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class PortalDerivedFieldReconciliation(Base):
    __tablename__ = "portal_derived_field_reconciliations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    preparation_revision_id: Mapped[str] = mapped_column(ForeignKey("preparation_revisions.id"), nullable=False)
    portal_field_code: Mapped[str] = mapped_column(String(120), nullable=False)
    semantic_field_code: Mapped[str] = mapped_column(String(120), nullable=False)
    purpose: Mapped[str] = mapped_column(String(100), nullable=False)
    expected_office_value: Mapped[Any] = mapped_column(JSON)
    observed_portal_value: Mapped[Any] = mapped_column(JSON)
    source_mode: Mapped[str] = mapped_column(String(40), nullable=False)
    field_authority_rule_version: Mapped[str | None] = mapped_column(String(40))
    target_rendering_rule_version: Mapped[str | None] = mapped_column(String(40))
    result: Mapped[str] = mapped_column(String(60), nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    evidence: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
