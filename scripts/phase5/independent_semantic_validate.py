"""Independent Phase5 semantic oracle.

This module deliberately has no dependency on the primary acceptance, registry,
or evidence-validator implementations.  It reads only the frozen v2 contract,
producer artifacts, and the acceptance rows supplied to it.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _at(value: Any, path: str) -> Any:
    for part in path.split("."):
        if not isinstance(value, dict) or part not in value:
            raise KeyError(path)
        value = value[part]
    return value


def _evaluate(operator: str, observed: Any, expected: Any) -> bool:
    if operator == "eq": return observed == expected
    if operator == "zero": return isinstance(observed, int) and not isinstance(observed, bool) and observed == 0
    if operator == "nonzero": return isinstance(observed, (int, float)) and not isinstance(observed, bool) and observed != 0
    if operator == "true": return observed is True
    if operator == "false": return observed is False
    if operator == "exists": return True
    if operator == "count_eq": return isinstance(observed, list) and len(observed) == expected
    if operator == "set_eq": return isinstance(observed, list) and set(observed) == set(expected)
    if operator == "contains": return expected in observed
    if operator == "all_pass": return isinstance(observed, dict) and all(item == "PASS" for item in observed.values())
    return False


def validate(spec_path: Path, acceptance_path: Path, evidence_dir: Path, candidate: str, validation: str, run_id: str) -> dict[str, Any]:
    spec = _json(spec_path)
    entries = {(item.get("category"), item.get("assertion")): item for item in spec.get("entries", [])}
    acceptance = _json(acceptance_path)
    checks = acceptance.get("checks", [])
    failures: list[dict[str, Any]] = []
    generic = specific = tautology = mismatches = 0
    for check in checks:
        key = (check.get("category"), check.get("assertion"))
        entry = entries.get(key)
        row_fail = False
        recomputed: list[dict[str, Any]] = []
        if entry is None:
            failures.append({"check_id": check.get("check_id"), "error": "missing_spec"}); continue
        for proof in entry.get("proofs", []):
            producer = proof.get("producer_id")
            kind = proof.get("artifact_kind")
            name = f"{producer}.{'meta.json' if kind == 'meta' else 'result.json'}"
            path = evidence_dir / name
            observed: Any = "MISSING"; passed = False; digest = None
            try:
                payload = _json(path); digest = hashlib.sha256(path.read_bytes()).hexdigest()
                observed = _at(payload, proof["json_path"])
                passed = _evaluate(proof["operator"], observed, proof.get("expected"))
                if kind == "meta" and (payload.get("producer_id") != producer or payload.get("candidate_sha") != candidate or payload.get("validation_sha") != validation or str(payload.get("run_id")) != str(run_id) or payload.get("exit_code") != 0):
                    passed = False
            except (OSError, json.JSONDecodeError, KeyError, TypeError):
                passed = False
            row = {"producer_id": producer, "artifact_kind": kind, "artifact_name": name, "json_path": proof.get("json_path"), "operator": proof.get("operator"), "expected": proof.get("expected"), "observed": observed, "result": "PASS" if passed else "FAIL", "artifact_sha256": digest, "observed_from_artifact": digest is not None}
            recomputed.append(row)
            if not passed: row_fail = True
            if digest is None or proof.get("json_path") == "result": tautology += 1
        supplied = check.get("semantic_proofs", [])
        if recomputed and all(row.get("json_path") == "result" for row in recomputed): generic += 1
        elif recomputed and any(row.get("json_path") != "result" and row.get("observed_from_artifact") for row in recomputed): specific += 1
        if len(supplied) != len(recomputed) or any((a.get("producer_id"), a.get("json_path"), a.get("observed"), a.get("result")) != (b.get("producer_id"), b.get("json_path"), b.get("observed"), b.get("result")) for a, b in zip(supplied, recomputed)):
            mismatches += 1; row_fail = True
        if row_fail or check.get("result") != "PASS":
            failures.append({"check_id": check.get("check_id"), "error": "semantic_failure"})
    result = {"version": 1, "result": "PASS" if len(checks) == 300 and not failures and generic == 0 and specific == 300 and tautology == 0 and mismatches == 0 else "FAIL", "independent_semantic_validator": "PASS" if len(checks) == 300 and not failures else "FAIL", "independent_semantic_check_count": len(checks), "independent_semantic_fail_count": len(failures), "independent_semantic_mismatch_count": mismatches, "independent_generic_result_only_count": generic, "independent_specific_field_count": specific, "independent_tautology_count": tautology, "failures": failures}
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--acceptance", type=Path, required=True)
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--candidate-sha", required=True)
    parser.add_argument("--validation-sha", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = validate(args.spec, args.acceptance, args.evidence_dir, args.candidate_sha, args.validation_sha, args.run_id)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
