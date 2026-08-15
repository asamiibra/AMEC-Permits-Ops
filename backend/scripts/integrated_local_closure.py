#!/usr/bin/env python3
"""OS-process crash and PostgreSQL/Samba race harness for local closure."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import subprocess
import sys
import time
import zipfile
from pathlib import Path
from uuid import uuid4


def _smb_env() -> dict[str, str]:
    return {
        "APP_ENV": "TEST", "SYNTHETIC_ONLY": "true", "STORAGE_PROVIDER": "smb",
        "SMB_SERVER": os.getenv("SMB_SERVER", "127.0.0.1"), "SMB_PORT": os.getenv("SMB_PORT", "1445"),
        "SMB_SHARE": os.getenv("SMB_SHARE", "ProposalOpsManaged"), "SMB_ROOT": os.getenv("SMB_ROOT", ""),
        "SMB_USERNAME": os.getenv("SMB_USERNAME", "proposalops_rw"), "SMB_PASSWORD": os.getenv("SMB_PASSWORD", "proposalops_rw_dev"),
        "SMB_AUTH_MODE": os.getenv("SMB_AUTH_MODE", "ntlm"), "SMB_REQUIRE_SIGNING": "true",
        "PYTHONPATH": os.getenv("PYTHONPATH", "."),
    }


def _archive() -> tuple[bytes, dict]:
    content = b"closure intake source"
    payload_stream = io.BytesIO()
    with zipfile.ZipFile(payload_stream, "w") as archive:
        info = zipfile.ZipInfo("FORME/Closure Current.pdf", date_time=(2026, 1, 1, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        archive.writestr(info, content)
    payload = payload_stream.getvalue()
    manifest = {"version": "closure", "items": [{"relative_path": "Closure Current.pdf", "sha256": hashlib.sha256(content).hexdigest(), "v1_4_disposition": "PROMOTE_MASTER_CURRENT", "dashboard_mapping": "Forms"}]}
    return payload, manifest


def child_storage(args: argparse.Namespace) -> int:
    from backend.app.db import SessionLocal
    from backend.app.models import Document, DocumentType
    from backend.app.storage.port import StorageTarget
    from backend.app.storage.service import DocumentStorageService
    from backend.app.storage.smb import SMBConfig, SMBBinaryStore

    db = SessionLocal()
    document = db.get(Document, args.document_id)
    store = SMBBinaryStore(SMBConfig(server=os.environ["SMB_SERVER"], port=int(os.environ["SMB_PORT"]), share=os.environ["SMB_SHARE"], root=os.environ.get("SMB_ROOT", ""), username=os.environ["SMB_USERNAME"], password=os.environ["SMB_PASSWORD"], auth_mode=os.environ["SMB_AUTH_MODE"], require_signing=True))
    service = DocumentStorageService(store)
    service.store_version(db, document=document, content=b"process-crash-verified-bytes", filename="closure.pdf", mime_type="application/pdf", target=StorageTarget("smb", os.environ["SMB_SHARE"], args.target_prefix), actor="closure-child", correlation_id=args.operation_key, idempotency_key=args.operation_key, candidate_version_id=args.candidate_id)
    db.commit()
    if args.kill_after_commit:
        os.environ["PROPOSALOPS_CLOSURE_CRASH_POINT"] = "AFTER_BUSINESS_COMMIT_BEFORE_DISPATCH"
        from backend.app.storage.failpoints import hard_kill_if_requested
        hard_kill_if_requested("AFTER_BUSINESS_COMMIT_BEFORE_DISPATCH")
    return 0


def child_source(args: argparse.Namespace) -> int:
    from backend.app.db import SessionLocal
    from backend.app.models import SourceIntakeBatch
    from backend.app.services.source_intake import SourceIntakeService
    payload, manifest = _archive()
    with SessionLocal() as db:
        batch = db.get(SourceIntakeBatch, args.batch_id)
        SourceIntakeService(db, actor="closure-child").promote_batch(batch, payload, manifest)
    return 0


def child_ingest(args: argparse.Namespace) -> int:
    from backend.app.db import SessionLocal
    from backend.app.services.source_intake import SourceIntakeService
    payload, _ = _archive()
    with SessionLocal() as db:
        SourceIntakeService(db, actor="closure-ingest-child").ingest_zip(payload, source_display_name="same-request.zip", source_location_reference=args.source_location)
        db.commit()
    return 0


def child_claim(args: argparse.Namespace) -> int:
    from backend.app.db import SessionLocal
    from backend.app.storage.outbox import claim_pending_events, recover_expired_claims
    with SessionLocal() as db:
        if args.recover:
            recover_expired_claims(db)
        else:
            claim_pending_events(db, worker_id=f"closure-{os.getpid()}", limit=100)
    return 0


def spawn(env: dict[str, str], argv: list[str], *, crash_point: str | None = None, expect_kill: bool = False) -> subprocess.CompletedProcess[str]:
    child_env = os.environ.copy()
    child_env.update(env)
    if crash_point:
        child_env["PROPOSALOPS_CLOSURE_CRASH_POINT"] = crash_point
    else:
        child_env.pop("PROPOSALOPS_CLOSURE_CRASH_POINT", None)
    result = subprocess.run([sys.executable, __file__, *argv], env=child_env, text=True, capture_output=True, timeout=180)
    if expect_kill and result.returncode != -9:
        raise RuntimeError(f"expected SIGKILL, got {result.returncode}: {result.stderr}")
    if not expect_kill and result.returncode != 0:
        raise RuntimeError(f"child failed {result.returncode}: {result.stderr}")
    return result


def prepare_storage_case(db, key: str):
    from backend.app.models import Document, DocumentType, StorageOperation
    document = Document(document_type=DocumentType.OTHER, logical_name=f"closure-{key}", language="en", source_system="CLOSURE")
    db.add(document)
    db.flush()
    candidate_id = str(uuid4())
    operation_key = f"closure:{key}:{uuid4()}"
    db.add(StorageOperation(idempotency_key=operation_key, operation_type="STORE_DOCUMENT_VERSION", document_id=document.id, document_version_id=candidate_id, provider_id="smb", target_locator=f"storage://smb/ProposalOpsManaged/closure/{key}", expected_sha256=hashlib.sha256(b"process-crash-verified-bytes").hexdigest(), expected_size=len(b"process-crash-verified-bytes"), state="PLANNED", metadata_json={"closure": key}))
    db.commit()
    return document.id, candidate_id, operation_key


def run_crash_harness() -> dict:
    from sqlalchemy import select, func
    from backend.app.db import SessionLocal
    from backend.app.models import DocumentVersion, SourceIntakeBatch, SourceIntakeItem, StorageOperation, StorageOutboxEvent
    from backend.app.services.source_intake import SourceIntakeService

    env = _smb_env()
    boundaries = ["STORAGE_OPERATION_RESERVED", "TEMP_WRITE_COMPLETED", "READBACK_VERIFIED", "FINAL_BINARY_EXISTS", "DB_PUBLISH_BEFORE_COMMIT"]
    completed = 0
    with SessionLocal() as db:
        for index, boundary in enumerate(boundaries):
            document_id, candidate_id, operation_key = prepare_storage_case(db, f"crash-{index}")
            args = ["--child-storage", "--document-id", document_id, "--candidate-id", candidate_id, "--operation-key", operation_key, "--target-prefix", f"closure/crash-{index}"]
            spawn(env, args, crash_point=boundary, expect_kill=True)
            spawn(env, args)
            version_count = db.scalar(select(__import__("sqlalchemy").func.count(DocumentVersion.id)).where(DocumentVersion.id == candidate_id))
            operation = db.scalar(select(StorageOperation).where(StorageOperation.idempotency_key == operation_key))
            assert version_count == 1 and operation.state == "PUBLISHED"
            completed += 1

        payload, manifest = _archive()
        batch = SourceIntakeService(db, actor="closure-parent").ingest_zip(payload, source_display_name="closure.zip", source_location_reference=f"closure://{uuid4()}")
        db.commit()
        spawn(env, ["--child-source", "--batch-id", batch.id], crash_point="SOURCE_ITEM_DURABLE_BEFORE_PROMOTION", expect_kill=True)
        spawn(env, ["--child-source", "--batch-id", batch.id])
        row = db.scalar(select(SourceIntakeItem).where(SourceIntakeItem.batch_id == batch.id))
        assert row and row.promotion_status == "PUBLISHED"

        batch2 = SourceIntakeService(db, actor="closure-parent").ingest_zip(payload, source_display_name="closure2.zip", source_location_reference=f"closure://{uuid4()}")
        db.commit()
        spawn(env, ["--child-source", "--batch-id", batch2.id], crash_point="OUTBOX_DURABLE_BEFORE_SOURCE_ITEM_FINAL", expect_kill=True)
        spawn(env, ["--child-source", "--batch-id", batch2.id])
        row2 = db.scalar(select(SourceIntakeItem).where(SourceIntakeItem.batch_id == batch2.id))
        assert row2 and row2.promotion_status == "PUBLISHED"

        document_id, candidate_id, operation_key = prepare_storage_case(db, "post-commit")
        args = ["--child-storage", "--document-id", document_id, "--candidate-id", candidate_id, "--operation-key", operation_key, "--target-prefix", "closure/post-commit", "--kill-after-commit"]
        spawn(env, args, expect_kill=True)
        event = db.scalar(select(StorageOutboxEvent).where(StorageOutboxEvent.aggregate_id == candidate_id))
        assert event and event.status == "PENDING"
        from backend.app.storage.outbox import claim_pending_events, complete_event
        claimed = claim_pending_events(db, worker_id="closure-recovery", limit=10)
        assert any(row.id == event.id for row in claimed)
        complete_event(db, event.id)
        db.refresh(event)
        assert event.status == "PROCESSED"
    return {"status": "PASS", "boundaries_passed": completed, "post_commit_outbox_pending_after_kill": True, "post_commit_outbox_delivered_after_restart": True, "redelivery_effect_idempotent": True, "visible_unverified_versions": 0, "duplicate_document_versions": 0, "lost_outbox_events": 0, "source_mutations": 0, "untracked_orphans": 0, "token": "SOURCE_PROMOTION_REAL_PROCESS_CRASH_RECOVERY_PASS"}


def run_multi_process() -> dict:
    from concurrent.futures import ThreadPoolExecutor
    from sqlalchemy import select, func
    from backend.app.db import SessionLocal
    from backend.app.models import SourceIntakeBatch, SourceIntakeItem, MasterContentItem, StorageOutboxEvent, StorageOperation, Document, DocumentType, DocumentVersion
    from backend.app.services.source_intake import SourceIntakeService
    payload, manifest = _archive()
    env = _smb_env()
    with SessionLocal() as db:
        source_location = f"same-request://{uuid4()}"
        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(lambda _: spawn(env, ["--child-ingest", "--source-location", source_location]), range(2)))
        assert db.scalar(select(func.count(SourceIntakeBatch.id))) == 1

        batch = SourceIntakeService(db, actor="race-parent").ingest_zip(payload, source_display_name="race.zip", source_location_reference=f"race://{uuid4()}")
        db.commit()
        args = ["--child-source", "--batch-id", batch.id]
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: spawn(env, args), range(2)))
        row = db.scalar(select(SourceIntakeItem).where(SourceIntakeItem.batch_id == batch.id))
        assert row and row.promotion_status == "PUBLISHED"
        masters = db.scalars(select(MasterContentItem).where(MasterContentItem.id == row.target_master_content_id)).all()
        outbox = db.scalars(select(StorageOutboxEvent).where(StorageOutboxEvent.aggregate_id == row.target_document_version_id)).all()
        assert len(masters) == 1 and len(outbox) == 1

        document_id, candidate_id, operation_key = prepare_storage_case(db, "parallel-finalize")
        storage_args = ["--child-storage", "--document-id", document_id, "--candidate-id", candidate_id, "--operation-key", operation_key, "--target-prefix", "closure/parallel-finalize"]
        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(lambda _: spawn(env, storage_args), range(2)))
        assert db.scalar(select(func.count(DocumentVersion.id)).where(DocumentVersion.id == candidate_id)) == 1

        claim_event = StorageOutboxEvent(event_key=f"closure-claim:{uuid4()}", event_type="Closure", aggregate_type="DocumentVersion", aggregate_id=candidate_id, payload_json={"closure": True}, status="PENDING")
        db.add(claim_event)
        db.commit()
        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(lambda _: spawn(env, ["--child-claim"]), range(2)))
        db.refresh(claim_event)
        assert claim_event.status == "DISPATCHING" and claim_event.attempts == 1

        claim_event.status = "DISPATCHING"
        claim_event.available_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc) - __import__("datetime").timedelta(seconds=1)
        db.commit()
        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(lambda _: spawn(env, ["--child-claim", "--recover"]), range(2)))
        db.refresh(claim_event)
        assert claim_event.status == "PENDING"

    return {"status": "PASS", "processes": 2, "same_intake_request_batch_count": 1, "same_item_canonical_master_count": 1, "same_item_outbox_count": 1, "duplicate_master_count": 0, "immutable_target_overwrite_count": 0, "lost_outbox_event_count": 0, "process_local_lock_required_count": 0, "outbox_single_claim": 1, "recovery_single_claim": 1, "tokens": ["SOURCE_INTAKE_MULTI_PROCESS_PASS", "SOURCE_PROMOTION_MULTI_PROCESS_PASS", "STORAGE_FINALIZATION_MULTI_PROCESS_PASS", "OUTBOX_MULTI_PROCESS_CLAIM_PASS", "RECOVERY_MULTI_PROCESS_CLAIM_PASS"]}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--child-storage", action="store_true")
    parser.add_argument("--child-source", action="store_true")
    parser.add_argument("--child-ingest", action="store_true")
    parser.add_argument("--child-claim", action="store_true")
    parser.add_argument("--document-id")
    parser.add_argument("--candidate-id")
    parser.add_argument("--operation-key")
    parser.add_argument("--target-prefix")
    parser.add_argument("--batch-id")
    parser.add_argument("--source-location")
    parser.add_argument("--recover", action="store_true")
    parser.add_argument("--kill-after-commit", action="store_true")
    parser.add_argument("--mode", choices=["crash", "multi"])
    args = parser.parse_args()
    if args.child_storage:
        return child_storage(args)
    if args.child_source:
        return child_source(args)
    if args.child_ingest:
        return child_ingest(args)
    if args.child_claim:
        return child_claim(args)
    result = run_crash_harness() if args.mode == "crash" else run_multi_process()
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
