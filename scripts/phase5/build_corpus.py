from __future__ import annotations

import json

from common import INPUT_IDENTITIES, corpus_cases, synthetic_evidence, write_json
from registry import canonical_path


def run() -> dict:
    cases = []
    for index, case in enumerate(corpus_cases(), start=1):
        item = {**case, "evidence_ids": [synthetic_evidence(case["case_id"], 1), synthetic_evidence(case["case_id"], 2)], "synthetic_only": True}
        cases.append(item)
    corpus = {"version": 2, "corpus_id": "AMEC_CLASSIFIER_ROBUSTNESS_CORPUS_V2", "content_mode": "METADATA_ONLY", "cases": cases}
    splits = {"calibration": [c["case_id"] for c in cases[:3]], "validation": [c["case_id"] for c in cases[3:8]], "holdout": [c["case_id"] for c in cases[8:10]], "adversarial": [c["case_id"] for c in cases[10:]]}
    write_json(canonical_path("corpus"), corpus)
    write_json(canonical_path("calibration_manifest"), {"version": 1, "split": "CALIBRATION_DEVELOPMENT", "case_ids": splits["calibration"], "frozen": True, "leakage_overlap_count": 0})
    write_json(canonical_path("validation_manifest"), {"version": 1, "split": "VALIDATION", "case_ids": splits["validation"], "frozen": True, "leakage_overlap_count": 0})
    write_json(canonical_path("holdout_manifest"), {"version": 1, "split": "HOLDOUT_ADVERSARIAL", "holdout_case_ids": splits["holdout"], "adversarial_case_ids": splits["adversarial"], "frozen": True, "evaluated_once": True, "prior_holdout_state": "BURNED_HISTORICAL_DEVELOPMENT_EVIDENCE", "reserve": "UNTOUCHED_SYNTHETIC"})
    write_json(canonical_path("input_identity"), {"version": 1, **INPUT_IDENTITIES, "source_mode_values": ["EXISTING_KNOWN_SOURCE", "NEW_UNKNOWN_SOURCE", "MODIFIED_KNOWN_SOURCE", "MOVE_RENAME_CANDIDATE"], "synthetic_only": True, "real_data_used": False})
    return {"case_count": len(cases), "split_counts": {key: len(value) for key, value in splits.items()}}


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
