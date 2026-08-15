"""Typed commercial/scoping companions for the BD Proposal workspace.

These records belong to a Proposal transaction. They reference canonical Party,
Property, Regulatory Core, Requirement Engine, and DocumentVersion records and
never become replacements for those shared domains.
"""

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, utcnow


def _id() -> str:
    return str(uuid4())


class ProposalContactContext(Base, TimestampMixin):
    __tablename__ = "proposal_contact_contexts"
    __table_args__ = (UniqueConstraint("proposal_id", name="uq_proposal_contact_context_proposal"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    proposal_id: Mapped[str] = mapped_column(ForeignKey("opportunities.id"), nullable=False, index=True)
    party_id: Mapped[str | None] = mapped_column(ForeignKey("parties.id"), index=True)
    display_name: Mapped[str | None] = mapped_column(String(240))
    email: Mapped[str | None] = mapped_column(String(240))
    mobile: Mapped[str | None] = mapped_column(String(80))
    purpose: Mapped[str] = mapped_column(String(50), nullable=False, default="PROPOSAL_CONTACT")
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="HUMAN_ENTERED")
    source_document_version_id: Mapped[str | None] = mapped_column(ForeignKey("document_versions.id"), index=True)
    notes: Mapped[str | None] = mapped_column(Text)


class ProposalSiteContext(Base, TimestampMixin):
    __tablename__ = "proposal_site_contexts"
    __table_args__ = (UniqueConstraint("proposal_id", name="uq_proposal_site_context_proposal"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    proposal_id: Mapped[str] = mapped_column(ForeignKey("opportunities.id"), nullable=False, index=True)
    property_id: Mapped[str | None] = mapped_column(ForeignKey("properties.id"), index=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="UNRESOLVED")
    location_text: Mapped[str | None] = mapped_column(String(300))
    plot_text: Mapped[str | None] = mapped_column(String(160))
    area_value: Mapped[float | None] = mapped_column(Float)
    area_unit: Mapped[str | None] = mapped_column(String(30))
    area_kind: Mapped[str] = mapped_column(String(50), nullable=False, default="LEGACY_UNSPECIFIED")
    site_description: Mapped[str | None] = mapped_column(Text)
    site_photo_source_link_id: Mapped[str | None] = mapped_column(String(36))
    source_document_version_id: Mapped[str | None] = mapped_column(ForeignKey("document_versions.id"), index=True)
    resolution_note: Mapped[str | None] = mapped_column(Text)
    resolved_by: Mapped[str | None] = mapped_column(String(200))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    historical_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class ProposalStakeholderIntent(Base, TimestampMixin):
    __tablename__ = "proposal_stakeholder_intents"
    __table_args__ = (Index("ix_proposal_stakeholder_proposal_status", "proposal_id", "status"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    proposal_id: Mapped[str] = mapped_column(ForeignKey("opportunities.id"), nullable=False, index=True)
    role_code: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    party_id: Mapped[str | None] = mapped_column(ForeignKey("parties.id"), index=True)
    display_snapshot: Mapped[str | None] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="UNKNOWN")
    source_type: Mapped[str] = mapped_column(String(40), nullable=False, default="HUMAN_ENTERED")
    source_document_version_id: Mapped[str | None] = mapped_column(ForeignKey("document_versions.id"), index=True)
    note: Mapped[str | None] = mapped_column(Text)


class ProposalSourceLink(Base, TimestampMixin):
    __tablename__ = "proposal_source_links"
    __table_args__ = (UniqueConstraint("proposal_id", "document_version_id", "source_role", name="uq_proposal_source_link_version_role"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    proposal_id: Mapped[str] = mapped_column(ForeignKey("opportunities.id"), nullable=False, index=True)
    source_evidence_id: Mapped[str | None] = mapped_column(ForeignKey("proposal_source_evidence.id"), index=True)
    document_id: Mapped[str | None] = mapped_column(ForeignKey("documents.id"), index=True)
    document_version_id: Mapped[str] = mapped_column(ForeignKey("document_versions.id"), nullable=False, index=True)
    source_role: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    added_by: Mapped[str] = mapped_column(String(200), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    note: Mapped[str | None] = mapped_column(Text)


class ProposalServiceScopeItem(Base, TimestampMixin):
    __tablename__ = "proposal_service_scope_items"
    __table_args__ = (Index("ix_proposal_service_scope_proposal_order", "proposal_id", "sort_order"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    proposal_id: Mapped[str] = mapped_column(ForeignKey("opportunities.id"), nullable=False, index=True)
    service_offering_code: Mapped[str | None] = mapped_column(String(100), index=True)
    scope_category_code: Mapped[str | None] = mapped_column(String(100))
    discipline_code: Mapped[str | None] = mapped_column(String(100), index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    included: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    commercial_treatment: Mapped[str] = mapped_column(String(40), nullable=False, default="AMEC_FEE")
    regulatory_service_type_id: Mapped[str | None] = mapped_column(ForeignKey("service_types.id"), index=True)
    external_body_id: Mapped[str | None] = mapped_column(ForeignKey("external_bodies.id"), index=True)
    source_document_version_id: Mapped[str | None] = mapped_column(ForeignKey("document_versions.id"), index=True)
    rationale: Mapped[str | None] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="DRAFT")


class ProposalRegulatoryScopeIntent(Base, TimestampMixin):
    __tablename__ = "proposal_regulatory_scope_intents"
    __table_args__ = (Index("ix_proposal_regulatory_scope_proposal_status", "proposal_id", "status"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    proposal_id: Mapped[str] = mapped_column(ForeignKey("opportunities.id"), nullable=False, index=True)
    proposal_scope_item_id: Mapped[str | None] = mapped_column(ForeignKey("proposal_service_scope_items.id"), index=True)
    external_body_id: Mapped[str | None] = mapped_column(ForeignKey("external_bodies.id"), index=True)
    service_type_id: Mapped[str | None] = mapped_column(ForeignKey("service_types.id"), index=True)
    service_type_version_id: Mapped[str | None] = mapped_column(ForeignKey("service_type_versions.id"), index=True)
    jurisdiction_id: Mapped[str | None] = mapped_column(ForeignKey("jurisdictions.id"), index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="DRAFT", index=True)
    source_type: Mapped[str] = mapped_column(String(40), nullable=False, default="HUMAN_ENTERED")
    source_document_version_id: Mapped[str | None] = mapped_column(ForeignKey("document_versions.id"), index=True)
    source_assertion_id: Mapped[str | None] = mapped_column(ForeignKey("verified_assertions.id"), index=True)
    rationale: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[float | None] = mapped_column(Float)
    human_confirmed_by: Mapped[str | None] = mapped_column(String(200))
    human_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)


class ProposalAssumption(Base, TimestampMixin):
    __tablename__ = "proposal_assumptions"
    __table_args__ = (Index("ix_proposal_assumption_proposal_status", "proposal_id", "status"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    proposal_id: Mapped[str] = mapped_column(ForeignKey("opportunities.id"), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(80), nullable=False)
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    materiality: Mapped[str] = mapped_column(String(30), nullable=False, default="INFORMATIONAL")
    source_type: Mapped[str] = mapped_column(String(40), nullable=False, default="HUMAN_ENTERED")
    source_reference: Mapped[str | None] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="OPEN")
    acknowledged_by: Mapped[str | None] = mapped_column(String(200))
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ProposalUnknown(Base, TimestampMixin):
    """A distinct unresolved fact; it is not an assumption or a generic issue."""

    __tablename__ = "proposal_unknowns"
    __table_args__ = (Index("ix_proposal_unknown_proposal_status", "proposal_id", "status"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    proposal_id: Mapped[str] = mapped_column(ForeignKey("opportunities.id"), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(80), nullable=False)
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    materiality: Mapped[str] = mapped_column(String(30), nullable=False, default="INFORMATIONAL")
    source_type: Mapped[str] = mapped_column(String(40), nullable=False, default="HUMAN_ENTERED")
    source_reference: Mapped[str | None] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="OPEN")
    resolution: Mapped[str | None] = mapped_column(Text)
    resolved_by: Mapped[str | None] = mapped_column(String(200))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ProposalConflict(Base, TimestampMixin):
    """Proposal-scoped source disagreement with both values retained."""

    __tablename__ = "proposal_conflicts"
    __table_args__ = (Index("ix_proposal_conflict_proposal_status", "proposal_id", "status"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    proposal_id: Mapped[str] = mapped_column(ForeignKey("opportunities.id"), nullable=False, index=True)
    field_code: Mapped[str] = mapped_column(String(100), nullable=False)
    source_a: Mapped[str] = mapped_column(String(300), nullable=False)
    value_a: Mapped[str | None] = mapped_column(Text)
    source_b: Mapped[str] = mapped_column(String(300), nullable=False)
    value_b: Mapped[str | None] = mapped_column(Text)
    materiality: Mapped[str] = mapped_column(String(30), nullable=False, default="MATERIAL")
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="OPEN")
    resolution: Mapped[str | None] = mapped_column(Text)
    resolver: Mapped[str | None] = mapped_column(String(200))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ProposalMaterialAcknowledgment(Base, TimestampMixin):
    """Human acceptance of commercial risk; acknowledgement is not resolution."""

    __tablename__ = "proposal_material_acknowledgments"
    __table_args__ = (UniqueConstraint("proposal_id", "target_type", "target_id", name="uq_proposal_material_ack_target"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    proposal_id: Mapped[str] = mapped_column(ForeignKey("opportunities.id"), nullable=False, index=True)
    target_type: Mapped[str] = mapped_column(String(40), nullable=False)
    target_id: Mapped[str] = mapped_column(String(36), nullable=False)
    target_revision_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    acknowledged_by: Mapped[str] = mapped_column(String(200), nullable=False)
    acknowledged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    note: Mapped[str | None] = mapped_column(Text)


class ProposalStalenessEvent(Base, TimestampMixin):
    """Material source/configuration change requiring Proposal review."""

    __tablename__ = "proposal_staleness_events"
    __table_args__ = (Index("ix_proposal_staleness_proposal_status", "proposal_id", "status"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    proposal_id: Mapped[str] = mapped_column(ForeignKey("opportunities.id"), nullable=False, index=True)
    trigger_type: Mapped[str] = mapped_column(String(80), nullable=False)
    trigger_reference: Mapped[str | None] = mapped_column(String(300))
    reason_code: Mapped[str] = mapped_column(String(100), nullable=False)
    impacted_sections: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="ACTIVE")
    detected_by: Mapped[str] = mapped_column(String(200), nullable=False)
    cleared_by: Mapped[str | None] = mapped_column(String(200))
    cleared_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ProposalRevision(Base):
    """Explicit mutable working revision created from an accepted revision."""

    __tablename__ = "proposal_revisions"
    __table_args__ = (UniqueConstraint("proposal_id", "revision_number", name="uq_proposal_revision_number"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    proposal_id: Mapped[str] = mapped_column(ForeignKey("opportunities.id"), nullable=False, index=True)
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    base_accepted_revision_id: Mapped[str | None] = mapped_column(String(36), index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="DRAFT")
    change_summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ProposalClientResponse(Base):
    """Recorded external commercial response, distinct from AMEC Accept."""

    __tablename__ = "proposal_client_responses"
    __table_args__ = (UniqueConstraint("idempotency_key", name="uq_proposal_client_response_idempotency"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    proposal_id: Mapped[str] = mapped_column(ForeignKey("opportunities.id"), nullable=False, index=True)
    accepted_revision_id: Mapped[str | None] = mapped_column(String(36), index=True)
    response_type: Mapped[str] = mapped_column(String(50), nullable=False)
    evidence_reference: Mapped[str | None] = mapped_column(String(600))
    notes: Mapped[str | None] = mapped_column(Text)
    recorded_by: Mapped[str] = mapped_column(String(200), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)


class ProposalCommercialOutcome(Base, TimestampMixin):
    """Commercial outcome kept separate from lifecycle lane and stage."""

    __tablename__ = "proposal_commercial_outcomes"
    __table_args__ = (UniqueConstraint("proposal_id", name="uq_proposal_commercial_outcome"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    proposal_id: Mapped[str] = mapped_column(ForeignKey("opportunities.id"), nullable=False, index=True)
    accepted_revision_id: Mapped[str | None] = mapped_column(String(36), index=True)
    outcome: Mapped[str] = mapped_column(String(50), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    evidence_reference: Mapped[str | None] = mapped_column(String(600))
    recorded_by: Mapped[str] = mapped_column(String(200), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class ProposalExternalCostAssumption(Base, TimestampMixin):
    __tablename__ = "proposal_external_cost_assumptions"
    __table_args__ = (Index("ix_proposal_external_cost_proposal", "proposal_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    proposal_id: Mapped[str] = mapped_column(ForeignKey("opportunities.id"), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    external_body_id: Mapped[str | None] = mapped_column(ForeignKey("external_bodies.id"), index=True)
    estimated_amount: Mapped[float | None] = mapped_column(Float)
    currency: Mapped[str | None] = mapped_column(String(20))
    treatment: Mapped[str] = mapped_column(String(40), nullable=False, default="ESTIMATE_ONLY")
    source_reference: Mapped[str | None] = mapped_column(String(300))
    rationale: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="OPEN")


class ProposalEngineeringContribution(Base, TimestampMixin):
    __tablename__ = "proposal_engineering_contributions"
    __table_args__ = (Index("ix_proposal_engineering_contribution_proposal", "proposal_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    proposal_id: Mapped[str] = mapped_column(ForeignKey("opportunities.id"), nullable=False, index=True)
    discipline_code: Mapped[str | None] = mapped_column(String(100), index=True)
    contribution_type: Mapped[str] = mapped_column(String(60), nullable=False, default="TECHNICAL_SCOPE")
    content: Mapped[str] = mapped_column(Text, nullable=False)
    technical_rule_set_version_id: Mapped[str | None] = mapped_column(ForeignKey("technical_rule_set_versions.id"), index=True)
    source_document_version_id: Mapped[str | None] = mapped_column(ForeignKey("document_versions.id"), index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="CONTRIBUTED")
    contributed_by: Mapped[str] = mapped_column(String(200), nullable=False)


class ProposalExpectedInputPreview(Base, TimestampMixin):
    __tablename__ = "proposal_expected_input_previews"
    __table_args__ = (Index("ix_proposal_expected_preview_proposal_created", "proposal_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    proposal_id: Mapped[str] = mapped_column(ForeignKey("opportunities.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    policy_version_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    scope_intent_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    result_items: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    evaluation_context: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    evaluated_by: Mapped[str] = mapped_column(String(200), nullable=False)
    superseded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)


class ProposalNote(Base, TimestampMixin):
    """Human-entered intake context; never promoted to external fact implicitly."""

    __tablename__ = "proposal_notes"
    __table_args__ = (Index("ix_proposal_notes_proposal_created", "proposal_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    proposal_id: Mapped[str] = mapped_column(ForeignKey("opportunities.id"), nullable=False, index=True)
    note_type: Mapped[str] = mapped_column(String(40), nullable=False, default="INTERNAL_INTAKE")
    content: Mapped[str] = mapped_column(Text, nullable=False)
    entered_by: Mapped[str] = mapped_column(String(200), nullable=False)
    related_contact: Mapped[str | None] = mapped_column(String(240))
    provenance: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="UNVERIFIED_CONTEXT")
