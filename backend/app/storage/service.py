from __future__ import annotations

import hashlib
import io
import tempfile
from dataclasses import dataclass
from datetime import timedelta
from typing import BinaryIO, Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit.service import audit
from ..models import Document, DocumentApprovalState, DocumentVersion, StorageOperation, StorageOutboxEvent
from ..models.base import utcnow
from .errors import StorageError, StorageErrorCode
from .path_policy import normalize_filename, normalize_relative_path
from .port import BinaryStorePort, StorageLocator, StorageTarget
from .failpoints import hard_kill_if_requested


@dataclass(frozen=True)
class StoredVersion:
    document: Document
    version: DocumentVersion
    operation: StorageOperation


class DocumentStorageService:
    """Provider-independent verified binary workflow.

    The caller owns the surrounding PostgreSQL transaction. Until this method
    returns successfully, no normal DocumentVersion row or current pointer is
    published. A StorageOperation journal is flushed at every state boundary
    so an enclosing transaction can persist the outcome with the business
    write.
    """

    def __init__(self, store: BinaryStorePort, *, provider_id: str | None = None, layout_version: str = "1"):
        self.store = store
        self.provider_id = provider_id or getattr(store, "provider_id", "storage")
        self.layout_version = layout_version

    @staticmethod
    def _hash_stream(stream: BinaryIO) -> tuple[int, str]:
        digest = hashlib.sha256()
        size = 0
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
            size += len(chunk)
        return size, digest.hexdigest()

    def _target(self, target: StorageTarget, document_id: str, version_id: str, filename: str) -> StorageTarget:
        safe_prefix = normalize_relative_path(target.relative_path)
        safe_name = normalize_filename(filename)
        return StorageTarget(target.provider_id, target.share_id, f"{safe_prefix}/documents/{document_id}/{version_id}/{safe_name}")

    def store_version(
        self,
        db: Session,
        *,
        document: Document,
        content: BinaryIO | bytes,
        filename: str,
        mime_type: str,
        target: StorageTarget,
        actor: str,
        correlation_id: str,
        idempotency_key: str | None = None,
        source_system: str = "DOCUMENT_STORAGE",
        metadata: dict[str, Any] | None = None,
        version_number: int | None = None,
        candidate_version_id: str | None = None,
    ) -> StoredVersion:
        stream = io.BytesIO(content) if isinstance(content, bytes) else content
        original_filename = filename
        safe_filename = normalize_filename(filename)
        stream_position = stream.tell() if hasattr(stream, "tell") else 0
        size, digest = self._hash_stream(stream)
        if hasattr(stream, "seek"):
            stream.seek(stream_position)
        operation_key = idempotency_key or f"{document.id}:{digest}:{safe_filename}"
        # Serialize concurrent retries of one logical operation on PostgreSQL.
        # The winner holds this row lock through finalization/publication; a
        # follower then observes PUBLISHED and returns the canonical version.
        prior_operation = db.scalar(select(StorageOperation).where(StorageOperation.idempotency_key == operation_key).with_for_update())
        if prior_operation and prior_operation.state == "PUBLISHED" and prior_operation.document_version_id:
            prior_version = db.get(DocumentVersion, prior_operation.document_version_id)
            if prior_version:
                return StoredVersion(document, prior_version, prior_operation)
        candidate_id = candidate_version_id or (prior_operation.document_version_id if prior_operation and prior_operation.document_version_id else str(uuid4()))
        final_target = self._target(target, document.id, candidate_id, safe_filename)
        operation = prior_operation or StorageOperation(
            idempotency_key=operation_key,
            operation_type="STORE_DOCUMENT_VERSION",
            document_id=document.id,
            document_version_id=candidate_id,
            provider_id=self.provider_id,
            target_locator=StorageLocator(final_target.provider_id, final_target.share_id, final_target.relative_path, self.layout_version).serialized(),
            expected_sha256=digest,
            expected_size=size,
            state="PLANNED",
            metadata_json={"original_filename": original_filename, "safe_filename": safe_filename, **(metadata or {})},
        )
        db.add(operation)
        db.flush()
        hard_kill_if_requested("STORAGE_OPERATION_RESERVED")
        operation.attempt_count += 1
        operation.state = "WRITING"
        operation.lease_expires_at = utcnow() + timedelta(minutes=15)
        db.flush()
        temporary = None
        try:
            directory_target = StorageTarget(target.provider_id, target.share_id, normalize_relative_path(target.relative_path))
            self.store.mkdirs(directory_target)
            temporary = self.store.write_temporary(directory_target, stream, operation_id=operation.id, expected_size=size, expected_sha256=digest)
            operation.temporary_locator = temporary.locator.serialized()
            operation.state = "READBACK_VERIFYING"
            db.flush()
            hard_kill_if_requested("TEMP_WRITE_COMPLETED")

            with self.store.open_read(temporary.locator) as readback:
                read_size, read_digest = self._hash_stream(readback)
            if read_size != size or read_digest != digest:
                operation.state = "FAILED_FINAL"
                operation.last_error_class = StorageErrorCode.INTEGRITY_MISMATCH.value
                operation.last_error_message = "Fresh SMB read-back did not match the input stream"
                db.flush()
                raise StorageError(StorageErrorCode.INTEGRITY_MISMATCH, "Storage read-back verification failed")

            hard_kill_if_requested("READBACK_VERIFIED")

            operation.state = "FINALIZING"
            db.flush()
            locator = self.store.finalize(temporary, final_target)
            operation.state = "STORAGE_VERIFIED"
            operation.temporary_locator = None
            db.flush()
            hard_kill_if_requested("FINAL_BINARY_EXISTS")

            with self.store.open_read(locator) as final_readback:
                final_size, final_digest = self._hash_stream(final_readback)
            if final_size != size or final_digest != digest:
                operation.state = "FAILED_FINAL"
                operation.last_error_class = StorageErrorCode.INTEGRITY_MISMATCH.value
                operation.last_error_message = "Final object verification failed"
                db.flush()
                raise StorageError(StorageErrorCode.INTEGRITY_MISMATCH, "Final storage verification failed")

            existing = db.get(DocumentVersion, candidate_id)
            if existing:
                if existing.sha256 != digest or existing.file_size != size:
                    raise StorageError(StorageErrorCode.CONFLICT, "Candidate version identity is already bound to different bytes")
                version = existing
                version.source_filename = original_filename
                version.source_path_or_reference = locator.serialized()
                version.mime_type = mime_type or "application/octet-stream"
                version.file_size = size
                version.sha256 = digest
                version.metadata_json = {**(version.metadata_json or {}), "storage_verified": True, "read_back_verified": True, "storage_provider": self.provider_id, "storage_locator": locator.serialized(), **(metadata or {})}
            else:
                prior = db.scalar(select(DocumentVersion).where(DocumentVersion.document_id == document.id).order_by(DocumentVersion.version_number.desc()))
                next_number = version_number or ((prior.version_number + 1) if prior else 1)
                version = DocumentVersion(
                    id=candidate_id,
                    document_id=document.id,
                    version_number=next_number,
                    source_filename=original_filename,
                    source_path_or_reference=locator.serialized(),
                    sha256=digest,
                    mime_type=mime_type or "application/octet-stream",
                    file_size=size,
                    language=document.language,
                    approval_state=DocumentApprovalState.WORKING,
                    source_system=source_system,
                    metadata_json={"storage_verified": True, "read_back_verified": True, "storage_provider": self.provider_id, "storage_locator": locator.serialized(), **(metadata or {})},
                )
                db.add(version)
                db.flush()
            document.current_version_id = version.id
            operation.state = "DB_PUBLISHING"
            db.flush()
            outbox_key = f"DocumentVersionStored:{version.id}"
            if not db.scalar(select(StorageOutboxEvent).where(StorageOutboxEvent.event_key == outbox_key)):
                db.add(StorageOutboxEvent(event_key=outbox_key, event_type="DocumentVersionStored", aggregate_type="DocumentVersion", aggregate_id=version.id, payload_json={"document_id": document.id, "document_version_id": version.id, "sha256": digest, "storage_locator": locator.serialized()}))
            hard_kill_if_requested("DB_PUBLISH_BEFORE_COMMIT")
            operation.state = "PUBLISHED"
            operation.completed_at = utcnow()
            operation.lease_expires_at = None
            db.flush()
            audit(db, correlation_id=correlation_id, event_type="DOCUMENT_VERSION_STORED", entity_type="DocumentVersion", entity_id=version.id, actor_id=actor, after={"sha256": digest, "size": size, "storage_verified": True, "provider": self.provider_id}, metadata={"storage_operation_id": operation.id, "storage_locator": locator.serialized()})
            return StoredVersion(document, version, operation)
        except StorageError as exc:
            operation.state = "FAILED_RETRYABLE" if exc.retryable else "FAILED_FINAL"
            operation.last_error_class = exc.code.value
            operation.last_error_message = str(exc)
            db.flush()
            if temporary and operation.state == "FAILED_FINAL":
                try:
                    self.store.cleanup_temporary(temporary)
                except Exception:
                    operation.state = "CLEANUP_PENDING"
            raise
        except Exception as exc:
            operation.state = "FAILED_FINAL"
            operation.last_error_class = StorageErrorCode.UNKNOWN.value
            operation.last_error_message = type(exc).__name__
            db.flush()
            raise StorageError(StorageErrorCode.UNKNOWN, "Document storage failed") from exc

    def read_verified(self, version: DocumentVersion, *, verify: bool = True) -> BinaryIO:
        if not version.source_path_or_reference.startswith("storage://"):
            raise StorageError(StorageErrorCode.CONFIGURATION_ERROR, "Document version does not have a provider locator")
        serialized = version.source_path_or_reference.removeprefix("storage://")
        provider_id, share_id, relative = serialized.split("/", 2)
        locator = StorageLocator(provider_id, share_id, relative)
        stream = self.store.open_read(locator)
        if verify:
            output = tempfile.SpooledTemporaryFile(max_size=8 * 1024 * 1024, mode="w+b")
            digest = hashlib.sha256()
            size = 0
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                output.write(chunk)
                digest.update(chunk)
                size += len(chunk)
            stream.close()
            if size != version.file_size or digest.hexdigest() != version.sha256:
                output.close()
                raise StorageError(StorageErrorCode.INTEGRITY_DRIFT, "Stored bytes no longer match the verified DocumentVersion")
            output.seek(0)
            return output
        return stream
