"""Small PostgreSQL-safe transactional-outbox claim seam."""

from __future__ import annotations

from datetime import timedelta
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import StorageOutboxEvent
from ..models.base import utcnow


def claim_pending_events(db: Session, *, worker_id: str, limit: int = 50, lease_seconds: int = 60) -> list[StorageOutboxEvent]:
    now = utcnow()
    rows = list(db.scalars(
        select(StorageOutboxEvent)
        .where(StorageOutboxEvent.status == "PENDING", StorageOutboxEvent.available_at <= now)
        .order_by(StorageOutboxEvent.created_at, StorageOutboxEvent.id)
        .with_for_update(skip_locked=True)
        .limit(limit)
    ).all())
    for row in rows:
        row.status = "DISPATCHING"
        row.attempts += 1
        row.available_at = now + timedelta(seconds=lease_seconds)
        row.payload_json = {**(row.payload_json or {}), "claimed_by": worker_id}
    db.commit()
    return rows


def complete_event(db: Session, event_id: str) -> bool:
    row = db.get(StorageOutboxEvent, event_id)
    if not row or row.status == "PROCESSED":
        return False
    row.status = "PROCESSED"
    row.processed_at = utcnow()
    row.available_at = utcnow()
    db.commit()
    return True


def recover_expired_claims(db: Session) -> int:
    now = utcnow()
    rows = db.scalars(select(StorageOutboxEvent).where(StorageOutboxEvent.status == "DISPATCHING", StorageOutboxEvent.available_at < now).with_for_update(skip_locked=True)).all()
    for row in rows:
        row.status = "PENDING"
        row.attempts += 1
        row.available_at = now
    db.commit()
    return len(rows)
