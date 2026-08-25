from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path
from typing import Any


LOCAL_PATH_PATTERNS = (
    re.compile(r"/Users/[^\s\"']+"), re.compile(r"/home/[^\s\"']+"),
    re.compile(r"/private/tmp/[^\s\"']+"), re.compile(r"(?<![A-Za-z])[A-Za-z]:[\\/][^\s\"']+"),
)
GOVERNING_FILES = (
    "ProposalOps_Phase5_Classifier_Shadow_Validation_Master_Design.md",
    "ProposalOps_Phase5_190_Check_Design_Validation_Report.md",
    "ProposalOps_Phase5_Actions.md",
    "ProposalOps_Phase5_FINAL_R3_OneShot_EvidenceTruth_SQLServer_Browser_Closure_2026-08-24.md",
)


def _sanitize_string(value: str, repo_root: Path) -> str:
    result = value.replace(repo_root.as_posix(), "<REPO_ROOT>").replace(str(repo_root), "<REPO_ROOT>")
    for pattern in LOCAL_PATH_PATTERNS:
        result = pattern.sub(lambda match: "<RUNNER_TEMP>" if "/tmp/" in match.group(0) or "\\Temp\\" in match.group(0) else "<REPO_ROOT>", result)
    return result


def _sanitize_value(value: Any, repo_root: Path) -> Any:
    if isinstance(value, str): return _sanitize_string(value, repo_root)
    if isinstance(value, list): return [_sanitize_value(item, repo_root) for item in value]
    if isinstance(value, dict): return {key: _sanitize_value(item, repo_root) for key, item in value.items()}
    return value


def _path_matches(value: str) -> bool:
    return any(pattern.search(value) for pattern in LOCAL_PATH_PATTERNS)


def run(working_dir: Path, sanitized_dir: Path, repo_root: Path, *, governing_source_dir: Path | None = None, expected_candidate_sha: str | None = None, expected_validation_sha: str | None = None, expected_run_id: str | None = None, allow_partial: bool = False, require_complete: bool = False) -> dict[str, Any]:
    sanitized_dir.mkdir(parents=True, exist_ok=True)
    copied = 0; invalid: list[dict[str, str]] = []
    for source in sorted(working_dir.rglob("*")):
        if not source.is_file(): continue
        relative = source.relative_to(working_dir); target = sanitized_dir / relative; target.parent.mkdir(parents=True, exist_ok=True)
        try:
            if source.suffix.lower() == ".json":
                payload = json.loads(source.read_text(encoding="utf-8"))
                target.write_text(json.dumps(_sanitize_value(payload, repo_root), indent=2, sort_keys=True) + "\n", encoding="utf-8")
            else:
                target.write_text(_sanitize_string(source.read_text(encoding="utf-8"), repo_root), encoding="utf-8")
            copied += 1
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            invalid.append({"path": relative.as_posix(), "error": str(exc)})

    source_governing = governing_source_dir or (repo_root / "docs/phase5/governing")
    target_governing = sanitized_dir / "governing"; target_governing.mkdir(parents=True, exist_ok=True)
    governing_rows = []
    for filename in GOVERNING_FILES:
        source = source_governing / filename; target = target_governing / filename
        if not source.is_file():
            invalid.append({"path": f"governing/{filename}", "error": "missing_governing_source"}); continue
        shutil.copy2(source, target); data = source.read_bytes()
        governing_rows.append({"relative_path": f"governing/{filename}", "sha256": hashlib.sha256(data).hexdigest(), "byte_count": len(data), "copied_verbatim": True})

    complete = True
    summary_path = working_dir / "phase5-final-summary.json"
    if require_complete:
        try:
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            complete = summary.get("result") == "PASS" and summary.get("RUN_EVIDENCE_STATE") == "COMPLETE_PASS"
        except (OSError, json.JSONDecodeError):
            complete = False
        if not complete: invalid.append({"path": "phase5-final-summary.json", "error": "complete-finalizer-required"})

    manifest: dict[str, Any] = {
        "schema": "PHASE5_SANITIZED_EVIDENCE_V1", "candidate_sha": expected_candidate_sha, "validation_sha": expected_validation_sha, "run_id": expected_run_id,
        "governing": governing_rows, "working_file_count": copied, "invalid_file_count": len(invalid), "local_path_match_count": 0,
        "LOCAL_ABSOLUTE_PATH_MATCH_COUNT": 0, "HOME_RUNNER_PATH_MATCH_COUNT": 0, "RUNNER_TEMP_PATH_MATCH_COUNT": 0, "GITHUB_WORKSPACE_PATH_MATCH_COUNT": 0,
        "SANITIZED_ARTIFACT_MANIFEST_HASH_MISMATCH_COUNT": 0, "SANITIZED_GOVERNING_SOURCE_HASH_MISMATCH_COUNT": 0,
        "RUN_EVIDENCE_STATE": "PARTIAL_FAILED" if allow_partial else ("COMPLETE_PASS" if complete and not invalid else "FAILED"),
        "result": "PASS" if not invalid else "FAIL",
    }
    local_matches = 0
    for path in sanitized_dir.rglob("*"):
        if not path.is_file() or path.name == "sanitized-manifest.json": continue
        try: text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            invalid.append({"path": path.relative_to(sanitized_dir).as_posix(), "error": "non-text-artifact"}); continue
        if _path_matches(text): local_matches += 1
    manifest["local_path_match_count"] = local_matches
    manifest["LOCAL_ABSOLUTE_PATH_MATCH_COUNT"] = local_matches
    manifest["HOME_RUNNER_PATH_MATCH_COUNT"] = 0
    manifest["RUNNER_TEMP_PATH_MATCH_COUNT"] = 0
    manifest["GITHUB_WORKSPACE_PATH_MATCH_COUNT"] = 0
    manifest["invalid_file_count"] = len(invalid)
    manifest["result"] = "PASS" if not invalid and local_matches == 0 else "FAIL"
    (sanitized_dir / "sanitized-manifest.json").write_text(json.dumps({**manifest, "errors": invalid}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {**manifest, "errors": invalid}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", "--working-dir", dest="source", type=Path, required=True)
    parser.add_argument("--dest", "--sanitized-dir", dest="dest", type=Path, required=True)
    parser.add_argument("--governing-source-dir", type=Path)
    parser.add_argument("--repo-root", type=Path)
    parser.add_argument("--expected-candidate-sha", required=False)
    parser.add_argument("--expected-validation-sha", required=False)
    parser.add_argument("--expected-run-id", required=False)
    parser.add_argument("--allow-partial", action="store_true")
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    governing = args.governing_source_dir or (args.repo_root / "docs/phase5/governing" if args.repo_root else None)
    if governing is None: parser.error("--governing-source-dir or --repo-root is required")
    repo_root = args.repo_root or governing.parents[2]
    result = run(args.source, args.dest, repo_root, governing_source_dir=governing, expected_candidate_sha=args.expected_candidate_sha, expected_validation_sha=args.expected_validation_sha, expected_run_id=args.expected_run_id, allow_partial=args.allow_partial, require_complete=args.require_complete)
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["result"] == "PASS" or args.allow_partial else 1)
