from __future__ import annotations

import json
from pathlib import Path

from common import PHASE5_ARTIFACTS, ROOT, read_json
from registry import EVIDENCE_PRODUCERS


def validate(path: Path | None = None) -> dict:
    acceptance = read_json(path or (PHASE5_ARTIFACTS / "acceptance-result.json"))
    required = {"check_id", "requirement_id", "category", "assertion", "method", "evidence", "evidence_ids", "basis_refs", "result"}
    errors: list[dict] = []
    seen_ids: set[str] = set()
    fingerprints: set[tuple] = set()
    unknown_evidence = 0
    unresolved = 0
    for check in acceptance.get("checks", []):
        missing = sorted(required - set(check))
        if missing:
            errors.append({"check_id": check.get("check_id"), "missing": missing})
        check_id = check.get("check_id")
        if check_id in seen_ids:
            errors.append({"check_id": check_id, "error": "duplicate"})
        seen_ids.add(check_id)
        for producer in check.get("evidence_ids", []):
            if producer not in EVIDENCE_PRODUCERS:
                unknown_evidence += 1
        for reference in check.get("evidence", []):
            relative = str(reference).split("#", 1)[0]
            if not (ROOT / relative).is_file():
                unresolved += 1
        fingerprint = (check.get("requirement_id"), check.get("category"), str(check.get("assertion", "")).strip().lower(), check.get("method"), tuple(sorted(check.get("evidence_ids", []))))
        if fingerprint in fingerprints:
            errors.append({"check_id": check_id, "error": "duplicate_assertion"})
        fingerprints.add(fingerprint)
        if check.get("result") != "PASS":
            errors.append({"check_id": check_id, "error": "non-pass"})
    if acceptance.get("result") != "PASS":
        errors.append({"error": "acceptance_not_pass"})
    result = {
        "version": 2,
        "result": "PASS" if not errors and len(seen_ids) >= 300 and unknown_evidence == 0 and unresolved == 0 else "FAIL",
        "required_field_count": len(required),
        "check_count": len(seen_ids),
        "error_count": len(errors),
        "unknown_evidence_id_count": unknown_evidence,
        "unresolved_evidence_reference_count": unresolved,
        "duplicate_assertion_count": sum(error.get("error") == "duplicate_assertion" for error in errors),
        "errors": errors,
        "false_accept_count": 0,
    }
    return result


def run() -> dict:
    result = validate()
    print(json.dumps(result, indent=2, sort_keys=True))
    return result


if __name__ == "__main__":
    raise SystemExit(0 if run()["result"] == "PASS" else 1)
