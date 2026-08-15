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
    from backend.app.models import SourceIntakeItem
    from backend.app.seed.cli import seed
    from backend.app.services.source_intake import SourceIntakeService
    from backend.app.config.settings import get_settings
    from sqlalchemy import select

    seed()
    os.environ["STORAGE_PROVIDER"] = requested_storage_provider
    get_settings.cache_clear()
    with SessionLocal() as db:
        service = SourceIntakeService(db, actor="forme-acceptance-v1.4")
        batch = service.ingest_zip(payload, source_display_name=archive_path.name, source_location_reference=str(archive_path.resolve()))
        counts = service.promote_batch(batch, payload, manifest)
        rows = db.scalars(select(SourceIntakeItem).where(SourceIntakeItem.batch_id == batch.id)).all()
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
