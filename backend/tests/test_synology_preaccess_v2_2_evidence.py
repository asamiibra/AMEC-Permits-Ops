from __future__ import annotations

import hashlib
import json

from scripts.synology_preaccess.evidence_audit import audit
from scripts.synology_preaccess.generate_evidence import build_registry, write_evidence
from backend.tests.test_evidence_synology_preaccess import write_fixture


def root_manifest(root):
    lines = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != "ROOT_MANIFEST.sha256":
            lines.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(root).as_posix()}")
    (root / "ROOT_MANIFEST.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")


def complete_artifact(tmp_path):
    raw = write_fixture(tmp_path)
    checks, metadata = build_registry(raw, artifact_root=tmp_path)
    write_evidence(tmp_path, "synthetic-v2.2", checks, metadata)
    (tmp_path / "evidence" / "52_ARTIFACT_HYGIENE.json").write_text(json.dumps({
        "scanner_executed": True,
        "files_scanned": 1,
        "patterns_checked": ["GHP_TOKEN"],
        "match_count": 0,
        "matches": [],
        "errors": [],
        "status": "PASS",
    }), encoding="utf-8")
    root_manifest(tmp_path)
    return tmp_path


def test_artifact_raw_evidence_presence_and_resolved_refs(tmp_path):
    result = audit(complete_artifact(tmp_path))
    assert result["status"] == "PASS"
    assert result["unresolved_evidence_ref_count"] == 0


def test_unresolved_evidence_ref_negative(tmp_path):
    root = complete_artifact(tmp_path)
    (root / "raw" / "entry_git.txt").unlink()
    result = audit(root)
    assert result["status"] == "FAIL" and result["unresolved_evidence_ref_count"] > 0


def test_normalized_duplicate_assertion_negative(tmp_path):
    root = complete_artifact(tmp_path)
    path = root / "evidence" / "50_ACCEPTANCE_REGISTRY.json"
    payload = json.loads(path.read_text())
    duplicate = dict(payload["checks"][0])
    duplicate["check_id"] = "SYN-PRE-V2-2-DUPLICATE"
    payload["checks"].append(duplicate)
    path.write_text(json.dumps(payload), encoding="utf-8")
    root_manifest(root)
    result = audit(root)
    assert result["status"] == "FAIL" and result["normalized_assertion_duplicate_count"] > 0


def test_unlisted_artifact_file_negative(tmp_path):
    root = complete_artifact(tmp_path)
    (root / "raw" / "unlisted.txt").write_text("unlisted", encoding="utf-8")
    result = audit(root)
    assert result["status"] == "FAIL"


def test_self_reference_negative(tmp_path):
    root = complete_artifact(tmp_path)
    path = root / "evidence" / "50_ACCEPTANCE_REGISTRY.json"
    payload = json.loads(path.read_text())
    payload["checks"][0]["evidence_refs"] = ["50_ACCEPTANCE_REGISTRY.json"]
    path.write_text(json.dumps(payload), encoding="utf-8")
    root_manifest(root)
    result = audit(root)
    assert result["status"] == "FAIL" and result["self_reference_count"] > 0
