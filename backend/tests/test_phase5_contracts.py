from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.phase5.registry import CANONICAL_ARTIFACTS


ROOT = Path(__file__).resolve().parents[2]
CONTRACTS = ROOT / "contracts" / "amec" / "phase5"


def test_phase5_acceptance_has_exact_primary_schema_and_300_checks():
    subprocess.run([sys.executable, "scripts/phase5/acceptance.py"], cwd=ROOT, check=True)
    payload = json.loads((ROOT / "artifacts/phase5/acceptance-result.json").read_text())
    required = {"check_id", "requirement_id", "category", "assertion", "method", "evidence", "evidence_ids", "basis_refs", "result"}
    checks = payload["checks"]
    assert payload["result"] == "PASS"
    assert len(checks) >= 300
    assert len({check["check_id"] for check in checks}) == len(checks)
    assert all(required <= set(check) and check["result"] == "PASS" for check in checks)


def test_phase5_evidence_validator_and_source_preflight_pass():
    environment = {"PYTHONPATH": str(ROOT / "scripts" / "phase5")}
    evidence = subprocess.run([sys.executable, "scripts/phase5/evidence_validate.py"], cwd=ROOT, env={**environment, "PATH": "/usr/bin:/bin"}, capture_output=True, text=True)
    assert evidence.returncode == 0, evidence.stdout + evidence.stderr
    preflight = subprocess.run([sys.executable, "scripts/phase5/source_preflight.py"], cwd=ROOT, env={**environment, "PATH": "/usr/bin:/bin"}, capture_output=True, text=True)
    assert preflight.returncode == 0, preflight.stdout + preflight.stderr


def test_phase5_freeze_manifest_is_synthetic_and_non_self_binding():
    manifest = json.loads((CONTRACTS / CANONICAL_ARTIFACTS["freeze_manifest"]).read_text())
    assert manifest["freeze_state"] == "FROZEN"
    assert manifest["final_commit_identity"] == "POST_COMMIT_EXTERNAL_HANDOFF"
    assert manifest["final_tree_identity"] == "POST_COMMIT_EXTERNAL_HANDOFF"
    assert manifest["llm_external_call_count"] == 0
    assert manifest["synthetic_only"] is True
    assert manifest["recursive_self_hash"] is False
    assert set(CANONICAL_ARTIFACTS.values()) == {path.name for path in CONTRACTS.glob("*.json")}
