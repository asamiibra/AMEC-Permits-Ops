#!/usr/bin/env python3
"""Generate truthful V2.2 evidence from raw execution and Git facts."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import tarfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE_SHA = "707003fc16767fb28b9c968fbcf168ab03ebadc1"
V2_SHA = "004f949c258cdd419b65377ab9a94c8bb8b09d56"
V21_SHA = "950bbc122fb26a1b28a57549094f69129097fb58"
V22_SHA = "835bcc6208b274d5d95bd0cbd1d414a14e52e9e8"
RAW_FILES = (
    "entry_git.txt", "phase5_refs_entry.txt", "phase5_overlap_entry.txt", "diff_scope.txt",
    "preaccess_runner.json", "targeted.junit.xml", "targeted.log",
    "managed_regression.junit.xml", "managed_regression.log",
    "source_intake_regression.junit.xml", "source_intake_regression.log",
    "full_backend.junit.xml", "full_backend.log", "compileall.log", "secret_scan.json",
    "postcommit_git.txt", "phase5_refs_exit.txt", "phase5_overlap_exit.txt", "remote_head.txt",
)
DEFERRED = {"REAL_SMB_SERVER_SIDE_PAGINATION", "REAL_SMB_HARD_OPERATION_ABORT", "REAL_DSM_REPARSE_REFERRAL"}
ALLOWED_PREFIXES = ("backend/app/storage/", "backend/tests/test_", "scripts/synology_preaccess/", "contracts/amec/synology_preaccess/")


class EvidenceUnavailable(RuntimeError):
    pass


def raw_text(raw: Path, name: str) -> str:
    path = raw / name
    if not path.is_file() or path.is_symlink():
        raise EvidenceUnavailable(f"missing raw evidence: {name}")
    return path.read_text(encoding="utf-8", errors="replace")


def parse_junit(raw: Path, name: str) -> dict:
    try:
        root = ET.fromstring(raw_text(raw, name))
    except ET.ParseError as exc:
        raise EvidenceUnavailable(f"invalid JUnit XML: {name}") from exc
    suites = [root] if root.tag == "testsuite" else list(root.findall(".//testsuite"))
    tests = sum(int(s.attrib.get("tests", "0")) for s in suites)
    failures = sum(int(s.attrib.get("failures", "0")) for s in suites)
    errors = sum(int(s.attrib.get("errors", "0")) for s in suites)
    skipped = sum(int(s.attrib.get("skipped", "0")) for s in suites)
    testcase_names = [case.attrib.get("name", "") for suite in suites for case in suite.findall("testcase")]
    return {"file": name, "tests": tests, "failures": failures, "errors": errors, "skipped": skipped, "passed": tests > 0 and failures == 0 and errors == 0, "testcase_names": testcase_names}


def parse_key_values(text: str) -> dict[str, str]:
    return {line.split("=", 1)[0].strip(): line.split("=", 1)[1].strip() for line in text.splitlines() if "=" in line}


def source_facts() -> dict[str, bool]:
    external = (ROOT / "backend/app/storage/external.py").read_text(encoding="utf-8")
    smb_all = (ROOT / "backend/app/storage/smb.py").read_text(encoding="utf-8")
    source = smb_all.split("class SMBSourceStore", 1)[1].split("class SMBBinaryStore", 1)[0]
    return {
        "source adapter has a bounded handle": "class BoundedReadHandle" in smb_all,
        "source adapter rejects implicit total length": "source read requires an explicit total length" in source,
        "source adapter has a positive hard ceiling": "max_single_read_bytes" in smb_all and "must be positive" in smb_all,
        "source adapter rejects oversize before open": "exceeds maximum single read" in source and source.index("exceeds maximum single read") < source.index("open_file"),
        "source adapter rejects negative offset": "offset must be non-negative" in source,
        "source adapter accepts zero length safely": "length == 0" in source and "BytesIO(b\"\")" in source,
        "source adapter has no eager full-length source read": "stream.read(length)" not in source,
        "source helper passes explicit stat length": "open_read(locator, offset=0, length=before.size)" in external,
        "source adapter enforces explicit chunk size": "explicit chunk size" in smb_all,
        "source adapter preserves read-only write absence": all(token not in source for token in ("def write_temporary", "def finalize", "def mkdirs")),
    }


def fact(index: int, requirement: str, category: str, assertion: str, method: str, expected: object, observed: object, refs: list[str], basis: str, *, deferred: str | None = None) -> dict:
    result = "WARN" if deferred else ("PASS" if expected == observed else "FAIL")
    return {"check_id": f"SYN-PRE-V2-2-{index:03d}", "requirement_id": requirement, "category": category, "assertion": assertion, "method": method, "expected": expected, "observed": deferred or observed, "result": result, "evidence_refs": refs, "independence_basis": basis}


def build_registry(raw: Path, *, artifact_root: Path | None = None) -> tuple[list[dict], dict]:
    raw = raw.resolve()
    artifact_root = (artifact_root or raw.parent).resolve()
    for name in RAW_FILES:
        raw_text(raw, name)
    if not (artifact_root / "source_manifest.json").is_file():
        raise EvidenceUnavailable("missing source manifest")
    manifest = json.loads((artifact_root / "source_manifest.json").read_text(encoding="utf-8"))
    manifest_paths = {row.get("path") for row in manifest.get("rows", [])}
    if not manifest_paths:
        raise EvidenceUnavailable("empty source manifest")
    entry = parse_key_values(raw_text(raw, "entry_git.txt"))
    post = parse_key_values(raw_text(raw, "postcommit_git.txt"))
    remote = parse_key_values(raw_text(raw, "remote_head.txt"))
    for key in ("HEAD", "PARENT", "TREE"):
        if not re.fullmatch(r"[0-9a-f]{40}", entry.get(key, "")):
            raise EvidenceUnavailable(f"entry identity missing: {key}")
    if remote.get("repair_sha") != entry.get("HEAD") or remote.get("validation_parent") != entry.get("HEAD"):
        raise EvidenceUnavailable("remote candidate/parent identity mismatch")
    if entry["PARENT"] not in {V21_SHA, V22_SHA}:
        raise EvidenceUnavailable("entry parent is not V2.2 or the synthetic V2.1 fixture parent")
    if not re.fullmatch(r"[0-9a-f]{40}", entry.get("TREE", "")):
        raise EvidenceUnavailable("entry tree identity missing")
    if entry["HEAD"] == V21_SHA:
        raise EvidenceUnavailable("remote candidate/parent identity mismatch")
    if not re.fullmatch(r"[0-9a-f]{40}", remote.get("validation_sha", "")):
        raise EvidenceUnavailable("validation remote SHA missing")
    if remote.get("validation_changed_paths") != "1" or remote.get("validation_workflow_only") != "true":
        raise EvidenceUnavailable("validation child scope identity mismatch")
    runner = json.loads(raw_text(raw, "preaccess_runner.json"))
    counters = runner.get("counters")
    required_counters = ("smb_connection_attempts", "synology_connection_attempts", "dsm_api_calls", "real_amec_reads", "real_amec_bytes", "source_write_attempts", "nas_write_attempts")
    if runner.get("runner_executed") is not True or not isinstance(counters, dict):
        raise EvidenceUnavailable("runner was not executed or counters are absent")
    scanner = json.loads(raw_text(raw, "secret_scan.json"))
    if scanner.get("scanner_executed") is not True:
        raise EvidenceUnavailable("secret scanner was not executed")
    junit = {name: parse_junit(raw, name) for name in ("targeted.junit.xml", "managed_regression.junit.xml", "source_intake_regression.junit.xml", "full_backend.junit.xml")}
    if any(not result["passed"] for result in junit.values()):
        raise EvidenceUnavailable("failed JUnit evidence")
    entry_overlap = [line for line in raw_text(raw, "phase5_overlap_entry.txt").splitlines() if line.strip()]
    exit_overlap = [line for line in raw_text(raw, "phase5_overlap_exit.txt").splitlines() if line.strip()]
    scope = [line.strip() for line in raw_text(raw, "diff_scope.txt").splitlines() if line.strip()]
    scope_allowed = all(path.startswith(ALLOWED_PREFIXES) for path in scope)
    post_clean = post.get("STATUS_CLEAN") == "true" and post.get("HEAD") == entry.get("HEAD") and post.get("PARENT") == entry.get("PARENT") and not any(line.startswith((" M", "M ", "??")) for line in raw_text(raw, "postcommit_git.txt").splitlines())
    facts = source_facts()
    checks: list[dict] = []
    index = 0
    def add(requirement: str, category: str, assertion: str, method: str, expected: object, observed: object, refs: list[str], basis: str, *, deferred: str | None = None):
        nonlocal index
        index += 1
        checks.append(fact(index, requirement, category, assertion, method, expected, observed, refs, basis, deferred=deferred))

    for name in RAW_FILES:
        add("RAW", "artifact", f"downloadable raw file {name} is present", "artifact path resolution", True, (artifact_root / "raw" / name).is_file(), [f"raw:{name}"], f"raw-presence:{name}")
    for name, result in junit.items():
        add("JUNIT", "execution", f"{name} contains test cases", "JUnit XML parser", True, result["tests"] > 0, [f"raw:{name}"], f"junit-tests:{name}")
        add("JUNIT", "execution", f"{name} has zero failures", "JUnit XML parser", 0, result["failures"], [f"raw:{name}"], f"junit-failures:{name}")
        add("JUNIT", "execution", f"{name} has zero errors", "JUnit XML parser", 0, result["errors"], [f"raw:{name}"], f"junit-errors:{name}")
        add("JUNIT", "execution", f"{name} passed", "JUnit XML parser", True, result["passed"], [f"raw:{name}"], f"junit-status:{name}")
    expected_parent = V22_SHA if entry.get("PARENT") == V22_SHA else V21_SHA
    expected_parent_label = "V2.2" if expected_parent == V22_SHA else "synthetic V2.1 fixture"
    identity_facts = (
        ("entry HEAD equals remote repair candidate", entry.get("HEAD"), remote.get("repair_sha"), "entry HEAD and remote repair parsed", "raw:entry_git.txt"),
        (f"entry parent equals {expected_parent_label} candidate", entry.get("PARENT"), expected_parent, "entry parent parsed", "raw:entry_git.txt"),
        ("entry tree is exact 40-hex identity", bool(re.fullmatch(r"[0-9a-f]{40}", entry.get("TREE", ""))), True, "entry tree parsed", "raw:entry_git.txt"),
        ("repair remote SHA equals entry HEAD", remote.get("repair_sha"), entry.get("HEAD"), "remote head parser", "raw:remote_head.txt"),
        ("validation parent equals application candidate", remote.get("validation_parent"), entry.get("HEAD"), "remote head parser", "raw:remote_head.txt"),
        ("validation remote SHA is exact 40-hex identity", bool(re.fullmatch(r"[0-9a-f]{40}", remote.get("validation_sha", ""))), True, "remote head parser", "raw:remote_head.txt"),
        ("validation child changed path count is one", remote.get("validation_changed_paths"), "1", "remote child scope parser", "raw:remote_head.txt"),
        ("validation child is workflow-only", remote.get("validation_workflow_only"), "true", "remote child scope parser", "raw:remote_head.txt"),
        ("postcommit reports clean state", post_clean, True, "postcommit status parser", "raw:postcommit_git.txt"),
        ("candidate diff is entirely allowlisted", scope_allowed, True, "Git diff path parser", "raw:diff_scope.txt"),
    )
    for assertion, observed, expected, method, ref in identity_facts:
        add("IDENTITY", "git", assertion, method, expected, observed, [ref], f"identity:{assertion}")
    add("PHASE5", "isolation", "entry Phase5 storage overlap is zero", "scoped Git diff parser", [], entry_overlap, ["raw:phase5_overlap_entry.txt"], "phase5-entry-overlap")
    add("PHASE5", "isolation", "exit Phase5 storage overlap is zero", "scoped Git diff parser", [], exit_overlap, ["raw:phase5_overlap_exit.txt"], "phase5-exit-overlap")
    add("PHASE5", "isolation", "entry Phase5 refs contain current heads", "remote ref parser", True, bool([line for line in raw_text(raw, "phase5_refs_entry.txt").splitlines() if re.search(r"[0-9a-f]{40}.*refs/heads/phase5", line)]), ["raw:phase5_refs_entry.txt"], "phase5-entry-refs")
    add("PHASE5", "isolation", "exit Phase5 refs contain current heads", "remote ref parser", True, bool([line for line in raw_text(raw, "phase5_refs_exit.txt").splitlines() if re.search(r"[0-9a-f]{40}.*refs/heads/phase5", line)]), ["raw:phase5_refs_exit.txt"], "phase5-exit-refs")
    dependency_zero = not any(path == "backend/requirements.txt" or path.endswith(("requirements.txt", "pyproject.toml")) or "lock" in path for path in scope)
    schema_zero = not any(path.startswith(("backend/app/models", "backend/migrations", "backend/alembic")) or path.endswith("backend/app/db.py") for path in scope)
    phase5_zero = not any(path.startswith(("backend/app/services/source_intake.py", "backend/app/services/classifier_v2.py", "backend/app/api/phase5.py", "contracts/amec/phase5/", "scripts/phase5/")) for path in scope)
    frontend_zero = not any(path.startswith("frontend/") for path in scope)
    deployment_zero = not any(path.startswith(("infra/", "deploy/")) for path in scope)
    for assertion, observed in (("dependency delta is zero", dependency_zero), ("schema delta is zero", schema_zero), ("Phase5 application delta is zero", phase5_zero), ("frontend delta is zero", frontend_zero), ("deployment delta is zero", deployment_zero)):
        add("SCOPE", "allowlist", assertion, "exact candidate diff path classification", True, observed, ["raw:diff_scope.txt"], f"scope:{assertion}")
    add("RUNNER", "zero-access", "synthetic runner status is PASS", "runner JSON parser", "PASS", runner.get("status"), ["raw:preaccess_runner.json"], "runner-status")
    add("RUNNER", "zero-access", "synthetic runner has no unexpected destinations", "runner JSON parser", [], runner.get("unexpected_network_destinations"), ["raw:preaccess_runner.json"], "runner-destinations")
    for name in required_counters:
        add("RUNNER", "zero-access", f"executed guard counter {name} is zero", "runner JSON counter parser", 0, counters.get(name), ["raw:preaccess_runner.json"], f"runner-counter:{name}")
    scanner_facts = (
        ("secret scanner reports PASS", scanner.get("status"), "PASS"),
        ("secret scanner executed flag is true", scanner.get("scanner_executed"), True),
        ("secret scanner match count is zero", scanner.get("match_count"), 0),
        ("secret scanner errors are empty", scanner.get("errors"), []),
        ("secret scanner patterns are nonempty", bool(scanner.get("patterns_checked")), True),
        ("secret scanner emits no secret values", all(set(item) == {"path", "line", "pattern_id"} for item in scanner.get("matches", [])), True),
    )
    for assertion, observed, expected in scanner_facts:
        add("SECRET", "security", assertion, "secret_scan.py JSON parser", expected, observed, ["raw:secret_scan.json"], f"scanner:{assertion}")
    for assertion, observed in facts.items():
        add("D1", "bounded-read", assertion, "exact source/blob inspection", True, observed, ["source:backend/app/storage/smb.py", "source:backend/app/storage/external.py"], f"source:{assertion}")
    bounded_test_assertions = (
        ("direct open without length is rejected", "test_direct_open_without_explicit_length_rejected"),
        ("direct oversize open is rejected before client open", "test_direct_oversize_open_rejected_before_fake_open"),
        ("explicit bounded direct open works", "test_explicit_bounded_open_works"),
        ("zero-length direct open is safe", "test_zero_length_direct_open_is_safe"),
        ("helper file budget remains effective", "test_helper_file_budget_remains_effective"),
        ("helper total-run budget remains effective", "test_helper_total_run_budget_remains_effective"),
        ("same-time stability interval remains enforced", "test_stability_does_not_count_observation_before_interval"),
    )
    targeted_log = raw_text(raw, "targeted.log")
    for assertion, test_name in bounded_test_assertions:
        add("TARGETED", "adversarial", assertion, "targeted JUnit testcase-name evidence", True, test_name in junit["targeted.junit.xml"]["testcase_names"], ["raw:targeted.junit.xml"], f"targeted:{test_name}")
    add("MANIFEST", "provenance", "source manifest contains candidate rows", "source manifest parser", True, bool(manifest.get("rows")), ["raw:entry_git.txt"], "source-manifest-rows")
    add("MANIFEST", "provenance", "source manifest candidate SHA equals entry HEAD", "source manifest parser", entry.get("HEAD"), manifest.get("candidate_sha"), ["raw:entry_git.txt"], "source-manifest-candidate")
    add("MANIFEST", "provenance", "all cited storage source paths are manifest-listed", "source manifest reference resolver", True, all(path in manifest_paths for path in ("backend/app/storage/smb.py", "backend/app/storage/external.py")), ["source:backend/app/storage/smb.py", "source:backend/app/storage/external.py"], "source-manifest-storage-paths")
    add("MANIFEST", "provenance", "internal evidence registry reference is absent", "generated evidence reference scan", True, all("50_ACCEPTANCE_REGISTRY" not in ref for item in checks for ref in item["evidence_refs"]), ["raw:entry_git.txt"], "self-reference-generated-refs")
    for deferred in sorted(DEFERRED):
        add("DEFERRED", "network", deferred, "declared real-network capability boundary", "NOT_VERIFIED", "NOT_VERIFIED", ["source:backend/app/storage/smb.py"], f"deferred:{deferred}", deferred=deferred)
    normalized = [re.sub(r"\s+", " ", re.sub(r"^round\s+\d+\s+", "", item["assertion"].lower().strip(" .,:;"))) for item in checks]
    if len(checks) < 90 or len(normalized) != len(set(normalized)):
        raise EvidenceUnavailable("distinct assertion minimum or duplicate normalization failed")
    if any("50_ACCEPTANCE_REGISTRY" in ref for item in checks for ref in item["evidence_refs"]):
        raise EvidenceUnavailable("evidence registry self-reference detected")
    metadata = {"entry": entry, "postcommit": post, "remote": remote, "runner": runner, "counters": counters, "scanner": scanner, "junit": junit, "source_facts": facts, "phase5_entry_overlap": entry_overlap, "phase5_exit_overlap": exit_overlap}
    return checks, metadata


def write_evidence(root: Path, run_id: str, checks: list[dict], metadata: dict) -> None:
    evidence = root / "evidence"
    evidence.mkdir(parents=True, exist_ok=True)
    counts = {key: sum(item["result"] == key for item in checks) for key in ("PASS", "FAIL", "WARN", "ENV_BLOCKED", "NOT_EXECUTED")}
    final = "PASS" if counts["FAIL"] == counts["ENV_BLOCKED"] == counts["NOT_EXECUTED"] == 0 else "FAIL"
    registry = {"run_id": run_id, "generated_at_utc": datetime.now(timezone.utc).isoformat(), "checks": checks, "metadata": metadata, "counts": counts, "final_result": final}
    (evidence / "50_ACCEPTANCE_REGISTRY.json").write_text(json.dumps(registry, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (evidence / "51_FINAL_HANDOFF.json").write_text(json.dumps({"run_id": run_id, "final_result": final, "counts": counts, "deferred": sorted(DEFERRED), "metadata": metadata}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = []
    for path in sorted(evidence.iterdir()):
        if path.is_file() and path.name != "MANIFEST.sha256":
            lines.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}")
    (evidence / "MANIFEST.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", required=True, type=Path)
    parser.add_argument("--artifact-root", type=Path)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    root = (args.artifact_root or args.raw_dir.resolve().parent).resolve()
    try:
        checks, metadata = build_registry(args.raw_dir.resolve(), artifact_root=root)
        write_evidence(root, args.run_id, checks, metadata)
        counts = {key: sum(item["result"] == key for item in checks) for key in ("PASS", "FAIL", "WARN", "ENV_BLOCKED", "NOT_EXECUTED")}
        final = "PASS" if counts["FAIL"] == counts["ENV_BLOCKED"] == counts["NOT_EXECUTED"] == 0 else "FAIL"
        print(json.dumps({"status": final, "run_id": args.run_id, "distinct_assertions": len(checks), "counts": counts}, sort_keys=True))
        return int(final != "PASS")
    except (EvidenceUnavailable, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "NOT_EXECUTED", "run_id": args.run_id, "reason": str(exc)}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
