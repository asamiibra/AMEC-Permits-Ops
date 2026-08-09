from datetime import date, datetime
from enum import Enum
from typing import Any
from uuid import uuid4
from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base, utcnow


class FixtureStatus(str, Enum): ACTIVE_GOLDEN_PATH = "ACTIVE_GOLDEN_PATH"; ACTIVE = "ACTIVE"; SUPERSEDED = "SUPERSEDED"; TEST_ONLY = "TEST_ONLY"; UNIT_TEST_ONLY = "UNIT_TEST_ONLY"; DEPRECATED = "DEPRECATED"
class InitiationType(str, Enum): QUOTATION_ACCEPTED = "QUOTATION_ACCEPTED"; CLIENT_INSTRUCTION = "CLIENT_INSTRUCTION"; CONTRACT_AWARD = "CONTRACT_AWARD"; MANUAL_APPROVED_TRIGGER = "MANUAL_APPROVED_TRIGGER"
class InitiationStatus(str, Enum): RECEIVED = "RECEIVED"; COMPLETED = "COMPLETED"; REJECTED = "REJECTED"
class ReservationStatus(str, Enum): PROPOSED = "PROPOSED"; RESERVED = "RESERVED"; CONFIRMED = "CONFIRMED"; CONFLICT = "CONFLICT"; RELEASED = "RELEASED"
class OwnershipStatus(str, Enum): CURRENT = "CURRENT"; HISTORICAL = "HISTORICAL"; DISPUTED = "DISPUTED"
class PartyType(str, Enum): INDIVIDUAL = "INDIVIDUAL"; COMPANY = "COMPANY"; GOVERNMENT = "GOVERNMENT"; OTHER = "OTHER"
class AuthorizationStatus4(str, Enum): VALID = "VALID"; EXPIRED = "EXPIRED"; PENDING = "PENDING"; REVOKED = "REVOKED"
class RenderingStatus(str, Enum): PROVISIONAL = "PROVISIONAL"; ACTIVE = "ACTIVE"; RETIRED = "RETIRED"
class RenderingTarget(str, Enum): FORM = "FORM"; EXCEL = "EXCEL"; MUNICIPALITY = "MUNICIPALITY"
class ExcelOwnership(str, Enum): HUMAN_OWNED = "HUMAN_OWNED"; PERMITOPS_OWNED = "PERMITOPS_OWNED"; AUTHORITY_DERIVED = "AUTHORITY_DERIVED"; READ_ONLY_REFERENCE = "READ_ONLY_REFERENCE"


class SyntheticFixtureSet(Base):
    __tablename__ = "synthetic_fixture_sets"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    fixture_set_id: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    semantic_version: Mapped[str] = mapped_column(String(30), nullable=False)
    manifest_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    source_manifest_path: Mapped[str] = mapped_column(String(300), default="backend/app/fixtures/canonical.py", nullable=False)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    synthetic_only: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    golden_path_authority: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[FixtureStatus] = mapped_column(String(30), nullable=False)
    manifest_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    notes: Mapped[str] = mapped_column(Text, nullable=False)


class LegacyFixtureAlias(Base):
    __tablename__ = "legacy_fixture_aliases"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    legacy_id: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    canonical_id: Mapped[str] = mapped_column(String(160), nullable=False)
    purpose: Mapped[str] = mapped_column(String(200), nullable=False)
    temporary: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    remove_by: Mapped[date | None] = mapped_column(Date)
    classification: Mapped[str] = mapped_column(String(40), default="LEGACY_UNIT_TEST_ONLY", nullable=False)


class ProjectInitiation(Base):
    __tablename__ = "project_initiations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    initiation_type: Mapped[InitiationType] = mapped_column(String(40), nullable=False)
    initiation_reference: Mapped[str] = mapped_column(String(200), nullable=False)
    initiated_by: Mapped[str] = mapped_column(String(200), nullable=False)
    initiated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    status: Mapped[InitiationStatus] = mapped_column(String(30), nullable=False)
    project_id: Mapped[str | None] = mapped_column(ForeignKey("projects.id"))
    notes: Mapped[str | None] = mapped_column(Text)


class ProjectNumberReservation(Base):
    __tablename__ = "project_number_reservations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    proposed_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    status: Mapped[ReservationStatus] = mapped_column(String(30), nullable=False)
    reserved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_authority: Mapped[str] = mapped_column(String(100), nullable=False)
    initiation_id: Mapped[str | None] = mapped_column(ForeignKey("project_initiations.id"))
    project_id: Mapped[str | None] = mapped_column(ForeignKey("projects.id"))


class SynologyProjectBootstrap(Base):
    __tablename__ = "synology_project_bootstraps"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), unique=True, nullable=False)
    root_path: Mapped[str] = mapped_column(String(400), nullable=False)
    subfolders_json: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    template_applied: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    template_manifest_json: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)


class ExcelProjectRow(Base):
    __tablename__ = "excel_project_rows"
    __table_args__ = (UniqueConstraint("workbook_identity", "sheet_name", "row_key", name="uq_excel_project_row_identity"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), unique=True, nullable=False)
    workbook_identity: Mapped[str] = mapped_column(String(300), nullable=False)
    sheet_name: Mapped[str] = mapped_column(String(120), nullable=False)
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    row_key: Mapped[str] = mapped_column(String(150), nullable=False)
    ownership_matrix_json: Mapped[dict[str, str]] = mapped_column(JSON, nullable=False)
    human_cells_fingerprint: Mapped[str | None] = mapped_column(String(64))
    projection_sheet: Mapped[str] = mapped_column(String(120), nullable=False)
    read_policy: Mapped[str] = mapped_column(String(200), nullable=False)
    write_policy: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)


class ExcelProjectionRule(Base):
    __tablename__ = "excel_projection_rules"
    __table_args__ = (UniqueConstraint("scenario_id", "sheet_name", "target_column", name="uq_excel_projection_rule"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    scenario_id: Mapped[str] = mapped_column(ForeignKey("scenario_configs.id"), nullable=False)
    sheet_name: Mapped[str] = mapped_column(String(120), nullable=False)
    row_key_rule: Mapped[str] = mapped_column(String(200), nullable=False)
    target_column: Mapped[str] = mapped_column(String(120), nullable=False)
    ownership: Mapped[ExcelOwnership] = mapped_column(String(40), nullable=False)
    source_field: Mapped[str] = mapped_column(String(120), nullable=False)
    rendering_rule_id: Mapped[str | None] = mapped_column(String(36))
    write_allowed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class Property(Base):
    __tablename__ = "properties"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    pin: Mapped[str] = mapped_column(String(100), nullable=False)
    plot_number: Mapped[str] = mapped_column(String(100), nullable=False)
    zone: Mapped[str | None] = mapped_column(String(100))
    municipality: Mapped[str] = mapped_column(String(100), nullable=False)
    plan_reference: Mapped[str | None] = mapped_column(String(100))
    land_area: Mapped[float | None] = mapped_column(Float)
    land_area_unit: Mapped[str | None] = mapped_column(String(20))
    source_document_version_id: Mapped[str | None] = mapped_column(ForeignKey("document_versions.id"))
    source_observation_id: Mapped[str | None] = mapped_column(ForeignKey("field_observations.id"))
    source_assertion_id: Mapped[str | None] = mapped_column(ForeignKey("verified_assertions.id"))
    status: Mapped[OwnershipStatus] = mapped_column(String(30), default=OwnershipStatus.CURRENT, nullable=False)


class Party(Base):
    __tablename__ = "parties"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    party_type: Mapped[PartyType] = mapped_column(String(30), nullable=False)
    name_ar: Mapped[str | None] = mapped_column(String(300))
    name_en: Mapped[str | None] = mapped_column(String(300))
    identifier_type: Mapped[str | None] = mapped_column(String(30))
    identifier_value: Mapped[str | None] = mapped_column(String(100))
    source_document_version_id: Mapped[str | None] = mapped_column(ForeignKey("document_versions.id"))
    status: Mapped[OwnershipStatus] = mapped_column(String(30), default=OwnershipStatus.CURRENT, nullable=False)


class PropertyOwnership(Base):
    __tablename__ = "property_ownerships"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    property_id: Mapped[str] = mapped_column(ForeignKey("properties.id"), nullable=False)
    party_id: Mapped[str] = mapped_column(ForeignKey("parties.id"), nullable=False)
    share_numerator: Mapped[int | None] = mapped_column(Integer)
    share_denominator: Mapped[int | None] = mapped_column(Integer)
    normalized_share: Mapped[float] = mapped_column(Float, nullable=False)
    valid_from: Mapped[date | None] = mapped_column(Date)
    valid_until: Mapped[date | None] = mapped_column(Date)
    source_document_version_id: Mapped[str | None] = mapped_column(ForeignKey("document_versions.id"))
    source_assertion_id: Mapped[str | None] = mapped_column(ForeignKey("verified_assertions.id"))
    status: Mapped[OwnershipStatus] = mapped_column(String(30), default=OwnershipStatus.CURRENT, nullable=False)


class Representation(Base):
    __tablename__ = "representations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    principal_party_id: Mapped[str] = mapped_column(ForeignKey("parties.id"), nullable=False)
    representative_party_id: Mapped[str] = mapped_column(ForeignKey("parties.id"), nullable=False)
    authorization_type: Mapped[str] = mapped_column(String(100), nullable=False)
    scope: Mapped[str] = mapped_column(Text, nullable=False)
    valid_from: Mapped[date | None] = mapped_column(Date)
    valid_until: Mapped[date | None] = mapped_column(Date)
    evidence_document_version_id: Mapped[str | None] = mapped_column(ForeignKey("document_versions.id"))
    authorization_id: Mapped[str | None] = mapped_column(ForeignKey("authorizations.id"))
    status: Mapped[AuthorizationStatus4] = mapped_column(String(30), nullable=False)


class Authorization(Base):
    __tablename__ = "authorizations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    principal_party_id: Mapped[str] = mapped_column(ForeignKey("parties.id"), nullable=False)
    representative_party_id: Mapped[str] = mapped_column(ForeignKey("parties.id"), nullable=False)
    authorization_type: Mapped[str] = mapped_column(String(100), nullable=False)
    scope: Mapped[str] = mapped_column(Text, nullable=False)
    valid_from: Mapped[date | None] = mapped_column(Date)
    valid_until: Mapped[date | None] = mapped_column(Date)
    evidence_document_version_id: Mapped[str | None] = mapped_column(ForeignKey("document_versions.id"))
    status: Mapped[AuthorizationStatus4] = mapped_column(String(30), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)


class TargetRenderingRule(Base):
    __tablename__ = "target_rendering_rules"
    __table_args__ = (UniqueConstraint("scenario_id", "field_definition_id", "target_system", "version", name="uq_target_rendering_rule"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    scenario_id: Mapped[str] = mapped_column(ForeignKey("scenario_configs.id"), nullable=False)
    field_definition_id: Mapped[str] = mapped_column(ForeignKey("field_definitions.id"), nullable=False)
    target_system: Mapped[RenderingTarget] = mapped_column(String(30), nullable=False)
    target_location: Mapped[str] = mapped_column(String(200), nullable=False)
    format_rule: Mapped[str | None] = mapped_column(String(200))
    language_rule: Mapped[str | None] = mapped_column(String(100))
    unit_rule: Mapped[str | None] = mapped_column(String(100))
    dropdown_code_map: Mapped[dict[str, str]] = mapped_column(JSON, default=dict, nullable=False)
    null_behavior: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[RenderingStatus] = mapped_column(String(30), nullable=False)
