import io
import json
import zipfile
from uuid import uuid4

from sqlalchemy import select

from backend.app.db import SessionLocal
from backend.app.models import MasterContentItem, SourceIntakeItem
from backend.app.services.source_intake import SourceIntakeService


def make_archive():
    entries = [("FORME/Current Form.pdf", b"current"), ("FORME/Needs Review.pdf", b"review"), ("FORME/History.pdf", b"history"), ("FORME/Reference.jpeg", b"reference"), ("FORME/Duplicate A.docx", b"same"), ("FORME/Duplicate B.docx", b"same"), ("FORME/EMPTY/", b"")]
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        for name, content in entries:
            archive.writestr(name, content)
    return stream.getvalue()


def test_intake_reconciles_every_observation_and_promotes_only_master_rows():
    payload = make_archive()
    digest = __import__("hashlib").sha256(payload).hexdigest()
    manifest = {"version": "v1", "items": [
        {"relative_path": "Current Form.pdf", "sha256": __import__("hashlib").sha256(b"current").hexdigest(), "v1_4_disposition": "PROMOTE_MASTER_CURRENT", "dashboard_mapping": "Forms"},
        {"relative_path": "Needs Review.pdf", "sha256": __import__("hashlib").sha256(b"review").hexdigest(), "v1_4_disposition": "PROMOTE_MASTER_NEEDS_REVIEW", "dashboard_mapping": "Forms"},
        {"relative_path": "History.pdf", "sha256": __import__("hashlib").sha256(b"history").hexdigest(), "v1_4_disposition": "TRANSACTIONAL_OR_HISTORICAL_SOURCE"},
        {"relative_path": "Reference.jpeg", "sha256": __import__("hashlib").sha256(b"reference").hexdigest(), "v1_4_disposition": "REFERENCE_ONLY"},
        {"relative_path": "Duplicate A.docx", "sha256": __import__("hashlib").sha256(b"same").hexdigest(), "v1_4_disposition": "BLOCKED_AMBIGUOUS_DUPLICATE"},
        {"relative_path": "Duplicate B.docx", "sha256": __import__("hashlib").sha256(b"same").hexdigest(), "v1_4_disposition": "BLOCKED_AMBIGUOUS_DUPLICATE"},
        {"relative_path": "EMPTY", "v1_4_disposition": "SOURCE_FOLDER_EMPTY"},
    ]}
    with SessionLocal() as db:
        service = SourceIntakeService(db)
        batch = service.ingest_zip(payload, source_display_name="synthetic.zip", source_location_reference=f"test://{uuid4()}")
        counts = service.promote_batch(batch, payload, manifest)
        rows = db.scalars(select(SourceIntakeItem).where(SourceIntakeItem.batch_id == batch.id)).all()
        assert len(rows) == 7
        assert counts["PROMOTE_MASTER_CURRENT"] == 1
        assert counts["PROMOTE_MASTER_NEEDS_REVIEW"] == 1
        assert counts["BLOCKED_AMBIGUOUS"] == 2
        assert counts["SOURCE_GAP"] == 1
        assert db.scalar(select(MasterContentItem).where(MasterContentItem.needs_review.is_(True), MasterContentItem.title == "Needs Review"))
        assert db.scalar(select(MasterContentItem).where(MasterContentItem.title == "Current Form"))
        assert db.scalar(select(MasterContentItem).where(MasterContentItem.title == "History")) is None
        assert batch.status == "COMPLETED"
        second_counts = service.promote_batch(batch, payload, manifest)
        assert second_counts["PROMOTE_MASTER_CURRENT"] == 1
        assert db.query(MasterContentItem).filter(MasterContentItem.title == "Current Form").count() == 1
