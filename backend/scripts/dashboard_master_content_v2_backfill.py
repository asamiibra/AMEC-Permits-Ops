"""Idempotently reconcile existing master-content rows with the v2 metadata seams.

This script never rewrites source bytes or business references. It only fills
additive defaults, seeds reference policy rows, and materializes bindings from
the already-authoritative ``used_in`` values.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
os.chdir(REPO_ROOT)
sys.path.insert(0, str(REPO_ROOT))

from sqlalchemy import select  # noqa: E402

from backend.app.db import SessionLocal, engine  # noqa: E402
from backend.app.models import DefinitionEntry, DefinitionRevision, DocumentVersion, MasterContentItem  # noqa: E402
from backend.app.services.master_content import _sync_module_bindings, seed_categories, seed_reference_sequences  # noqa: E402


def _modules(value):
    if not isinstance(value, list):
        return []
    return sorted({str(item).strip().upper() for item in value if str(item).strip()})


def main() -> None:
    if engine.dialect.name != "postgresql":
        raise RuntimeError("Dashboard master-content v2 backfill requires PostgreSQL")
    with SessionLocal() as db:
        seed_categories(db)
        seed_reference_sequences(db)
        item_count = 0
        binding_count = 0
        rendition_count = 0
        for item in db.scalars(select(MasterContentItem)).all():
            item.used_in = _modules(item.used_in)
            item.engineering_metadata = item.engineering_metadata if isinstance(item.engineering_metadata, dict) else {}
            current = db.get(DocumentVersion, item.current_document_version_id) if item.current_document_version_id else None
            if current:
                is_pdf = current.mime_type == "application/pdf" or current.source_filename.lower().endswith(".pdf")
                if is_pdf and current.rendition_status != "SOURCE_PDF":
                    current.rendition_status = "SOURCE_PDF"
                    current.rendition_path_or_reference = current.source_path_or_reference
                    current.rendition_sha256 = current.sha256
                    current.rendition_mime_type = "application/pdf"
                    current.rendition_file_size = current.file_size
                    rendition_count += 1
            _sync_module_bindings(db, item_id=item.id, modules=item.used_in, actor="v2-backfill")
            item_count += 1
        definition_count = 0
        for definition in db.scalars(select(DefinitionEntry)).all():
            definition.used_in = _modules(definition.used_in)
            current = db.get(DefinitionRevision, definition.current_revision_id) if definition.current_revision_id else None
            if current:
                current.category = current.category if current.category is not None else definition.category
                current.used_in = _modules(current.used_in or definition.used_in)
            definition_count += 1
        db.commit()
        result = {
            "status": "APPLIED",
            "database": engine.url.render_as_string(hide_password=True),
            "master_content_rows_reconciled": item_count,
            "definition_rows_reconciled": definition_count,
            "rendition_metadata_filled": rendition_count,
            "reference_policy": "seeded_and_existing_numeric_suffixes_preserved",
            "source_bytes_rewritten": False,
        }
        print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
