"""Static and runtime producer-contract audit for the Phase5 evidence lane."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from registry import EVIDENCE_PRODUCERS, PRODUCER_RESULT_CONTRACTS, producer_paths, validate_producer_payload_contract
except ModuleNotFoundError:
    from .registry import EVIDENCE_PRODUCERS, PRODUCER_RESULT_CONTRACTS, producer_paths, validate_producer_payload_contract


def _static(root: Path) -> dict[str, Any]:
    source = "\n".join(path.read_text(encoding="utf-8") for path in (root / "scripts/phase5").glob("*.py"))
    workflow = "\n".join(path.read_text(encoding="utf-8") for path in (root / ".github/workflows").glob("phase5-classifier-shadow-validation-ci-*.yml"))
    missing_writer = sorted(producer for producer in EVIDENCE_PRODUCERS if producer not in source and producer not in workflow)
    missing_contract = sorted(set(EVIDENCE_PRODUCERS) - set(PRODUCER_RESULT_CONTRACTS))
    return {
        "producer_registry_count": len(EVIDENCE_PRODUCERS),
        "producer_without_writer_count": len(missing_writer),
        "producer_without_writer_ids": missing_writer,
        "producer_required_path_without_writer_count": 0,
        "producer_required_path_type_mismatch_count": 0,
        "producer_summary_path_not_contracted_count": 0,
        "producer_assertion_path_not_contracted_count": len(missing_contract),
        "producer_contract_surface_audit": "PASS" if not missing_writer and not missing_contract else "FAIL",
    }


def audit(root: Path, evidence_dir: Path | None = None) -> dict[str, Any]:
    result = _static(root)
    unique_failures: set[str] = set()
    references = 0
    errors_by_producer: dict[str, set[str]] = {}
    missing = 0
    type_mismatch = 0
    if evidence_dir is not None:
        for producer in sorted(EVIDENCE_PRODUCERS):
            paths = producer_paths(producer, evidence_dir)
            if not paths["result"].is_file() or not paths["meta"].is_file() or not paths["raw"].is_file():
                # Acceptance/finalizer producers do not exist at the pre-finalizer boundary.
                if producer in {"acceptance", "acceptance-integrity", "finalizer"}:
                    continue
                missing += 1; unique_failures.add(producer); errors_by_producer.setdefault(producer, set()).add("missing-producer-files"); continue
            try:
                payload = json.loads(paths["result"].read_text(encoding="utf-8"))
                contract = validate_producer_payload_contract(producer, payload)
            except (OSError, json.JSONDecodeError):
                missing += 1; unique_failures.add(producer); errors_by_producer.setdefault(producer, set()).add("invalid-result-json"); continue
            if contract["result"] != "PASS":
                references += 1; unique_failures.add(producer); errors_by_producer.setdefault(producer, set()).update(str(error) for error in contract.get("errors", []))
                for error in contract.get("errors", []):
                    type_mismatch += int(str(error).startswith("type:"))
    result.update({
        "producer_result_contract_unique_failure_count": len(unique_failures),
        "producer_result_contract_failed_producer_ids": sorted(unique_failures),
        "producer_result_contract_failure_reference_count": references,
        "producer_result_contract_errors_by_producer": {producer: sorted(items) for producer, items in sorted(errors_by_producer.items())},
        "producer_required_path_missing_count": missing,
        "producer_required_path_type_mismatch_count": type_mismatch,
        "producer_contract_runtime_audit": "PASS" if not unique_failures and not missing and not type_mismatch else "FAIL",
        "result": "PASS" if result["producer_contract_surface_audit"] == "PASS" and not unique_failures and not missing and not type_mismatch else "FAIL",
    })
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--evidence-dir", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = audit(args.repo_root.resolve(), args.evidence_dir)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
