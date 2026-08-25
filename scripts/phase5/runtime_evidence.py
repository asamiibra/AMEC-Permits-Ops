from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from registry import EVIDENCE_PRODUCERS, producer_paths


def _read(path: Path, fallback: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return fallback


def _producer(evidence_dir: Path, producer_id: str, candidate: str, validation: str, run_id: str, source_result: dict[str, Any] | None = None) -> None:
    paths = producer_paths(producer_id, evidence_dir)
    meta = _read(paths["meta"], {})
    code = meta.get("exit_code")
    result_payload = source_result if source_result is not None else {"result": "PASS" if code == 0 else "FAIL", "producer_id": producer_id, "evidence_derived": True}
    result_payload = {**result_payload, "producer_id": producer_id}
    paths["result"].write_text(json.dumps(result_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not paths["raw"].is_file():
        paths["raw"].write_text(f"producer={producer_id}\nexit_code={code}\n", encoding="utf-8")
    meta = {**meta, "producer_id": producer_id, "candidate_sha": candidate, "validation_sha": validation, "run_id": run_id, "exit_code": code}
    paths["meta"].write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run(evidence_dir: Path, candidate: str, validation: str, run_id: str) -> dict[str, Any]:
    evidence_dir.mkdir(parents=True, exist_ok=True)
    derived = {"backend-targeted": "backend-targeted.result.json", "phase4-integration-regression": "phase4-integration-regression.result.json", "backend-full": "backend-full.result.json", "frontend-targeted": "frontend-targeted.result.json", "frontend-full": "frontend-full.result.json", "frontend-build": "frontend-build.result.json", "authority-denial": "authority-denial.result.json", "observability": "observability.result.json", "security-hygiene": "security-hygiene.result.json"}
    statuses: dict[str, str] = {}
    for producer_id, filename in derived.items():
        source = _read(evidence_dir / filename)
        _producer(evidence_dir, producer_id, candidate, validation, run_id, source)
        statuses[producer_id] = str(source.get("result", "FAIL") if source else "FAIL")
    for producer_id in ("sqlserver-bootstrap", "sqlserver-targeted", "shadow-replay", "browser-required-paths", "browser-quality"):
        paths = producer_paths(producer_id, evidence_dir)
        source = _read(paths["result"])
        _producer(evidence_dir, producer_id, candidate, validation, run_id, source)
        statuses[producer_id] = str(source.get("result", "FAIL") if source else "FAIL")
    result = {"result": "PASS" if statuses and all(value == "PASS" for value in statuses.values()) else "FAIL", "producer_statuses": statuses, "runtime_producer_count": len(statuses), "candidate_sha": candidate, "validation_sha": validation, "run_id": run_id}
    (evidence_dir / "runtime-evidence.result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--candidate-sha", required=True)
    parser.add_argument("--validation-sha", required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    result = run(args.evidence_dir, args.candidate_sha, args.validation_sha, args.run_id)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
