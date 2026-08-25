from __future__ import annotations

import argparse
import json
from pathlib import Path

from finalize import produce, run, seal


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=("produce", "seal"))
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--contracts-dir", type=Path, default=Path("contracts/amec/phase5"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-candidate-sha", required=True)
    parser.add_argument("--expected-validation-sha", required=True)
    parser.add_argument("--expected-run-id", required=True)
    parser.add_argument("--pre-finalizer-acceptance-result", type=Path)
    parser.add_argument("--pre-finalizer-validation-result", type=Path)
    parser.add_argument("--acceptance-result", type=Path)
    parser.add_argument("--validation-result", type=Path)
    parser.add_argument("--acceptance-integrity-result", type=Path)
    parser.add_argument("--handoff-seal-result", type=Path)
    parser.add_argument("--local-test-mode", action="store_true")
    args = parser.parse_args()
    if args.stage == "produce":
        if not args.pre_finalizer_acceptance_result or not args.pre_finalizer_validation_result:
            parser.error("produce requires pre-finalizer acceptance and validation")
        result = produce(contracts_dir=args.contracts_dir, evidence_dir=args.evidence_dir, pre_finalizer_acceptance_path=args.pre_finalizer_acceptance_result, pre_finalizer_validation_path=args.pre_finalizer_validation_result, output_path=args.output, expected_candidate_sha=args.expected_candidate_sha, expected_validation_sha=args.expected_validation_sha, expected_run_id=args.expected_run_id)
    elif args.stage == "seal":
        if any(item is None for item in (args.acceptance_result, args.validation_result, args.acceptance_integrity_result, args.handoff_seal_result)):
            parser.error("seal requires final acceptance, validation, integrity, and handoff paths")
        result = seal(contracts_dir=args.contracts_dir, evidence_dir=args.evidence_dir, acceptance_path=args.acceptance_result, validation_path=args.validation_result, acceptance_integrity_path=args.acceptance_integrity_result, output_path=args.output, handoff_path=args.handoff_seal_result, expected_candidate_sha=args.expected_candidate_sha, expected_validation_sha=args.expected_validation_sha, expected_run_id=args.expected_run_id)
    else:
        # Compatibility only; workflow calls must specify produce or seal.
        if not args.acceptance_result or not args.validation_result:
            parser.error("legacy invocation requires acceptance and validation")
        result = run(args.contracts_dir, args.acceptance_result, args.evidence_dir, args.output, expected_candidate_sha=args.expected_candidate_sha, expected_validation_sha=args.expected_validation_sha, expected_run_id=args.expected_run_id, validation_result_path=args.validation_result, local_test_mode=args.local_test_mode)
    print(json.dumps({"result": result.get("result", result.get("summary", {}).get("result", "PASS"))}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
