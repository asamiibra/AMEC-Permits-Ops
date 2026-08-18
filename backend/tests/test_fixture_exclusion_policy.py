import io
import zipfile
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select

from backend.app.adapters.synology.adapter import MockSynologyAdapter
from backend.app.db import SessionLocal
from backend.app.models import SourceIntakeBatch, SourceIntakeItem
from backend.app.services.source_intake import SourceIntakeService
from backend.app.services.master_content import create_master_content, read_master_content_bytes
from backend.app.services.document_intelligence import LocalSyntheticExtractor, RuleBasedDocumentClassifier, sha256_for_source
from backend.app.storage.archive import ArchiveEntryObservation, BoundedZipReader
from backend.app.storage.fixture_exclusion import (
    FixturePathExcludedError,
    filter_fixture_excluded_paths,
    is_fixture_excluded_path,
)
from backend.app.storage.mock import MockBinaryStore
from backend.app.storage.port import StorageLocator
from backend.app.storage.smb import SMBConfig, SMBBinaryStore


REQUIRED_CANARIES = [
    "ADMIN WORKS/ProposalOps_Certification/Phase3B_0_4/v1/preflight/admin_works-preflight-canary.bin",
    "Correspondence/ProposalOps_Certification/Phase3B_0_4/v1/preflight/correspondence-preflight-canary.bin",
    "DESIGN/ProposalOps_Certification/Phase3B_0_4/v1/preflight/design-preflight-canary.bin",
    "PRO/ProposalOps_Certification/Phase3B_0_4/v1/preflight/pro-preflight-canary.bin",
    "Services Provider/ProposalOps_Certification/Phase3B_0_4/v1/preflight/services_provider-preflight-canary.bin",
    "Supervision/ProposalOps_Certification/Phase3B_0_4/v1/preflight/supervision-preflight-canary.bin",
    "Tenders/ProposalOps_Certification/Phase3B_0_4/v1/preflight/tenders-preflight-canary.bin",
]


def make_zip(entries: list[tuple[str, bytes]]) -> bytes:
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        for name, content in entries:
            archive.writestr(name, content)
    return stream.getvalue()


def test_all_controlled_roots_future_paths_and_supported_normalization_fail_closed():
    paths = [
        "ProposalOps-Inventory/anything.bin",
        *REQUIRED_CANARIES,
        "Tenders/ProposalOps_Certification/Phase3B_0_4/v9/stream/stream-canary-16MiB.bin",
        "Tenders/ProposalOps_Certification/Phase3B_0_4/v9/nested/future.bin",
        r"\\AMEC\DESIGN\ProposalOps_Certification\Phase3B_0_4\v2\future.bin",
        "./Tenders/ProposalOps_Certification/Phase3B_0_4/v3/future.bin",
        "../ProposalOps_Certification/Phase3B_0_4/v3/traversal.bin",
    ]
    assert all(is_fixture_excluded_path(path) for path in paths)


def test_legitimate_paths_and_similarly_named_files_remain_allowed():
    eligible, excluded = filter_fixture_excluded_paths([
        "Tenders/ordinary-business.pdf",
        "DESIGN/ordinary-business.dwg",
        "ProposalOps_Certification_notes.docx",
        *REQUIRED_CANARIES,
    ])
    assert eligible == [
        "Tenders/ordinary-business.pdf",
        "DESIGN/ordinary-business.dwg",
        "ProposalOps_Certification_notes.docx",
    ]
    assert excluded == REQUIRED_CANARIES


def test_archive_hashing_skips_excluded_members_before_content_read(monkeypatch):
    payload = make_zip([
        (REQUIRED_CANARIES[0], b"fixture"),
        ("Tenders/ordinary.pdf", b"business-control"),
    ])
    original_read_bytes = ArchiveEntryObservation.read_bytes
    observed_reads: list[str] = []

    def record_read(observation):
        observed_reads.append(observation.normalized_safe_path)
        if is_fixture_excluded_path(observation.normalized_safe_path):
            raise AssertionError("excluded fixture was read before filtering")
        return original_read_bytes(observation)

    monkeypatch.setattr(ArchiveEntryObservation, "read_bytes", record_read)
    observations = BoundedZipReader(payload).observations_with_hashes(exclude=is_fixture_excluded_path)
    assert [item.normalized_safe_path for item in observations] == ["Tenders/ordinary.pdf"]
    assert observed_reads == ["Tenders/ordinary.pdf"]


def test_fixture_only_source_short_circuits_before_source_business_row_creation():
    payload = make_zip([(REQUIRED_CANARIES[0], b"fixture")])
    with SessionLocal() as db:
        before = db.scalar(select(func.count(SourceIntakeBatch.id)))
        with pytest.raises(ValueError, match="SOURCE_EXCLUDED_SYNTHETIC_FIXTURE_OR_INVENTORY"):
            SourceIntakeService(db).ingest_zip(payload, source_display_name="fixture-only.zip", source_location_reference=f"test://{uuid4()}")
        after = db.scalar(select(func.count(SourceIntakeBatch.id)))
        assert after == before
        assert db.scalars(select(SourceIntakeItem)).all() == []


def test_mixed_source_filters_fixture_before_promotion_and_keeps_business_control(monkeypatch):
    payload = make_zip([
        (REQUIRED_CANARIES[0], b"fixture"),
        ("Tenders/ordinary.pdf", b"business-control"),
    ])
    digest = __import__("hashlib").sha256(b"business-control").hexdigest()
    calls: list[str] = []

    def fake_create_master_content(*args, **kwargs):
        calls.append(kwargs["filename"])
        return {"id": "synthetic-control-master", "current_version_id": "synthetic-control-version"}

    monkeypatch.setattr("backend.app.services.source_intake.create_master_content", fake_create_master_content)
    with SessionLocal() as db:
        service = SourceIntakeService(db)
        batch = service.ingest_zip(payload, source_display_name="mixed.zip", source_location_reference=f"test://{uuid4()}")
        rows = db.scalars(select(SourceIntakeItem).where(SourceIntakeItem.batch_id == batch.id)).all()
        assert [row.original_relative_path for row in rows] == ["Tenders/ordinary.pdf"]
        manifest = {"version": "v1", "items": [{"relative_path": "Tenders/ordinary.pdf", "sha256": digest, "v1_4_disposition": "PROMOTE_MASTER_CURRENT", "dashboard_mapping": "Forms"}]}
        service.promote_batch(batch, payload, manifest)
        assert calls == ["ordinary.pdf"]


def test_storage_and_synology_boundaries_fail_closed(tmp_path):
    with pytest.raises(FixturePathExcludedError):
        MockBinaryStore(tmp_path / "binary").open_read(StorageLocator("mock-test", "test", REQUIRED_CANARIES[0]))

    smb = object.__new__(SMBBinaryStore)
    smb.config = SMBConfig(server="synthetic", share="test", username="u", password="p")
    with pytest.raises(FixturePathExcludedError):
        smb._unc(REQUIRED_CANARIES[0])

    adapter = MockSynologyAdapter(str(tmp_path / "synology"))
    with pytest.raises(FixturePathExcludedError):
        adapter.list_project_files("ProposalOps-Inventory")
    with pytest.raises(FixturePathExcludedError):
        adapter.read_configured_artifact(REQUIRED_CANARIES[0])


def test_direct_master_content_create_and_read_boundaries_fail_closed():
    with pytest.raises(HTTPException) as create_error:
        create_master_content(
            None,
            content_type="REPORT",
            ref=None,
            title="fixture",
            category_id=None,
            description=None,
            filename="fixture.bin",
            mime_type="application/octet-stream",
            content=b"fixture",
            actor="test",
            idempotency_key="fixture-boundary",
            correlation_id="fixture-boundary",
            engineering_metadata={"original_relative_path": REQUIRED_CANARIES[0]},
        )
    assert create_error.value.detail["code"] == "FIXTURE_SOURCE_EXCLUDED"

    with pytest.raises(FixturePathExcludedError):
        read_master_content_bytes(None, SimpleNamespace(source_path_or_reference=REQUIRED_CANARIES[0]))


def test_classification_extraction_and_source_hash_boundaries_fail_closed():
    version = SimpleNamespace(source_path_or_reference=REQUIRED_CANARIES[0], metadata_json={"synthetic_text": "TITLE DEED"})
    with pytest.raises(FixturePathExcludedError):
        RuleBasedDocumentClassifier().classify(version)
    with pytest.raises(FixturePathExcludedError):
        LocalSyntheticExtractor().extract_text(version)
    with pytest.raises(FixturePathExcludedError):
        sha256_for_source(REQUIRED_CANARIES[0])
