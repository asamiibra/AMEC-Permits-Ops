"""Owner-facing master/reference content and structured definitions."""

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, utcnow


def _id() -> str:
    return str(uuid4())


class MasterContentItem(Base, TimestampMixin):
    __tablename__ = "master_content_items"
    __table_args__ = (UniqueConstraint("content_type", "ref", name="uq_master_content_type_ref"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    ref: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    content_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    category_id: Mapped[str | None] = mapped_column(ForeignKey("content_categories.id"), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    used_in: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    engineering_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    source_type_code: Mapped[str | None] = mapped_column(String(80), index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="ACTIVE", index=True)
    # Small Owner-facing review overlay.  The underlying governance profile
    # remains available for internal controls, but it is not the Owner's
    # lifecycle taxonomy.
    needs_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    review_note: Mapped[str | None] = mapped_column(String(500))
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), nullable=False, unique=True)
    current_document_version_id: Mapped[str | None] = mapped_column(ForeignKey("document_versions.id"), index=True)
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)
    document: Mapped["Document"] = relationship(foreign_keys=[document_id])
    category: Mapped["ContentCategory | None"] = relationship()


class ContentCategory(Base):
    __tablename__ = "content_categories"
    __table_args__ = (UniqueConstraint("code", name="uq_content_category_code"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    code: Mapped[str] = mapped_column(String(80), nullable=False)
    label: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    allowed_content_types: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    source_kind: Mapped[str] = mapped_column(String(40), default="SYNTHETIC_CONFIGURABLE", nullable=False)


class MasterContentReferenceSequence(Base, TimestampMixin):
    __tablename__ = "master_content_reference_sequences"
    __table_args__ = (UniqueConstraint("content_type", "scope", name="uq_master_content_reference_sequence"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    content_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    prefix: Mapped[str] = mapped_column(String(20), nullable=False)
    padding: Mapped[int] = mapped_column(Integer, nullable=False, default=4)
    scope: Mapped[str] = mapped_column(String(80), nullable=False, default="GLOBAL")
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    current_value: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class MasterContentModuleBinding(Base, TimestampMixin):
    __tablename__ = "master_content_module_bindings"
    __table_args__ = (
        UniqueConstraint("master_content_id", "module", "usage_type", name="uq_master_content_module_binding"),
        UniqueConstraint("definition_id", "module", "usage_type", name="uq_definition_module_binding"),
        CheckConstraint("master_content_id IS NOT NULL OR definition_id IS NOT NULL", name="ck_binding_source_present"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    master_content_id: Mapped[str | None] = mapped_column(ForeignKey("master_content_items.id"), nullable=True, index=True)
    definition_id: Mapped[str | None] = mapped_column(ForeignKey("definition_entries.id"), nullable=True, index=True)
    module: Mapped[str] = mapped_column(String(40), nullable=False)
    usage_type: Mapped[str] = mapped_column(String(50), nullable=False, default="AVAILABLE")
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)


class DefinitionEntry(Base, TimestampMixin):
    __tablename__ = "definition_entries"
    __table_args__ = (UniqueConstraint("term", name="uq_definition_term"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    ref: Mapped[str | None] = mapped_column(String(100), index=True)
    term: Mapped[str] = mapped_column(String(240), nullable=False, index=True)
    category: Mapped[str | None] = mapped_column(String(100))
    used_in: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="ACTIVE", index=True)
    # Nullable pointer avoids a cyclic DDL dependency with DefinitionRevision;
    # the service enforces that it points to a revision of this entry.
    current_revision_id: Mapped[str | None] = mapped_column(String(36), index=True)
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)


class DefinitionRevision(Base):
    __tablename__ = "definition_revisions"
    __table_args__ = (UniqueConstraint("definition_id", "revision_number", name="uq_definition_revision_number"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    definition_id: Mapped[str] = mapped_column(ForeignKey("definition_entries.id"), nullable=False, index=True)
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    term: Mapped[str] = mapped_column(String(240), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str | None] = mapped_column(String(100))
    used_in: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    aliases: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    changed_by: Mapped[str] = mapped_column(String(200), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    change_reason: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="CURRENT")


class MasterContentIdempotency(Base):
    __tablename__ = "master_content_idempotency"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    master_content_id: Mapped[str] = mapped_column(ForeignKey("master_content_items.id"), nullable=False)
    document_version_id: Mapped[str] = mapped_column(ForeignKey("document_versions.id"), nullable=False)
    result_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class MasterContentChangeEvent(Base):
    """Global master-content material-change hook; project lineage remains separate."""
    __tablename__ = "master_content_change_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    master_content_id: Mapped[str | None] = mapped_column(ForeignKey("master_content_items.id"), index=True)
    definition_id: Mapped[str | None] = mapped_column(ForeignKey("definition_entries.id"), index=True)
    previous_version_id: Mapped[str | None] = mapped_column(String(36))
    new_version_id: Mapped[str] = mapped_column(String(36), nullable=False)
    change_type: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="APPLIED")
    correlation_id: Mapped[str] = mapped_column(String(100), nullable=False)
    actor_or_system: Mapped[str] = mapped_column(String(200), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, default="MASTER_CONTENT_VERSION_PROMOTED")
    content_type: Mapped[str | None] = mapped_column(String(40))
    business_ref: Mapped[str | None] = mapped_column(String(100))
    category_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    change_kind: Mapped[str | None] = mapped_column(String(40))
    change_reason: Mapped[str | None] = mapped_column(String(500))
    materiality: Mapped[str] = mapped_column(String(30), nullable=False, default="MATERIAL")
    source_hash: Mapped[str | None] = mapped_column(String(64))


class MasterContentDependency(Base, TimestampMixin):
    """Explicit, configured dependency; it never copies master-content bytes."""
    __tablename__ = "master_content_dependencies"
    __table_args__ = (UniqueConstraint("master_content_id", "downstream_type", "downstream_id", "dependency_kind", name="uq_master_content_dependency"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    master_content_id: Mapped[str] = mapped_column(ForeignKey("master_content_items.id"), nullable=False, index=True)
    bound_document_version_id: Mapped[str] = mapped_column(ForeignKey("document_versions.id"), nullable=False)
    expected_current_version_id: Mapped[str] = mapped_column(ForeignKey("document_versions.id"), nullable=False)
    downstream_type: Mapped[str] = mapped_column(String(100), nullable=False)
    downstream_id: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    project_id: Mapped[str | None] = mapped_column(ForeignKey("projects.id"), index=True)
    dependency_kind: Mapped[str] = mapped_column(String(80), nullable=False)
    policy: Mapped[str] = mapped_column(String(80), nullable=False, default="REVALIDATE_ON_CURRENT_CHANGE")
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="CURRENT")
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)


class MasterContentEventDelivery(Base):
    """Idempotency ledger for deterministic cross-module projections."""
    __tablename__ = "master_content_event_deliveries"
    __table_args__ = (UniqueConstraint("event_id", "delivery_type", "target_type", "target_id", "recipient_role", name="uq_master_content_event_delivery"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    event_id: Mapped[str] = mapped_column(ForeignKey("master_content_change_events.id"), nullable=False, index=True)
    delivery_type: Mapped[str] = mapped_column(String(60), nullable=False)
    target_type: Mapped[str] = mapped_column(String(100), nullable=False)
    target_id: Mapped[str] = mapped_column(String(160), nullable=False)
    recipient_role: Mapped[str] = mapped_column(String(80), nullable=False, default="-")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
