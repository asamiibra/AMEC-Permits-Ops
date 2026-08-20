from datetime import timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy.dialects import postgresql

from backend.app import worker
from backend.app.models.base import utcnow


def _settings(
    *,
    app_env: str = "AZURE-PREPROD",
    synthetic_only: bool = True,
    real_data_allowed: bool = False,
):
    return SimpleNamespace(
        app_env=app_env,
        synthetic_only=synthetic_only,
        real_data_allowed=real_data_allowed,
    )


def _event(
    *,
    worker_id="test-worker",
    event_type="DocumentVersionStored",
    aggregate_type="DocumentVersion",
    aggregate_id="version-1",
    payload=None,
    status="DISPATCHING",
    available_at=None,
):
    base_payload = {
        "document_version_id": aggregate_id,
        "document_id": "document-1",
        "sha256": "abc123",
        "storage_locator": (
            "storage://mock/root/file"
        ),
        "claimed_by": worker_id,
    }

    return SimpleNamespace(
        id="event-1",
        event_type=event_type,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        payload_json=(
            payload
            if payload is not None
            else base_payload
        ),
        status=status,
        available_at=(
            available_at
            if available_at is not None
            else (
                utcnow()
                + timedelta(minutes=5)
            )
        ),
    )


class _DB:
    def __init__(
        self,
        *,
        event=None,
        version=None,
    ):
        self.event = event
        self.version = version
        self.rollbacks = 0
        self.last_scalar_statement = None

    def scalar(
        self,
        statement,
    ):
        self.last_scalar_statement = (
            statement
        )

        return self.event

    def get(
        self,
        model,
        identity,
    ):
        if model is worker.DocumentVersion:
            return self.version

        return None

    def rollback(self):
        self.rollbacks += 1


class _Context:
    def __init__(
        self,
        db,
    ):
        self.db = db

    def __enter__(self):
        return self.db

    def __exit__(
        self,
        exc_type,
        exc,
        traceback,
    ):
        return False


def _version(
    *,
    sha256="abc123",
):
    return SimpleNamespace(
        id="version-1",
        document_id="document-1",
        sha256=sha256,
        source_path_or_reference=(
            "storage://mock/root/file"
        ),
    )


def test_valid_document_version_event_is_accepted():
    worker._process_event(
        _DB(
            version=_version()
        ),
        _event(),
    )


@pytest.mark.parametrize(
    (
        "event",
        "message",
    ),
    [
        (
            _event(
                event_type="Unknown"
            ),
            "Unsupported",
        ),
        (
            _event(
                aggregate_type="Wrong"
            ),
            "aggregate type",
        ),
        (
            _event(
                payload={
                    "document_version_id": (
                        "other"
                    ),
                    "document_id": (
                        "document-1"
                    ),
                    "sha256": "abc123",
                    "storage_locator": (
                        "storage://mock/root/file"
                    ),
                    "claimed_by": (
                        "test-worker"
                    ),
                }
            ),
            "aggregate_id",
        ),
    ],
)
def test_invalid_event_contract_is_rejected(
    event,
    message,
):
    with pytest.raises(
        RuntimeError,
        match=message,
    ):
        worker._process_event(
            _DB(
                version=_version()
            ),
            event,
        )


def test_missing_document_version_is_rejected():
    with pytest.raises(
        RuntimeError,
        match="missing",
    ):
        worker._process_event(
            _DB(
                version=None
            ),
            _event(),
        )


def test_hash_mismatch_is_rejected():
    with pytest.raises(
        RuntimeError,
        match="hash",
    ):
        worker._process_event(
            _DB(
                version=_version(
                    sha256="different"
                )
            ),
            _event(),
        )


def test_owned_event_query_uses_postgresql_row_lock():
    db = _DB(
        event=_event()
    )

    worker._load_owned_event_for_update(
        db,
        event_id="event-1",
        worker_id="test-worker",
    )

    sql = str(
        db.last_scalar_statement.compile(
            dialect=postgresql.dialect()
        )
    )

    assert "FOR UPDATE" in sql


def test_wrong_worker_cannot_use_claim():
    db = _DB(
        event=_event(
            worker_id="other-worker"
        )
    )

    with pytest.raises(
        RuntimeError,
        match="different worker",
    ):
        worker._load_owned_event_for_update(
            db,
            event_id="event-1",
            worker_id="test-worker",
        )


def test_expired_lease_cannot_be_processed():
    db = _DB(
        event=_event(
            available_at=(
                utcnow()
                - timedelta(seconds=1)
            )
        )
    )

    with pytest.raises(
        RuntimeError,
        match="expired",
    ):
        worker._load_owned_event_for_update(
            db,
            event_id="event-1",
            worker_id="test-worker",
        )


@pytest.mark.parametrize(
    (
        "limit",
        "lease_seconds",
    ),
    [
        (0, 60),
        (101, 60),
        (50, 29),
        (50, 901),
    ],
)
def test_worker_options_are_bounded(
    limit,
    lease_seconds,
):
    with pytest.raises(
        ValueError
    ):
        worker._validate_worker_options(
            worker_id="worker",
            limit=limit,
            lease_seconds=lease_seconds,
        )


def test_blank_worker_id_is_rejected():
    with pytest.raises(
        ValueError
    ):
        worker._validate_worker_options(
            worker_id=" ",
            limit=50,
            lease_seconds=60,
        )


def test_non_preprod_worker_is_rejected(
    monkeypatch,
):
    monkeypatch.setattr(
        worker,
        "get_settings",
        lambda: _settings(
            app_env="TEST"
        ),
    )

    with pytest.raises(
        RuntimeError,
        match="restricted",
    ):
        worker.run_worker_once()


def test_worker_recovers_claims_processes_and_completes(
    monkeypatch,
):
    event = _event()

    claim_db = _DB()

    event_db = _DB(
        event=event,
        version=_version(),
    )

    contexts = iter(
        [
            _Context(claim_db),
            _Context(event_db),
        ]
    )

    monkeypatch.setattr(
        worker,
        "SessionLocal",
        lambda: next(contexts),
    )

    monkeypatch.setattr(
        worker,
        "get_settings",
        lambda: _settings(),
    )

    monkeypatch.setattr(
        worker,
        "verify_database_migration_head",
        lambda: "0059_entra_user_identity",
    )

    calls = []

    monkeypatch.setattr(
        worker,
        "recover_expired_claims",
        lambda db: (
            calls.append("recover")
            or 2
        ),
    )

    monkeypatch.setattr(
        worker,
        "claim_pending_events",
        lambda db, **kwargs: (
            calls.append("claim")
            or [event]
        ),
    )

    monkeypatch.setattr(
        worker,
        "_process_event",
        lambda db, item: (
            calls.append("process")
        ),
    )

    monkeypatch.setattr(
        worker,
        "complete_event",
        lambda db, event_id: (
            calls.append("complete")
            or True
        ),
    )

    result = worker.run_worker_once(
        worker_id="test-worker",
        limit=10,
        lease_seconds=60,
    )

    assert calls == [
        "recover",
        "claim",
        "process",
        "complete",
    ]

    assert result.recovered == 2
    assert result.claimed == 1
    assert result.processed == 1
    assert result.failed == 0


def test_reclaimed_event_is_not_completed(
    monkeypatch,
):
    event = _event(
        worker_id="other-worker"
    )

    contexts = iter(
        [
            _Context(_DB()),
            _Context(
                _DB(
                    event=event,
                    version=_version(),
                )
            ),
        ]
    )

    monkeypatch.setattr(
        worker,
        "SessionLocal",
        lambda: next(contexts),
    )

    monkeypatch.setattr(
        worker,
        "get_settings",
        lambda: _settings(),
    )

    monkeypatch.setattr(
        worker,
        "verify_database_migration_head",
        lambda: "0059_entra_user_identity",
    )

    monkeypatch.setattr(
        worker,
        "recover_expired_claims",
        lambda db: 0,
    )

    monkeypatch.setattr(
        worker,
        "claim_pending_events",
        lambda db, **kwargs: [
            event
        ],
    )

    completed = []

    monkeypatch.setattr(
        worker,
        "complete_event",
        lambda db, event_id: (
            completed.append(event_id)
            or True
        ),
    )

    result = worker.run_worker_once(
        worker_id="test-worker",
    )

    assert result.processed == 0
    assert result.failed == 1
    assert completed == []


def test_failed_event_causes_partial_failure(
    monkeypatch,
):
    event = _event()

    contexts = iter(
        [
            _Context(_DB()),
            _Context(
                _DB(
                    event=event,
                    version=_version(),
                )
            ),
        ]
    )

    monkeypatch.setattr(
        worker,
        "SessionLocal",
        lambda: next(contexts),
    )

    monkeypatch.setattr(
        worker,
        "get_settings",
        lambda: _settings(),
    )

    monkeypatch.setattr(
        worker,
        "verify_database_migration_head",
        lambda: "0059_entra_user_identity",
    )

    monkeypatch.setattr(
        worker,
        "recover_expired_claims",
        lambda db: 0,
    )

    monkeypatch.setattr(
        worker,
        "claim_pending_events",
        lambda db, **kwargs: [
            event
        ],
    )

    def fail(
        db,
        item,
    ):
        raise RuntimeError(
            "synthetic"
        )

    monkeypatch.setattr(
        worker,
        "_process_event",
        fail,
    )

    result = worker.run_worker_once(
        worker_id="test-worker",
    )

    assert result.processed == 0
    assert result.failed == 1


def test_main_returns_nonzero_for_partial_failure(
    monkeypatch,
    capsys,
):
    monkeypatch.setattr(
        worker,
        "run_worker_once",
        lambda **kwargs: (
            worker.WorkerResult(
                recovered=0,
                claimed=1,
                processed=0,
                failed=1,
            )
        ),
    )

    assert worker.main([]) == 1

    output = capsys.readouterr()

    assert (
        "PARTIAL_FAILURE"
        in output.out
    )
