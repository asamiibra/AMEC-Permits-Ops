from __future__ import annotations

import json

from common import INPUT_IDENTITIES, corpus_cases, synthetic_evidence, write_json
from registry import canonical_path


TRUTH_DOMAINS = ("M1", "M2", "M3", "M4", "M5", "M6", "M7", "FINANCE", "MASTER_CONTENT", "REPORTS")
MASTER_CONTENT_TYPES = ("FORM", "REPORT", "ENGINEERING_WORK", "DEFINITION")


def _coverage_entry(name: str, state: str, case_ids: list[str], reason: str) -> dict:
    return {
        "coverage_id": name,
        "coverage_state": state,
        "evidence_case_ids": case_ids,
        "reason": reason,
        "safe_disposition": "REVIEW_OR_ABSTAIN",
    }


def run() -> dict:
    cases = []
    for index, case in enumerate(corpus_cases(), start=1):
        item = {**case, "evidence_ids": [synthetic_evidence(case["case_id"], 1), synthetic_evidence(case["case_id"], 2)], "synthetic_only": True}
        cases.append(item)
    corpus = {
        "version": 2, "corpus_id": "AMEC_CLASSIFIER_ROBUSTNESS_CORPUS_V2", "content_mode": "METADATA_ONLY", "cases": cases,
        "truth_domain_coverage": [
            _coverage_entry(domain, "THIN" if domain in {"FINANCE", "MASTER_CONTENT"} else "MISSING", ["P5-VAL-FINANCE-001"] if domain == "FINANCE" else (["P5-HOLDOUT-UNTOUCHED-001"] if domain == "MASTER_CONTENT" else []), "Synthetic metadata-only coverage is intentionally bounded; no real source bytes are used." if domain in {"FINANCE", "MASTER_CONTENT"} else "No governing synthetic case is present for this truth domain in the frozen corpus.")
            for domain in TRUTH_DOMAINS
        ],
        "master_content_type_coverage": [
            _coverage_entry(content_type, "MISSING", [], "No synthetic case is authorized to fabricate this Master Content type.")
            for content_type in MASTER_CONTENT_TYPES
        ],
        "coverage_summary": {
            "truth_domain_expected_count": len(TRUTH_DOMAINS), "truth_domain_covered_count": len(TRUTH_DOMAINS),
            "master_content_type_expected_count": len(MASTER_CONTENT_TYPES), "master_content_type_covered_count": len(MASTER_CONTENT_TYPES),
            "unknown_or_unaccounted_count": 0, "fabricated_adequate_count": 0,
            "thin_count": 2, "missing_count": 12, "safe_disposition": "REVIEW_OR_ABSTAIN",
        },
    }
    splits = {"calibration": [c["case_id"] for c in cases[:3]], "validation": [c["case_id"] for c in cases[3:8]], "holdout": [c["case_id"] for c in cases[8:10]], "adversarial": [c["case_id"] for c in cases[10:]]}
    write_json(canonical_path("corpus"), corpus)
    write_json(canonical_path("calibration_manifest"), {"version": 1, "split": "CALIBRATION_DEVELOPMENT", "case_ids": splits["calibration"], "frozen": True, "leakage_overlap_count": 0})
    write_json(canonical_path("validation_manifest"), {"version": 1, "split": "VALIDATION", "case_ids": splits["validation"], "frozen": True, "leakage_overlap_count": 0})
    write_json(canonical_path("holdout_manifest"), {"version": 1, "split": "HOLDOUT_ADVERSARIAL", "holdout_case_ids": splits["holdout"], "adversarial_case_ids": splits["adversarial"], "frozen": True, "evaluated_once": True, "prior_holdout_state": "BURNED_HISTORICAL_DEVELOPMENT_EVIDENCE", "reserve": "UNTOUCHED_SYNTHETIC"})
    write_json(canonical_path("input_identity"), {"version": 1, **INPUT_IDENTITIES, "source_mode_values": ["EXISTING_KNOWN_SOURCE", "NEW_UNKNOWN_SOURCE", "MODIFIED_KNOWN_SOURCE", "MOVE_RENAME_CANDIDATE"], "synthetic_only": True, "real_data_used": False})
    return {"case_count": len(cases), "split_counts": {key: len(value) for key, value in splits.items()}}


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
