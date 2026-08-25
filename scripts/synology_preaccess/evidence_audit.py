#!/usr/bin/env python3
"""Audit generated evidence for provenance and status-shape defects."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ALLOWED = {"PASS", "FAIL", "WARN", "ENV_BLOCKED", "NOT_EXECUTED"}
DEFERRED = {"REAL_SMB_SERVER_SIDE_PAGINATION", "REAL_SMB_HARD_OPERATION_ABORT", "REAL_DSM_REPARSE_REFERRAL"}


def audit(path: Path) -> list[str]:
    errors: list[str] = []
    registry = json.loads((path / "50_ACCEPTANCE_REGISTRY.json").read_text(encoding="utf-8"))
    checks = registry.get("checks", [])
    if len(checks) < 180:
        errors.append("fewer than 180 checks")
    if len({item.get("check_id") for item in checks}) != len(checks):
        errors.append("duplicate check ids")
    for item in checks:
        if item.get("result") not in ALLOWED:
            errors.append(f"invalid result: {item.get('check_id')}")
        refs = item.get("evidence_refs", [])
        if not refs or any("50_ACCEPTANCE_REGISTRY" in ref for ref in refs):
            errors.append(f"invalid evidence provenance: {item.get('check_id')}")
    warnings = {item.get("assertion") for item in checks if item.get("result") == "WARN"}
    if warnings != DEFERRED:
        errors.append("WARN set is not exactly the three declared deferred capabilities")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", required=True, type=Path)
    args = parser.parse_args()
    errors = audit(args.evidence.resolve())
    payload = {"status": "PASS" if not errors else "FAIL", "errors": errors}
    print(json.dumps(payload, sort_keys=True))
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
