"""Independent Week 9 execution wrapper.

Runs the existing Week 9 tests against their isolated fixture, captures the
result, and records the attachment/grid/portal-derived evidence boundary.
This is retroactive execution evidence, not a claim that the report existed
at the original Week 9 date.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from backend.app.fixtures.canonical import CANONICAL_FIXTURE_ID, CANONICAL_FIXTURE_MANIFEST_HASH, CANONICAL_FIXTURE_VERSION


def main() -> dict:
    env = os.environ.copy()
    env["PYTHONPATH"] = "."
    result = subprocess.run(["python3", "-m", "pytest", "-q", "backend/tests/test_week9.py"], env=env, capture_output=True, text=True)
    output = (result.stdout + "\n" + result.stderr).strip()
    passed = result.returncode == 0
    evidence = {
        "status": "PASS" if passed else "FAIL",
        "evidence_class": "RETROACTIVE_EXECUTION_EVIDENCE",
        "test_command": "PYTHONPATH=. python3 -m pytest -q backend/tests/test_week9.py",
        "test_output_tail": output[-2000:],
        "attachment_categories": {"active": 17, "order": "deterministic portal_order", "manifest_trace": "category → Document → DocumentVersion → SHA256 → approval/current state"},
        "attachment_persistence": ["MATCH", "MISSING", "WRONG_CATEGORY", "DUPLICATE", "EXTRA", "structure drift"],
        "grid_identity": ["building_ref", "building_ref + floor_ref", "stable canonical row id", "parent identity"],
        "grid_persistence": ["reorder", "missing", "duplicate key", "parent mismatch", "MATCH persistence evidence"],
        "portal_derived": "difference preserves office truth and records LEGITIMATE_SOURCE_DIFFERENCE",
        "week8_staleness_integration": "reused current PreparationRevision/package staleness gate",
        "remaining_live_proof": "approved TEST/live authority behavior remains external",
        "fixture": {"name": CANONICAL_FIXTURE_ID, "version": CANONICAL_FIXTURE_VERSION, "manifest_hash": CANONICAL_FIXTURE_MANIFEST_HASH},
    }
    artifact = Path("artifacts/week9-independent-reconciliation-result.json")
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text(json.dumps(evidence, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(evidence, indent=2, sort_keys=True))
    if not passed:
        raise SystemExit(result.returncode)
    return evidence


if __name__ == "__main__":
    main()
