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
