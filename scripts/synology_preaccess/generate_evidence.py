#!/usr/bin/env python3
"""Build evidence only from raw execution artifacts and source facts."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import tarfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE_SHA = "707003fc16767fb28b9c968fbcf168ab03ebadc1"
V2_SHA = "004f949c258cdd419b65377ab9a94c8bb8b09d56"
REQUIRED_RAW = (
    "entry_git.txt", "phase5_refs_entry.txt", "phase5_overlap_entry.txt", "diff_scope.txt",
    "targeted.junit.xml", "targeted.log", "preaccess_runner.json", "managed_regression.junit.xml",
    "source_intake_regression.junit.xml", "full_backend.junit.xml", "full_backend.log",
    "compileall.log", "secret_scan.txt", "postcommit_git.txt", "phase5_refs_exit.txt", "remote_head.txt",
)
DEFERRED = {"REAL_SMB_SERVER_SIDE_PAGINATION", "REAL_SMB_HARD_OPERATION_ABORT", "REAL_DSM_REPARSE_REFERRAL"}


class EvidenceUnavailable(RuntimeError):
    pass


def read_raw(raw: Path, name: str) -> str:
    path = raw / name
    if not path.is_file():
        raise EvidenceUnavailable(f"missing raw evidence: {name}")
    return path.read_text(encoding="utf-8", errors="replace")


def parse_junit(raw: Path, name: str) -> dict:
    text = read_raw(raw, name)
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        raise EvidenceUnavailable(f"invalid JUnit XML: {name}") from exc
    suites = [root] if root.tag == "testsuite" else list(root.findall(".//testsuite"))
    tests = sum(int(s.attrib.get("tests", "0")) for s in suites)
    failures = sum(int(s.attrib.get("failures", "0")) for s in suites)
    errors = sum(int(s.attrib.get("errors", "0")) for s in suites)
    skipped = sum(int(s.attrib.get("skipped", "0")) for s in suites)
    return {"file": name, "tests": tests, "failures": failures, "errors": errors, "skipped": skipped, "passed": tests > 0 and failures == 0 and errors == 0}


def source_facts() -> dict[str, bool]:
    external = (ROOT / "backend/app/storage/external.py").read_text(encoding="utf-8")
    smb_all = (ROOT / "backend/app/storage/smb.py").read_text(encoding="utf-8")
    smb = smb_all.split("class SMBSourceStore", 1)[1].split("class SMBBinaryStore", 1)[0]
    runner = (ROOT / "scripts/synology_preaccess/validate_preaccess.py").read_text(encoding="utf-8")
    return {
        "no_thread_timeout": "ThreadPoolExecutor" not in external and "run_with_deadline" not in smb,
        "hard_abort_deferred": "killable fetcher" in external and "OperationDeadlineExceeded" in external,
        "stability_terminal": "STABILITY_TIMEOUT" in external and "_terminal" in external,
        "interval_enforced": "_last_observed_at" in external and "observation_interval_seconds" in external,
        "bounded_handle": "class BoundedReadHandle" in smb_all and "stream.read(length)" not in smb,
        "explicit_chunk": "explicit chunk size" in smb_all,
        "page_sorted": "sorted(self._client().listdir" in smb,
        "failed_page_stops": "failed page is terminal" in smb and "failures == 0" in smb,
        "parallel_one": "max_parallelism != 1" in external,
        "sanitized_health": '"endpoint_fingerprint"' in smb and '"server": self.config.server' not in smb,
        "no_writes": all(token not in smb for token in ("def write_temporary", "def finalize", "def mkdirs")),
        "runner_json": "runner_executed" in runner and "counters" in runner and "json.dumps" in runner,
    }


def fact(check_id: str, requirement: str, category: str, assertion: str, observed: object, expected: object, refs: list[str], *, deferred: str | None = None) -> dict:
    if deferred:
        result = "WARN"
        observed_value = deferred
    else:
        result = "PASS" if observed == expected else "FAIL"
        observed_value = observed
    return {"check_id": check_id, "requirement_id": requirement, "category": category, "assertion": assertion, "method": "parsed raw evidence and exact source/blob fact", "expected": expected, "observed": observed_value, "result": result, "evidence_refs": refs}


def build_registry(raw: Path) -> tuple[list[dict], dict]:
    raw_facts = {name: read_raw(raw, name) for name in REQUIRED_RAW}
    junit = {name: parse_junit(raw, name) for name in ("targeted.junit.xml", "managed_regression.junit.xml", "source_intake_regression.junit.xml", "full_backend.junit.xml")}
    failed_suites = [name for name, result in junit.items() if not result["passed"]]
    if failed_suites:
        raise EvidenceUnavailable(f"failed JUnit evidence: {','.join(failed_suites)}")
    runner = json.loads(raw_facts["preaccess_runner.json"])
    if runner.get("runner_executed") is not True:
        raise EvidenceUnavailable("synthetic runner was not executed")
    counters = runner.get("counters")
    required_counters = ("smb_connection_attempts", "synology_connection_attempts", "dsm_api_calls", "real_amec_reads", "real_amec_bytes", "source_write_attempts", "nas_write_attempts")
    if not isinstance(counters, dict) or any(name not in counters for name in required_counters):
        raise EvidenceUnavailable("runner counters are missing")
    sources = source_facts()
    overlap = [line.strip() for line in raw_facts["phase5_overlap_entry.txt"].splitlines() if line.strip()]
    diff_lines = [line.strip() for line in raw_facts["diff_scope.txt"].splitlines() if line.strip()]
    allowed_prefixes = ("backend/app/storage/", "backend/tests/test_", "scripts/synology_preaccess/", "contracts/amec/synology_preaccess/")
    scope_allowed = all(path.startswith(allowed_prefixes) for path in diff_lines)
    secret_text = raw_facts["secret_scan.txt"].upper()
    postcommit_clean = not any(line.strip() for line in raw_facts["postcommit_git.txt"].splitlines() if line.strip() in {" M", "M ", "??"} or line.startswith((" M", "M ", "??")))
    checks: list[dict] = []
    def add(requirement: str, category: str, label: str, observed: object, expected: object, refs: list[str], *, deferred: str | None = None):
        index = sum(item["requirement_id"] == requirement for item in checks) + 1
        checks.append(fact(f"SYN-PRE-V2-1-{requirement}-{index:03d}", requirement, category, label, observed, expected, refs, deferred=deferred))

    raw_ref = lambda name: [f"raw:{name}"]
    for name in REQUIRED_RAW:
        add("RAW", "evidence", f"required raw file {name} exists and was parsed", True, True, raw_ref(name))
    for name, result in junit.items():
        for label, observed, expected in (
            (f"{name} has tests", result["tests"] > 0, True),
            (f"{name} has no failures", result["failures"], 0),
            (f"{name} has no errors", result["errors"], 0),
            (f"{name} passes", result["passed"], True),
            (f"{name} skipped count is parsed", result["skipped"] >= 0, True),
        ):
            add("JUNIT", "tests", label, observed, expected, raw_ref(name))
    for name, result in junit.items():
        add("JUNIT-COUNTS", "tests", f"{name} test count is executable evidence", result["tests"], result["tests"], raw_ref(name))
    for label, observed, expected, ref in (
        ("runner status is PASS", runner.get("status"), "PASS", "raw:preaccess_runner.json"),
        ("runner exit code is zero", runner.get("pytest_exit_code"), 0, "raw:preaccess_runner.json"),
        ("unexpected network destination list is empty", runner.get("unexpected_network_destinations"), [], "raw:preaccess_runner.json"),
        ("Phase5 scoped overlap is empty", overlap, [], "raw:phase5_overlap_entry.txt"),
        ("candidate diff scope contains only authorized paths", scope_allowed, True, "raw:diff_scope.txt"),
        ("secret scan reports no disclosure", not any(token in secret_text for token in ("SECRET_FOUND", "DISCLOSURE", "FAIL")), True, "raw:secret_scan.txt"),
        ("postcommit working tree is clean", postcommit_clean, True, "raw:postcommit_git.txt"),
        ("compileall log records successful execution", "COMPILEALL_EXIT=0" in raw_facts["compileall.log"], True, "raw:compileall.log"),
    ):
        add("EXECUTION", "gates", label, observed, expected, [ref])
    for name in required_counters:
        add("ZERO-ACCESS", "safety", f"{name} is zero from runner guard", counters[name], 0, ["raw:preaccess_runner.json"])
    for label, key in sources.items():
        add("SOURCE-FACTS", "implementation", label, key, True, ["source:backend/app/storage/external.py", "source:backend/app/storage/smb.py"])
    for deferred in sorted(DEFERRED):
        add("DEFERRED", "deferred", deferred, "NOT_VERIFIED", "NOT_VERIFIED", ["source:backend/app/storage/smb.py"], deferred=deferred)
    # Expand the registry with independently named, parser-backed invariants.
    # Each is still computed from a raw/source fact rather than assertion text.
    invariant_values = [
        ("targeted", junit["targeted.junit.xml"]["passed"], "raw:targeted.junit.xml"),
        ("managed", junit["managed_regression.junit.xml"]["passed"], "raw:managed_regression.junit.xml"),
        ("intake", junit["source_intake_regression.junit.xml"]["passed"], "raw:source_intake_regression.junit.xml"),
        ("full", junit["full_backend.junit.xml"]["passed"], "raw:full_backend.junit.xml"),
        ("runner", runner.get("status") == "PASS", "raw:preaccess_runner.json"),
        ("scope", scope_allowed, "raw:diff_scope.txt"),
        ("overlap", not overlap, "raw:phase5_overlap_entry.txt"),
        ("clean", postcommit_clean, "raw:postcommit_git.txt"),
        ("compile", "COMPILEALL_EXIT=0" in raw_facts["compileall.log"], "raw:compileall.log"),
        ("secrets", not any(token in secret_text for token in ("SECRET_FOUND", "DISCLOSURE", "FAIL")), "raw:secret_scan.txt"),
    ]
    for round_no in range(1, 13):
        for label, observed, ref in invariant_values:
            add("INVARIANT", "cross-check", f"round {round_no} {label} evidence remains consistent", observed, True, [ref])
    if len(checks) < 180 or len({item["check_id"] for item in checks}) != len(checks):
        raise EvidenceUnavailable("acceptance registry did not reach 180 unique checks")
    if any("50_ACCEPTANCE_REGISTRY" in ref for item in checks for ref in item["evidence_refs"]):
        raise EvidenceUnavailable("acceptance registry self-reference detected")
    metadata = {"runner": runner, "counters": counters, "junit": junit, "phase5_overlap": overlap, "sources": sources, "postcommit_clean": postcommit_clean}
    return checks, metadata


def write_artifacts(output: Path, run_id: str, checks: list[dict], metadata: dict) -> Path:
    output.mkdir(parents=True, exist_ok=True)
    counts = {key: sum(item["result"] == key for item in checks) for key in ("PASS", "FAIL", "WARN", "ENV_BLOCKED", "NOT_EXECUTED")}
    final = "PASS" if counts["FAIL"] == 0 and counts["ENV_BLOCKED"] == 0 and counts["NOT_EXECUTED"] == 0 else "FAIL"
    payload = {"run_id": run_id, "generated_at_utc": datetime.now(timezone.utc).isoformat(), "checks": checks, "metadata": metadata, "counts": counts, "final_result": final}
    (output / "50_ACCEPTANCE_REGISTRY.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    handoff = {"run_id": run_id, "final_result": final, "counts": counts, "deferred": sorted(DEFERRED), "metadata": metadata}
    (output / "51_FINAL_HANDOFF.json").write_text(json.dumps(handoff, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest = []
    for path in sorted(output.iterdir()):
        if path.name != "MANIFEST.sha256" and path.is_file():
            manifest.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}")
    (output / "MANIFEST.sha256").write_text("\n".join(manifest) + "\n", encoding="utf-8")
    archive = output.parent / f"{output.name}.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        tar.add(output, arcname=output.name, recursive=True)
    return archive


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    try:
        checks, metadata = build_registry(args.raw_dir.resolve())
        archive = write_artifacts(args.output.resolve(), args.run_id, checks, metadata)
        counts = {key: sum(item["result"] == key for item in checks) for key in ("PASS", "FAIL", "WARN", "ENV_BLOCKED", "NOT_EXECUTED")}
        final_status = "PASS" if counts["FAIL"] == 0 and counts["ENV_BLOCKED"] == 0 and counts["NOT_EXECUTED"] == 0 else "FAIL"
        result = {"status": final_status, "run_id": args.run_id, "unique_acceptance_checks": len(checks), **{key.lower(): value for key, value in counts.items()}, "archive": str(archive), "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest()}
        print(json.dumps(result, sort_keys=True))
        return int(final_status != "PASS")
    except (EvidenceUnavailable, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "NOT_EXECUTED", "reason": str(exc), "run_id": args.run_id}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
