from __future__ import annotations

import base64
import hashlib
import json
from types import SimpleNamespace

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from backend.app.auth.bridge import BridgeIdentity
from backend.app.models import Base, ProposalSourceScanEntry
from backend.app.schemas.bridge_intake import BridgeScanEntryIn, BridgeScanIn
from backend.app.services.bridge_intake import (
    canonical_scan_signature_payload,
    ingest_bridge_scan,
)


def test_scan_finalization_collapses_duplicate_inventory_paths(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'bridge-scan.db'}")
    Base.metadata.create_all(engine)
    private_key = Ed25519PrivateKey.generate()
    entries = [
        BridgeScanEntryIn(
            relative_path="454 - Al Watan Center/Client data/repeated.pdf",
            entry_type="FILE",
            size_bytes=10,
            mtime_token="1",
            sha256="a" * 64,
            capture_status="CAPTURED",
            source_version_token="1:a",
        ),
        BridgeScanEntryIn(
            relative_path="454 - Al Watan Center/Client data/repeated.pdf",
            entry_type="FILE",
            size_bytes=11,
            mtime_token="2",
            sha256="b" * 64,
            capture_status="CAPTURED",
            source_version_token="2:b",
        ),
    ]
    manifest_hash = hashlib.sha256(
        json.dumps(
            sorted((entry.model_dump(mode="json") for entry in entries), key=lambda item: item["relative_path"]),
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    payload = BridgeScanIn(
        scan_id="qatar-scan-duplicate-test",
        source_identity="QATAR_SYNOLOGY_LIVE",
        source_root="Tenders/1- Proposal/2026",
        source_project_identity="qatar-live:454",
        project_number="454",
        status="COMPLETED",
        started_at="2026-09-18T12:00:00Z",
        completed_at="2026-09-18T12:01:00Z",
        entries=entries,
        counts={"files_seen": 2, "files_successfully_captured": 2},
        manifest_hash=manifest_hash,
        signature_b64="pending",
    )
    payload = payload.model_copy(update={
        "signature_b64": base64.b64encode(private_key.sign(canonical_scan_signature_payload(payload))).decode(),
    })
    settings = SimpleNamespace(
        bridge_allowed_source_identities="QATAR_SYNOLOGY_LIVE",
        bridge_allowed_source_path_prefixes="synology://qatar/Tenders/1- Proposal/2026/",
        bridge_package_signing_public_key=base64.b64encode(private_key.public_key().public_bytes_raw()).decode(),
    )
    identity = BridgeIdentity("tenant", "client", "bridge-object", "audience", "proposalops.source-intake")

    with Session(engine) as db:
        result = ingest_bridge_scan(db, payload, identity, settings)
        db.commit()
        rows = db.scalars(select(ProposalSourceScanEntry)).all()

    assert result["result"] == "RECORDED"
    assert len(rows) == 1
    assert rows[0].relative_path.endswith("repeated.pdf")
    assert rows[0].source_version_token == "2:b"
    engine.dispose()
