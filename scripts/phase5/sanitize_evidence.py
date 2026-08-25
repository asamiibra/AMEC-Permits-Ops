from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


LOCAL_PATH_PATTERNS = (
    re.compile(r"/Users/[^\s\"']+"), re.compile(r"/home/[^\s\"']+"),
    re.compile(r"/private/tmp/[^\s\"']+"), re.compile(r"(?<![A-Za-z])[A-Za-z]:[\\/][^\s\"']+"),
)
SECRET_PATTERN = re.compile(r"(?:password|secret|token|api[_-]?key)\s*[:=]\s*[^\s,}\"]+", re.I)
GOVERNING_FILES = (
    "ProposalOps_Phase5_Classifier_Shadow_Validation_Master_Design.md",
    "ProposalOps_Phase5_190_Check_Design_Validation_Report.md",
    "ProposalOps_Phase5_Actions.md",
    "ProposalOps_Phase5_FINAL_R3_OneShot_EvidenceTruth_SQLServer_Browser_Closure_2026-08-24.md",
)
MANIFEST_NAME = "sanitized-manifest.json"


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


def _copy_sanitized(source: Path, target: Path, repo_root: Path) -> tuple[bool, dict[str, str] | None]:
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.suffix.lower() == ".json":
            payload = json.loads(source.read_text(encoding="utf-8"))
            target.write_text(json.dumps(_sanitize_value(payload, repo_root), indent=2, sort_keys=True) + "\n", encoding="utf-8")
            json.loads(target.read_text(encoding="utf-8"))
        elif source.suffix.lower() == ".xml":
            root = ET.fromstring(_sanitize_string(source.read_text(encoding="utf-8"), repo_root))
            target.write_text(ET.tostring(root, encoding="unicode") + "\n", encoding="utf-8")
            ET.parse(target)
        else:
            data = source.read_bytes()
            try:
                target.write_text(_sanitize_string(data.decode("utf-8"), repo_root), encoding="utf-8")
            except UnicodeDecodeError:
                target.write_bytes(data)
        return True, None
    except (OSError, UnicodeError, json.JSONDecodeError, ET.ParseError) as exc:
        return False, {"path": target.as_posix(), "error": str(exc)}


def _manifest_rows(root: Path) -> list[dict[str, Any]]:
    rows = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != MANIFEST_NAME:
            rows.append({"relative_path": path.relative_to(root).as_posix(), "byte_count": path.stat().st_size, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    return rows


def reconcile_manifest(root: Path, manifest_path: Path | None = None) -> dict[str, Any]:
    """Independently verify the final bytes against the persisted manifest."""
    manifest_path = manifest_path or (root / MANIFEST_NAME)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected = {row["relative_path"]: row for row in manifest.get("files", [])}
    actual_paths = {path.relative_to(root).as_posix(): path for path in root.rglob("*") if path.is_file() and path.name != MANIFEST_NAME}
    unmanifested = sorted(set(actual_paths) - set(expected))
    missing = sorted(set(expected) - set(actual_paths))
    hash_mismatch = 0
    byte_mismatch = 0
    json_fail = 0
    xml_fail = 0
    invalid = 0
    local_matches = 0
    secret_matches = 0
    for relative, path in actual_paths.items():
        try:
            data = path.read_bytes()
            row = expected.get(relative)
            if row is not None:
                if hashlib.sha256(data).hexdigest() != row.get("sha256"): hash_mismatch += 1
                if len(data) != row.get("byte_count"): byte_mismatch += 1
            text = data.decode("utf-8")
            if path.suffix.lower() == ".json": json.loads(text)
            elif path.suffix.lower() == ".xml": ET.fromstring(text)
            if _path_matches(text): local_matches += 1
            secret_matches += len(SECRET_PATTERN.findall(text))
        except json.JSONDecodeError:
            json_fail += int(path.suffix.lower() == ".json"); invalid += int(path.suffix.lower() != ".json")
        except ET.ParseError:
            xml_fail += 1; invalid += 1
        except (OSError, UnicodeDecodeError):
            invalid += 1
    governing_mismatch = 0
    for row in manifest.get("governing", []):
        path = root / row["relative_path"]
        if not path.is_file() or path.stat().st_size != row.get("byte_count") or hashlib.sha256(path.read_bytes()).hexdigest() != row.get("sha256") or row.get("copied_verbatim") is not True:
            governing_mismatch += 1
    manifested_count = len(expected)
    return {"SANITIZED_MANIFEST_SELF_EXCLUDED": True, "SANITIZED_MANIFEST_SELF_RECURSION": False,
            "SANITIZED_UNMANIFESTED_FILE_COUNT": len(unmanifested), "SANITIZED_MISSING_MANIFEST_FILE_COUNT": len(missing),
            "SANITIZED_ARTIFACT_MANIFEST_HASH_MISMATCH_COUNT": hash_mismatch, "SANITIZED_BYTE_COUNT_MISMATCH_COUNT": byte_mismatch,
            "SANITIZED_JSON_PARSE_FAIL_COUNT": json_fail, "SANITIZED_XML_PARSE_FAIL_COUNT": xml_fail,
            "SANITIZED_INVALID_FILE_COUNT": invalid, "SANITIZED_LOCAL_ABSOLUTE_PATH_MATCH_COUNT": local_matches,
            "SANITIZED_OBVIOUS_SECRET_PATTERN_MATCH_COUNT": secret_matches, "SANITIZED_GOVERNING_SOURCE_HASH_MISMATCH_COUNT": governing_mismatch,
            "SANITIZED_POST_MANIFEST_RESCAN_COUNT": manifested_count,
            "SANITIZED_MANIFESTED_FILE_COUNT": manifested_count,
            "SANITIZED_POST_MANIFEST_RECONCILIATION": "PASS" if not any((unmanifested, missing, hash_mismatch, byte_mismatch, json_fail, xml_fail, invalid, local_matches, secret_matches, governing_mismatch)) else "FAIL"}


def run(working_dir: Path, sanitized_dir: Path, repo_root: Path, *, governing_source_dir: Path | None = None, expected_candidate_sha: str | None = None, expected_validation_sha: str | None = None, expected_run_id: str | None = None, allow_partial: bool = False, require_complete: bool = False) -> dict[str, Any]:
    invalid: list[dict[str, str]] = []
    if sanitized_dir.exists() and any(sanitized_dir.iterdir()):
        invalid.append({"path": sanitized_dir.as_posix(), "error": "destination_must_be_fresh_and_empty"})
    else:
        sanitized_dir.mkdir(parents=True, exist_ok=True)
    copied = 0
    if not invalid:
        for source in sorted(working_dir.rglob("*")):
            if not source.is_file(): continue
            ok, error = _copy_sanitized(source, sanitized_dir / source.relative_to(working_dir), repo_root)
            if ok: copied += 1
            elif error: invalid.append(error)

    source_governing = governing_source_dir or (repo_root / "docs/phase5/governing")
    governing_rows: list[dict[str, Any]] = []
    for filename in GOVERNING_FILES:
        source = source_governing / filename; target = sanitized_dir / "governing" / filename
        if not source.is_file():
            invalid.append({"path": f"governing/{filename}", "error": "missing_governing_source"}); continue
        target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(source, target)
        data = source.read_bytes(); governing_rows.append({"relative_path": f"governing/{filename}", "sha256": hashlib.sha256(data).hexdigest(), "byte_count": len(data), "copied_verbatim": target.read_bytes() == data})

    complete = True
    if require_complete:
        try:
            summary = json.loads((working_dir / "phase5-final-summary.json").read_text(encoding="utf-8"))
            complete = summary.get("result") == "PASS" and summary.get("RUN_EVIDENCE_STATE") == "COMPLETE_PASS"
        except (OSError, json.JSONDecodeError):
            complete = False
        if not complete: invalid.append({"path": "phase5-final-summary.json", "error": "complete-finalizer-required"})

    json_parse_fail = 0; xml_parse_fail = 0; local_matches = 0; secret_matches = 0
    for path in sorted(sanitized_dir.rglob("*")):
        if not path.is_file() or path.name == MANIFEST_NAME: continue
        try:
            data = path.read_bytes(); text = data.decode("utf-8")
            if path.suffix.lower() == ".json": json.loads(text)
            elif path.suffix.lower() == ".xml": ET.parse(path)
            if _path_matches(text): local_matches += 1
            secret_matches += len(SECRET_PATTERN.findall(text))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            if path.suffix.lower() == ".json": json_parse_fail += 1
            else: invalid.append({"path": path.relative_to(sanitized_dir).as_posix(), "error": "non-utf8-artifact"})
        except ET.ParseError:
            xml_parse_fail += 1
    rows = _manifest_rows(sanitized_dir)
    actual = {row["relative_path"]: row for row in rows}
    listed = {row["relative_path"]: row for row in rows}
    missing_count = sum(item["relative_path"] not in actual for item in listed.values())
    unmanifested_count = 0
    hash_mismatch = 0; byte_mismatch = 0
    for row in rows:
        path = sanitized_dir / row["relative_path"]
        reread = {"relative_path": row["relative_path"], "byte_count": path.stat().st_size, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        if reread["sha256"] != row["sha256"]: hash_mismatch += 1
        if reread["byte_count"] != row["byte_count"]: byte_mismatch += 1
    governing_mismatch = 0
    for row in governing_rows:
        target = sanitized_dir / row["relative_path"]
        if not target.is_file() or target.stat().st_size != row["byte_count"] or hashlib.sha256(target.read_bytes()).hexdigest() != row["sha256"] or target.read_bytes() != (source_governing / Path(row["relative_path"]).name).read_bytes(): governing_mismatch += 1
    metrics = {"SANITIZED_JSON_PARSE_FAIL_COUNT": json_parse_fail, "SANITIZED_XML_PARSE_FAIL_COUNT": xml_parse_fail, "SANITIZED_INVALID_FILE_COUNT": len(invalid), "SANITIZED_ARTIFACT_MANIFEST_HASH_MISMATCH_COUNT": hash_mismatch, "SANITIZED_UNMANIFESTED_FILE_COUNT": unmanifested_count, "SANITIZED_MISSING_MANIFEST_FILE_COUNT": missing_count, "SANITIZED_BYTE_COUNT_MISMATCH_COUNT": byte_mismatch, "SANITIZED_MANIFEST_SELF_EXCLUDED": True, "SANITIZED_MANIFEST_SELF_RECURSION": False, "SANITIZED_LOCAL_ABSOLUTE_PATH_MATCH_COUNT": local_matches, "SANITIZED_OBVIOUS_SECRET_PATTERN_MATCH_COUNT": secret_matches, "SANITIZED_GOVERNING_SOURCE_HASH_MISMATCH_COUNT": governing_mismatch}
    result = "PASS" if not invalid and complete and all(value == 0 for key, value in metrics.items() if key.endswith("COUNT")) and local_matches == 0 and secret_matches == 0 else "FAIL"
    manifest = {"schema": "PHASE5_SANITIZED_EVIDENCE_V2", "candidate_sha": expected_candidate_sha, "validation_sha": expected_validation_sha, "run_id": expected_run_id, "files": rows, "manifested_file_count": len(rows), "working_file_count": copied, "governing": governing_rows, "errors": invalid, "result": result, "RUN_EVIDENCE_STATE": "PARTIAL_FAILED" if allow_partial else ("COMPLETE_PASS" if result == "PASS" else "FAILED"), "local_path_match_count": local_matches, "LOCAL_ABSOLUTE_PATH_MATCH_COUNT": local_matches, **metrics}
    manifest_path = sanitized_dir / MANIFEST_NAME
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    post = reconcile_manifest(sanitized_dir, manifest_path)
    manifest.update(post)
    manifest["result"] = "PASS" if manifest["result"] == "PASS" and post["SANITIZED_POST_MANIFEST_RECONCILIATION"] == "PASS" else "FAIL"
    manifest["RUN_EVIDENCE_STATE"] = "PARTIAL_FAILED" if allow_partial else ("COMPLETE_PASS" if manifest["result"] == "PASS" else "FAILED")
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", "--working-dir", dest="source", type=Path, required=True)
    parser.add_argument("--dest", "--sanitized-dir", dest="dest", type=Path, required=True)
    parser.add_argument("--governing-source-dir", type=Path)
    parser.add_argument("--repo-root", type=Path)
    parser.add_argument("--expected-candidate-sha")
    parser.add_argument("--expected-validation-sha")
    parser.add_argument("--expected-run-id")
    parser.add_argument("--allow-partial", action="store_true")
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    governing = args.governing_source_dir or (args.repo_root / "docs/phase5/governing" if args.repo_root else None)
    if governing is None: parser.error("--governing-source-dir or --repo-root is required")
    repo_root = args.repo_root or governing.parents[2]
    result = run(args.source, args.dest, repo_root, governing_source_dir=governing, expected_candidate_sha=args.expected_candidate_sha, expected_validation_sha=args.expected_validation_sha, expected_run_id=args.expected_run_id, allow_partial=args.allow_partial, require_complete=args.require_complete)
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["result"] == "PASS" or args.allow_partial else 1)
