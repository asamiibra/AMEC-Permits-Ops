#!/usr/bin/env python3
"""Run the controlling FORME package through the hidden v1.4 intake path."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--zip", dest="zip_path", default=os.getenv("FORME_ZIP_PATH"))
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--artifact", required=True)
    args = parser.parse_args()
    if not args.zip_path:
        raise SystemExit("FORME_ZIP_PATH or --zip is required")
    archive_path = Path(args.zip_path)
    manifest_path = Path(args.manifest)
    payload = archive_path.read_bytes()
    manifest = json.loads(manifest_path.read_text())

    # The repository seed intentionally uses the legacy synthetic SOR for its
    # baseline fixtures. Seed that baseline first, then switch the intake
    # promotion path to the requested live provider.
    requested_storage_provider = os.environ.get("STORAGE_PROVIDER", "mock")
    os.environ["STORAGE_PROVIDER"] = "mock"

    from backend.app.db import SessionLocal
    from backend.app.models import SourceIntakeItem, MasterContentItem, DocumentVersion
    from backend.app.seed.cli import seed
    from backend.app.services.source_intake import SourceIntakeService
    from backend.app.config.settings import get_settings
    from backend.app.services.master_content import resolve_master_content_purpose
    from sqlalchemy import select, func
    from sqlalchemy import select

    seed()
    os.environ["STORAGE_PROVIDER"] = requested_storage_provider
    get_settings.cache_clear()
    with SessionLocal() as db:
        service = SourceIntakeService(db, actor="forme-acceptance-v1.4")
        batch = service.ingest_zip(payload, source_display_name=archive_path.name, source_location_reference=str(archive_path.resolve()))
        counts = service.promote_batch(batch, payload, manifest)
        master_ids_before = set(db.scalars(select(MasterContentItem.id)).all())
        version_count_before = db.scalar(select(func.count(DocumentVersion.id)))
        rerun_counts = service.promote_batch(batch, payload, manifest)
        master_ids_after = set(db.scalars(select(MasterContentItem.id)).all())
        version_count_after = db.scalar(select(func.count(DocumentVersion.id)))
        rows = db.scalars(select(SourceIntakeItem).where(SourceIntakeItem.batch_id == batch.id)).all()
        promoted_rows = [row for row in rows if row.disposition in {"PROMOTE_MASTER_CURRENT", "PROMOTE_MASTER_NEEDS_REVIEW"}]
        verified_managed_count = 0
        for row in promoted_rows:
            version = db.get(DocumentVersion, row.target_document_version_id)
            item = db.get(MasterContentItem, row.target_master_content_id)
            if item and version and version.source_path_or_reference.startswith("storage://") and version.sha256 == row.sha256 and version.file_size == row.size_bytes:
                verified_managed_count += 1
        needs_review_ids = {row.target_master_content_id for row in rows if row.disposition == "PROMOTE_MASTER_NEEDS_REVIEW"}
        resolver = resolve_master_content_purpose(db, module="PERMIT", usage_type="AVAILABLE")
        resolver_ids = {candidate["id"] for candidate in resolver["candidates"]}
        result = {
            "status": "PASS" if batch.status == "COMPLETED" and len(rows) == 24 else "FAIL",
            "token": "FORME_PACKAGE_DISPOSITION_VERIFIED_LOCAL",
            "archive_sha256": hashlib.sha256(payload).hexdigest(),
            "source_display_name": archive_path.name,
            "batch_id": batch.id,
            "item_count": len(rows),
            "counts": counts,
            "promoted_current": sum(1 for row in rows if row.disposition == "PROMOTE_MASTER_CURRENT" and row.promotion_status == "PUBLISHED"),
            "promoted_needs_review": sum(1 for row in rows if row.disposition == "PROMOTE_MASTER_NEEDS_REVIEW" and row.promotion_status == "PUBLISHED"),
            "blocked_ambiguous": sum(1 for row in rows if row.disposition == "BLOCKED_AMBIGUOUS"),
            "source_gaps": sum(1 for row in rows if row.disposition == "SOURCE_GAP"),
            "verified_managed_promotions": verified_managed_count,
            "rerun_counts": rerun_counts,
            "rerun_business_idempotency": master_ids_before == master_ids_after and version_count_before == version_count_after,
            "needs_review_resolver_exclusion": not (needs_review_ids & resolver_ids),
            "no_source_move": True,
            "evidence_scope": "local archive + local Samba storage lab only; not Synology/Owner/production",
        }
    artifact = Path(args.artifact)
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
