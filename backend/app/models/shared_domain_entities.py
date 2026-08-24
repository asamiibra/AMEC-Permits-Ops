"""Canonical shared-domain foundations for regulatory, policy, technical, and form runtime work.

These records deliberately sit below Dashboard V1/V2.  They provide stable
identities and versioned lineage; source documents, generated artifacts, and
UI surfaces remain separate concerns.
"""

from datetime import date, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, utcnow


def _id() -> str:
    return str(uuid4())


class ExternalBody(Base, TimestampMixin):
    __tablename__ = "external_bodies"
    __table_args__ = (UniqueConstraint("code", name="uq_external_body_code"), Index("ix_external_body_status", "status"), Index("ix_external_body_jurisdiction", "jurisdiction_id"))

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    code: Mapped[str] = mapped_column(String(80), nullable=False)
    name_en: Mapped[str] = mapped_column(String(240), nullable=False)
    name_ar: Mapped[str | None] = mapped_column(String(240))
    body_type: Mapped[str] = mapped_column(String(80), nullable=False, default="AUTHORITY")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="DRAFT")
    jurisdiction_id: Mapped[str | None] = mapped_column(ForeignKey("jurisdictions.id"), index=True)
    effective_from: Mapped[date | None] = mapped_column(Date)
    effective_to: Mapped[date | None] = mapped_column(Date)
    provenance_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    verification_state: Mapped[str] = mapped_column(String(40), nullable=False, default="UNVERIFIED")
    created_by: Mapped[str] = mapped_column(String(200), nullable=False, default="SYSTEM")


class ExternalBodyUnit(Base, TimestampMixin):
    __tablename__ = "external_body_units"
    __table_args__ = (UniqueConstraint("external_body_id", "code", name="uq_external_body_unit_code"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    external_body_id: Mapped[str] = mapped_column(ForeignKey("external_bodies.id"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(80), nullable=False)
    name_en: Mapped[str] = mapped_column(String(240), nullable=False)
    name_ar: Mapped[str | None] = mapped_column(String(240))
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="DRAFT")


class Jurisdiction(Base, TimestampMixin):
    __tablename__ = "jurisdictions"
    __table_args__ = (UniqueConstraint("code", name="uq_jurisdiction_code"), Index("ix_jurisdiction_status", "status"), Index("ix_jurisdiction_parent", "parent_id"))

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    code: Mapped[str] = mapped_column(String(100), nullable=False)
    country_code: Mapped[str] = mapped_column(String(8), nullable=False)
    name_en: Mapped[str] = mapped_column(String(240), nullable=False)
    name_ar: Mapped[str | None] = mapped_column(String(240))
    level: Mapped[str] = mapped_column(String(40), nullable=False, default="LOCALITY")
    parent_id: Mapped[str | None] = mapped_column(ForeignKey("jurisdictions.id"), index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="DRAFT")
    coverage_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    provenance_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class ServiceType(Base, TimestampMixin):
    __tablename__ = "service_types"
    __table_args__ = (UniqueConstraint("code", name="uq_service_type_code"), Index("ix_service_type_status", "status"))

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    code: Mapped[str] = mapped_column(String(100), nullable=False)
    name_en: Mapped[str] = mapped_column(String(240), nullable=False)
    name_ar: Mapped[str | None] = mapped_column(String(240))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="DRAFT")
    current_version_id: Mapped[str | None] = mapped_column(String(36), index=True)
    provenance_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class ServiceTypeVersion(Base, TimestampMixin):
    __tablename__ = "service_type_versions"
    __table_args__ = (UniqueConstraint("service_type_id", "version", name="uq_service_type_version"), Index("ix_service_type_version_effective", "service_type_id", "effective_from", "effective_to"))

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    service_type_id: Mapped[str] = mapped_column(ForeignKey("service_types.id"), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="DRAFT")
    effective_from: Mapped[date | None] = mapped_column(Date)
    effective_to: Mapped[date | None] = mapped_column(Date)
    provenance_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    approved_by: Mapped[str | None] = mapped_column(String(200))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RegulatoryLifecyclePhase(Base, TimestampMixin):
    __tablename__ = "regulatory_lifecycle_phases"
    __table_args__ = (UniqueConstraint("code", name="uq_regulatory_phase_code"), Index("ix_regulatory_phase_order", "sort_order"))

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    code: Mapped[str] = mapped_column(String(60), nullable=False)
    name_en: Mapped[str] = mapped_column(String(160), nullable=False)
    name_ar: Mapped[str | None] = mapped_column(String(160))
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="ACTIVE")


class RegulatoryJourney(Base, TimestampMixin):
    __tablename__ = "regulatory_journeys"
    __table_args__ = (UniqueConstraint("journey_code", name="uq_regulatory_journey_code"), Index("ix_regulatory_journey_project", "project_id"), Index("ix_regulatory_journey_status", "status"))

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    journey_code: Mapped[str] = mapped_column(String(100), nullable=False)
    project_id: Mapped[str | None] = mapped_column(ForeignKey("projects.id"), index=True)
    service_type_id: Mapped[str] = mapped_column(ForeignKey("service_types.id"), nullable=False, index=True)
    jurisdiction_id: Mapped[str] = mapped_column(ForeignKey("jurisdictions.id"), nullable=False, index=True)
    external_body_id: Mapped[str | None] = mapped_column(ForeignKey("external_bodies.id"), index=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="DRAFT")
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)


class AuthorityCase(Base, TimestampMixin):
    __tablename__ = "authority_cases"
    __table_args__ = (UniqueConstraint("case_reference", name="uq_authority_case_reference"), Index("ix_authority_case_journey", "regulatory_journey_id"), Index("ix_authority_case_context", "external_body_id", "service_type_id", "jurisdiction_id"))

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    case_reference: Mapped[str] = mapped_column(String(100), nullable=False)
    regulatory_journey_id: Mapped[str | None] = mapped_column(ForeignKey("regulatory_journeys.id"), index=True)
    external_body_id: Mapped[str] = mapped_column(ForeignKey("external_bodies.id"), nullable=False, index=True)
    service_type_id: Mapped[str] = mapped_column(ForeignKey("service_types.id"), nullable=False, index=True)
    jurisdiction_id: Mapped[str] = mapped_column(ForeignKey("jurisdictions.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="DRAFT")
    subject_type: Mapped[str | None] = mapped_column(String(50))
    subject_id: Mapped[str | None] = mapped_column(String(36), index=True)
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)


class AuthorityCaseIdentifier(Base, TimestampMixin):
    __tablename__ = "authority_case_identifiers"
    __table_args__ = (UniqueConstraint("authority_case_id", "identifier_type", "value", name="uq_authority_case_identifier"), Index("ix_authority_case_identifier_value", "value"))

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    authority_case_id: Mapped[str] = mapped_column(ForeignKey("authority_cases.id"), nullable=False, index=True)
    identifier_type: Mapped[str] = mapped_column(String(60), nullable=False)
    value: Mapped[str] = mapped_column(String(240), nullable=False)
    issued_by: Mapped[str | None] = mapped_column(String(200))
    issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class AuthorityCaseWorkPeriod(Base, TimestampMixin):
    __tablename__ = "authority_case_work_periods"
    __table_args__ = (Index("ix_authority_case_work_period_case", "authority_case_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    authority_case_id: Mapped[str] = mapped_column(ForeignKey("authority_cases.id"), nullable=False)
    period_type: Mapped[str] = mapped_column(String(50), nullable=False)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_document_version_id: Mapped[str | None] = mapped_column(ForeignKey("document_versions.id"), index=True)
    note: Mapped[str | None] = mapped_column(Text)


class ExternalInteractionProfile(Base, TimestampMixin):
    __tablename__ = "external_interaction_profiles"
    __table_args__ = (UniqueConstraint("external_body_id", "channel_code", name="uq_external_interaction_channel"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    external_body_id: Mapped[str] = mapped_column(ForeignKey("external_bodies.id"), nullable=False, index=True)
    channel_code: Mapped[str] = mapped_column(String(60), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="DRAFT")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    read_only: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class AuthorityOutcome(Base, TimestampMixin):
    __tablename__ = "authority_outcomes"
    __table_args__ = (Index("ix_authority_outcome_case", "authority_case_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    authority_case_id: Mapped[str] = mapped_column(ForeignKey("authority_cases.id"), nullable=False)
    outcome_type: Mapped[str] = mapped_column(String(60), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="RECORDED")
    issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_document_version_id: Mapped[str | None] = mapped_column(ForeignKey("document_versions.id"), index=True)
    decision_payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    recorded_by: Mapped[str] = mapped_column(String(200), nullable=False)


class RegulatoryRelation(Base, TimestampMixin):
    __tablename__ = "regulatory_relations"
    __table_args__ = (UniqueConstraint("source_type", "source_id", "relation_type", "target_type", "target_id", name="uq_regulatory_relation"), Index("ix_regulatory_relation_source", "source_type", "source_id"), Index("ix_regulatory_relation_target", "target_type", "target_id"))

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    source_type: Mapped[str] = mapped_column(String(60), nullable=False)
    source_id: Mapped[str] = mapped_column(String(36), nullable=False)
    relation_type: Mapped[str] = mapped_column(String(60), nullable=False)
    target_type: Mapped[str] = mapped_column(String(60), nullable=False)
    target_id: Mapped[str] = mapped_column(String(36), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="ACTIVE")


class MasterContentApplicability(Base, TimestampMixin):
    """Version-pinned regulatory applicability for a canonical source."""
    __tablename__ = "master_content_applicability"
    __table_args__ = (
        Index("uq_master_content_applicability_version", "master_content_item_id", "source_document_version_id", "external_body_id", "jurisdiction_id", "service_type_id", "lifecycle_phase_id", unique=True, mssql_where=text("jurisdiction_id IS NOT NULL AND lifecycle_phase_id IS NOT NULL")),
        Index("ix_master_content_applicability_context", "external_body_id", "jurisdiction_id", "service_type_id", "lifecycle_phase_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    master_content_item_id: Mapped[str] = mapped_column(ForeignKey("master_content_items.id"), nullable=False, index=True)
    source_document_version_id: Mapped[str] = mapped_column(ForeignKey("document_versions.id"), nullable=False, index=True)
    external_body_id: Mapped[str] = mapped_column(ForeignKey("external_bodies.id"), nullable=False, index=True)
    jurisdiction_id: Mapped[str | None] = mapped_column(ForeignKey("jurisdictions.id"), index=True)
    service_type_id: Mapped[str] = mapped_column(ForeignKey("service_types.id"), nullable=False, index=True)
    lifecycle_phase_id: Mapped[str | None] = mapped_column(ForeignKey("regulatory_lifecycle_phases.id"), index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="DRAFT", index=True)
    effective_from: Mapped[date | None] = mapped_column(Date)
    effective_to: Mapped[date | None] = mapped_column(Date)
    confirmed_by: Mapped[str | None] = mapped_column(String(200))
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)
    supersedes_id: Mapped[str | None] = mapped_column(ForeignKey("master_content_applicability.id"))


class AutomationReadinessAssessment(Base, TimestampMixin):
    """Immutable evidence snapshot for derived AUTOMATED_USE_READY state."""
    __tablename__ = "automation_readiness_assessments"
    __table_args__ = (Index("ix_automation_readiness_profile", "profile_id", "evaluated_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    profile_id: Mapped[str] = mapped_column(ForeignKey("form_automation_profiles.id"), nullable=False, index=True)
    master_content_item_id: Mapped[str] = mapped_column(ForeignKey("master_content_items.id"), nullable=False, index=True)
    source_document_version_id: Mapped[str] = mapped_column(ForeignKey("document_versions.id"), nullable=False, index=True)
    mapping_release_id: Mapped[str | None] = mapped_column(ForeignKey("form_mapping_releases.id"), index=True)
    state: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    blocking_reasons: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    evidence_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    evaluated_by: Mapped[str] = mapped_column(String(200), nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    provenance_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class RequirementDefinition(Base, TimestampMixin):
    __tablename__ = "requirement_definitions"
    __table_args__ = (UniqueConstraint("code", name="uq_requirement_definition_code"), Index("ix_requirement_definition_status", "status"))

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    code: Mapped[str] = mapped_column(String(120), nullable=False)
    name_en: Mapped[str] = mapped_column(String(240), nullable=False)
    name_ar: Mapped[str | None] = mapped_column(String(240))
    description: Mapped[str | None] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="DRAFT")


class RequirementPolicyVersion(Base, TimestampMixin):
    __tablename__ = "requirement_policy_versions"
    __table_args__ = (Index("uq_requirement_policy_context_version", "service_type_id", "jurisdiction_id", "external_body_id", "version", unique=True, mssql_where=text("jurisdiction_id IS NOT NULL AND external_body_id IS NOT NULL")), Index("ix_requirement_policy_context", "service_type_id", "jurisdiction_id", "external_body_id"), Index("ix_requirement_policy_effective", "effective_from", "effective_to"), Index("ix_requirement_policy_status", "status"))

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    service_type_id: Mapped[str] = mapped_column(ForeignKey("service_types.id"), nullable=False)
    jurisdiction_id: Mapped[str | None] = mapped_column(ForeignKey("jurisdictions.id"))
    external_body_id: Mapped[str | None] = mapped_column(ForeignKey("external_bodies.id"))
    version: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="DRAFT")
    effective_from: Mapped[date | None] = mapped_column(Date)
    effective_to: Mapped[date | None] = mapped_column(Date)
    purpose: Mapped[str] = mapped_column(String(50), nullable=False, default="AUTHORITY_SUBMISSION")
    provenance_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    approved_by: Mapped[str | None] = mapped_column(String(200))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    supersedes_id: Mapped[str | None] = mapped_column(ForeignKey("requirement_policy_versions.id"))


class RequirementGroup(Base, TimestampMixin):
    __tablename__ = "requirement_groups"
    __table_args__ = (UniqueConstraint("policy_version_id", "code", name="uq_requirement_group_code"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    policy_version_id: Mapped[str] = mapped_column(ForeignKey("requirement_policy_versions.id"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(100), nullable=False)
    group_type: Mapped[str] = mapped_column(String(30), nullable=False, default="ALL_OF")
    min_count: Mapped[int | None] = mapped_column(Integer)
    label: Mapped[str | None] = mapped_column(String(240))


class RequirementPolicyItem(Base, TimestampMixin):
    __tablename__ = "requirement_policy_items"
    __table_args__ = (Index("uq_requirement_policy_item", "policy_version_id", "requirement_definition_id", "phase_id", unique=True, mssql_where=text("phase_id IS NOT NULL")), Index("ix_requirement_policy_item_policy", "policy_version_id"), Index("ix_requirement_policy_item_requirement", "requirement_definition_id"))

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    policy_version_id: Mapped[str] = mapped_column(ForeignKey("requirement_policy_versions.id"), nullable=False)
    requirement_definition_id: Mapped[str] = mapped_column(ForeignKey("requirement_definitions.id"), nullable=False)
    phase_id: Mapped[str | None] = mapped_column(ForeignKey("regulatory_lifecycle_phases.id"), index=True)
    group_id: Mapped[str | None] = mapped_column(ForeignKey("requirement_groups.id"), index=True)
    applicability_expression: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="ACTIVE")
    source_section_id: Mapped[str | None] = mapped_column(ForeignKey("master_content_source_sections.id"), index=True)


class RequirementEvidenceConstraint(Base, TimestampMixin):
    __tablename__ = "requirement_evidence_constraints"
    __table_args__ = (UniqueConstraint("policy_item_id", name="uq_requirement_evidence_constraint_item"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    policy_item_id: Mapped[str] = mapped_column(ForeignKey("requirement_policy_items.id"), nullable=False, index=True)
    copy_type: Mapped[str | None] = mapped_column(String(40))
    side_requirement: Mapped[str | None] = mapped_column(String(30))
    min_count: Mapped[int | None] = mapped_column(Integer)
    allowed_formats: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    freshness_days: Mapped[int | None] = mapped_column(Integer)
    validity_days: Mapped[int | None] = mapped_column(Integer)
    signature_roles: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    stamp_roles: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    accreditation: Mapped[str | None] = mapped_column(String(160))
    approval_authority: Mapped[str | None] = mapped_column(String(160))
    extra_constraints: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class RequirementPolicyLineage(Base, TimestampMixin):
    __tablename__ = "requirement_policy_lineage"
    __table_args__ = (Index("uq_requirement_policy_lineage", "policy_version_id", "master_content_item_id", "document_version_id", "source_section_id", unique=True, mssql_where=text("source_section_id IS NOT NULL")),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    policy_version_id: Mapped[str] = mapped_column(ForeignKey("requirement_policy_versions.id"), nullable=False, index=True)
    master_content_item_id: Mapped[str] = mapped_column(ForeignKey("master_content_items.id"), nullable=False, index=True)
    document_version_id: Mapped[str] = mapped_column(ForeignKey("document_versions.id"), nullable=False, index=True)
    source_section_id: Mapped[str | None] = mapped_column(ForeignKey("master_content_source_sections.id"), index=True)
    relation_type: Mapped[str] = mapped_column(String(40), nullable=False, default="SOURCE_OF_POLICY")
    source_role: Mapped[str] = mapped_column(String(40), nullable=False, default="PRIMARY")
    governance_status: Mapped[str] = mapped_column(String(30), nullable=False, default="DRAFT", index=True)
    governance_note: Mapped[str | None] = mapped_column(Text)
    confirmed_by: Mapped[str | None] = mapped_column(String(200))
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RequirementApplicabilityDecision(Base, TimestampMixin):
    __tablename__ = "requirement_applicability_decisions"
    __table_args__ = (Index("ix_requirement_applicability_context", "context_type", "context_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    policy_item_id: Mapped[str] = mapped_column(ForeignKey("requirement_policy_items.id"), nullable=False, index=True)
    context_type: Mapped[str] = mapped_column(String(50), nullable=False)
    context_id: Mapped[str] = mapped_column(String(36), nullable=False)
    value: Mapped[str] = mapped_column(String(30), nullable=False, default="APPLICABILITY_UNKNOWN")
    reason: Mapped[str | None] = mapped_column(Text)
    authority: Mapped[str | None] = mapped_column(String(200))
    decided_by: Mapped[str] = mapped_column(String(200), nullable=False)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class RequirementEvaluation(Base, TimestampMixin):
    __tablename__ = "requirement_evaluations"
    __table_args__ = (Index("ix_requirement_evaluation_context", "context_type", "context_id"), Index("ix_requirement_evaluation_policy", "policy_version_id"))

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    policy_version_id: Mapped[str] = mapped_column(ForeignKey("requirement_policy_versions.id"), nullable=False)
    policy_item_id: Mapped[str] = mapped_column(ForeignKey("requirement_policy_items.id"), nullable=False)
    context_type: Mapped[str] = mapped_column(String(50), nullable=False)
    context_id: Mapped[str] = mapped_column(String(36), nullable=False)
    applicability: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    evidence_summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class RequirementEvidenceEvaluation(Base, TimestampMixin):
    __tablename__ = "requirement_evidence_evaluations"
    __table_args__ = (Index("ix_requirement_evidence_evaluation_requirement", "requirement_evaluation_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    requirement_evaluation_id: Mapped[str] = mapped_column(ForeignKey("requirement_evaluations.id"), nullable=False)
    document_version_id: Mapped[str | None] = mapped_column(ForeignKey("document_versions.id"), index=True)
    evidence_ref: Mapped[str | None] = mapped_column(String(240))
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    details_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class RequirementDecision(Base, TimestampMixin):
    __tablename__ = "requirement_decisions"
    __table_args__ = (Index("ix_requirement_decision_context", "context_type", "context_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    policy_item_id: Mapped[str] = mapped_column(ForeignKey("requirement_policy_items.id"), nullable=False)
    context_type: Mapped[str] = mapped_column(String(50), nullable=False)
    context_id: Mapped[str] = mapped_column(String(36), nullable=False)
    decision_type: Mapped[str] = mapped_column(String(30), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    authority: Mapped[str | None] = mapped_column(String(200))
    policy_version_id: Mapped[str] = mapped_column(ForeignKey("requirement_policy_versions.id"), nullable=False)
    decided_by: Mapped[str] = mapped_column(String(200), nullable=False)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class TechnicalRuleSetVersion(Base, TimestampMixin):
    __tablename__ = "technical_rule_set_versions"
    __table_args__ = (UniqueConstraint("code", "version", name="uq_technical_rule_set_version"), Index("ix_technical_rule_set_context", "service_type_id", "jurisdiction_id", "external_body_id"), Index("ix_technical_rule_set_effective", "effective_from", "effective_to"), Index("ix_technical_rule_set_status", "status"))

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    code: Mapped[str] = mapped_column(String(120), nullable=False)
    name: Mapped[str] = mapped_column(String(240), nullable=False)
    discipline: Mapped[str | None] = mapped_column(String(80))
    service_type_id: Mapped[str | None] = mapped_column(ForeignKey("service_types.id"), index=True)
    jurisdiction_id: Mapped[str | None] = mapped_column(ForeignKey("jurisdictions.id"), index=True)
    external_body_id: Mapped[str | None] = mapped_column(ForeignKey("external_bodies.id"), index=True)
    version: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="DRAFT")
    effective_from: Mapped[date | None] = mapped_column(Date)
    effective_to: Mapped[date | None] = mapped_column(Date)
    provenance_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    approved_by: Mapped[str | None] = mapped_column(String(200))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    supersedes_id: Mapped[str | None] = mapped_column(ForeignKey("technical_rule_set_versions.id"))


class TechnicalRule(Base, TimestampMixin):
    __tablename__ = "technical_rules"
    __table_args__ = (UniqueConstraint("rule_set_version_id", "code", name="uq_technical_rule_code"), Index("ix_technical_rule_set", "rule_set_version_id"), Index("ix_technical_rule_status", "status"))

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    rule_set_version_id: Mapped[str] = mapped_column(ForeignKey("technical_rule_set_versions.id"), nullable=False)
    code: Mapped[str] = mapped_column(String(120), nullable=False)
    name: Mapped[str] = mapped_column(String(240), nullable=False)
    rule_type: Mapped[str] = mapped_column(String(50), nullable=False)
    expression_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="DRAFT")
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=100)


class TechnicalRuleLineage(Base, TimestampMixin):
    __tablename__ = "technical_rule_lineage"
    __table_args__ = (Index("uq_technical_rule_lineage", "technical_rule_id", "master_content_item_id", "document_version_id", "source_section_id", unique=True, mssql_where=text("source_section_id IS NOT NULL")),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    technical_rule_id: Mapped[str] = mapped_column(ForeignKey("technical_rules.id"), nullable=False, index=True)
    master_content_item_id: Mapped[str] = mapped_column(ForeignKey("master_content_items.id"), nullable=False, index=True)
    document_version_id: Mapped[str] = mapped_column(ForeignKey("document_versions.id"), nullable=False, index=True)
    source_section_id: Mapped[str | None] = mapped_column(ForeignKey("master_content_source_sections.id"), index=True)
    relation_type: Mapped[str] = mapped_column(String(40), nullable=False, default="SOURCE_OF_RULE")
    source_role: Mapped[str] = mapped_column(String(40), nullable=False, default="PRIMARY")
    governance_status: Mapped[str] = mapped_column(String(30), nullable=False, default="DRAFT", index=True)
    governance_note: Mapped[str | None] = mapped_column(Text)
    confirmed_by: Mapped[str | None] = mapped_column(String(200))
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class TechnicalRuleEvaluation(Base, TimestampMixin):
    __tablename__ = "technical_rule_evaluations"
    __table_args__ = (Index("ix_technical_rule_evaluation_context", "context_type", "context_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    technical_rule_id: Mapped[str] = mapped_column(ForeignKey("technical_rules.id"), nullable=False)
    context_type: Mapped[str] = mapped_column(String(50), nullable=False)
    context_id: Mapped[str] = mapped_column(String(36), nullable=False)
    result: Mapped[str] = mapped_column(String(20), nullable=False)
    calculated_values: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    inputs_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    rule_version: Mapped[str] = mapped_column(String(40), nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)


class FormAutomationProfile(Base, TimestampMixin):
    __tablename__ = "form_automation_profiles"
    __table_args__ = (UniqueConstraint("master_content_item_id", name="uq_form_automation_profile_item"), Index("ix_form_automation_profile_source", "source_document_version_id"), Index("ix_form_automation_profile_status", "automation_status"))

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    master_content_item_id: Mapped[str] = mapped_column(ForeignKey("master_content_items.id"), nullable=False)
    source_document_version_id: Mapped[str] = mapped_column(ForeignKey("document_versions.id"), nullable=False)
    renderer_type: Mapped[str] = mapped_column(String(50), nullable=False, default="SYNTHETIC")
    automation_status: Mapped[str] = mapped_column(String(40), nullable=False, default="DRAFT")
    semantic_contract_version: Mapped[str] = mapped_column(String(40), nullable=False, default="1.0")
    working_rendition_ref: Mapped[str | None] = mapped_column(String(500))
    writer_policy_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    source_version_state: Mapped[str] = mapped_column(String(40), nullable=False, default="CURRENT")
    managed_by: Mapped[str] = mapped_column(String(200), nullable=False)


class SemanticKeyDefinition(Base, TimestampMixin):
    __tablename__ = "semantic_key_definitions"
    __table_args__ = (UniqueConstraint("semantic_key", name="uq_semantic_key"), Index("ix_semantic_key_status", "status"))

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    semantic_key: Mapped[str] = mapped_column(String(200), nullable=False)
    value_type: Mapped[str] = mapped_column(String(40), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="ACTIVE")
    consequential: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class SemanticValueAssertion(Base, TimestampMixin):
    __tablename__ = "semantic_value_assertions"
    __table_args__ = (Index("ix_semantic_assertion_context", "context_type", "context_id"), Index("ix_semantic_assertion_key", "semantic_key_id"))

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    semantic_key_id: Mapped[str] = mapped_column(ForeignKey("semantic_key_definitions.id"), nullable=False)
    context_type: Mapped[str] = mapped_column(String(50), nullable=False)
    context_id: Mapped[str] = mapped_column(String(36), nullable=False)
    value_json: Mapped[Any] = mapped_column(JSON, nullable=False)
    value_type: Mapped[str] = mapped_column(String(40), nullable=False)
    source_type: Mapped[str] = mapped_column(String(60), nullable=False)
    source_id: Mapped[str] = mapped_column(String(36), nullable=False)
    source_version: Mapped[str | None] = mapped_column(String(80))
    verification_status: Mapped[str] = mapped_column(String(40), nullable=False, default="UNVERIFIED")
    authority: Mapped[str | None] = mapped_column(String(200))
    effective_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    asserted_by: Mapped[str] = mapped_column(String(200), nullable=False)


class FormMappingRelease(Base, TimestampMixin):
    __tablename__ = "form_mapping_releases"
    __table_args__ = (UniqueConstraint("profile_id", "version", name="uq_form_mapping_release_version"), Index("ix_form_mapping_release_status", "status"))

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    profile_id: Mapped[str] = mapped_column(ForeignKey("form_automation_profiles.id"), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="DRAFT")
    mapping_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    master_content_item_id: Mapped[str | None] = mapped_column(ForeignKey("master_content_items.id"), index=True)
    source_document_version_id: Mapped[str | None] = mapped_column(ForeignKey("document_versions.id"), index=True)
    normalized_rendition_ref: Mapped[str | None] = mapped_column(String(500))
    normalized_rendition_hash: Mapped[str | None] = mapped_column(String(128))
    semantic_contract_version: Mapped[str | None] = mapped_column(String(40))
    renderer_type: Mapped[str | None] = mapped_column(String(50))
    renderer_version: Mapped[str | None] = mapped_column(String(60))
    mapping_checksum: Mapped[str | None] = mapped_column(String(128), index=True)
    reviewed_by: Mapped[str | None] = mapped_column(String(200))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_by: Mapped[str | None] = mapped_column(String(200))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    released_by: Mapped[str | None] = mapped_column(String(200))
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retired_by: Mapped[str | None] = mapped_column(String(200))
    retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    invalidation_reason: Mapped[str | None] = mapped_column(Text)


class FormMappingRule(Base, TimestampMixin):
    __tablename__ = "form_mapping_rules"
    __table_args__ = (UniqueConstraint("mapping_release_id", "logical_field_key", "target_key", name="uq_form_mapping_rule_target"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    mapping_release_id: Mapped[str] = mapped_column(ForeignKey("form_mapping_releases.id"), nullable=False, index=True)
    logical_field_key: Mapped[str] = mapped_column(String(200), nullable=False)
    target_key: Mapped[str] = mapped_column(String(200), nullable=False)
    transform_type: Mapped[str] = mapped_column(String(50), nullable=False, default="SCALAR")
    target_writer: Mapped[str] = mapped_column(String(40), nullable=False, default="SYSTEM")
    page_number: Mapped[int | None] = mapped_column(Integer)
    rect_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    capacity: Mapped[int | None] = mapped_column(Integer)
    configuration_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class FormInstance(Base, TimestampMixin):
    __tablename__ = "form_instances"
    __table_args__ = (Index("ix_form_instance_context", "context_type", "context_id"), Index("ix_form_instance_source", "source_document_version_id"), Index("ix_form_instance_status", "status"))

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    master_content_item_id: Mapped[str] = mapped_column(ForeignKey("master_content_items.id"), nullable=False, index=True)
    source_document_version_id: Mapped[str] = mapped_column(ForeignKey("document_versions.id"), nullable=False, index=True)
    profile_id: Mapped[str] = mapped_column(ForeignKey("form_automation_profiles.id"), nullable=False, index=True)
    mapping_release_id: Mapped[str | None] = mapped_column(ForeignKey("form_mapping_releases.id"), index=True)
    context_type: Mapped[str] = mapped_column(String(50), nullable=False)
    context_id: Mapped[str] = mapped_column(String(36), nullable=False)
    resolved_values: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    resolved_assertion_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="DRAFT")
    invalidation_reason: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)


class GeneratedArtifact(Base, TimestampMixin):
    __tablename__ = "generated_artifacts"
    __table_args__ = (Index("ix_generated_artifact_instance", "form_instance_id"), Index("ix_generated_artifact_hash", "content_hash"))

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    form_instance_id: Mapped[str] = mapped_column(ForeignKey("form_instances.id"), nullable=False)
    source_document_version_id: Mapped[str] = mapped_column(ForeignKey("document_versions.id"), nullable=False)
    profile_id: Mapped[str] = mapped_column(ForeignKey("form_automation_profiles.id"), nullable=False)
    mapping_release_id: Mapped[str | None] = mapped_column(ForeignKey("form_mapping_releases.id"))
    renderer_version: Mapped[str] = mapped_column(String(60), nullable=False)
    artifact_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_path_or_reference: Mapped[str | None] = mapped_column(String(500))
    generated_payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    resolved_assertion_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)


class FormValidationResult(Base, TimestampMixin):
    __tablename__ = "form_validation_results"
    __table_args__ = (Index("ix_form_validation_artifact", "generated_artifact_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    generated_artifact_id: Mapped[str] = mapped_column(ForeignKey("generated_artifacts.id"), nullable=False)
    validation_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    result_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    validated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    validated_by: Mapped[str] = mapped_column(String(200), nullable=False)


class FormQARun(Base, TimestampMixin):
    __tablename__ = "form_qa_runs"
    __table_args__ = (Index("ix_form_qa_artifact", "generated_artifact_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    generated_artifact_id: Mapped[str] = mapped_column(ForeignKey("generated_artifacts.id"), nullable=False)
    mapping_release_id: Mapped[str | None] = mapped_column(ForeignKey("form_mapping_releases.id"), index=True)
    qa_type: Mapped[str] = mapped_column(String(50), nullable=False, default="STRUCTURAL_MAPPING")
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    result: Mapped[str] = mapped_column(String(30), nullable=False)
    checks_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    synthetic_only: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)


class FormMappingReleaseQAGate(Base, TimestampMixin):
    """Links an executed shared-runtime QA run to a release gate."""
    __tablename__ = "form_mapping_release_qa_gates"
    __table_args__ = (UniqueConstraint("mapping_release_id", "qa_run_id", "qa_type", name="uq_form_mapping_release_qa_gate"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    mapping_release_id: Mapped[str] = mapped_column(ForeignKey("form_mapping_releases.id"), nullable=False, index=True)
    qa_run_id: Mapped[str] = mapped_column(ForeignKey("form_qa_runs.id"), nullable=False, index=True)
    qa_type: Mapped[str] = mapped_column(String(50), nullable=False)
    required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class FormSignatureRequirement(Base, TimestampMixin):
    __tablename__ = "form_signature_requirements"
    __table_args__ = (Index("ix_form_signature_requirement_instance", "form_instance_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    form_instance_id: Mapped[str] = mapped_column(ForeignKey("form_instances.id"), nullable=False)
    logical_field_key: Mapped[str] = mapped_column(String(200), nullable=False)
    signer_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="REQUIRED")
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)


class SignaturePacket(Base, TimestampMixin):
    __tablename__ = "signature_packets"
    __table_args__ = (Index("ix_signature_packet_instance", "form_instance_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    form_instance_id: Mapped[str] = mapped_column(ForeignKey("form_instances.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="DRAFT")
    signer_refs: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)
