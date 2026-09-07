from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.phase5.registry import CANONICAL_ARTIFACTS, EVIDENCE_PRODUCERS

ROOT = Path(__file__).resolve().parents[2]
CONTRACTS = ROOT / "contracts" / "amec" / "phase5"


def test_phase5_acceptance_has_exact_primary_schema_and_300_checks():
    result = subprocess.run([sys.executable, "scripts/phase5/acceptance.py", "--dry-run", "--output", "/tmp/phase5-r3-acceptance.json"], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode != 0
    payload = json.loads(Path("/tmp/phase5-r3-acceptance.json").read_text())
    required = {"check_id", "requirement_id", "category", "assertion", "method", "evidence", "evidence_ids", "basis_refs", "result"}
    assert payload["result"] == "DRY_RUN"
    assert len(payload["checks"]) == 300
    assert all(required <= set(check) and check["result"] == "NOT_EXECUTED" for check in payload["checks"])


def test_phase5_registry_is_canonical_and_non_self_binding():
    assert set(CANONICAL_ARTIFACTS.values()) == {path.name for path in CONTRACTS.glob("*.json")}
    assert all({"producer_id", "raw_log_name", "meta_name", "result_name", "runtime_required"} <= set(value) for value in EVIDENCE_PRODUCERS.values())
    manifest = json.loads((CONTRACTS / CANONICAL_ARTIFACTS["freeze_manifest"]).read_text())
    assert manifest["final_commit_identity"] == "POST_COMMIT_EXTERNAL_HANDOFF"
    assert manifest["final_tree_identity"] == "POST_COMMIT_EXTERNAL_HANDOFF"
