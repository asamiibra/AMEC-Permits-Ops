"""Case-scoped party, representation, contact, and subject evidence.

These records extend the canonical Party/Property domains without creating a
Permit-local party truth.  Snapshots are immutable evidence for preparation
and historical reproduction; live role assignments remain changeable.
"""

from datetime import date, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, JSON, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, utcnow


def _id() -> str:
    return str(uuid4())


class AuthorityCaseSubject(Base):
    __tablename__ = "authority_case_subjects"
    __table_args__ = (UniqueConstraint("authority_case_id", name="uq_authority_case_subject_case"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    authority_case_id: Mapped[str] = mapped_column(ForeignKey("authority_cases.id"), nullable=False, index=True)
    subject_type: Mapped[str] = mapped_column(String(50), nullable=False)
    subject_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    subject_snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="CURRENT", nullable=False)
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class PartyRoleAssignment(Base):
    __tablename__ = "party_role_assignments"
    __table_args__ = (Index("ix_party_role_assignment_case_status", "authority_case_id", "status"), Index("ix_party_role_assignment_project_role", "project_id", "role_code", "status"))

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    authority_case_id: Mapped[str] = mapped_column(ForeignKey("authority_cases.id"), nullable=False, index=True)
    party_id: Mapped[str] = mapped_column(ForeignKey("parties.id"), nullable=False, index=True)
    role_code: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE", nullable=False)
    valid_from: Mapped[date | None] = mapped_column(Date)
    valid_until: Mapped[date | None] = mapped_column(Date)
    source_document_version_id: Mapped[str | None] = mapped_column(ForeignKey("document_versions.id"), index=True)
    source_kind: Mapped[str] = mapped_column(String(50), default="HUMAN_CONFIRMED", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    assigned_by: Mapped[str] = mapped_column(String(200), nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class AuthorizationGrant(Base):
    __tablename__ = "authorization_grants"
    __table_args__ = (Index("ix_authorization_grant_case_status", "authority_case_id", "status"), Index("ix_authorization_grant_scope", "grantor_party_id", "grantee_party_id", "status"))

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    authority_case_id: Mapped[str] = mapped_column(ForeignKey("authority_cases.id"), nullable=False, index=True)
    grantor_party_id: Mapped[str] = mapped_column(ForeignKey("parties.id"), nullable=False, index=True)
    grantee_party_id: Mapped[str] = mapped_column(ForeignKey("parties.id"), nullable=False, index=True)
    authorization_type: Mapped[str] = mapped_column(String(80), nullable=False)
    scope: Mapped[str] = mapped_column(Text, nullable=False)
    valid_from: Mapped[date | None] = mapped_column(Date)
    valid_until: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(30), default="PENDING", nullable=False)
    evidence_document_version_id: Mapped[str | None] = mapped_column(ForeignKey("document_versions.id"), index=True)
    verified_by: Mapped[str | None] = mapped_column(String(200))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class ContactPoint(Base):
    __tablename__ = "contact_points"
    __table_args__ = (Index("ix_contact_point_case_purpose", "authority_case_id", "purpose", "status"), Index("ix_contact_point_project_purpose", "project_id", "purpose", "status"))

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    authority_case_id: Mapped[str] = mapped_column(ForeignKey("authority_cases.id"), nullable=False, index=True)
    party_id: Mapped[str | None] = mapped_column(ForeignKey("parties.id"), index=True)
    purpose: Mapped[str] = mapped_column(String(60), nullable=False)
    channel: Mapped[str] = mapped_column(String(30), nullable=False)
    value: Mapped[str] = mapped_column(String(300), nullable=False)
    verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="PENDING_VERIFICATION", nullable=False)
    effective_from: Mapped[date | None] = mapped_column(Date)
    effective_until: Mapped[date | None] = mapped_column(Date)
    maintained_by: Mapped[str] = mapped_column(String(200), nullable=False)
    source_document_version_id: Mapped[str | None] = mapped_column(ForeignKey("document_versions.id"), index=True)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class CasePartySnapshot(Base):
    __tablename__ = "case_party_snapshots"
    __table_args__ = (Index("uq_case_party_snapshot_scope", "authority_case_id", "preparation_revision_id", "snapshot_number", unique=True, mssql_where=text("preparation_revision_id IS NOT NULL")), Index("ix_case_party_snapshot_case", "authority_case_id", "snapshot_number"))

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    authority_case_id: Mapped[str] = mapped_column(ForeignKey("authority_cases.id"), nullable=False, index=True)
    preparation_revision_id: Mapped[str | None] = mapped_column(ForeignKey("preparation_revisions.id"), index=True)
    snapshot_number: Mapped[int] = mapped_column(nullable=False, default=1)
    snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="IMMUTABLE", nullable=False)
    captured_by: Mapped[str] = mapped_column(String(200), nullable=False)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
