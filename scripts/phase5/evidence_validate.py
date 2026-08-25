from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from common import PHASE5_ARTIFACTS, read_json
    from registry import EVIDENCE_PRODUCERS, producer_paths
except ModuleNotFoundError:
    from .common import PHASE5_ARTIFACTS, read_json
    from .registry import EVIDENCE_PRODUCERS, producer_paths


REQUIRED_FIELDS = {"check_id", "requirement_id", "category", "assertion", "method", "evidence", "evidence_ids", "basis_refs", "result"}


def validate(acceptance_path: Path, evidence_dir: Path) -> dict[str, Any]:
    errors: list[dict[str, Any]] = []
    try:
        acceptance = read_json(acceptance_path)
    except (OSError, json.JSONDecodeError):
        return {"version": 3, "result": "FAIL", "error_count": 1, "errors": [{"error": "invalid_acceptance"}]}
    seen: set[str] = set()
    fingerprints: set[tuple[Any, ...]] = set()
    producer_states: dict[str, str] = {}
    for check in acceptance.get("checks", []):
        missing = sorted(REQUIRED_FIELDS - set(check))
        if missing:
            errors.append({"check_id": check.get("check_id"), "error": "missing_fields", "fields": missing})
        check_id = check.get("check_id")
        if not check_id or check_id in seen:
            errors.append({"check_id": check_id, "error": "duplicate_or_missing_check_id"})
        seen.add(check_id)
        fingerprint = (check.get("requirement_id"), check.get("category"), str(check.get("assertion", "")).strip().lower(), check.get("method"), tuple(sorted(check.get("evidence_ids", []))))
        if fingerprint in fingerprints:
            errors.append({"check_id": check_id, "error": "duplicate_assertion"})
        fingerprints.add(fingerprint)
        for producer_id in check.get("evidence_ids", []):
            if producer_id not in EVIDENCE_PRODUCERS:
                errors.append({"check_id": check_id, "error": "unknown_evidence_id", "producer_id": producer_id})
                continue
            paths = producer_paths(producer_id, evidence_dir)
            if any(not path.is_file() or path.stat().st_size == 0 for path in paths.values()):
                errors.append({"check_id": check_id, "error": "missing_or_zero_byte_producer", "producer_id": producer_id})
                producer_states[producer_id] = "MISSING"
                continue
            try:
                meta = json.loads(paths["meta"].read_text(encoding="utf-8"))
                payload = json.loads(paths["result"].read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                errors.append({"check_id": check_id, "error": "invalid_producer_json", "producer_id": producer_id})
                producer_states[producer_id] = "INVALID"
                continue
            state = str(payload.get("result", "FAIL"))
            producer_states[producer_id] = state
            if meta.get("exit_code") != 0 or state in {"NOT_EXECUTED", "DRY_RUN"}:
                errors.append({"check_id": check_id, "error": "producer_not_executed_or_failed", "producer_id": producer_id, "state": state})
            if check.get("result") == "PASS" and state != "PASS":
                errors.append({"check_id": check_id, "error": "pass_without_producer_pass", "producer_id": producer_id})
        if check.get("result") != "PASS":
            errors.append({"check_id": check_id, "error": "non_pass_primary_check"})
        if any("acceptance.py" in str(item) for item in check.get("evidence", [])):
            errors.append({"check_id": check_id, "error": "self_referential_acceptance_evidence"})
    if acceptance.get("result") != "PASS":
        errors.append({"error": "acceptance_not_pass"})
    runtime_required_source_only = sum(EVIDENCE_PRODUCERS[item]["runtime_required"] and producer_states.get(item) == "PASS" for item in producer_states)
    return {
        "version": 3, "result": "PASS" if not errors and len(seen) == 300 else "FAIL",
        "required_field_count": len(REQUIRED_FIELDS), "check_count": len(seen), "error_count": len(errors),
        "unknown_evidence_id_count": sum(item.get("error") == "unknown_evidence_id" for item in errors),
        "unresolved_evidence_reference_count": sum(item.get("error", "").startswith("missing") for item in errors),
        "duplicate_assertion_count": sum(item.get("error") == "duplicate_assertion" for item in errors),
        "runtime_required_source_only_pass_count": runtime_required_source_only,
        "false_accept_count": sum(item.get("error") in {"producer_not_executed_or_failed", "pass_without_producer_pass"} for item in errors),
        "producer_states": producer_states, "errors": errors,
    }


def run(evidence_dir: Path, acceptance_path: Path, output: Path) -> dict[str, Any]:
    result = validate(acceptance_path, evidence_dir)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--acceptance-result", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    return 0 if run(args.evidence_dir, args.acceptance_result, args.output)["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
