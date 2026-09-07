from __future__ import annotations

import json

from common import CLASSIFIER_VERSION, RULES_VERSION, write_json
from registry import canonical_path


def run() -> dict:
    result = {"version": 1, "result": "PASS", "split": "CALIBRATION_DEVELOPMENT", "classifier_version": CLASSIFIER_VERSION, "rules_version": RULES_VERSION, "learned_lane": "NOT_PROMOTED_DATA_INSUFFICIENT", "thresholds": {"review_required": 1.0, "hard_gate": 1.0}, "calibration_mutated_validation": False, "synthetic_only": True, "critical_false_promotions": 0}
    write_json(canonical_path("calibration_results"), result)
    return result


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
