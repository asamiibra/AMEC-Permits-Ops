"""Scoped Handover and administrative closeout records.

These records deliberately separate delivery, acceptance, service closure,
contract administration, finance, regulatory assessment, and archive state.
They reference existing canonical domains and never replace them.
"""

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, utcnow


def _id() -> str:
    return str(uuid4())


class ServiceEngagement(Base):
    __tablename__ = "service_engagements"
    __table_args__ = (
        UniqueConstraint("project_id", "contract_id", "service_ref", name="uq_service_engagement_ref"),
        Index("ix_service_engagement_project_status", "project_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    contract_id: Mapped[str] = mapped_column(ForeignKey("contracts.id"), nullable=False, index=True)
    contract_revision_id: Mapped[str] = mapped_column(ForeignKey("contract_revisions.id"), nullable=False, index=True)
    proposal_scope_item_id: Mapped[str | None] = mapped_column(ForeignKey("proposal_service_scope_items.id"), index=True)
    service_ref: Mapped[str] = mapped_column(String(120), nullable=False)
    service_offering_code: Mapped[str] = mapped_column(String(100), nullable=False)
    scope_category_code: Mapped[str | None] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="ACTIVE")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class HandoverPolicyVersion(Base):
    __tablename__ = "handover_policy_versions"
    __table_args__ = (UniqueConstraint("policy_code", "version", name="uq_handover_policy_version"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    policy_code: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="DRAFT")
    required_renditions_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    distribution_rules_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    acceptance_rules_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    closeout_rules_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    source_document_version_id: Mapped[str | None] = mapped_column(ForeignKey("document_versions.id"), index=True)
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class HandoverPackage(Base):
    __tablename__ = "handover_packages"
    __table_args__ = (UniqueConstraint("service_engagement_id", "package_ref", name="uq_handover_package_ref"), Index("ix_handover_package_project_status", "project_id", "status"))

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    service_engagement_id: Mapped[str] = mapped_column(ForeignKey("service_engagements.id"), nullable=False, index=True)
    contract_id: Mapped[str] = mapped_column(ForeignKey("contracts.id"), nullable=False, index=True)
    package_ref: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="PREPARING")
    current_revision_id: Mapped[str | None] = mapped_column(String(36), index=True)
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class HandoverPackageRevision(Base):
    __tablename__ = "handover_package_revisions"
    __table_args__ = (UniqueConstraint("handover_package_id", "revision_number", name="uq_handover_package_revision_number"), Index("ix_handover_revision_state", "handover_package_id", "status"))

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    handover_package_id: Mapped[str] = mapped_column(ForeignKey("handover_packages.id"), nullable=False, index=True)
    service_engagement_id: Mapped[str] = mapped_column(ForeignKey("service_engagements.id"), nullable=False, index=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    contract_id: Mapped[str] = mapped_column(ForeignKey("contracts.id"), nullable=False, index=True)
    contract_revision_id: Mapped[str] = mapped_column(ForeignKey("contract_revisions.id"), nullable=False, index=True)
    policy_version_id: Mapped[str | None] = mapped_column(ForeignKey("handover_policy_versions.id"), index=True)
    authority_case_outcome_id: Mapped[str | None] = mapped_column(ForeignKey("authority_case_outcomes.id"), index=True)
    approved_design_baseline_id: Mapped[str | None] = mapped_column(ForeignKey("approved_design_baselines.id"), index=True)
    as_built_baseline_id: Mapped[str | None] = mapped_column(ForeignKey("as_built_baselines.id"), index=True)
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="DRAFT")
    manifest_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    participant_snapshot_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    punch_snapshot_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    distribution_snapshot_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    locked_by: Mapped[str | None] = mapped_column(String(200))
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class HandoverPackageItem(Base):
    __tablename__ = "handover_package_items"
    __table_args__ = (UniqueConstraint("handover_package_revision_id", "display_order", name="uq_handover_item_order"), Index("ix_handover_item_revision", "handover_package_revision_id", "status"))

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    handover_package_revision_id: Mapped[str] = mapped_column(ForeignKey("handover_package_revisions.id", ondelete="CASCADE"), nullable=False, index=True)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    item_type: Mapped[str] = mapped_column(String(80), nullable=False)
    discipline: Mapped[str | None] = mapped_column(String(100))
    label: Mapped[str] = mapped_column(String(240), nullable=False)
    required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    required_renditions_json: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    available_renditions_json: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    source_type: Mapped[str] = mapped_column(String(80), nullable=False)
    document_version_id: Mapped[str | None] = mapped_column(ForeignKey("document_versions.id"), index=True)
    rendered_artifact_id: Mapped[str | None] = mapped_column(ForeignKey("rendered_artifacts.id"), index=True)
    engineering_revision_id: Mapped[str | None] = mapped_column(ForeignKey("engineering_deliverable_revisions.id"), index=True)
    engineering_rendition_id: Mapped[str | None] = mapped_column(ForeignKey("engineering_renditions.id"), index=True)
    as_built_baseline_id: Mapped[str | None] = mapped_column(ForeignKey("as_built_baselines.id"), index=True)
    authority_case_id: Mapped[str | None] = mapped_column(ForeignKey("authority_cases.id"), index=True)
    form_instance_id: Mapped[str | None] = mapped_column(ForeignKey("form_instances.id"), index=True)
    source_ref: Mapped[str | None] = mapped_column(String(240))
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="MISSING")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class HandoverReadiness(Base):
    __tablename__ = "handover_readiness"
    __table_args__ = (UniqueConstraint("handover_package_revision_id", name="uq_handover_readiness_revision"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    handover_package_revision_id: Mapped[str] = mapped_column(ForeignKey("handover_package_revisions.id", ondelete="CASCADE"), nullable=False, index=True)
    state: Mapped[str] = mapped_column(String(40), nullable=False, default="NOT_READY")
    digital_ready: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    physical_ready: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    checks_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    evaluated_by: Mapped[str] = mapped_column(String(200), nullable=False)


class DistributionRequirement(Base):
    __tablename__ = "handover_distribution_requirements"
    __table_args__ = (Index("ix_handover_distribution_requirement_revision", "handover_package_revision_id", "status"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    handover_package_revision_id: Mapped[str] = mapped_column(ForeignKey("handover_package_revisions.id", ondelete="CASCADE"), nullable=False, index=True)
    recipient_party_id: Mapped[str | None] = mapped_column(ForeignKey("parties.id"), index=True)
    recipient_role: Mapped[str] = mapped_column(String(80), nullable=False)
    medium: Mapped[str] = mapped_column(String(50), nullable=False)
    copy_type: Mapped[str] = mapped_column(String(50), nullable=False, default="COPY")
    copy_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    item_ids_json: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    acknowledgement_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="REQUIRED")
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class HandoverDistribution(Base):
    __tablename__ = "handover_distributions"
    __table_args__ = (UniqueConstraint("idempotency_key", name="uq_handover_distribution_idempotency"), Index("ix_handover_distribution_revision_status", "handover_package_revision_id", "status"))

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    handover_package_revision_id: Mapped[str] = mapped_column(ForeignKey("handover_package_revisions.id"), nullable=False, index=True)
    distribution_requirement_id: Mapped[str | None] = mapped_column(ForeignKey("handover_distribution_requirements.id"), index=True)
    recipient_party_id: Mapped[str | None] = mapped_column(ForeignKey("parties.id"), index=True)
    recipient_role: Mapped[str] = mapped_column(String(80), nullable=False)
    medium: Mapped[str] = mapped_column(String(50), nullable=False)
    copy_type: Mapped[str] = mapped_column(String(50), nullable=False)
    copy_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    delivery_reference: Mapped[str | None] = mapped_column(String(240))
    evidence_document_version_id: Mapped[str | None] = mapped_column(ForeignKey("document_versions.id"), index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="PREPARED")
    delivered_by: Mapped[str | None] = mapped_column(String(200))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)


class HandoverReceipt(Base):
    __tablename__ = "handover_receipts"
    __table_args__ = (UniqueConstraint("distribution_id", name="uq_handover_receipt_distribution"), UniqueConstraint("idempotency_key", name="uq_handover_receipt_idempotency"))

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    distribution_id: Mapped[str] = mapped_column(ForeignKey("handover_distributions.id"), nullable=False, index=True)
    received_by_party_id: Mapped[str | None] = mapped_column(ForeignKey("parties.id"), index=True)
    received_by_ref: Mapped[str] = mapped_column(String(200), nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    evidence_document_version_id: Mapped[str | None] = mapped_column(ForeignKey("document_versions.id"), index=True)
    verification_status: Mapped[str] = mapped_column(String(30), nullable=False, default="RECORDED")
    recorded_by: Mapped[str] = mapped_column(String(200), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)


class HandoverParticipant(Base):
    __tablename__ = "handover_participants"
    __table_args__ = (UniqueConstraint("handover_package_revision_id", "participant_ref", "participant_role", name="uq_handover_participant"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    handover_package_revision_id: Mapped[str] = mapped_column(ForeignKey("handover_package_revisions.id", ondelete="CASCADE"), nullable=False, index=True)
    party_id: Mapped[str | None] = mapped_column(ForeignKey("parties.id"), index=True)
    participant_ref: Mapped[str] = mapped_column(String(200), nullable=False)
    participant_role: Mapped[str] = mapped_column(String(80), nullable=False)
    authority_snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    required_signer: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class HandoverPunchItem(Base):
    __tablename__ = "handover_punch_items"
    __table_args__ = (Index("ix_handover_punch_revision_status", "handover_package_revision_id", "status", "blocking"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    handover_package_revision_id: Mapped[str] = mapped_column(ForeignKey("handover_package_revisions.id"), nullable=False, index=True)
    package_item_id: Mapped[str | None] = mapped_column(ForeignKey("handover_package_items.id"), index=True)
    category: Mapped[str] = mapped_column(String(80), nullable=False, default="REMARK")
    remark: Mapped[str] = mapped_column(Text, nullable=False)
    blocking: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="OPEN")
    owner_ref: Mapped[str | None] = mapped_column(String(200))
    resolution: Mapped[str | None] = mapped_column(Text)
    resolution_evidence_document_version_id: Mapped[str | None] = mapped_column(ForeignKey("document_versions.id"), index=True)
    resolved_by: Mapped[str | None] = mapped_column(String(200))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class HandoverReleaseAuthorization(Base):
    __tablename__ = "handover_release_authorizations"
    __table_args__ = (UniqueConstraint("handover_package_revision_id", name="uq_handover_release_revision"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    handover_package_revision_id: Mapped[str] = mapped_column(ForeignKey("handover_package_revisions.id"), nullable=False, index=True)
    readiness_id: Mapped[str] = mapped_column(ForeignKey("handover_readiness.id"), nullable=False)
    authorized_by: Mapped[str] = mapped_column(String(200), nullable=False)
    authorized_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    delivery_plan_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)


class HandoverAcceptance(Base):
    __tablename__ = "handover_acceptances"
    __table_args__ = (UniqueConstraint("handover_package_revision_id", name="uq_handover_acceptance_revision"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    handover_package_revision_id: Mapped[str] = mapped_column(ForeignKey("handover_package_revisions.id"), nullable=False, index=True)
    acceptance_status: Mapped[str] = mapped_column(String(40), nullable=False)
    signed_form_document_version_id: Mapped[str | None] = mapped_column(ForeignKey("document_versions.id"), index=True)
    signature_packet_id: Mapped[str | None] = mapped_column(ForeignKey("signature_packets.id"), index=True)
    participant_snapshot_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    punch_snapshot_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    accepted_by_party_id: Mapped[str | None] = mapped_column(ForeignKey("parties.id"), index=True)
    evidence_reference: Mapped[str | None] = mapped_column(String(300))
    accepted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    recorded_by: Mapped[str] = mapped_column(String(200), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)


class ServiceScopeClosure(Base):
    __tablename__ = "service_scope_closures"
    __table_args__ = (UniqueConstraint("service_engagement_id", name="uq_service_scope_closure_engagement"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    service_engagement_id: Mapped[str] = mapped_column(ForeignKey("service_engagements.id"), nullable=False, index=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    contract_id: Mapped[str] = mapped_column(ForeignKey("contracts.id"), nullable=False, index=True)
    contract_revision_id: Mapped[str] = mapped_column(ForeignKey("contract_revisions.id"), nullable=False, index=True)
    handover_package_revision_id: Mapped[str] = mapped_column(ForeignKey("handover_package_revisions.id"), nullable=False)
    handover_acceptance_id: Mapped[str] = mapped_column(ForeignKey("handover_acceptances.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="CLOSED")
    closure_basis: Mapped[str] = mapped_column(String(120), nullable=False)
    closed_by: Mapped[str] = mapped_column(String(200), nullable=False)
    closed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)


class ContractAdministrativeClosure(Base):
    __tablename__ = "contract_administrative_closures"
    __table_args__ = (UniqueConstraint("contract_id", name="uq_contract_admin_closure_contract"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    contract_id: Mapped[str] = mapped_column(ForeignKey("contracts.id"), nullable=False, index=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    contract_revision_id: Mapped[str] = mapped_column(ForeignKey("contract_revisions.id"), nullable=False)
    service_closure_ids_json: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="CLOSED")
    closed_by: Mapped[str] = mapped_column(String(200), nullable=False)
    closed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    evidence_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)


class RegulatoryCloseoutAssessment(Base):
    __tablename__ = "regulatory_closeout_assessments"
    __table_args__ = (Index("uq_regulatory_closeout_scope", "project_id", "service_engagement_id", unique=True, mssql_where=text("service_engagement_id IS NOT NULL")),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    service_engagement_id: Mapped[str | None] = mapped_column(ForeignKey("service_engagements.id"), index=True)
    state: Mapped[str] = mapped_column(String(50), nullable=False, default="NEEDS_REVIEW")
    authority_case_ids_json: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    blocking_case_ids_json: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    assessment_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    assessed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    assessed_by: Mapped[str] = mapped_column(String(200), nullable=False)


class FinancialSettlementContext(Base):
    __tablename__ = "financial_settlement_contexts"
    __table_args__ = (UniqueConstraint("contract_id", "project_id", name="uq_financial_settlement_context_scope"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    contract_id: Mapped[str] = mapped_column(ForeignKey("contracts.id"), nullable=False, index=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    readiness_state: Mapped[str] = mapped_column(String(40), nullable=False, default="NEEDS_REVIEW")
    snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    unsupported_conditions_json: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    assessed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    assessed_by: Mapped[str] = mapped_column(String(200), nullable=False)


class FinancialSettlementRecord(Base):
    __tablename__ = "financial_settlement_records"
    __table_args__ = (UniqueConstraint("contract_id", "project_id", name="uq_financial_settlement_record_scope"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    contract_id: Mapped[str] = mapped_column(ForeignKey("contracts.id"), nullable=False, index=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    context_id: Mapped[str] = mapped_column(ForeignKey("financial_settlement_contexts.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="SETTLED")
    snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    settled_by: Mapped[str] = mapped_column(String(200), nullable=False)
    settled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    basis: Mapped[str] = mapped_column(Text, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)


class ProjectCloseoutPolicyVersion(Base):
    __tablename__ = "project_closeout_policy_versions"
    __table_args__ = (UniqueConstraint("policy_code", "version", name="uq_project_closeout_policy_version"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    policy_code: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="DRAFT")
    required_axes_json: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class ProjectCloseoutAssessment(Base):
    __tablename__ = "project_closeout_assessments"
    __table_args__ = (UniqueConstraint("project_id", name="uq_project_closeout_assessment_project"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    policy_version_id: Mapped[str | None] = mapped_column(ForeignKey("project_closeout_policy_versions.id"), index=True)
    service_scope_state: Mapped[str] = mapped_column(String(40), nullable=False, default="NEEDS_REVIEW")
    handover_state: Mapped[str] = mapped_column(String(40), nullable=False, default="NEEDS_REVIEW")
    regulatory_state: Mapped[str] = mapped_column(String(40), nullable=False, default="NEEDS_REVIEW")
    contract_admin_state: Mapped[str] = mapped_column(String(40), nullable=False, default="NEEDS_REVIEW")
    financial_state: Mapped[str] = mapped_column(String(40), nullable=False, default="NEEDS_REVIEW")
    archive_state: Mapped[str] = mapped_column(String(50), nullable=False, default="NEEDS_CLOSEOUT_POLICY")
    axes_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    assessed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    assessed_by: Mapped[str] = mapped_column(String(200), nullable=False)


class ProjectArchiveRecord(Base):
    __tablename__ = "project_archive_records"
    __table_args__ = (UniqueConstraint("project_id", name="uq_project_archive_project"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    assessment_id: Mapped[str] = mapped_column(ForeignKey("project_closeout_assessments.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="ARCHIVED")
    archived_by: Mapped[str] = mapped_column(String(200), nullable=False)
    archived_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
