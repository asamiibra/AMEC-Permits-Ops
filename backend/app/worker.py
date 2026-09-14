from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import null, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .config.settings import get_settings
from .db import (
    SessionLocal,
    verify_database_migration_head,
)
from .models import (
    Contract,
    ContractReconciliationSchedulerState,
    DocumentVersion,
    StorageOutboxEvent,
)
from .models.base import utcnow
from .services.contract_workspace import evaluate_contract_exceptions
from .storage.outbox import (
    claim_pending_events,
    complete_event,
    recover_expired_claims,
)


MAX_BATCH_SIZE = 100
MIN_LEASE_SECONDS = 30
MAX_LEASE_SECONDS = 900
RECONCILIATION_SCHEDULER_ID = "contract-exceptions"


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


@dataclass(frozen=True)
class WorkerResult:
    recovered: int
    claimed: int
    processed: int
    failed: int
    contracts_reconciled: int = 0
    contract_reconciliation_failed: int = 0
    exceptions_created: int = 0
    exceptions_resolved: int = 0


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


def _ensure_reconciliation_scheduler_state(
    db: Session,
) -> ContractReconciliationSchedulerState:
    """Return the singleton scheduler row, tolerating concurrent first use."""
    state = db.get(
        ContractReconciliationSchedulerState,
        RECONCILIATION_SCHEDULER_ID,
    )
    if state is None:
        try:
            with db.begin_nested():
                db.add(
                    ContractReconciliationSchedulerState(
                        id=RECONCILIATION_SCHEDULER_ID,
                        cycle_number=0,
                    )
                )
        except IntegrityError:
            pass
        state = db.get(
            ContractReconciliationSchedulerState,
            RECONCILIATION_SCHEDULER_ID,
        )
    if state is None:
        raise RuntimeError("Contract reconciliation scheduler state is unavailable.")
    return state


def _release_reconciliation_lease(*, worker_id: str) -> None:
    with SessionLocal() as db:
        state = db.scalar(
            select(ContractReconciliationSchedulerState)
            .where(
                ContractReconciliationSchedulerState.id
                == RECONCILIATION_SCHEDULER_ID
            )
            .with_for_update()
        )
        if state is not None and state.lease_owner == worker_id:
            state.lease_owner = None
            state.lease_expires_at = None
            state.updated_at = utcnow()
            db.commit()


def _acquire_reconciliation_lease(
    *,
    worker_id: str,
    now: datetime,
    lease_seconds: int,
) -> bool:
    """Acquire the singleton lease with a database compare-and-set."""
    lease_expires_at = now + timedelta(seconds=lease_seconds)
    with SessionLocal() as db:
        _ensure_reconciliation_scheduler_state(db)
        # End the initialization/read transaction before the compare-and-set.
        # This matters on SQLite, whose deferred snapshot can otherwise retain
        # the pre-race lease row while the write lock is being acquired.
        db.commit()
        result = db.execute(
            update(ContractReconciliationSchedulerState)
            .where(
                ContractReconciliationSchedulerState.id
                == RECONCILIATION_SCHEDULER_ID,
                or_(
                    ContractReconciliationSchedulerState.lease_owner == null(),
                    ContractReconciliationSchedulerState.lease_expires_at == null(),
                    ContractReconciliationSchedulerState.lease_expires_at <= now,
                ),
            )
            .values(
                lease_owner=worker_id,
                lease_expires_at=lease_expires_at,
                updated_at=now,
            )
        )
        if result.rowcount != 1:
            db.rollback()
            return False
        db.commit()
        return True


def _advance_reconciliation_cursor(
    *,
    worker_id: str,
    contract_id: str,
    lease_seconds: int,
) -> None:
    """Advance after a failed item so one bad contract cannot starve later items."""
    with SessionLocal() as db:
        state = db.scalar(
            select(ContractReconciliationSchedulerState)
            .where(
                ContractReconciliationSchedulerState.id
                == RECONCILIATION_SCHEDULER_ID
            )
            .with_for_update()
        )
        if state is None or state.lease_owner != worker_id:
            return
        state.last_contract_id = contract_id
        state.lease_expires_at = utcnow() + timedelta(seconds=lease_seconds)
        state.updated_at = utcnow()
        db.commit()


def reconcile_contract_exceptions_once(
    *,
    worker_id: str,
    limit: int = 50,
    lease_seconds: int = 60,
) -> tuple[int, int, int, int]:
    """Reconcile one fair, leased page of Contracts against the canonical queue."""
    _validate_worker_options(
        worker_id=worker_id,
        limit=limit,
        lease_seconds=lease_seconds,
    )

    now = utcnow()
    if not _acquire_reconciliation_lease(
        worker_id=worker_id,
        now=now,
        lease_seconds=lease_seconds,
    ):
        return 0, 0, 0, 0

    with SessionLocal() as db:
        state = _ensure_reconciliation_scheduler_state(db)

        contract_query = select(Contract.id).order_by(Contract.id)
        if state.last_contract_id is not None:
            contract_query = contract_query.where(
                Contract.id > state.last_contract_id
            )
        contract_ids = list(db.scalars(contract_query.limit(limit)).all())

        if not contract_ids and state.last_contract_id is not None:
            wrapped_query = (
                select(Contract.id)
                .order_by(Contract.id)
                .limit(limit)
            )
            wrapped_ids = list(db.scalars(wrapped_query).all())
            if wrapped_ids:
                contract_ids.extend(wrapped_ids)
                state.cycle_number += 1
                state.updated_at = utcnow()
                db.commit()

    if not contract_ids:
        _release_reconciliation_lease(worker_id=worker_id)
        return 0, 0, 0, 0

    reconciled = 0
    failed = 0
    created = 0
    resolved = 0

    for contract_id in contract_ids:
        with SessionLocal() as db:
            try:
                state = db.scalar(
                    select(ContractReconciliationSchedulerState)
                    .where(
                        ContractReconciliationSchedulerState.id
                        == RECONCILIATION_SCHEDULER_ID
                    )
                    .with_for_update()
                )
                if state is None or state.lease_owner != worker_id:
                    break
                state.lease_expires_at = utcnow() + timedelta(seconds=lease_seconds)
                contract = db.get(Contract, contract_id)
                if contract is None:
                    state.last_contract_id = contract_id
                    state.updated_at = utcnow()
                    db.commit()
                    continue
                result = evaluate_contract_exceptions(
                    db,
                    contract,
                    actor=f"worker:{worker_id}",
                    correlation_id=(
                        f"worker:{worker_id}:contract:{contract_id}"
                    )[:100],
                )
                state.last_contract_id = contract_id
                state.updated_at = utcnow()
                db.commit()
            except Exception:
                db.rollback()
                _advance_reconciliation_cursor(
                    worker_id=worker_id,
                    contract_id=contract_id,
                    lease_seconds=lease_seconds,
                )
                failed += 1
                continue

            reconciled += 1
            created += len(result.get("created", []))
            resolved += int(result.get("resolved", 0))

    _release_reconciliation_lease(worker_id=worker_id)
    return reconciled, failed, created, resolved


def run_worker_once(
    *,
    worker_id: str | None = None,
    limit: int = 50,
    lease_seconds: int = 60,
) -> WorkerResult:
    settings = get_settings()

    if settings.app_env.upper() not in {"AZURE-PREPROD", "PROD"}:
        raise RuntimeError(
            "The Azure worker is restricted to AZURE-PREPROD or PROD."
        )

    if settings.app_env.upper() == "AZURE-PREPROD" and not settings.synthetic_only:
        raise RuntimeError(
            "AZURE-PREPROD worker requires "
            "SYNTHETIC_ONLY=true."
        )

    if settings.app_env.upper() == "AZURE-PREPROD" and settings.real_data_allowed:
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

    contracts_reconciled = 0
    contract_reconciliation_failed = 0
    exceptions_created = 0
    exceptions_resolved = 0
    if getattr(
        settings,
        "worker_contract_reconciliation_enabled",
        True,
    ):
        (
            contracts_reconciled,
            contract_reconciliation_failed,
            exceptions_created,
            exceptions_resolved,
        ) = reconcile_contract_exceptions_once(
            worker_id=resolved_worker_id,
            limit=limit,
            lease_seconds=lease_seconds,
        )

    return WorkerResult(
        recovered=recovered,
        claimed=len(event_ids),
        processed=processed,
        failed=failed,
        contracts_reconciled=contracts_reconciled,
        contract_reconciliation_failed=contract_reconciliation_failed,
        exceptions_created=exceptions_created,
        exceptions_resolved=exceptions_resolved,
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
    continuous = os.getenv(
        "WORKER_CONTINUOUS",
        "false",
    ).strip().lower() in {"1", "true", "yes"}
    try:
        poll_interval = int(
            os.getenv(
                "WORKER_POLL_INTERVAL_SECONDS",
                "60",
            )
        )
    except ValueError:
        print(
            json.dumps(
                {
                    "event": "proposalops_outbox_worker",
                    "status": "FAILED",
                    "error_class": "INVALID_WORKER_POLL_INTERVAL",
                },
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 1
    if not 5 <= poll_interval <= 3600:
        print(
            json.dumps(
                {
                    "event": "proposalops_outbox_worker",
                    "status": "FAILED",
                    "error_class": "WORKER_POLL_INTERVAL_OUT_OF_RANGE",
                },
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 1

    while True:
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
            if (
                result.failed == 0
                and result.contract_reconciliation_failed == 0
            )
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
                    "contracts_reconciled": (
                        result.contracts_reconciled
                    ),
                    "contract_reconciliation_failed": (
                        result.contract_reconciliation_failed
                    ),
                    "exceptions_created": (
                        result.exceptions_created
                    ),
                    "exceptions_resolved": (
                        result.exceptions_resolved
                    ),
                },
                sort_keys=True,
            )
        )

        if not continuous:
            return 0 if status == "SUCCEEDED" else 1

        time.sleep(poll_interval)


if __name__ == "__main__":
    raise SystemExit(main())
