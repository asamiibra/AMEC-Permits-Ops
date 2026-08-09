"""Week 4–5 package and assisted-municipality workflow entities.

These records deliberately keep canonical truth, target rendering, operator
intent, and observed simulator state separate. They are synthetic-fixture
capabilities only; no submission operation is represented here.
"""

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, utcnow


def _id() -> str:
    return str(uuid4())


class ApplicableRuleSet(Base):
    __tablename__ = "applicable_rule_sets"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    preparation_revision_id: Mapped[str | None] = mapped_column(String(36))
    scenario_version: Mapped[str] = mapped_column(String(40), nullable=False)
    requirement_config_version: Mapped[str] = mapped_column(String(40), nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    evaluated_by_system_version: Mapped[str] = mapped_column(String(80), nullable=False)
    input_snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    result_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    configuration_bundle_id: Mapped[str | None] = mapped_column(ForeignKey("configuration_bundles.id"))
    configuration_checksum: Mapped[str | None] = mapped_column(String(64))


class ProfessionalCredential(Base):
    __tablename__ = "professional_credentials"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    credential_type: Mapped[str] = mapped_column(String(100), nullable=False)
    holder: Mapped[str] = mapped_column(String(200), nullable=False)
    registration_number: Mapped[str] = mapped_column(String(120), nullable=False)
    authority: Mapped[str] = mapped_column(String(200), nullable=False)
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    evidence_document_version_id: Mapped[str | None] = mapped_column(ForeignKey("document_versions.id"))


class OfficeCredential(Base):
    __tablename__ = "office_credentials"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    office_id: Mapped[str] = mapped_column(ForeignKey("consultancy_offices.id"), nullable=False)
    credential_type: Mapped[str] = mapped_column(String(100), nullable=False)
    holder: Mapped[str] = mapped_column(String(200), nullable=False)
    registration_number: Mapped[str] = mapped_column(String(120), nullable=False)
    authority: Mapped[str] = mapped_column(String(200), nullable=False)
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    evidence_document_version_id: Mapped[str | None] = mapped_column(ForeignKey("document_versions.id"))


class MinimumPackageDefinition(Base):
    __tablename__ = "minimum_package_definitions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    scenario_id: Mapped[str] = mapped_column(ForeignKey("scenario_configs.id"), nullable=False)
    version: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    required_field_codes: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    required_document_rules: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    required_attachment_rules: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    required_dependency_rules: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    required_drawing_controls: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    required_human_gates: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    unresolved_conflict_policy: Mapped[str] = mapped_column(String(120), nullable=False)
    package_approver_role: Mapped[str] = mapped_column(String(100), nullable=False)
    notes: Mapped[str] = mapped_column(Text, nullable=False)


class PackageReadinessEvaluation(Base):
    __tablename__ = "package_readiness_evaluations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    preparation_revision_id: Mapped[str | None] = mapped_column(String(36))
    minimum_package_definition_version: Mapped[str] = mapped_column(String(40), nullable=False)
    applicable_rule_set_id: Mapped[str] = mapped_column(ForeignKey("applicable_rule_sets.id"), nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    overall_status: Mapped[str] = mapped_column(String(50), nullable=False)
    blocker_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    warning_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    result_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    configuration_bundle_id: Mapped[str | None] = mapped_column(ForeignKey("configuration_bundles.id"))


class ReadinessResultItem(Base):
    __tablename__ = "readiness_result_items"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    evaluation_id: Mapped[str] = mapped_column(ForeignKey("package_readiness_evaluations.id"), nullable=False)
    requirement_code: Mapped[str] = mapped_column(String(120), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    severity: Mapped[str] = mapped_column(String(30), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_refs: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    related_entity_refs: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)


class Package(Base):
    __tablename__ = "packages"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    preparation_revision_id: Mapped[str | None] = mapped_column(String(36))
    package_definition_version: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_by: Mapped[str | None] = mapped_column(String(200))
    manifest_hash: Mapped[str | None] = mapped_column(String(64))
    source_truth_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    configuration_bundle_id: Mapped[str | None] = mapped_column(ForeignKey("configuration_bundles.id"))


class PackageItem(Base):
    __tablename__ = "package_items"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    package_id: Mapped[str] = mapped_column(ForeignKey("packages.id"), nullable=False)
    document_version_id: Mapped[str] = mapped_column(ForeignKey("document_versions.id"), nullable=False)
    document_type: Mapped[str] = mapped_column(String(100), nullable=False)
    attachment_category_code: Mapped[str] = mapped_column(String(120), nullable=False)
    file_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    revision: Mapped[str | None] = mapped_column(String(80))
    approval_state: Mapped[str] = mapped_column(String(40), nullable=False)
    validity_state: Mapped[str] = mapped_column(String(40), nullable=False)
    source_reason: Mapped[str] = mapped_column(Text, nullable=False)
    order: Mapped[int] = mapped_column(Integer, nullable=False)


class AttachmentManifest(Base):
    __tablename__ = "attachment_manifests"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    package_id: Mapped[str] = mapped_column(ForeignKey("packages.id"), unique=True, nullable=False)
    scenario_version: Mapped[str] = mapped_column(String(40), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    items: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    manifest_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    preparation_revision_id: Mapped[str | None] = mapped_column(String(36))
    scenario_id: Mapped[str | None] = mapped_column(String(36))
    manifest_version: Mapped[str] = mapped_column(String(40), default="WEEK4-BASE-1.0", nullable=False)
    generated_by: Mapped[str] = mapped_column(String(200), default="permitops-system", nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="DRAFT", nullable=False)


class FormTemplate(Base):
    __tablename__ = "form_templates"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    template_code: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)


class FormTemplateVersion(Base):
    __tablename__ = "form_template_versions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    template_id: Mapped[str] = mapped_column(ForeignKey("form_templates.id"), nullable=False)
    version: Mapped[str] = mapped_column(String(40), nullable=False)
    source_field_mapping_version: Mapped[str] = mapped_column(String(40), nullable=False)
    mapping_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)


class RenderedForm(Base):
    __tablename__ = "rendered_forms"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    package_id: Mapped[str | None] = mapped_column(ForeignKey("packages.id"))
    template_version_id: Mapped[str] = mapped_column(ForeignKey("form_template_versions.id"), nullable=False)
    rendering_rule_versions: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    input_truth_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    output_file_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    rendered_values: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    review_state: Mapped[str] = mapped_column(String(40), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    configuration_bundle_id: Mapped[str | None] = mapped_column(ForeignKey("configuration_bundles.id"))


class ExcelProjection(Base):
    __tablename__ = "excel_projections"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    workbook_ref: Mapped[str] = mapped_column(String(300), nullable=False)
    sheet: Mapped[str] = mapped_column(String(120), nullable=False)
    row_key: Mapped[str] = mapped_column(String(150), nullable=False)
    target_column: Mapped[str] = mapped_column(String(120), nullable=False)
    ownership: Mapped[str] = mapped_column(String(40), nullable=False)
    rendered_value: Mapped[str | None] = mapped_column(Text)
    source_verified_assertion_id: Mapped[str | None] = mapped_column(ForeignKey("verified_assertions.id"))
    rendering_rule_version: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    configuration_bundle_id: Mapped[str | None] = mapped_column(ForeignKey("configuration_bundles.id"))
    target_rendering_rule_id: Mapped[str | None] = mapped_column(ForeignKey("target_rendering_rules.id"))


class Approval(Base):
    __tablename__ = "approvals"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    approval_type: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False)
    preparation_revision_id: Mapped[str | None] = mapped_column(String(36))
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    decided_by: Mapped[str] = mapped_column(String(200), nullable=False)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    role_at_decision: Mapped[str] = mapped_column(String(100), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    evidence_refs: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)


class PreparationRevision(Base):
    __tablename__ = "preparation_revisions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    application_id: Mapped[str] = mapped_column(ForeignKey("permit_applications.id"), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    scenario_version: Mapped[str] = mapped_column(String(40), nullable=False)
    field_authority_version: Mapped[str] = mapped_column(String(40), nullable=False)
    requirement_config_version: Mapped[str] = mapped_column(String(40), nullable=False)
    rendering_config_version: Mapped[str] = mapped_column(String(40), nullable=False)
    package_id: Mapped[str | None] = mapped_column(ForeignKey("packages.id"))
    package_manifest_hash: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)
    configuration_bundle_id: Mapped[str | None] = mapped_column(ForeignKey("configuration_bundles.id"))


class PreparationSnapshot(Base):
    __tablename__ = "preparation_snapshots"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    preparation_revision_id: Mapped[str] = mapped_column(ForeignKey("preparation_revisions.id"), unique=True, nullable=False)
    verified_field_values: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    rendered_target_values: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    repeating_rows: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    attachment_manifest: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    dependency_state: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    human_gate_state: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False)


class PortalGridRowIntent(Base):
    __tablename__ = "portal_grid_row_intents"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    preparation_revision_id: Mapped[str] = mapped_column(ForeignKey("preparation_revisions.id"), nullable=False)
    row_type: Mapped[str] = mapped_column(String(50), nullable=False)
    canonical_row_id: Mapped[str] = mapped_column(String(120), nullable=False)
    target_values: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    rendering_rule_versions: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    grid_code: Mapped[str] = mapped_column(String(100), default="BUILDING_FLOOR_UNIT", nullable=False)
    parent_canonical_row_id: Mapped[str | None] = mapped_column(String(160))
    business_key: Mapped[str | None] = mapped_column(String(300))
    source_entity_version: Mapped[str | None] = mapped_column(String(160))
    intended_sequence: Mapped[int | None] = mapped_column(Integer)
    row_hash: Mapped[str | None] = mapped_column(String(64))


class PortalIntendedState(Base):
    __tablename__ = "portal_intended_states"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    preparation_revision_id: Mapped[str] = mapped_column(ForeignKey("preparation_revisions.id"), unique=True, nullable=False)
    application_identity: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    fields: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    repeating_rows: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    attachments: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    state_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    configuration_bundle_id: Mapped[str | None] = mapped_column(ForeignKey("configuration_bundles.id"))


class PortalSnapshot(Base):
    __tablename__ = "portal_snapshots"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    application_id: Mapped[str] = mapped_column(ForeignKey("permit_applications.id"), nullable=False)
    preparation_revision_id: Mapped[str] = mapped_column(ForeignKey("preparation_revisions.id"), nullable=False)
    snapshot_type: Mapped[str] = mapped_column(String(40), nullable=False)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    capture_method: Mapped[str] = mapped_column(String(40), nullable=False)
    field_state: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    grid_state: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    attachment_state: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    validation_state: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    precheck_state: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False)


class PortalReconciliationResult(Base):
    __tablename__ = "portal_reconciliation_results"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    preparation_revision_id: Mapped[str] = mapped_column(ForeignKey("preparation_revisions.id"), nullable=False)
    identity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    identity_key: Mapped[str] = mapped_column(String(150), nullable=False)
    expected: Mapped[Any] = mapped_column(JSON)
    observed: Mapped[Any] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    severity: Mapped[str] = mapped_column(String(30), nullable=False)
    evidence: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)


class HumanPortalVerification(Base):
    __tablename__ = "human_portal_verifications"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    application_id: Mapped[str] = mapped_column(ForeignKey("permit_applications.id"), nullable=False)
    preparation_revision_id: Mapped[str] = mapped_column(ForeignKey("preparation_revisions.id"), nullable=False)
    verifier: Mapped[str] = mapped_column(String(200), nullable=False)
    verifier_role: Mapped[str] = mapped_column(String(100), nullable=False)
    verification_scope: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    evidence_artifact_id: Mapped[str] = mapped_column(String(300), nullable=False)
    result: Mapped[str] = mapped_column(String(40), nullable=False)
    verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class AuthorityPrecheckRun(Base):
    __tablename__ = "authority_precheck_runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    application_id: Mapped[str] = mapped_column(ForeignKey("permit_applications.id"), nullable=False)
    preparation_revision_id: Mapped[str] = mapped_column(ForeignKey("preparation_revisions.id"), nullable=False)
    run_reference: Mapped[str] = mapped_column(String(150), nullable=False)
    run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    raw_evidence_artifact_id: Mapped[str | None] = mapped_column(String(300))
    result_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    configuration_bundle_id: Mapped[str | None] = mapped_column(ForeignKey("configuration_bundles.id"))
    clearance_result: Mapped[str | None] = mapped_column(String(60))
    invalidated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    invalidated_reason: Mapped[str | None] = mapped_column(Text)


class AuthorityPrecheckItem(Base):
    __tablename__ = "authority_precheck_items"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    precheck_run_id: Mapped[str] = mapped_column(ForeignKey("authority_precheck_runs.id"), nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    code: Mapped[str] = mapped_column(String(100), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)


class AttendedSession(Base):
    __tablename__ = "attended_sessions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    application_id: Mapped[str] = mapped_column(ForeignKey("permit_applications.id"), nullable=False)
    preparation_revision_id: Mapped[str] = mapped_column(ForeignKey("preparation_revisions.id"), nullable=False)
    mfa_mode: Mapped[str] = mapped_column(String(50), nullable=False)
    session_started: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    attendance_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    human_attendance_confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    session_established: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    session_expired: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class SubmissionHandoff(Base):
    __tablename__ = "submission_handoffs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    application_id: Mapped[str] = mapped_column(ForeignKey("permit_applications.id"), nullable=False)
    preparation_revision_id: Mapped[str] = mapped_column(ForeignKey("preparation_revisions.id"), nullable=False)
    package_id: Mapped[str] = mapped_column(ForeignKey("packages.id"), nullable=False)
    portal_snapshot_id: Mapped[str | None] = mapped_column(ForeignKey("portal_snapshots.id"))
    handoff_status: Mapped[str] = mapped_column(String(50), nullable=False)
    final_submitter_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    prepared_by: Mapped[str] = mapped_column(String(200), nullable=False)
    prepared_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    from_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    from_role: Mapped[str | None] = mapped_column(String(80))
    final_submitter_role: Mapped[str | None] = mapped_column(String(80))
    handoff_state: Mapped[str | None] = mapped_column(String(50))
    checklist_hash: Mapped[str | None] = mapped_column(String(64))
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    correlation_id: Mapped[str | None] = mapped_column(String(100))
    readiness_summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    unresolved_nonblocking_items: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    evidence_refs: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)


class MunicipalityPreparationException(Base):
    __tablename__ = "municipality_preparation_exceptions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    application_id: Mapped[str] = mapped_column(ForeignKey("permit_applications.id"), nullable=False)
    preparation_revision_id: Mapped[str] = mapped_column(ForeignKey("preparation_revisions.id"), nullable=False)
    exception_type: Mapped[str] = mapped_column(String(80), nullable=False)
    severity: Mapped[str] = mapped_column(String(30), nullable=False)
    expected: Mapped[Any] = mapped_column(JSON)
    observed: Mapped[Any] = mapped_column(JSON)
    evidence: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    owner: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)


class OperatorExerciseEvidence(Base):
    __tablename__ = "operator_exercise_evidence"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    case_id: Mapped[str] = mapped_column(String(100), nullable=False)
    user_role: Mapped[str] = mapped_column(String(100), nullable=False)
    preparation_revision_id: Mapped[str] = mapped_column(ForeignKey("preparation_revisions.id"), nullable=False)
    fields_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    grid_rows_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    attachments_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    manual_corrections: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    portal_mismatches: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    time_to_prepare_seconds: Mapped[float | None] = mapped_column(Float)
    time_to_verify_seconds: Mapped[float | None] = mapped_column(Float)
    exceptions: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    friction_note: Mapped[str | None] = mapped_column(Text)
