"""Prove the Azure-preprod PostgreSQL, identity, and worker seams."""

from __future__ import annotations

import json
import sys
from datetime import timedelta
from typing import Any
from unittest.mock import patch
from uuid import uuid4

from sqlalchemy import inspect, select, text

from backend.app.api import dependencies
from backend.app.auth.entra import EntraIdentity
from backend.app.bootstrap_preprod import _bootstrap_anchors
from backend.app.config.settings import get_settings
from backend.app.db import (
    SessionLocal,
    database_migration_heads,
    engine,
    repository_migration_head,
)
from backend.app.models import (
    Document,
    DocumentApprovalState,
    DocumentType,
    DocumentVersion,
    MasterContentReferenceSequence,
    StorageOutboxEvent,
    User,
)
from backend.app.models.base import utcnow
from backend.app.worker import run_worker_once


EXPECTED_HEAD = "0059_entra_user_identity"
EXPECTED_OID = "44444444-4444-4444-8444-444444444444"
OWNER_EMAIL = "owner@amec.synthetic"
PROOF_PREFIX = f"BATCH3A2-PROOF-{uuid4().hex.upper()}"


def _fail(message: str) -> None:
    raise RuntimeError(message)


def _verify_settings() -> None:
    settings = get_settings()
    if settings.app_env.upper() != "AZURE-PREPROD":
        _fail("APP_ENV is not AZURE-PREPROD")
    if not settings.synthetic_only:
        _fail("SYNTHETIC_ONLY must be true")
    if settings.real_data_allowed:
        _fail("REAL_DATA_ALLOWED must be false")
    if settings.auth_mode.upper() != "ENTRA":
        _fail("AUTH_MODE must be ENTRA")
    if settings.storage_provider.lower() != "mock":
        _fail("STORAGE_PROVIDER must be mock")
    if settings.synology_mode.upper() != "SYNTHETIC":
        _fail("SYNOLOGY_MODE must be SYNTHETIC")
    if engine.dialect.name != "postgresql":
        _fail("database dialect is not PostgreSQL")


def _verify_database() -> None:
    with engine.connect() as connection:
        server_version_num = int(
            connection.execute(
                text("select current_setting('server_version_num')")
            ).scalar_one()
        )
        if server_version_num // 10000 != 16:
            _fail("PostgreSQL major version is not 16")

        if repository_migration_head() != EXPECTED_HEAD:
            _fail("repository migration head is not 0059")
        if database_migration_heads() != (EXPECTED_HEAD,):
            _fail("database migration head is not the single 0059 head")

        inspector = inspect(connection)
        columns = {column["name"] for column in inspector.get_columns("users")}
        if "entra_object_id" not in columns:
            _fail("users.entra_object_id is missing")
        indexes = {
            index["name"] for index in inspector.get_indexes("users")
        }
        if "ix_users_entra_object_id" not in indexes:
            _fail("ix_users_entra_object_id is missing")

        baseline = connection.execute(
            select(
                MasterContentReferenceSequence.id,
                MasterContentReferenceSequence.content_type,
                MasterContentReferenceSequence.prefix,
                MasterContentReferenceSequence.padding,
                MasterContentReferenceSequence.scope,
                MasterContentReferenceSequence.active,
                MasterContentReferenceSequence.current_value,
            )
        ).all()
        if baseline != [
            (
                "proposal-reference-sequence",
                "PROPOSAL_REFERENCE",
                "AMEC-SYN-PROP",
                4,
                "GLOBAL",
                True,
                0,
            )
        ]:
            _fail("migration-owned baseline is not exact")


def _verify_identity_binding() -> None:
    with SessionLocal() as db:
        anchors = _bootstrap_anchors(db)
        if not anchors.complete:
            _fail("canonical bootstrap anchors are incomplete")

        owner = db.scalar(select(User).where(User.email == OWNER_EMAIL))
        if owner is None or not owner.active:
            _fail("synthetic owner is missing or inactive")
        if owner.entra_object_id != EXPECTED_OID:
            _fail("synthetic owner has the wrong Entra object ID")

        owners = db.scalars(
            select(User).where(User.entra_object_id == EXPECTED_OID)
        ).all()
        if len(owners) != 1 or owners[0].id != owner.id:
            _fail("synthetic Entra object ID is not uniquely bound")

        identity = EntraIdentity(
            tenant_id="11111111-1111-4111-8111-111111111111",
            object_id=EXPECTED_OID,
            subject="synthetic-proof-subject",
            client_id="22222222-2222-4222-8222-222222222222",
            scopes=frozenset({"access_as_user"}),
        )

        class SyntheticValidator:
            def validate(self, token: str) -> EntraIdentity:
                if token != "synthetic-proof-token":
                    raise AssertionError("unexpected proof token")
                return identity

        with patch.object(
            dependencies,
            "get_entra_validator",
            lambda: SyntheticValidator(),
        ):
            credentials = type(
                "Credentials",
                (),
                {
                    "scheme": "Bearer",
                    "credentials": "synthetic-proof-token",
                },
            )()
            principal = dependencies.current_principal(
                credentials=credentials,
                x_dev_role="SYSTEM_ADMIN",
                db=db,
            )

        if principal.user_id != owner.id:
            _fail("synthetic identity did not resolve to the owner")
        if principal.object_id != EXPECTED_OID:
            _fail("principal did not preserve the Entra object ID")
        if principal.role != owner.role:
            _fail("resolved principal role is incorrect")
        if principal.auth_mode != "ENTRA":
            _fail("resolved principal is not ENTRA-authenticated")


def _create_worker_rows() -> tuple[str, str, str]:
    document_id = str(uuid4())
    version_id = str(uuid4())
    event_id = str(uuid4())
    locator = f"{PROOF_PREFIX}/documents/{document_id}/v1"
    digest = "a" * 64

    with SessionLocal() as db:
        document = Document(
            id=document_id,
            document_type=DocumentType.OTHER,
            logical_name=f"{PROOF_PREFIX}-document",
            language="en",
            source_system="BATCH3A2_SYNTHETIC",
        )
        version = DocumentVersion(
            id=version_id,
            document_id=document_id,
            version_number=1,
            source_filename=f"{PROOF_PREFIX}.txt",
            source_path_or_reference=locator,
            sha256=digest,
            mime_type="text/plain",
            file_size=7,
            language="en",
            approval_state=DocumentApprovalState.WORKING,
            source_system="BATCH3A2_SYNTHETIC",
        )
        event = StorageOutboxEvent(
            id=event_id,
            event_key=f"{PROOF_PREFIX}-{event_id}-event",
            event_type="DocumentVersionStored",
            aggregate_type="DocumentVersion",
            aggregate_id=version_id,
            payload_json={
                "document_id": document_id,
                "document_version_id": version_id,
                "sha256": digest,
                "storage_locator": locator,
            },
        )
        db.add_all([document, version, event])
        db.commit()
    return document_id, version_id, event_id


def _event_status(event_id: str) -> tuple[str, int]:
    with SessionLocal() as db:
        event = db.get(StorageOutboxEvent, event_id)
        if event is None:
            _fail("proof event disappeared")
        return event.status, event.attempts


def _cleanup(row_ids: list[tuple[str, str, str]]) -> None:
    with SessionLocal() as db:
        for document_id, version_id, event_id in row_ids:
            event = db.get(StorageOutboxEvent, event_id)
            if event is not None:
                db.delete(event)
            version = db.get(DocumentVersion, version_id)
            if version is not None:
                db.delete(version)
            document = db.get(Document, document_id)
            if document is not None:
                db.delete(document)
        db.commit()


def _verify_worker_paths() -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []

    try:
        fresh = _create_worker_rows()
        rows.append(fresh)
        result = run_worker_once(
            worker_id=f"{PROOF_PREFIX}-fresh",
            lease_seconds=30,
        )
        if result.claimed != 1 or result.processed != 1 or result.failed != 0:
            _fail("fresh outbox event was not completed")
        if _event_status(fresh[2])[0] != "PROCESSED":
            _fail("fresh outbox event is not PROCESSED")

        expired = _create_worker_rows()
        rows.append(expired)
        with SessionLocal() as db:
            event = db.get(StorageOutboxEvent, expired[2])
            if event is None:
                _fail("expired outbox event was not created")
            event.status = "DISPATCHING"
            event.attempts = 1
            event.available_at = utcnow() - timedelta(seconds=5)
            event.payload_json = {
                **(event.payload_json or {}),
                "claimed_by": f"{PROOF_PREFIX}-expired",
            }
            db.commit()

        recovered = run_worker_once(
            worker_id=f"{PROOF_PREFIX}-recovery",
            lease_seconds=30,
        )
        if (
            recovered.recovered < 1
            or recovered.claimed != 1
            or recovered.processed != 1
            or recovered.failed != 0
        ):
            _fail("expired outbox claim was not recovered and processed")
        status, attempts = _event_status(expired[2])
        if status != "PROCESSED" or attempts < 3:
            _fail("recovered outbox event did not complete exactly once")
        return rows
    except Exception:
        _cleanup(rows)
        raise


def run_proof() -> dict[str, Any]:
    _verify_settings()
    _verify_database()
    _verify_identity_binding()
    rows: list[tuple[str, str, str]] = []
    try:
        rows = _verify_worker_paths()
        return {
            "step": "3A.2",
            "postgres_major": 16,
            "migration_head": EXPECTED_HEAD,
            "bootstrap_anchors": "PASS",
            "entra_db_binding": "PASS",
            "worker_claim_complete": "PASS",
            "worker_expired_recovery": "PASS",
            "real_data_used": False,
            "azure_resources_created": False,
            "entra_resources_created": False,
            "authority_key": "entra_object_id",
            "status": "PASS",
        }
    finally:
        if rows:
            _cleanup(rows)


def main() -> int:
    try:
        print(json.dumps(run_proof(), sort_keys=True))
    except Exception as exc:
        print(
            json.dumps(
                {
                    "step": "3A.2",
                    "status": "FAIL",
                    "error_class": type(exc).__name__,
                },
                sort_keys=True,
            )
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
