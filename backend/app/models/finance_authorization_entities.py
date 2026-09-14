"""Persisted, scoped Finance capability assignments."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, utcnow


class ScopedCapabilityAssignment(Base, TimestampMixin):
    """Explicit human capability grant; never inferred from a global Role."""

    __tablename__ = "scoped_capability_assignments"
    __table_args__ = (
        CheckConstraint(
            "office_id IS NOT NULL OR client_account_id IS NOT NULL OR project_id IS NOT NULL",
            name="ck_scoped_assignment_non_empty_scope",
        ),
        CheckConstraint(
            "effective_to IS NULL OR effective_to >= effective_from",
            name="ck_scoped_assignment_effective_interval",
        ),
        CheckConstraint(
            "status IN ('ACTIVE', 'REVOKED', 'EXPIRED')",
            name="ck_scoped_assignment_status",
        ),
        Index("ix_scoped_capability_assignments_user_capability", "user_id", "capability_code"),
        Index("ix_scoped_capability_assignments_project_status", "project_id", "status"),
        Index("ix_scoped_capability_assignments_client_status", "client_account_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    capability_code: Mapped[str] = mapped_column(String(120), nullable=False)
    office_id: Mapped[str | None] = mapped_column(ForeignKey("consultancy_offices.id"), index=True)
    client_account_id: Mapped[str | None] = mapped_column(ForeignKey("client_accounts.id"), index=True)
    project_id: Mapped[str | None] = mapped_column(ForeignKey("projects.id"), index=True)
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE", nullable=False)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    assignment_reference: Mapped[str] = mapped_column(String(200), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_reference: Mapped[str | None] = mapped_column(String(300))
    granted_by: Mapped[str] = mapped_column(String(36), nullable=False)
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    revoked_by: Mapped[str | None] = mapped_column(String(36))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class GovernedSignatoryAuthority(Base, TimestampMixin):
    """Reusable, effective-dated human signatory authority evidence."""

    __tablename__ = "governed_signatory_authorities"
    __table_args__ = (
        CheckConstraint("effective_to IS NULL OR effective_to >= effective_from", name="ck_signatory_authority_effective_interval"),
        CheckConstraint("status IN ('PENDING_APPROVAL', 'ACTIVE', 'REVOKED', 'EXPIRED', 'SUPERSEDED')", name="ck_signatory_authority_status"),
        Index("ix_signatory_authority_user_status", "user_id", "status"),
        Index("ix_signatory_authority_entity_status", "legal_entity_ref", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    office_id: Mapped[str] = mapped_column(ForeignKey("consultancy_offices.id"), nullable=False, index=True)
    legal_entity_ref: Mapped[str] = mapped_column(String(160), nullable=False)
    capacity: Mapped[str] = mapped_column(String(120), nullable=False)
    authority_type: Mapped[str] = mapped_column(String(120), nullable=False)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(30), default="PENDING_APPROVAL", nullable=False)
    owner_authorization_reference: Mapped[str] = mapped_column(String(240), nullable=False)
    authority_evidence_document_version_id: Mapped[str | None] = mapped_column(ForeignKey("document_versions.id"), index=True)
    authority_evidence_reference: Mapped[str | None] = mapped_column(String(500))
    created_by: Mapped[str] = mapped_column(String(36), nullable=False)
    approved_by: Mapped[str | None] = mapped_column(String(36))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_by: Mapped[str | None] = mapped_column(String(36))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    superseded_by_id: Mapped[str | None] = mapped_column(String(36))
