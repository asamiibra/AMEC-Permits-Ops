from datetime import date, datetime
from enum import Enum
from typing import Any
from uuid import uuid4
from sqlalchemy import JSON, Boolean, Date, DateTime, Enum as SAEnum, ForeignKey, Integer, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, utcnow


def enum_col(enum_type): return SAEnum(enum_type)


class DocumentType(str, Enum):
    TITLE_DEED = "TITLE_DEED"; OWNER_QID = "OWNER_QID"; COMMERCIAL_REGISTRATION = "COMMERCIAL_REGISTRATION"; AUTHORIZATION = "AUTHORIZATION"; SURVEY_PLAN = "SURVEY_PLAN"; COORDINATE_REPORT = "COORDINATE_REPORT"; DRAWING_SET = "DRAWING_SET"; NOC = "NOC"; APPLICATION_FORM = "APPLICATION_FORM"; OTHER = "OTHER"
class DocumentApprovalState(str, Enum): WORKING = "WORKING"; REVIEWED = "REVIEWED"; APPROVED = "APPROVED"; SUPERSEDED = "SUPERSEDED"; SUBMITTED = "SUBMITTED"
class ClassificationReviewStatus(str, Enum): PENDING = "PENDING"; AUTO_ACCEPTED_LOW_RISK = "AUTO_ACCEPTED_LOW_RISK"; HUMAN_CONFIRMED = "HUMAN_CONFIRMED"; HUMAN_CORRECTED = "HUMAN_CORRECTED"
class Criticality(str, Enum): CRITICAL = "CRITICAL"; MAJOR = "MAJOR"; NORMAL = "NORMAL"; ADVISORY = "ADVISORY"
class DataType(str, Enum): STRING = "STRING"; IDENTIFIER = "IDENTIFIER"; NUMBER = "NUMBER"; DATE = "DATE"; BOOLEAN = "BOOLEAN"; CODE = "CODE"
class ExtractionMethod(str, Enum): RULE = "RULE"; OCR_RULE = "OCR_RULE"; MODEL = "MODEL"; MANUAL_KEYED = "MANUAL_KEYED"; IMPORT = "IMPORT"
class AssertionStatus(str, Enum): CURRENT = "CURRENT"; SUPERSEDED = "SUPERSEDED"; STALE = "STALE"; REJECTED = "REJECTED"
class VerificationMethod(str, Enum): SOURCE_CONFIRMED = "SOURCE_CONFIRMED"; CROSS_SOURCE_MATCH = "CROSS_SOURCE_MATCH"; HUMAN_VERIFIED = "HUMAN_VERIFIED"; MANUAL_KEYED_VERIFIED = "MANUAL_KEYED_VERIFIED"; OTHER = "OTHER"
class ConflictSeverity(str, Enum): CRITICAL = "CRITICAL"; MAJOR = "MAJOR"; MINOR = "MINOR"; ADVISORY = "ADVISORY"
class ConflictStatus(str, Enum): OPEN = "OPEN"; RESOLVED = "RESOLVED"; ACCEPTED = "ACCEPTED"; BLOCKED = "BLOCKED"
class ConfigStatus(str, Enum): PROVISIONAL = "PROVISIONAL"; CONFIRMED = "CONFIRMED"; NEEDS_DECISION = "NEEDS_DECISION"
class RequirementType(str, Enum): DOCUMENT = "DOCUMENT"; FIELD = "FIELD"; DEPENDENCY = "DEPENDENCY"; ATTACHMENT = "ATTACHMENT"; PORTAL_SECTION = "PORTAL_SECTION"; HUMAN_DECISION = "HUMAN_DECISION"
class InteractionMode(str, Enum): ASSISTED = "ASSISTED"; API_CANDIDATE = "API_CANDIDATE"; BROWSER_CANDIDATE = "BROWSER_CANDIDATE"; MOCK = "MOCK"; NOT_SUPPORTED = "NOT_SUPPORTED"
class AuthorizationStatus(str, Enum): UNKNOWN = "UNKNOWN"; CONFIRMED = "CONFIRMED"; PROHIBITED = "PROHIBITED"
class DatasetType(str, Enum): SYNTHETIC = "SYNTHETIC"; APPROVED_REAL_TEST = "APPROVED_REAL_TEST"
class EvidenceUsability(str, Enum): GOOD = "GOOD"; USABLE = "USABLE"; POOR = "POOR"; MISSING = "MISSING"


class ScenarioConfig(Base):
    __tablename__ = "scenario_configs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    scenario_code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    version: Mapped[str] = mapped_column(String(30), nullable=False)
    office_workstream: Mapped[str] = mapped_column(String(200), nullable=False)
    municipality: Mapped[str] = mapped_column(String(100), nullable=False)
    permit_type: Mapped[str] = mapped_column(String(100), nullable=False)
    application_transaction_type: Mapped[str] = mapped_column(String(100), nullable=False)
    supported_owner_variants: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    supported_languages: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    supported_complexity_notes: Mapped[str] = mapped_column(Text, nullable=False)
    interaction_mode: Mapped[InteractionMode] = mapped_column(enum_col(InteractionMode), nullable=False)
    status: Mapped[ConfigStatus] = mapped_column(enum_col(ConfigStatus), nullable=False)


class Document(Base):
    __tablename__ = "documents"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    # Project scope is optional for AMEC-level master/reference content. Existing
    # project evidence continues to populate this field.
    project_id: Mapped[str | None] = mapped_column(ForeignKey("projects.id"), nullable=True, index=True)
    document_type: Mapped[DocumentType] = mapped_column(enum_col(DocumentType), nullable=False)
    logical_name: Mapped[str] = mapped_column(String(240), nullable=False)
    language: Mapped[str] = mapped_column(String(30), nullable=False)
    source_system: Mapped[str] = mapped_column(String(100), nullable=False)
    current_version_id: Mapped[str | None] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)
    versions: Mapped[list["DocumentVersion"]] = relationship(back_populates="document", foreign_keys="DocumentVersion.document_id", cascade="all, delete-orphan")


class DocumentVersion(Base):
    __tablename__ = "document_versions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), nullable=False, index=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    source_filename: Mapped[str] = mapped_column(String(300), nullable=False)
    source_path_or_reference: Mapped[str] = mapped_column(String(500), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    language: Mapped[str] = mapped_column(String(30), nullable=False)
    revision_label: Mapped[str | None] = mapped_column(String(50))
    document_date: Mapped[date | None] = mapped_column(Date)
    valid_from: Mapped[date | None] = mapped_column(Date)
    valid_until: Mapped[date | None] = mapped_column(Date)
    approval_state: Mapped[DocumentApprovalState] = mapped_column(enum_col(DocumentApprovalState), nullable=False)
    source_system: Mapped[str] = mapped_column(String(100), nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    superseded_by: Mapped[str | None] = mapped_column(String(36))
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    rendition_status: Mapped[str] = mapped_column(String(40), nullable=False, default="RENDITION_NOT_AVAILABLE")
    rendition_path_or_reference: Mapped[str | None] = mapped_column(String(500))
    rendition_sha256: Mapped[str | None] = mapped_column(String(64))
    rendition_mime_type: Mapped[str | None] = mapped_column(String(100))
    rendition_file_size: Mapped[int | None] = mapped_column(Integer)
    document: Mapped[Document] = relationship(back_populates="versions", foreign_keys=[document_id])
    classifications: Mapped[list["DocumentClassification"]] = relationship(back_populates="document_version", cascade="all, delete-orphan")
    observations: Mapped[list["FieldObservation"]] = relationship(back_populates="document_version", cascade="all, delete-orphan")


class DocumentClassification(Base):
    __tablename__ = "document_classifications"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    document_version_id: Mapped[str] = mapped_column(ForeignKey("document_versions.id"), nullable=False)
    predicted_type: Mapped[str] = mapped_column(String(100), nullable=False)
    classification_method: Mapped[str] = mapped_column(String(100), nullable=False)
    model_or_rule_version: Mapped[str] = mapped_column(String(100), nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float)
    final_type: Mapped[str | None] = mapped_column(String(100))
    review_status: Mapped[ClassificationReviewStatus] = mapped_column(enum_col(ClassificationReviewStatus), nullable=False)
    reviewed_by: Mapped[str | None] = mapped_column(String(36))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    evidence_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    document_version: Mapped[DocumentVersion] = relationship(back_populates="classifications")


class FieldDefinition(Base):
    __tablename__ = "field_definitions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    field_code: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    name_en: Mapped[str] = mapped_column(String(200), nullable=False)
    name_ar: Mapped[str | None] = mapped_column(String(200))
    data_type: Mapped[DataType] = mapped_column(enum_col(DataType), nullable=False)
    unit: Mapped[str | None] = mapped_column(String(30))
    criticality: Mapped[Criticality] = mapped_column(enum_col(Criticality), nullable=False)
    normalization_rule: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class FieldObservation(Base):
    __tablename__ = "field_observations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    field_definition_id: Mapped[str] = mapped_column(ForeignKey("field_definitions.id"), nullable=False)
    document_version_id: Mapped[str] = mapped_column(ForeignKey("document_versions.id"), nullable=False)
    raw_value: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_candidate_value: Mapped[str | None] = mapped_column(Text)
    structured_value_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    page_number: Mapped[int | None] = mapped_column(Integer)
    bounding_box_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    source_region_text: Mapped[str | None] = mapped_column(Text)
    extraction_method: Mapped[ExtractionMethod] = mapped_column(enum_col(ExtractionMethod), nullable=False)
    extractor_version: Mapped[str] = mapped_column(String(100), nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(100), nullable=False)
    document_version: Mapped[DocumentVersion] = relationship(back_populates="observations")


class VerifiedAssertion(Base):
    __tablename__ = "verified_assertions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    field_definition_id: Mapped[str] = mapped_column(ForeignKey("field_definitions.id"), nullable=False)
    semantic_value_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    display_value: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[AssertionStatus] = mapped_column(enum_col(AssertionStatus), nullable=False)
    source_observation_id: Mapped[str | None] = mapped_column(ForeignKey("field_observations.id"))
    verification_method: Mapped[VerificationMethod] = mapped_column(enum_col(VerificationMethod), nullable=False)
    verified_by: Mapped[str] = mapped_column(String(36), nullable=False)
    verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    authority_rule_id: Mapped[str | None] = mapped_column(String(36))
    reason: Mapped[str | None] = mapped_column(Text)
    supersedes_assertion_id: Mapped[str | None] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class FieldAuthorityRule(Base):
    __tablename__ = "field_authority_rules"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    scenario_id: Mapped[str] = mapped_column(ForeignKey("scenario_configs.id"), nullable=False)
    field_definition_id: Mapped[str] = mapped_column(ForeignKey("field_definitions.id"), nullable=False)
    purpose: Mapped[str] = mapped_column(String(100), nullable=False)
    primary_source_type: Mapped[str] = mapped_column(String(100), nullable=False)
    fallback_source_type: Mapped[str | None] = mapped_column(String(100))
    conflict_behavior: Mapped[str] = mapped_column(String(50), nullable=False)
    human_verifier_role: Mapped[str] = mapped_column(String(100), nullable=False)
    effective_from: Mapped[date | None] = mapped_column(Date)
    effective_to: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)
    status: Mapped[ConfigStatus] = mapped_column(enum_col(ConfigStatus), nullable=False)


class RequirementConfig(Base):
    __tablename__ = "requirement_configs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    scenario_id: Mapped[str] = mapped_column(ForeignKey("scenario_configs.id"), nullable=False)
    requirement_code: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    requirement_type: Mapped[RequirementType] = mapped_column(enum_col(RequirementType), nullable=False)
    applicability_expression_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    required_document_type: Mapped[str | None] = mapped_column(String(100))
    required_dependency_type: Mapped[str | None] = mapped_column(String(100))
    human_decision_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    blocking: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    effective_from: Mapped[date | None] = mapped_column(Date)
    effective_to: Mapped[date | None] = mapped_column(Date)
    status: Mapped[ConfigStatus] = mapped_column(enum_col(ConfigStatus), nullable=False)


class ApprovalDependency(Base):
    __tablename__ = "approval_dependencies"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    dependency_type: Mapped[str] = mapped_column(String(100), nullable=False)
    authority_or_owner: Mapped[str] = mapped_column(String(200), nullable=False)
    reference_number: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    valid_from: Mapped[date | None] = mapped_column(Date)
    valid_until: Mapped[date | None] = mapped_column(Date)
    blocking: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    evidence_document_id: Mapped[str | None] = mapped_column(ForeignKey("documents.id"))
    notes: Mapped[str | None] = mapped_column(Text)


class AttachmentCategoryConfig(Base):
    __tablename__ = "attachment_category_configs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    scenario_id: Mapped[str] = mapped_column(ForeignKey("scenario_configs.id"), nullable=False)
    category_code: Mapped[str] = mapped_column(String(100), nullable=False)
    label_en: Mapped[str] = mapped_column(String(200), nullable=False)
    label_ar: Mapped[str | None] = mapped_column(String(200))
    required_state: Mapped[str] = mapped_column(String(50), nullable=False)
    applicability_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    allowed_document_types: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    multiple_files_allowed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    language_requirement: Mapped[str | None] = mapped_column(String(50))
    max_size_mb: Mapped[int | None] = mapped_column(Integer)
    allowed_formats_json: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    portal_order: Mapped[int] = mapped_column(Integer, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)


class DrawingMetadataControl(Base):
    __tablename__ = "drawing_metadata_controls"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    scenario_id: Mapped[str] = mapped_column(ForeignKey("scenario_configs.id"), nullable=False)
    control_code: Mapped[str] = mapped_column(String(100), nullable=False)
    field_definition_id: Mapped[str] = mapped_column(ForeignKey("field_definitions.id"), nullable=False)
    drawing_source: Mapped[str] = mapped_column(String(100), nullable=False)
    canonical_field_code: Mapped[str] = mapped_column(String(120), nullable=False)
    comparison_type: Mapped[str] = mapped_column(String(50), nullable=False)
    blocking: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)


class Conflict(Base):
    __tablename__ = "conflicts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    field_definition_id: Mapped[str] = mapped_column(ForeignKey("field_definitions.id"), nullable=False)
    observation_ids_json: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    severity: Mapped[ConflictSeverity] = mapped_column(enum_col(ConflictSeverity), nullable=False)
    status: Mapped[ConflictStatus] = mapped_column(enum_col(ConflictStatus), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    resolver: Mapped[str | None] = mapped_column(String(200))
    resolution: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class MunicipalityConfig(Base):
    __tablename__ = "municipality_configs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    scenario_id: Mapped[str] = mapped_column(ForeignKey("scenario_configs.id"), nullable=False)
    tabs_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    fields_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    dropdowns_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    grids_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    attachments_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    operations_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    mfa_mode: Mapped[str] = mapped_column(String(50), nullable=False)
    attended_session_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    session_notes: Mapped[str] = mapped_column(Text, nullable=False)
    precheck_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    submission_confirmation_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class MunicipalityDraft(Base):
    __tablename__ = "municipality_drafts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    application_id: Mapped[str] = mapped_column(ForeignKey("permit_applications.id"), unique=True, nullable=False)
    state_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class ExtractionSpikeRun(Base):
    __tablename__ = "extraction_spike_runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    dataset_name: Mapped[str] = mapped_column(String(200), nullable=False)
    dataset_type: Mapped[DatasetType] = mapped_column(enum_col(DatasetType), nullable=False)
    environment: Mapped[str] = mapped_column(String(20), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    document_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    extractor_config_version: Mapped[str] = mapped_column(String(100), nullable=False)
    classifier_config_version: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="CREATED", nullable=False)
    metrics_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)


class SpikeDocumentResult(Base):
    __tablename__ = "spike_document_results"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    spike_run_id: Mapped[str] = mapped_column(ForeignKey("extraction_spike_runs.id"), nullable=False)
    document_version_id: Mapped[str] = mapped_column(ForeignKey("document_versions.id"), nullable=False)
    expected_class: Mapped[str] = mapped_column(String(100), nullable=False)
    predicted_class: Mapped[str] = mapped_column(String(100), nullable=False)
    result: Mapped[str] = mapped_column(String(30), nullable=False)
    critical_fields_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    corrections: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    verification_time_seconds: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    evidence_usability: Mapped[EvidenceUsability] = mapped_column(enum_col(EvidenceUsability), nullable=False)
    failure_mode: Mapped[str | None] = mapped_column(String(100))


class SpikeFieldResult(Base):
    __tablename__ = "spike_field_results"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    spike_run_id: Mapped[str] = mapped_column(ForeignKey("extraction_spike_runs.id"), nullable=False)
    field_code: Mapped[str] = mapped_column(String(120), nullable=False)
    samples: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    correct_candidate: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    wrong_candidate: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    missing_candidate: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    keyed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    corrected: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class GoldDocumentLabel(Base):
    __tablename__ = "gold_document_labels"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    document_version_id: Mapped[str] = mapped_column(ForeignKey("document_versions.id"), nullable=False)
    expected_class: Mapped[str] = mapped_column(String(100), nullable=False)
    adjudicated_by: Mapped[str] = mapped_column(String(200), nullable=False)
    adjudicated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class GoldFieldLabel(Base):
    __tablename__ = "gold_field_labels"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    document_version_id: Mapped[str] = mapped_column(ForeignKey("document_versions.id"), nullable=False)
    field_definition_id: Mapped[str] = mapped_column(ForeignKey("field_definitions.id"), nullable=False)
    expected_semantic_value: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    source_page: Mapped[int | None] = mapped_column(Integer)
    source_region: Mapped[str | None] = mapped_column(Text)
    adjudicated_by: Mapped[str] = mapped_column(String(200), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)


class RealDocumentTestGate(Base):
    __tablename__ = "real_document_test_gates"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    real_document_test_approved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    approved_test_location: Mapped[str | None] = mapped_column(String(300))
    raw_access_roles: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    remote_raw_access_allowed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    external_ai_allowed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    approved_ai_provider: Mapped[str | None] = mapped_column(String(100))
    approved_region: Mapped[str | None] = mapped_column(String(100))
    retention_policy_reference: Mapped[str | None] = mapped_column(String(300))
    approval_reference: Mapped[str | None] = mapped_column(String(300))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class SubmissionConfirmation(Base):
    __tablename__ = "submission_confirmations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    application_id: Mapped[str] = mapped_column(ForeignKey("permit_applications.id"), nullable=False)
    mode: Mapped[str] = mapped_column(String(50), nullable=False)
    request_reference: Mapped[str] = mapped_column(String(100), nullable=False)
    visible_status: Mapped[str] = mapped_column(String(50), nullable=False)
    confirmation_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    evidence_reference: Mapped[str | None] = mapped_column(String(300))
    second_verifier: Mapped[str | None] = mapped_column(String(200))
    notes: Mapped[str | None] = mapped_column(Text)
    preparation_revision_id: Mapped[str | None] = mapped_column(ForeignKey("preparation_revisions.id"))
    application_identity_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    confirmed_by: Mapped[str | None] = mapped_column(String(200))
    status: Mapped[str | None] = mapped_column(String(40))
