from datetime import date, datetime
from enum import Enum
from typing import Any
from uuid import uuid4
from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, utcnow


class Role(str, Enum):
    OWNER_SPONSOR = "OWNER_SPONSOR"
    PROCESS_CHAMPION = "PROCESS_CHAMPION"
    REQUIREMENT_STEWARD = "REQUIREMENT_STEWARD"
    RESPONSIBLE_ENGINEER = "RESPONSIBLE_ENGINEER"
    PERMIT_PREPARER = "PERMIT_PREPARER"
    FINAL_SUBMITTER = "FINAL_SUBMITTER"
    SYSTEM_ADMIN = "SYSTEM_ADMIN"


class ApplicationStatus(str, Enum):
    DRAFT = "DRAFT"
    PREPARING = "PREPARING"
    SUBMITTED = "SUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    RETURNED = "RETURNED"
    APPROVED = "APPROVED"


class SystemType(str, Enum):
    SYNOLOGY = "SYNOLOGY"
    EXCEL = "EXCEL"
    MUNICIPALITY = "MUNICIPALITY"


class DecisionStatus(str, Enum):
    CONFIRMED = "CONFIRMED"
    PROVISIONAL = "PROVISIONAL"
    UNKNOWN = "UNKNOWN"
    BLOCKED = "BLOCKED"


class InquiryStatus(str, Enum):
    NOT_ASKED = "NOT_ASKED"
    ASKED = "ASKED"
    ANSWERED = "ANSWERED"
    NO_RESPONSE = "NO_RESPONSE"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class RaidType(str, Enum):
    RISK = "RISK"
    ASSUMPTION = "ASSUMPTION"
    ISSUE = "ISSUE"
    DEPENDENCY = "DEPENDENCY"


class ConsultancyOffice(Base, TimestampMixin):
    __tablename__ = "consultancy_offices"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    office_code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
    )
    name_en: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    name_ar: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(30),
        default="ACTIVE",
        nullable=False,
    )
    users: Mapped[list["User"]] = relationship(
        back_populates="office",
    )
    projects: Mapped[list["Project"]] = relationship(
        back_populates="office",
    )


class User(Base, TimestampMixin):
    __tablename__ = "users"
    __table_args__ = (
        Index(
            "ix_users_entra_object_id",
            "entra_object_id",
            unique=True,
            mssql_where=text("entra_object_id IS NOT NULL"),
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # Immutable Microsoft Entra user identity. Authentication validates the
    # tenant separately; ProposalOps authorization binds the validated oid to
    # this application-controlled user record. Email, UPN, and display-name
    # claims must never be used as authorization keys.
    entra_object_id: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
    )

    email: Mapped[str] = mapped_column(
        String(200),
        unique=True,
        nullable=False,
    )
    display_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    role: Mapped[Role] = mapped_column(
        SAEnum(Role),
        nullable=False,
    )
    active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    office_id: Mapped[str] = mapped_column(
        ForeignKey("consultancy_offices.id"),
        nullable=False,
    )
    office: Mapped[ConsultancyOffice] = relationship(
        back_populates="users",
    )


class Project(Base, TimestampMixin):
    __tablename__ = "projects"
    __table_args__ = (
        Index(
            "ix_projects_project_code",
            "project_code",
            unique=True,
            mssql_where=text("project_code IS NOT NULL"),
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    project_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
    )
    project_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    office_id: Mapped[str] = mapped_column(
        ForeignKey("consultancy_offices.id"),
        nullable=False,
    )
    workstream: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    municipality: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    permit_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    assigned_engineer: Mapped[str | None] = mapped_column(
        String(200),
    )

    # Project Code is the controlled activation identity. project_number is
    # retained as the canonical Project/Opportunity reference for legacy and
    # permit consumers; the two values are intentionally separate.
    project_code: Mapped[str | None] = mapped_column(
        String(80),
    )
    start_date: Mapped[date | None] = mapped_column(
        Date,
    )
    activated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )
    activated_by: Mapped[str | None] = mapped_column(
        String(200),
    )
    office: Mapped[ConsultancyOffice] = relationship(
        back_populates="projects",
    )
    links: Mapped[list["ExternalSystemLink"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
    )
    applications: Mapped[list["PermitApplication"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
    )


class ExternalSystemLink(Base):
    __tablename__ = "external_system_links"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id"),
        nullable=False,
    )
    system_type: Mapped[SystemType] = mapped_column(
        SAEnum(SystemType),
        nullable=False,
    )
    external_reference: Mapped[str] = mapped_column(
        String(300),
        nullable=False,
    )
    display_reference: Mapped[str] = mapped_column(
        String(300),
        nullable=False,
    )
    active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False,
    )
    project: Mapped[Project] = relationship(
        back_populates="links",
    )


class PermitApplication(Base, TimestampMixin):
    __tablename__ = "permit_applications"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id"),
        nullable=False,
    )
    authority: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )
    municipality: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    permit_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    external_request_number: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
    )
    application_status: Mapped[ApplicationStatus] = mapped_column(
        SAEnum(ApplicationStatus),
        nullable=False,
    )
    repetition_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    last_status_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False,
    )
    controlling_contract_id: Mapped[str | None] = mapped_column(
        ForeignKey("contracts.id"),
        index=True,
    )

    # Durable workflow projection for the downstream permit workspace. Legacy
    # rows remain status-derived until a deliberate stage command writes this.
    workflow_stage: Mapped[str | None] = mapped_column(
        String(60),
        index=True,
    )
    project_sources_confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )
    project_sources_confirmed_by: Mapped[str | None] = mapped_column(
        String(120),
    )
    project: Mapped[Project] = relationship(
        back_populates="applications",
    )


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    correlation_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    actor_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    actor_id: Mapped[str | None] = mapped_column(
        String(36),
    )
    event_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    entity_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    entity_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    before_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
    )
    after_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False,
    )


class DiscoveryDecision(Base):
    __tablename__ = "discovery_decisions"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    key: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
    )
    status: Mapped[DecisionStatus] = mapped_column(
        SAEnum(DecisionStatus),
        nullable=False,
    )
    value_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
    )
    owner: Mapped[str | None] = mapped_column(
        String(200),
    )
    evidence_reference: Mapped[str | None] = mapped_column(
        String(300),
    )
    notes: Mapped[str | None] = mapped_column(
        Text,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
        nullable=False,
    )


class BusinessCase(Base):
    __tablename__ = "business_case"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    values_json: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
        nullable=False,
    )


class VolumeBaseline(Base):
    __tablename__ = "volume_baseline"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    values_json: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
        nullable=False,
    )


class MinistryInquiry(Base):
    __tablename__ = "ministry_inquiries"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    question_code: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
    )
    question: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    status: Mapped[InquiryStatus] = mapped_column(
        SAEnum(InquiryStatus),
        nullable=False,
    )
    client_owner: Mapped[str | None] = mapped_column(
        String(200),
    )
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )
    response_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )
    response_text: Mapped[str | None] = mapped_column(
        Text,
    )
    notes: Mapped[str | None] = mapped_column(
        Text,
    )


class RaidItem(Base):
    __tablename__ = "raid_items"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    type: Mapped[RaidType] = mapped_column(
        SAEnum(RaidType),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(
        String(300),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    severity: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )
    owner: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    mitigation: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    due_date: Mapped[date | None] = mapped_column(
        Date,
    )
    phase0_close_impact: Mapped[str] = mapped_column(
        String(30),
        default="NONE",
        nullable=False,
    )
