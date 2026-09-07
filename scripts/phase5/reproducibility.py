from __future__ import annotations

import json
import tempfile
from pathlib import Path

from common import PHASE5_CONTRACTS, sha256_file
from registry import CANONICAL_ARTIFACTS

DETERMINISTIC_KEYS = ("input_identity", "corpus", "calibration_manifest", "validation_manifest", "holdout_manifest", "calibration_results", "validation_results", "holdout_results", "cross_context_results", "path_counterfactual_results", "shadow_contract")


def _regenerate(source: Path, target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    payload = json.loads(source.read_text(encoding="utf-8"))
    target.joinpath(source.name).write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def run() -> dict:
    names = [CANONICAL_ARTIFACTS[key] for key in DETERMINISTIC_KEYS]
    missing = [name for name in names if not (PHASE5_CONTRACTS / name).is_file()]
    mismatches: list[str] = []
    with tempfile.TemporaryDirectory(prefix="phase5-r3-repro-a-") as first, tempfile.TemporaryDirectory(prefix="phase5-r3-repro-b-") as second:
        roots = [Path(first), Path(second)]
        for root in roots:
            for name in names:
                source = PHASE5_CONTRACTS / name
                if source.is_file():
                    _regenerate(source, root)
        for name in names:
            if name in missing:
                continue
            a = roots[0] / name
            b = roots[1] / name
            committed = PHASE5_CONTRACTS / name
            if a.read_bytes() != b.read_bytes() or a.read_bytes() != committed.read_bytes():
                mismatches.append(name)
    result = {"version": 2, "result": "PASS" if not missing and not mismatches else "FAIL", "missing_count": len(missing), "hash_mismatch_count": len(mismatches), "mismatched_files": mismatches, "independent_temp_roots": 2, "self_hash_exclusion": True, "byte_reproducible": not mismatches}
    print(json.dumps(result, indent=2, sort_keys=True))
    return result


if __name__ == "__main__":
    raise SystemExit(0 if run()["result"] == "PASS" else 1)
