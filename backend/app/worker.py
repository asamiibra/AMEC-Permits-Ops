from __future__ import annotations

import argparse
import json
import os
import socket
import sys
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from .config.settings import get_settings
from .db import (
    SessionLocal,
    verify_database_migration_head,
)
from .models import (
    DocumentVersion,
    StorageOutboxEvent,
)
from .models.base import utcnow
from .storage.outbox import (
    claim_pending_events,
    complete_event,
    recover_expired_claims,
)


MAX_BATCH_SIZE = 100
MIN_LEASE_SECONDS = 30
MAX_LEASE_SECONDS = 900


@dataclass(frozen=True)
class WorkerResult:
    recovered: int
    claimed: int
    processed: int
    failed: int


def _default_worker_id() -> str:
    return (
        f"{socket.gethostname()}:{os.getpid()}"
    )[:100]


def _validate_worker_options(
    *,
    worker_id: str,
    limit: int,
    lease_seconds: int,
) -> None:
    if not worker_id.strip():
        raise ValueError(
            "worker_id must not be blank."
        )

    if len(worker_id) > 100:
        raise ValueError(
            "worker_id must not exceed "
            "100 characters."
        )

    if not 1 <= limit <= MAX_BATCH_SIZE:
        raise ValueError(
            "limit must be between 1 and "
            f"{MAX_BATCH_SIZE}."
        )

    if not (
        MIN_LEASE_SECONDS
        <= lease_seconds
        <= MAX_LEASE_SECONDS
    ):
        raise ValueError(
            "lease_seconds must be between "
            f"{MIN_LEASE_SECONDS} and "
            f"{MAX_LEASE_SECONDS}."
        )


def _load_owned_event_for_update(
    db: Session,
    *,
    event_id: str,
    worker_id: str,
) -> StorageOutboxEvent:
    # Lock the row for the complete validation/processing operation.
    # A recovery/reclaim worker therefore cannot take ownership while
    # this worker is completing the currently valid lease.
    event = db.scalar(
        select(StorageOutboxEvent)
        .where(
            StorageOutboxEvent.id
            == event_id
        )
        .with_for_update()
    )

    if event is None:
        raise RuntimeError(
            "Claimed outbox event no longer "
            "exists."
        )

    if event.status != "DISPATCHING":
        raise RuntimeError(
            "Claimed outbox event is no longer "
            "in DISPATCHING state."
        )

    claimed_by = (
        event.payload_json
        or {}
    ).get("claimed_by")

    if claimed_by != worker_id:
        raise RuntimeError(
            "Claimed outbox event is owned by "
            "a different worker."
        )

    if (
        event.available_at is None
        or event.available_at <= utcnow()
    ):
        raise RuntimeError(
            "Claimed outbox event lease has "
            "expired."
        )

    return event


def _process_event(
    db: Session,
    event: StorageOutboxEvent,
) -> None:
    if event.event_type != (
        "DocumentVersionStored"
    ):
        raise RuntimeError(
            "Unsupported storage outbox "
            f"event type: {event.event_type}"
        )

    if event.aggregate_type != (
        "DocumentVersion"
    ):
        raise RuntimeError(
            "DocumentVersionStored event has "
            "an invalid aggregate type."
        )

    payload = (
        event.payload_json
        or {}
    )

    payload_version_id = payload.get(
        "document_version_id"
    )

    if (
        payload_version_id
        != event.aggregate_id
    ):
        raise RuntimeError(
            "Outbox payload document version "
            "does not match aggregate_id."
        )

    version = db.get(
        DocumentVersion,
        event.aggregate_id,
    )

    if version is None:
        raise RuntimeError(
            "Outbox event references a missing "
            "DocumentVersion."
        )

    if (
        payload.get("document_id")
        != version.document_id
    ):
        raise RuntimeError(
            "Outbox payload document ID does "
            "not match the persisted "
            "DocumentVersion."
        )

    if (
        payload.get("sha256")
        != version.sha256
    ):
        raise RuntimeError(
            "Outbox payload hash does not "
            "match the persisted "
            "DocumentVersion."
        )

    if (
        payload.get("storage_locator")
        != version.source_path_or_reference
    ):
        raise RuntimeError(
            "Outbox payload storage locator "
            "does not match the persisted "
            "DocumentVersion."
        )


def run_worker_once(
    *,
    worker_id: str | None = None,
    limit: int = 50,
    lease_seconds: int = 60,
) -> WorkerResult:
    settings = get_settings()

    if settings.app_env.upper() != (
        "AZURE-PREPROD"
    ):
        raise RuntimeError(
            "The Azure worker is restricted "
            "to AZURE-PREPROD."
        )

    if not settings.synthetic_only:
        raise RuntimeError(
            "AZURE-PREPROD worker requires "
            "SYNTHETIC_ONLY=true."
        )

    if settings.real_data_allowed:
        raise RuntimeError(
            "AZURE-PREPROD worker requires "
            "REAL_DATA_ALLOWED=false."
        )

    resolved_worker_id = (
        worker_id
        or _default_worker_id()
    )

    _validate_worker_options(
        worker_id=resolved_worker_id,
        limit=limit,
        lease_seconds=lease_seconds,
    )

    verify_database_migration_head()

    with SessionLocal() as db:
        recovered = (
            recover_expired_claims(
                db
            )
        )

        claimed_events = (
            claim_pending_events(
                db,
                worker_id=(
                    resolved_worker_id
                ),
                limit=limit,
                lease_seconds=(
                    lease_seconds
                ),
            )
        )

        event_ids = [
            event.id
            for event in claimed_events
        ]

    processed = 0
    failed = 0

    for event_id in event_ids:
        with SessionLocal() as db:
            try:
                event = (
                    _load_owned_event_for_update(
                        db,
                        event_id=event_id,
                        worker_id=(
                            resolved_worker_id
                        ),
                    )
                )

                _process_event(
                    db,
                    event,
                )

                completed = complete_event(
                    db,
                    event.id,
                )

                if not completed:
                    raise RuntimeError(
                        "Claimed outbox event "
                        "could not be completed."
                    )

            except Exception:
                db.rollback()
                failed += 1
                continue

            processed += 1

    return WorkerResult(
        recovered=recovered,
        claimed=len(event_ids),
        processed=processed,
        failed=failed,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run one bounded ProposalOps "
            "transactional-outbox worker pass."
        )
    )

    parser.add_argument(
        "--worker-id",
        default=None,
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=50,
    )

    parser.add_argument(
        "--lease-seconds",
        type=int,
        default=60,
    )

    return parser


def main(
    argv: list[str] | None = None,
) -> int:
    args = _parser().parse_args(
        argv
    )

    try:
        result = run_worker_once(
            worker_id=args.worker_id,
            limit=args.limit,
            lease_seconds=(
                args.lease_seconds
            ),
        )

    except Exception as exc:
        print(
            json.dumps(
                {
                    "event": (
                        "proposalops_outbox_worker"
                    ),
                    "status": "FAILED",
                    "error_class": (
                        type(exc).__name__
                    ),
                },
                sort_keys=True,
            ),
            file=sys.stderr,
        )

        return 1

    status = (
        "SUCCEEDED"
        if result.failed == 0
        else "PARTIAL_FAILURE"
    )

    print(
        json.dumps(
            {
                "event": (
                    "proposalops_outbox_worker"
                ),
                "status": status,
                "recovered": result.recovered,
                "claimed": result.claimed,
                "processed": result.processed,
                "failed": result.failed,
            },
            sort_keys=True,
        )
    )

    return (
        0
        if result.failed == 0
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
