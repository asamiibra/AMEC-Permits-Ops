"""Project Engineering Drawing Review taxonomy and owner-facing artifacts.

Review categories are configured workflow classifications, not disciplines,
master-content categories, authority ServiceTypes, or global identity roles.
"""

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, utcnow


def _id() -> str:
    return str(uuid4())


class EngineeringReviewCategory(Base):
    __tablename__ = "engineering_review_categories"
    __table_args__ = (UniqueConstraint("code", name="uq_engineering_review_category_code"), Index("ix_engineering_review_category_active_order", "active", "sort_order"))

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    code: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    discipline: Mapped[str | None] = mapped_column(String(100))
    stage_class: Mapped[str | None] = mapped_column(String(100))
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    source_kind: Mapped[str] = mapped_column(String(50), default="OWNER_CONFIGURED", nullable=False)
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class EngineeringCategoryAssignment(Base):
    __tablename__ = "engineering_category_assignments"
    __table_args__ = (UniqueConstraint("project_id", "work_package_id", "review_category_id", name="uq_engineering_category_assignment_scope"), Index("ix_engineering_category_assignment_project_state", "project_id", "effective_state"))

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    work_package_id: Mapped[str | None] = mapped_column(ForeignKey("engineering_work_packages.id"), index=True)
    review_category_id: Mapped[str] = mapped_column(ForeignKey("engineering_review_categories.id"), nullable=False, index=True)
    assignee_actor: Mapped[str] = mapped_column(String(200), nullable=False)
    team: Mapped[str | None] = mapped_column(String(120))
    responsibility: Mapped[str] = mapped_column(String(120), nullable=False, default="ENGINEERING_REVIEW")
    capability: Mapped[str] = mapped_column(String(100), nullable=False, default="ENGINEERING_REVIEW")
    effective_state: Mapped[str] = mapped_column(String(40), nullable=False, default="ACTIVE")
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class EngineeringInternalReviewComment(Base):
    __tablename__ = "engineering_internal_review_comments"
    __table_args__ = (Index("ix_engineering_internal_review_comment_review", "review_id", "status"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    review_id: Mapped[str] = mapped_column(ForeignKey("project_engineering_reviews.id"), nullable=False, index=True)
    revision_id: Mapped[str] = mapped_column(ForeignKey("engineering_deliverable_revisions.id"), nullable=False, index=True)
    drawing_document_version_id: Mapped[str] = mapped_column(ForeignKey("document_versions.id"), nullable=False)
    comment_text: Mapped[str] = mapped_column(Text, nullable=False)
    location_reference: Mapped[str | None] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(40), default="OPEN", nullable=False)
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class EngineeringAICommentArtifact(Base):
    __tablename__ = "engineering_ai_comment_artifacts"
    __table_args__ = (Index("ix_engineering_ai_comment_artifact_review", "review_id", "generated_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    review_id: Mapped[str] = mapped_column(ForeignKey("project_engineering_reviews.id"), nullable=False, index=True)
    revision_id: Mapped[str] = mapped_column(ForeignKey("engineering_deliverable_revisions.id"), nullable=False)
    drawing_document_version_id: Mapped[str] = mapped_column(ForeignKey("document_versions.id"), nullable=False)
    artifact_type: Mapped[str] = mapped_column(String(80), default="AI_COMMENT_SUMMARY_REVIEW_DRAFT", nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="AI_ASSISTED_DRAFT", nullable=False)
    draft_text: Mapped[str] = mapped_column(Text, nullable=False)
    model_name: Mapped[str] = mapped_column(String(120), default="DETERMINISTIC_SYNTHETIC_REVIEW_ASSISTANT", nullable=False)
    model_version: Mapped[str] = mapped_column(String(80), default="ENGINEERING-DRAWING-REVIEW-1.0", nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(80), default="ENGINEERING-DRAWING-COMMENTS-1.0", nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    generated_by: Mapped[str] = mapped_column(String(200), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class EngineeringAuthorityFindingLink(Base):
    __tablename__ = "engineering_authority_finding_links"
    __table_args__ = (UniqueConstraint("authority_finding_id", "revision_id", name="uq_engineering_authority_finding_revision_link"), Index("ix_engineering_authority_link_project", "project_id", "status"))

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    review_id: Mapped[str] = mapped_column(ForeignKey("project_engineering_reviews.id"), nullable=False, index=True)
    revision_id: Mapped[str] = mapped_column(ForeignKey("engineering_deliverable_revisions.id"), nullable=False, index=True)
    review_category_id: Mapped[str | None] = mapped_column(ForeignKey("engineering_review_categories.id"), index=True)
    authority_finding_id: Mapped[str] = mapped_column(ForeignKey("authority_case_findings.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(40), default="LINKED", nullable=False)
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
