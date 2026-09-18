"""Durable, hidden source-intake ledger for archive reconciliation."""

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, utcnow


def _id() -> str:
    return str(uuid4())


class SourceIntakeBatch(Base, TimestampMixin):
    __tablename__ = "source_intake_batches"
    __table_args__ = (UniqueConstraint("source_archive_hash", "source_location_reference", name="uq_source_intake_batch_source"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    source_kind: Mapped[str] = mapped_column(String(40), nullable=False, default="ZIP")
    source_display_name: Mapped[str] = mapped_column(String(300), nullable=False)
    source_archive_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source_location_reference: Mapped[str] = mapped_column(String(700), nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    received_by: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="DISCOVERED", index=True)
    item_count_discovered: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    empty_folder_count_observed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    manifest_version: Mapped[str | None] = mapped_column(String(40))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_summary: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class SourceIntakeItem(Base, TimestampMixin):
    __tablename__ = "source_intake_items"
    __table_args__ = (
        UniqueConstraint("batch_id", "source_ordinal", "original_relative_path", name="uq_source_intake_item_identity"),
        Index("ix_source_intake_item_batch_disposition", "batch_id", "disposition"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    batch_id: Mapped[str] = mapped_column(ForeignKey("source_intake_batches.id", ondelete="CASCADE"), nullable=False, index=True)
    source_ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    original_relative_path: Mapped[str] = mapped_column(String(700), nullable=False)
    original_filename: Mapped[str | None] = mapped_column(String(300))
    normalized_safe_path: Mapped[str] = mapped_column(String(700), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sha256: Mapped[str | None] = mapped_column(String(64), index=True)
    media_type: Mapped[str | None] = mapped_column(String(120))
    source_mtime: Mapped[str | None] = mapped_column(String(80))
    source_locator: Mapped[str | None] = mapped_column(String(900))
    disposition: Mapped[str | None] = mapped_column(String(50), index=True)
    disposition_reason: Mapped[str | None] = mapped_column(Text)
    duplicate_group: Mapped[str | None] = mapped_column(String(120), index=True)
    promotion_status: Mapped[str] = mapped_column(String(40), nullable=False, default="NOT_STARTED", index=True)
    target_master_content_id: Mapped[str | None] = mapped_column(ForeignKey("master_content_items.id"), index=True)
    target_document_version_id: Mapped[str | None] = mapped_column(ForeignKey("document_versions.id"), index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class ProposalSourceScan(Base, TimestampMixin):
    """Authoritative enumeration of one read-only Synology bridge scan."""

    __tablename__ = "proposal_source_scans"
    __table_args__ = (UniqueConstraint("source_identity", "scan_id", name="uq_proposal_source_scan_identity"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    scan_id: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    source_identity: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    source_root: Mapped[str] = mapped_column(String(700), nullable=False)
    source_project_identity: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    project_number: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="IN_PROGRESS", index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    bridge_machine_identity: Mapped[str | None] = mapped_column(String(200))
    signed_manifest_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    signature_b64: Mapped[str | None] = mapped_column(Text)
    directories_seen: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    files_seen: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_bytes_seen: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    files_successfully_captured: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    files_skipped_oversize: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    files_failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    files_unsupported: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    projects_unmapped: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class ProposalSourceScanEntry(Base, TimestampMixin):
    """Directory/file entry in a signed source scan, including no-payload files."""

    __tablename__ = "proposal_source_scan_entries"
    __table_args__ = (UniqueConstraint("scan_id", "relative_path", name="uq_proposal_source_scan_entry_path"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    scan_id: Mapped[str] = mapped_column(ForeignKey("proposal_source_scans.id", ondelete="CASCADE"), nullable=False, index=True)
    relative_path: Mapped[str] = mapped_column(String(700), nullable=False)
    entry_type: Mapped[str] = mapped_column(String(20), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    mtime_token: Mapped[str | None] = mapped_column(String(160))
    sha256: Mapped[str | None] = mapped_column(String(64), index=True)
    capture_status: Mapped[str] = mapped_column(String(40), nullable=False, default="PENDING", index=True)
    failure_reason: Mapped[str | None] = mapped_column(Text)
    source_version_token: Mapped[str | None] = mapped_column(String(160))
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
