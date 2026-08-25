from __future__ import annotations

import argparse
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

REQUIRED_GATES = [
    "source_event_idempotency", "replay_stable_across_time", "evidence_intake_idempotency",
    "classification_envelope_immutability", "review_locking_concurrency", "correction_append_only",
    "reviewed_assertion_promotion", "assertion_supersession", "projection_idempotency",
    "duplicate_side_effect_protection", "rollback", "freeze_metadata", "hard_gate_short_circuit",
    "out_of_scope_no_projection", "secret_exclude_no_projection", "protected_action_denial",
]


def _junit(path: Path) -> dict[str, str]:
    root = ET.parse(path).getroot()
    cases = root.findall(".//testcase")
    statuses: dict[str, str] = {}
    for case in cases:
        name = case.attrib.get("name", "")
        status = "PASS"
        if case.find("failure") is not None or case.find("error") is not None:
            status = "FAIL"
        elif case.find("skipped") is not None:
            status = "NOT_EXECUTED"
        statuses[name] = status
    return statuses


def run(junitxml: Path, bootstrap_result: Path, output: Path) -> dict[str, Any]:
    statuses = _junit(junitxml)
    bootstrap = json.loads(bootstrap_result.read_text(encoding="utf-8"))
    gates: dict[str, str] = {}
    for gate in REQUIRED_GATES:
        candidates = [name for name in statuses if gate in name]
        gates[gate] = statuses[candidates[0]] if candidates else "NOT_EXECUTED"
    failed = sum(value == "FAIL" for value in gates.values())
    skipped = sum(value == "NOT_EXECUTED" for value in gates.values())
    engine_ok = bootstrap.get("engine") == "MICROSOFT_SQL_SERVER_2022_X64" and bootstrap.get("sqlserver_major") == 16
    result = {
        "version": 2, "result": "PASS" if not failed and not skipped and engine_ok and bootstrap.get("result") == "PASS" else "FAIL",
        "engine": bootstrap.get("engine"), "sqlserver_major": bootstrap.get("sqlserver_major"),
        "migration_head": bootstrap.get("migration_head"), "migration_pass": bootstrap.get("migration_pass"),
        "gate_count": len(REQUIRED_GATES), "failed_count": failed, "skipped_count": skipped,
        "gates": gates, "gate_test_names": {gate: next((name for name in statuses if gate in name), None) for gate in REQUIRED_GATES},
        "database_schema_delta": bootstrap.get("database_schema_delta"), "junit_testcase_count": len(statuses),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--junitxml", type=Path, required=True)
    parser.add_argument("--bootstrap-result", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    return 0 if run(args.junitxml, args.bootstrap_result, args.output)["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
