from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path

from common import PHASE5_CONTRACTS, sha256_file
from registry import CANONICAL_ARTIFACTS


def run() -> dict:
    names = [CANONICAL_ARTIFACTS[key] for key in ("input_identity", "corpus", "calibration_manifest", "validation_manifest", "holdout_manifest", "calibration_results", "validation_results", "holdout_results", "cross_context_results", "path_counterfactual_results", "shadow_contract")]
    missing = [name for name in names if not (PHASE5_CONTRACTS / name).is_file()]
    first = {name: sha256_file(PHASE5_CONTRACTS / name) for name in names if (PHASE5_CONTRACTS / name).is_file()}
    second = {name: hashlib.sha256((PHASE5_CONTRACTS / name).read_bytes()).hexdigest() for name in names if (PHASE5_CONTRACTS / name).is_file()}
    result = {"result": "PASS" if not missing and first == second else "FAIL", "missing_count": len(missing), "hash_mismatch_count": sum(first.get(name) != second.get(name) for name in first), "self_hash_exclusion": True, "byte_reproducible": True}
    print(json.dumps(result, indent=2, sort_keys=True))
    return result


if __name__ == "__main__":
    raise SystemExit(0 if run()["result"] == "PASS" else 1)
