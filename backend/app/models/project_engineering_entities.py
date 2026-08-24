"""Project-scoped engineering deliverables and approved design baselines.

These tables deliberately keep business revision identity separate from the
canonical DocumentVersion binary identity.  They are additive companions to
the existing Project, Party, Property, TechnicalRule, Requirement, Audit and
Lineage domains.
"""

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, utcnow


def _id() -> str:
    return str(uuid4())


class EngineeringProjectMember(Base):
    __tablename__ = "engineering_project_members"
    __table_args__ = (UniqueConstraint("project_id", "actor_id", name="uq_engineering_project_member"), Index("ix_engineering_member_project", "project_id", "status"))
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    actor_id: Mapped[str] = mapped_column(String(200), nullable=False)
    capability: Mapped[str] = mapped_column(String(80), nullable=False, default="ENGINEERING_EDIT")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="ACTIVE")
    added_by: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class EngineeringWorkPackage(Base):
    __tablename__ = "engineering_work_packages"
    __table_args__ = (UniqueConstraint("project_id", "package_ref", name="uq_engineering_work_package_ref"), Index("ix_engineering_work_package_project", "project_id", "status"), Index("engineering_work_packages_idempotency_key_key", "idempotency_key", unique=True, mssql_where=text("idempotency_key IS NOT NULL")))
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    package_ref: Mapped[str] = mapped_column(String(120), nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    discipline: Mapped[str] = mapped_column(String(80), nullable=False, default="GENERAL")
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="OPEN")
    owner_actor: Mapped[str] = mapped_column(String(200), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    idempotency_key: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class EngineeringDeliverable(Base):
    __tablename__ = "engineering_deliverables"
    __table_args__ = (UniqueConstraint("work_package_id", "deliverable_ref", name="uq_engineering_deliverable_ref"), Index("ix_engineering_deliverable_project", "project_id", "status"), Index("ix_engineering_deliverable_discipline", "discipline"))
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    work_package_id: Mapped[str] = mapped_column(ForeignKey("engineering_work_packages.id"), nullable=False)
    deliverable_ref: Mapped[str] = mapped_column(String(120), nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    discipline: Mapped[str] = mapped_column(String(80), nullable=False, default="GENERAL")
    deliverable_type: Mapped[str] = mapped_column(String(80), nullable=False, default="ENGINEERING_DOCUMENT")
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="DRAFT")
    current_revision_id: Mapped[str | None] = mapped_column(ForeignKey("engineering_deliverable_revisions.id"), index=True)
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class EngineeringDeliverableRevision(Base):
    __tablename__ = "engineering_deliverable_revisions"
    __table_args__ = (UniqueConstraint("deliverable_id", "revision_code", name="uq_engineering_deliverable_revision"), UniqueConstraint("deliverable_id", "sequence", name="uq_engineering_deliverable_revision_sequence"), Index("ix_engineering_revision_status", "status", "approval_status"), Index("ix_engineering_revision_deliverable", "deliverable_id", "sequence"), Index("engineering_deliverable_revisions_idempotency_key_key", "idempotency_key", unique=True, mssql_where=text("idempotency_key IS NOT NULL")))
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    deliverable_id: Mapped[str] = mapped_column(ForeignKey("engineering_deliverables.id"), nullable=False)
    revision_code: Mapped[str] = mapped_column(String(40), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    issue_purpose: Mapped[str] = mapped_column(String(100), nullable=False, default="FOR_REVIEW")
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="DRAFT")
    approval_status: Mapped[str] = mapped_column(String(40), nullable=False, default="NOT_APPROVED")
    prepared_by: Mapped[str] = mapped_column(String(200), nullable=False)
    supersedes_revision_id: Mapped[str | None] = mapped_column(ForeignKey("engineering_deliverable_revisions.id"))
    immutable_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    idempotency_key: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class EngineeringRendition(Base):
    __tablename__ = "engineering_renditions"
    __table_args__ = (UniqueConstraint("revision_id", "rendition_kind", name="uq_engineering_rendition_kind"), Index("ix_engineering_rendition_document", "document_version_id"))
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    revision_id: Mapped[str] = mapped_column(ForeignKey("engineering_deliverable_revisions.id"), nullable=False)
    document_version_id: Mapped[str] = mapped_column(ForeignKey("document_versions.id"), nullable=False)
    rendition_kind: Mapped[str] = mapped_column(String(30), nullable=False)  # NATIVE or PUBLISHED
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    renderer_type: Mapped[str | None] = mapped_column(String(80))
    renderer_version: Mapped[str | None] = mapped_column(String(80))
    source_rendition_id: Mapped[str | None] = mapped_column(ForeignKey("engineering_renditions.id"))
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class ProjectEngineeringReview(Base):
    __tablename__ = "project_engineering_reviews"
    __table_args__ = (Index("ix_project_engineering_review_revision", "revision_id", "status"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    revision_id: Mapped[str] = mapped_column(ForeignKey("engineering_deliverable_revisions.id"), nullable=False)
    review_category_id: Mapped[str | None] = mapped_column(ForeignKey("engineering_review_categories.id"), index=True)
    review_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="OPEN")
    started_by: Mapped[str] = mapped_column(String(200), nullable=False)
    completed_by: Mapped[str | None] = mapped_column(String(200))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class EngineeringReviewFinding(Base):
    __tablename__ = "engineering_review_findings"
    __table_args__ = (Index("ix_engineering_finding_review", "review_id", "status", "severity"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    review_id: Mapped[str] = mapped_column(ForeignKey("project_engineering_reviews.id"), nullable=False)
    finding_ref: Mapped[str] = mapped_column(String(80), nullable=False)
    severity: Mapped[str] = mapped_column(String(30), nullable=False, default="MAJOR")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="OPEN")
    description: Mapped[str] = mapped_column(Text, nullable=False)
    response: Mapped[str | None] = mapped_column(Text)
    disposition_by: Mapped[str | None] = mapped_column(String(200))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class EngineeringProfessionalApproval(Base):
    __tablename__ = "engineering_professional_approvals"
    __table_args__ = (UniqueConstraint("revision_id", "approval_type", name="uq_engineering_professional_approval"), Index("ix_engineering_approval_revision", "revision_id", "status"))
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    revision_id: Mapped[str] = mapped_column(ForeignKey("engineering_deliverable_revisions.id"), nullable=False)
    approval_type: Mapped[str] = mapped_column(String(60), nullable=False, default="PROFESSIONAL_DESIGN_REVIEW")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="APPROVED")
    approver_actor: Mapped[str] = mapped_column(String(200), nullable=False)
    approver_party_id: Mapped[str | None] = mapped_column(ForeignKey("parties.id"), index=True)
    professional_credential_id: Mapped[str | None] = mapped_column(ForeignKey("professional_credentials.id"), index=True)
    credential_reference: Mapped[str] = mapped_column(String(240), nullable=False)
    pinned_rendition_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    approved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reason: Mapped[str | None] = mapped_column(Text)


class EngineeringTechnicalCheck(Base):
    __tablename__ = "engineering_technical_checks"
    __table_args__ = (Index("ix_engineering_technical_check_revision", "revision_id", "result"), Index("ix_engineering_technical_check_rule_set", "technical_rule_set_version_id"))
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    revision_id: Mapped[str] = mapped_column(ForeignKey("engineering_deliverable_revisions.id"), nullable=False)
    technical_rule_set_version_id: Mapped[str] = mapped_column(ForeignKey("technical_rule_set_versions.id"), nullable=False)
    technical_rule_id: Mapped[str | None] = mapped_column(ForeignKey("technical_rules.id"), index=True)
    result: Mapped[str] = mapped_column(String(20), nullable=False)  # PASS, FAIL, UNKNOWN
    inputs_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    calculated_values_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    rule_version: Mapped[str] = mapped_column(String(40), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    evaluated_by: Mapped[str] = mapped_column(String(200), nullable=False, default="DETERMINISTIC_ENGINE")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class EngineeringCalculationRecord(Base):
    __tablename__ = "engineering_calculation_records"
    __table_args__ = (Index("ix_engineering_calculation_revision", "revision_id"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    revision_id: Mapped[str] = mapped_column(ForeignKey("engineering_deliverable_revisions.id"), nullable=False)
    technical_rule_set_version_id: Mapped[str] = mapped_column(ForeignKey("technical_rule_set_versions.id"), nullable=False)
    input_values_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    normalized_units_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    result_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    result_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class EngineeringMaterialTest(Base):
    __tablename__ = "engineering_material_tests"
    __table_args__ = (Index("ix_engineering_material_test_project", "project_id", "status"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    revision_id: Mapped[str | None] = mapped_column(ForeignKey("engineering_deliverable_revisions.id"))
    material_code: Mapped[str] = mapped_column(String(120), nullable=False)
    test_type: Mapped[str] = mapped_column(String(120), nullable=False)
    result_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    certificate_document_version_id: Mapped[str | None] = mapped_column(ForeignKey("document_versions.id"))
    laboratory_party_id: Mapped[str | None] = mapped_column(ForeignKey("parties.id"))
    accreditation_evidence_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="RECORDED")
    accepted_by: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class ApprovedDesignBaseline(Base):
    __tablename__ = "approved_design_baselines"
    __table_args__ = (UniqueConstraint("project_id", "purpose", "baseline_ref", name="uq_approved_design_baseline_ref"), Index("ix_approved_design_baseline_project", "project_id", "purpose", "status"))
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    baseline_ref: Mapped[str] = mapped_column(String(120), nullable=False)
    purpose: Mapped[str] = mapped_column(String(80), nullable=False, default="AMEC_APPROVED_DESIGN")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="CANDIDATE")
    manifest_hash: Mapped[str | None] = mapped_column(String(64))
    manifest_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    validation_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    approved_by: Mapped[str | None] = mapped_column(String(200))
    approval_credential_reference: Mapped[str | None] = mapped_column(String(240))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    supersedes_baseline_id: Mapped[str | None] = mapped_column(ForeignKey("approved_design_baselines.id"))
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class ApprovedDesignBaselineMember(Base):
    __tablename__ = "approved_design_baseline_members"
    __table_args__ = (UniqueConstraint("baseline_id", "revision_id", "rendition_id", name="uq_approved_design_baseline_member"), Index("ix_approved_design_baseline_member_baseline", "baseline_id"))
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    baseline_id: Mapped[str] = mapped_column(ForeignKey("approved_design_baselines.id"), nullable=False)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    revision_id: Mapped[str] = mapped_column(ForeignKey("engineering_deliverable_revisions.id"), nullable=False)
    rendition_id: Mapped[str] = mapped_column(ForeignKey("engineering_renditions.id"), nullable=False)
    member_role: Mapped[str] = mapped_column(String(80), nullable=False, default="APPROVED_DESIGN_INPUT")
    pinned_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class DesignChangeRequest(Base):
    __tablename__ = "design_change_requests"
    __table_args__ = (UniqueConstraint("project_id", "change_ref", name="uq_design_change_ref"), Index("ix_design_change_project_status", "project_id", "status"))
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    change_ref: Mapped[str] = mapped_column(String(120), nullable=False)
    from_baseline_id: Mapped[str] = mapped_column(ForeignKey("approved_design_baselines.id"), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    regulatory_impact: Mapped[str] = mapped_column(String(30), nullable=False, default="UNKNOWN")
    commercial_impact: Mapped[str] = mapped_column(String(30), nullable=False, default="UNKNOWN")
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="DRAFT")
    linked_revision_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    next_baseline_id: Mapped[str | None] = mapped_column(ForeignKey("approved_design_baselines.id"))
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)
    approved_to_proceed_by: Mapped[str | None] = mapped_column(String(200))
    implemented_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
