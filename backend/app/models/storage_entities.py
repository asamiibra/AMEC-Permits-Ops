from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, utcnow


class StorageOperation(Base):
    """Durable journal for the non-ACID SMB/PostgreSQL boundary."""

    __tablename__ = "storage_operations"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_storage_operation_idempotency"),
        Index("ix_storage_operation_state", "state"),
        Index("ix_storage_operation_document_version", "document_version_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    idempotency_key: Mapped[str] = mapped_column(String(240), nullable=False)
    operation_type: Mapped[str] = mapped_column(String(60), nullable=False, default="STORE_DOCUMENT_VERSION")
    document_id: Mapped[str | None] = mapped_column(ForeignKey("documents.id"), index=True)
    document_version_id: Mapped[str | None] = mapped_column(String(36), index=True)
    provider_id: Mapped[str] = mapped_column(String(100), nullable=False)
    target_locator: Mapped[str] = mapped_column(String(900), nullable=False)
    temporary_locator: Mapped[str | None] = mapped_column(String(900))
    expected_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    expected_size: Mapped[int] = mapped_column(Integer, nullable=False)
    state: Mapped[str] = mapped_column(String(50), nullable=False, default="PLANNED")
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error_class: Mapped[str | None] = mapped_column(String(80))
    last_error_message: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class StorageOutboxEvent(Base):
    """Transactional outbox entry for post-publication document processing."""

    __tablename__ = "storage_outbox_events"
    __table_args__ = (UniqueConstraint("event_key", name="uq_storage_outbox_event_key"), Index("ix_storage_outbox_status", "status"))

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    event_key: Mapped[str] = mapped_column(String(240), nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    aggregate_type: Mapped[str] = mapped_column(String(100), nullable=False)
    aggregate_id: Mapped[str] = mapped_column(String(36), nullable=False)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="PENDING")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

