"""Hidden source-intake reconciliation and promotion service."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..models import SourceIntakeBatch, SourceIntakeItem
from ..storage.archive import ArchiveEntryObservation, BoundedZipReader
from ..storage.external import StableSourceRead
from ..storage.fixture_exclusion import is_fixture_excluded_path
from .master_content import create_master_content
from ..storage.failpoints import hard_kill_if_requested

DISPOSITIONS = {
    "PROMOTE_MASTER_CURRENT",
    "PROMOTE_MASTER_NEEDS_REVIEW",
    "TRANSACTIONAL_OR_HISTORICAL_SOURCE",
    "REFERENCE_ONLY",
    "BLOCKED_AMBIGUOUS",
    "SOURCE_GAP",
}


def _path_key(path: str) -> str:
    return path.removeprefix("FORME/").strip("/")


def _safe_title(path: str) -> str:
    stem = Path(path).stem.replace("_", " ").strip()
    return re.sub(r"\s+", " ", stem)[:240] or "Imported source document"


def _content_type(item: dict[str, Any]) -> str:
    mapping = str(item.get("dashboard_mapping", "Forms")).lower()
    return "ENGINEERING_WORK" if "engineering" in mapping else "REPORT" if "report" in mapping else "FORM"


class SourceIntakeService:
    def __init__(self, db: Session, *, actor: str = "source-intake-v1.4"):
        self.db = db
        self.actor = actor

    def ingest_zip(self, payload: bytes, *, source_display_name: str, source_location_reference: str) -> SourceIntakeBatch:
        if is_fixture_excluded_path(source_location_reference):
            raise ValueError("SOURCE_EXCLUDED_SYNTHETIC_FIXTURE_OR_INVENTORY")
        digest = hashlib.sha256(payload).hexdigest()
        prior = self.db.scalar(select(SourceIntakeBatch).where(SourceIntakeBatch.source_archive_hash == digest, SourceIntakeBatch.source_location_reference == source_location_reference))
        if prior:
            return prior
        reader = BoundedZipReader(payload)
        raw_observations = reader.observations()
        excluded = any(is_fixture_excluded_path(o.normalized_safe_path) for o in raw_observations)
        observations = reader.observations_with_hashes(exclude=is_fixture_excluded_path)
        if excluded and not any(not observation.is_dir for observation in observations):
            raise ValueError("SOURCE_EXCLUDED_SYNTHETIC_FIXTURE_OR_INVENTORY")
        file_paths = {o.normalized_safe_path for o in observations if not o.is_dir}
        effective: list[ArchiveEntryObservation] = []
        for observation in observations:
            if not observation.is_dir:
                effective.append(observation)
                continue
            prefix = observation.normalized_safe_path.rstrip("/") + "/"
            if not any(path.startswith(prefix) for path in file_paths):
                effective.append(observation)
        batch = SourceIntakeBatch(source_kind="ZIP", source_display_name=source_display_name, source_archive_hash=digest, source_location_reference=source_location_reference, received_by=self.actor, status="DISCOVERED", item_count_discovered=len(effective), empty_folder_count_observed=sum(1 for o in effective if o.is_dir), metadata_json={"archive_entry_count": len(observations)})
        try:
            with self.db.begin_nested():
                self.db.add(batch)
                self.db.flush()
        except IntegrityError:
            existing = self.db.scalar(select(SourceIntakeBatch).where(SourceIntakeBatch.source_archive_hash == digest, SourceIntakeBatch.source_location_reference == source_location_reference))
            if existing:
                return existing
            raise
        for observation in effective:
            self.db.add(SourceIntakeItem(batch_id=batch.id, source_ordinal=observation.ordinal, original_relative_path=observation.original_relative_path, original_filename=Path(observation.normalized_safe_path).name if not observation.is_dir else None, normalized_safe_path=observation.normalized_safe_path, size_bytes=observation.size_bytes, sha256=observation.sha256, media_type=observation.media_type, source_locator=f"archive://{digest}/{observation.normalized_safe_path}", disposition="SOURCE_GAP" if observation.is_dir else None, promotion_status="DISPOSITIONED" if observation.is_dir else "NOT_STARTED", metadata_json={"is_directory": observation.is_dir}))
        batch.status = "DISCOVERED"
        self.db.flush()
        return batch

    def apply_manifest(self, batch: SourceIntakeBatch, manifest: dict[str, Any]) -> dict[str, int]:
        manifest_by_path = {_path_key(str(row["relative_path"])): row for row in manifest.get("items", [])}
        rows = self.db.scalars(select(SourceIntakeItem).where(SourceIntakeItem.batch_id == batch.id).order_by(SourceIntakeItem.source_ordinal)).all()
        if is_fixture_excluded_path(batch.source_location_reference) or any(is_fixture_excluded_path(row.original_relative_path) for row in rows):
            raise ValueError("SOURCE_EXCLUDED_SYNTHETIC_FIXTURE_OR_INVENTORY")
        if len(rows) != len(manifest_by_path):
            raise ValueError(f"manifest/item count mismatch: {len(manifest_by_path)} != {len(rows)}")
        counts: dict[str, int] = {}
        for row in rows:
            if row.disposition == "SOURCE_GAP":
                key = _path_key(row.normalized_safe_path)
                match = next((value for path, value in manifest_by_path.items() if (path.rstrip("/") == key.rstrip("/") or path.rstrip("/").removesuffix("/[NO FILE]") == key.rstrip("/")) and value.get("v1_4_disposition") == "SOURCE_FOLDER_EMPTY"), None)
            else:
                match = manifest_by_path.get(_path_key(row.normalized_safe_path))
            if not match or (row.sha256 and match.get("sha256") != row.sha256):
                raise ValueError(f"manifest does not exactly reconcile source item {row.original_relative_path}")
            disposition = str(match.get("v1_4_disposition", "")).replace("_DUPLICATE", "")
            if disposition == "SOURCE_FOLDER_EMPTY":
                disposition = "SOURCE_GAP"
            if disposition not in DISPOSITIONS:
                raise ValueError(f"unsupported disposition {disposition}")
            row.disposition = disposition
            row.disposition_reason = match.get("required_action") or match.get("summary")
            row.duplicate_group = "sha256:" + row.sha256 if disposition == "BLOCKED_AMBIGUOUS" and row.sha256 else None
            row.metadata_json = {**(row.metadata_json or {}), "manifest": {"version": manifest.get("version"), "audit_index": match.get("audit_index"), "dashboard_mapping": match.get("dashboard_mapping"), "category": match.get("category"), "used_in": match.get("used_in")}}
            row.promotion_status = "DISPOSITIONED"
            counts[disposition] = counts.get(disposition, 0) + 1
        batch.manifest_version = str(manifest.get("version", "v1"))
        batch.status = "DISPOSITIONED"
        self.db.flush()
        return counts

    def promote_batch(self, batch: SourceIntakeBatch, payload: bytes, manifest: dict[str, Any]) -> dict[str, int]:
        if hashlib.sha256(payload).hexdigest() != batch.source_archive_hash:
            raise ValueError("source archive hash does not match intake batch")
        self.apply_manifest(batch, manifest)
        hard_kill_if_requested("SOURCE_ITEM_DURABLE_BEFORE_PROMOTION")
        reader = BoundedZipReader(payload)
        by_path = {_path_key(o.normalized_safe_path): o for o in reader.observations_with_hashes(exclude=is_fixture_excluded_path) if not o.is_dir}
        counts: dict[str, int] = {}
        row_ids = self.db.scalars(select(SourceIntakeItem.id).where(SourceIntakeItem.batch_id == batch.id).order_by(SourceIntakeItem.source_ordinal)).all()
        for row_id in row_ids:
            # PostgreSQL row locking is the correctness mechanism for two
            # independent workers racing the same source item. SQLite keeps
            # the same code path for secondary tests, where the lock is a no-op.
            row = self.db.scalar(select(SourceIntakeItem).where(SourceIntakeItem.id == row_id).with_for_update())
            if not row:
                continue
            disposition = row.disposition
            if disposition in {"SOURCE_GAP", "TRANSACTIONAL_OR_HISTORICAL_SOURCE", "REFERENCE_ONLY", "BLOCKED_AMBIGUOUS"}:
                row.promotion_status = "HELD" if disposition != "SOURCE_GAP" else "DISPOSITIONED"
                counts[disposition] = counts.get(disposition, 0) + 1
                continue
            if row.promotion_status == "PUBLISHED" and row.target_master_content_id:
                counts[disposition] = counts.get(disposition, 0) + 1
                continue
            observation = by_path.get(_path_key(row.normalized_safe_path))
            if not observation or observation.sha256 != row.sha256:
                raise ValueError(f"source item missing or changed before promotion: {row.original_relative_path}")
            content = observation.read_bytes()
            if hashlib.sha256(content).hexdigest() != row.sha256:
                raise ValueError(f"source item hash mismatch: {row.original_relative_path}")
            row.promotion_status = "PROMOTING"
            self.db.flush()
            metadata = row.metadata_json.get("manifest", {}) if row.metadata_json else {}
            result = create_master_content(self.db, content_type=_content_type(metadata), ref=None, title=_safe_title(row.normalized_safe_path), category_id=None, description=metadata.get("category"), filename=row.original_filename or "source.bin", mime_type=observation.media_type or "application/octet-stream", content=content, actor=self.actor, idempotency_key=f"source-intake:{row.id}", correlation_id=f"source-intake:{batch.id}:{row.id}", source_surface="SOURCE_INTAKE_V1_4", used_in=["PERMIT", "ENGINEERING"] if _content_type(metadata) == "FORM" else ["REPORTS"], engineering_metadata={"source_intake_batch_id": batch.id, "source_intake_item_id": row.id, "original_relative_path": row.original_relative_path}, needs_review=disposition == "PROMOTE_MASTER_NEEDS_REVIEW", review_note=row.disposition_reason if disposition == "PROMOTE_MASTER_NEEDS_REVIEW" else None)
            row.target_master_content_id = result["id"]
            row.target_document_version_id = result.get("current_version_id")
            hard_kill_if_requested("OUTBOX_DURABLE_BEFORE_SOURCE_ITEM_FINAL")
            row.promotion_status = "PUBLISHED"
            counts[disposition] = counts.get(disposition, 0) + 1
            self.db.flush()
        batch.status = "COMPLETED"
        batch.completed_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
        self.db.commit()
        return counts

    def manifest_from_json(self, text: str) -> dict[str, Any]:
        return json.loads(text)
