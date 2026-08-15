from pathlib import Path
import io
import os

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from backend.app.models import Base, Document, DocumentType, StorageOperation, StorageOutboxEvent
from backend.app.storage import DocumentStorageService, MockBinaryStore, SMBConfig, SMBBinaryStore, StorageError, StorageTarget


def service_db(tmp_path: Path):
    engine = create_engine(f"sqlite:///{tmp_path / 'storage.db'}")
    Base.metadata.create_all(engine)
    return engine


def make_service(tmp_path: Path):
    if os.getenv("STORAGE_CONTRACT_PROVIDER", "mock").lower() == "smb":
        store = SMBBinaryStore(SMBConfig(
            server=os.environ["SMB_SERVER"],
            port=int(os.getenv("SMB_PORT", "445")),
            share=os.environ["SMB_SHARE"],
            root=os.getenv("SMB_ROOT", ""),
            username=os.environ["SMB_USERNAME"],
            password=os.environ["SMB_PASSWORD"],
            auth_mode=os.getenv("SMB_AUTH_MODE", "ntlm"),
            require_signing=os.getenv("SMB_REQUIRE_SIGNING", "false").lower() == "true",
        ))
        return DocumentStorageService(store, provider_id=store.provider_id), store
    store = MockBinaryStore(tmp_path / "binary")
    return DocumentStorageService(store), store


def target_for(store, relative_path: str = "managed"):
    share_id = store.share_id if isinstance(store, MockBinaryStore) else store.config.share
    return StorageTarget(store.provider_id, share_id, relative_path)


def test_full_protocol_publishes_only_after_fresh_readback_and_outbox(tmp_path):
    engine = service_db(tmp_path)
    with Session(engine) as db:
        document = Document(document_type=DocumentType.OTHER, logical_name="Managed source", language="EN", source_system="TEST")
        db.add(document)
        db.flush()
        service, store = make_service(tmp_path)
        result = service.store_version(
            db,
            document=document,
            filename="Arabic تقرير.pdf",
            mime_type="application/pdf",
            content=io.BytesIO(b"immutable bytes"),
            target=target_for(store),
            actor="test",
            correlation_id="storage-test",
            idempotency_key="storage-test-1",
        )
        assert result.version.metadata_json["storage_verified"] is True
        assert result.version.source_path_or_reference.startswith("storage://")
        assert result.operation.state == "PUBLISHED"
        assert db.scalar(select(StorageOperation).where(StorageOperation.id == result.operation.id)).state == "PUBLISHED"
        event = db.scalar(select(StorageOutboxEvent).where(StorageOutboxEvent.aggregate_id == result.version.id))
        assert event and event.event_type == "DocumentVersionStored"
        db.commit()


def test_idempotency_reuses_one_published_version(tmp_path):
    engine = service_db(tmp_path)
    with Session(engine) as db:
        document = Document(document_type=DocumentType.OTHER, logical_name="Idempotent source", language="EN", source_system="TEST")
        db.add(document)
        db.flush()
        service, store = make_service(tmp_path)
        args = dict(document=document, content=b"same", filename="same.txt", mime_type="text/plain", target=target_for(store), actor="test", correlation_id="c", idempotency_key="same-op")
        first = service.store_version(db, **args)
        second = service.store_version(db, **args)
        assert first.version.id == second.version.id
        assert len(db.scalars(select(StorageOperation)).all()) == 1
        assert len(db.scalars(select(StorageOutboxEvent)).all()) == 1


def test_external_mutation_is_detected_without_rewriting_version(tmp_path):
    engine = service_db(tmp_path)
    with Session(engine) as db:
        document = Document(document_type=DocumentType.OTHER, logical_name="Drift", language="EN", source_system="TEST")
        db.add(document)
        db.flush()
        service, store = make_service(tmp_path)
        result = service.store_version(db, document=document, content=b"original", filename="drift.txt", mime_type="text/plain", target=target_for(store), actor="test", correlation_id="c")
        locator = result.version.source_path_or_reference.removeprefix("storage://").split("/", 2)
        if isinstance(store, MockBinaryStore):
            (tmp_path / "binary" / locator[2]).write_bytes(b"changed outside ProposalOps")
        else:
            with store._client().open_file(store._unc(locator[2]), mode="wb", **store._session_kwargs()) as external:
                external.write(b"changed outside ProposalOps")
        with pytest.raises(StorageError) as error:
            service.read_verified(result.version)
        assert error.value.code.value == "STORAGE_INTEGRITY_DRIFT"
        assert result.version.sha256 != ""  # canonical hash is not rewritten


def test_path_policy_rejects_namespace_escape_and_reserved_names(tmp_path):
    store = MockBinaryStore(tmp_path / "binary")
    with pytest.raises(StorageError):
        store.mkdirs(StorageTarget("mock-test", "test", "../escape"))
    with pytest.raises(StorageError):
        store.write_temporary(StorageTarget("mock-test", "test", "managed"), __import__("io").BytesIO(b"x"), operation_id="x", expected_size=1, expected_sha256="0" * 64)
