from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from registry import producer_paths
except ModuleNotFoundError:
    from .registry import producer_paths


TRUTH_DOMAINS = {"M1", "M2", "M3", "M4", "M5", "M6", "M7", "FINANCE", "MASTER_CONTENT", "REPORTS"}
MASTER_CONTENT_TYPES = {"FORM", "REPORT", "ENGINEERING_WORK", "DEFINITION"}


def run(corpus_path: Path, output: Path, evidence_dir: Path | None = None, candidate_sha: str | None = None, validation_sha: str | None = None, run_id: str | None = None) -> dict[str, Any]:
    corpus = json.loads(corpus_path.read_text(encoding="utf-8"))
    domains = corpus.get("truth_domain_coverage", [])
    types = corpus.get("master_content_type_coverage", [])
    domain_ids = {item.get("coverage_id") for item in domains}
    type_ids = {item.get("coverage_id") for item in types}
    errors = []
    if domain_ids != TRUTH_DOMAINS:
        errors.append("truth-domain-set")
    if type_ids != MASTER_CONTENT_TYPES:
        errors.append("master-content-type-set")
    if any(item.get("safe_disposition") != "REVIEW_OR_ABSTAIN" for item in domains + types):
        errors.append("unsafe-disposition")
    if corpus.get("coverage_summary", {}).get("unknown_or_unaccounted_count") != 0:
        errors.append("unknown-or-unaccounted")
    result = {
        "version": 1, "producer_id": "corpus-coverage", "result": "PASS" if not errors else "FAIL",
        "truth_domain_count": len(domains), "master_content_type_count": len(types),
        "truth_domain_expected_count": 10, "master_content_type_expected_count": 4,
        "unknown_or_unaccounted_count": corpus.get("coverage_summary", {}).get("unknown_or_unaccounted_count"),
        "fabricated_adequate_count": corpus.get("coverage_summary", {}).get("fabricated_adequate_count"),
        "errors": errors, "synthetic_only": True, "real_data_used": False,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if evidence_dir is not None:
        if not all((candidate_sha, validation_sha, run_id)):
            raise ValueError("candidate, validation, and run identity are required for producer evidence")
        paths = producer_paths("corpus-coverage", evidence_dir)
        paths["raw"].write_text("producer=corpus-coverage\n", encoding="utf-8")
        paths["meta"].write_text(json.dumps({"producer_id": "corpus-coverage", "candidate_sha": candidate_sha, "validation_sha": validation_sha, "run_id": run_id, "exit_code": 0 if result["result"] == "PASS" else 1}, sort_keys=True) + "\n", encoding="utf-8")
        paths["result"].write_text(json.dumps(result, sort_keys=True) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--evidence-dir", type=Path)
    parser.add_argument("--candidate-sha")
    parser.add_argument("--validation-sha")
    parser.add_argument("--run-id")
    args = parser.parse_args()
    raise SystemExit(0 if run(args.corpus, args.output, args.evidence_dir, args.candidate_sha, args.validation_sha, args.run_id)["result"] == "PASS" else 1)
