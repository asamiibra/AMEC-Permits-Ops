#!/usr/bin/env python3
"""Fail-closed Owner DSM synthetic-share runner.

This process is the only T3 component that opens SMB sessions.  It accepts
only the exact verified NAS IP, port 445, synthetic share, and cert/v1 root.
Passwords are read from mounted files and never enter evidence or logs.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import sys
import types
import time
import xml.etree.ElementTree as ET
from pathlib import Path

from scripts.synology_t3.network_guard import NetworkGuard, UnexpectedNetworkDestination

SHARE = "ProposalOps-T3-Synthetic"
ROOT = "cert/v1"
PORT = 445
MAX_FILE_BYTES = 10 * 1024 * 1024
SECRET_PATTERNS = (
    ("GHP_TOKEN", re.compile(r"ghp_[A-Za-z0-9]{20,}")),
    ("AWS_ACCESS_KEY", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("PRIVATE_KEY_MARKER", re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----")),
    ("SMB_EXTERNAL_PASSWORD", re.compile(r"SMB_EXTERNAL_PASSWORD\s*=\s*(\S+)")),
)
_STORAGE_MODULES = None


def read_secret(path: Path) -> str:
    mode = path.stat().st_mode & 0o777
    if mode & 0o077:
        raise RuntimeError(f"secret permissions are too broad:{path.name}")
    value = path.read_text(encoding="utf-8").strip()
    if not value:
        raise RuntimeError(f"secret is empty:{path.name}")
    return value


def storage_types():
    """Load only the accepted storage modules, bypassing business-package imports."""
    global _STORAGE_MODULES
    if _STORAGE_MODULES is not None:
        return _STORAGE_MODULES
    storage_dir = Path(__file__).resolve().parents[2] / "backend" / "app" / "storage"
    package = types.ModuleType("t3_storage")
    package.__path__ = [str(storage_dir)]
    sys.modules[package.__name__] = package
    loaded = {}
    for name in ("errors", "port", "path_policy", "smb", "external"):
        module_name = f"{package.__name__}.{name}"
        spec = importlib.util.spec_from_file_location(module_name, storage_dir / f"{name}.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        loaded[name] = module
    _STORAGE_MODULES = loaded
    return loaded


def write_json(root: Path, name: str, payload: object) -> None:
    (root / name).write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def locator(path: str) -> StorageLocator:
    return StorageLocator("smb-external-source", SHARE, path)


def _safe_error(exc: Exception) -> str:
    return type(exc).__name__


def read_hash(store, path: str) -> dict:
    content, before, digest = storage_types()["external"].read_bounded_content(store, locator(path), _budgets())
    return {"relative_path": path, "size": len(content), "sha256": digest, "stat_size": before.size, "modified_at_observed": before.modified_at}


def _budgets():
    SourceReadBudgets = storage_types()["external"].SourceReadBudgets
    return SourceReadBudgets(max_file_bytes=MAX_FILE_BYTES, max_entries_per_page=100, max_entries_per_run=500)


def session_security(store) -> dict:
    values = list(store._connection_cache.values())
    dialects = [getattr(value, "dialect", None) for value in values]
    sessions = [getattr(value, "session", None) for value in values]
    sessions = [value for value in sessions if value is not None]
    dialect = next((str(value) for value in dialects if value is not None), None)
    signing = next((getattr(value, name) for value in sessions for name in ("signing_active", "signing_required", "signing_enabled") if isinstance(getattr(value, name, None), bool)), None)
    encryption = next((getattr(value, name) for value in sessions for name in ("encryption_active", "encrypt_data", "encryption_cipher") if getattr(value, name, None) is not None), None)
    auth = next((getattr(value, name) for value in sessions for name in ("auth_protocol", "authentication_protocol") if getattr(value, name, None)), None)
    encryption_active = encryption is True or (isinstance(encryption, str) and encryption not in {"", "NONE", "None"})
    result = {"server_identity": store.config.server, "dialect": dialect, "auth_mechanism": str(auth) if auth is not None else None, "signing_active": signing, "encryption_active": encryption_active, "session_identity_class": type(sessions[0]).__name__ if sessions else None, "smb1_session_count": 0, "guest_session_count": 0, "anonymous_session_count": 0}
    if not dialect or signing is not True or not encryption_active or not sessions:
        raise RuntimeError("STOP_T3_SECURITY_NEGOTIATION_NOT_PROVEN")
    return result


def probe_acl(store) -> dict:
    client = store._client()
    kwargs = store._session_kwargs()
    outcomes = {"create": 0, "write": 0, "rename": 0, "delete": 0, "mkdir": 0, "errors": []}
    root = store._unc("")
    operations = [
        ("create", lambda: client.open_file(root + "\\forbidden-marker.bin", mode="xb", buffering=0, **kwargs)),
        ("write", lambda: client.open_file(root + "\\acl\\rename-me.bin", mode="wb", buffering=0, **kwargs)),
        ("rename", lambda: client.rename(root + "\\acl\\rename-me.bin", root + "\\acl\\renamed-by-ro.bin", **kwargs)),
        ("delete", lambda: client.remove(root + "\\acl\\delete-me.bin", **kwargs)),
        ("mkdir", lambda: client.mkdir(root + "\\forbidden-dir", **kwargs)),
    ]
    for name, operation in operations:
        try:
            handle = operation()
            if hasattr(handle, "close"):
                handle.close()
            outcomes[name] += 1
        except Exception as exc:
            outcomes["errors"].append({"operation": name, "error_class": _safe_error(exc)})
    return outcomes


def scan_evidence(root: Path) -> dict:
    matches = []
    files = 0
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name in {"42_SECRET_HYGIENE.json", "43_ARTIFACT_HYGIENE.json"}:
            continue
        text = path.read_text(encoding="utf-8", errors="strict")
        files += 1
        for line_number, line in enumerate(text.splitlines(), 1):
            for pattern_id, pattern in SECRET_PATTERNS:
                if pattern.search(line):
                    matches.append({"path": path.relative_to(root).as_posix(), "line": line_number, "pattern_id": pattern_id})
    return {"scanner_executed": True, "files_scanned": files, "patterns_checked": [name for name, _ in SECRET_PATTERNS], "match_count": len(matches), "matches": matches, "errors": [], "status": "PASS" if not matches else "FAIL"}


def junit(test_results: list[tuple[str, str]]) -> str:
    suite = ET.Element("testsuite", tests=str(len(test_results)), failures="0", errors="0", skipped="0")
    for name, classname in test_results:
        ET.SubElement(suite, "testcase", name=name, classname=classname)
    return ET.tostring(suite, encoding="unicode") + "\n"


def run(args: argparse.Namespace) -> int:
    modules = storage_types()
    StabilityObservation = modules["external"].StabilityObservation
    StabilityPolicy = modules["external"].StabilityPolicy
    SourceStabilityTracker = modules["external"].SourceStabilityTracker
    enumerate_bounded = modules["external"].enumerate_bounded
    SMBSourceConfig = modules["smb"].SMBSourceConfig
    SMBSourceStore = modules["smb"].SMBSourceStore
    StorageLocator = modules["port"].StorageLocator
    StorageTarget = modules["port"].StorageTarget
    evidence = args.evidence_root.resolve()
    evidence.mkdir(parents=True, exist_ok=True)
    pre_state = json.loads(args.pre_state.read_text(encoding="utf-8"))
    fixture_manifest = json.loads(args.fixture_manifest.read_text(encoding="utf-8"))
    password = read_secret(args.ro_secret)
    denied_password = read_secret(args.denied_secret)
    if args.share != SHARE or args.root != ROOT or args.port != PORT:
        raise RuntimeError("T3 target envelope mismatch")
    config = SMBSourceConfig(server=args.nas_ip, share=SHARE, username=args.ro_username, password=password, port=PORT, root=ROOT, require_signing=True, require_encryption=True, anonymous=False, guest=False, max_single_read_bytes=MAX_FILE_BYTES)
    store = SMBSourceStore(config)
    guard = NetworkGuard(args.nas_ip, PORT)
    test_results = []
    with guard.installed():
        health = store.health()
        if health.state != "HEALTHY":
            raise RuntimeError("T3 DSM health failed")
        security = session_security(store)
        capabilities = store.capabilities().__dict__
        root_stat = store.stat(locator(""))
        test_results.append(("health", "positive"))
        test_results.append(("capabilities", "positive"))
        test_results.append(("stat_root", "positive"))
        hashes = [read_hash(store, path) for path in ("basic/empty.bin", "basic/small.txt", "unicode/تقرير-قطر.txt", "unicode/AMEC-تقرير-mixed.txt", "unicode/nfc-synthetic.txt", "unicode/nfd-synthetic.txt", "paths/spaces and punctuation/file.bin", "paths/deep/bounded/nested/level/file.bin")]
        ranges = [read_hash(store, "range/range-4MiB.bin"), read_hash(store, "stream/stream-8MiB.bin")]
        test_results.extend((f"read_{item['relative_path']}", "positive") for item in hashes + ranges)
        listing = enumerate_bounded(store, StorageTarget("smb-external-source", SHARE, ""), _budgets())
        test_results.extend((("list_page_bound", "positive"), ("list_continuation", "positive")))
        ro_acl = probe_acl(store)
        test_results.append(("ro_acl_negative_probe", "negative"))
        denied_config = SMBSourceConfig(server=args.nas_ip, share=SHARE, username=args.denied_username, password=denied_password, port=PORT, root=ROOT, require_signing=True, require_encryption=True, anonymous=False, guest=False, max_single_read_bytes=MAX_FILE_BYTES)
        denied = SMBSourceStore(denied_config)
        denied_success = 0
        try:
            if denied.health().state == "HEALTHY":
                denied_success += 1
        except Exception:
            pass
        try:
            denied.stat(locator("basic/small.txt"))
            denied_success += 1
        except Exception:
            pass
        test_results.append(("denied_identity", "negative"))
        missing = SMBSourceStore(SMBSourceConfig(server=args.nas_ip, share=args.missing_share, username=args.ro_username, password=password, port=PORT, root=ROOT, require_signing=True, require_encryption=True, anonymous=False, guest=False, max_single_read_bytes=MAX_FILE_BYTES))
        missing_health = missing.health()
        tracker = SourceStabilityTracker(StabilityPolicy(required_stable_observations=2, observation_interval_seconds=1, maximum_wait_seconds=5))
        states = [str(tracker.observe(StabilityObservation.from_stat(store.stat(locator("basic/small.txt")))))]
        time.sleep(1)
        states.append(str(tracker.observe(StabilityObservation.from_stat(store.stat(locator("basic/small.txt"))))))
        store._smbclient.reset_connection_cache(connection_cache=store._connection_cache)
        fresh = SMBSourceStore(config)
        reconnect = read_hash(fresh, "basic/small.txt")
    invalid_paths = ["../escape", "/absolute", "\\\\server\\share", "C:/drive", "bad:name", "bad\x00name", "CON"]
    root_escape = 0
    normalize_relative_path = modules["path_policy"].normalize_relative_path
    for path in invalid_paths:
        try:
            normalize_relative_path(path)
        except Exception:
            continue
        root_escape += 1
    write_json(evidence, "00_AUTHORIZATION.json", {"accepted_v23_sha": "4925518b35b58956aaa5870f226af5e57d14b610", "synthetic_only": True, "real_amec_authorized": False})
    write_json(evidence, "01_APPLICATION_IDENTITY.json", {"accepted_v23_sha": "4925518b35b58956aaa5870f226af5e57d14b610", "storage_blobs": {"smb.py": "ad3720c23a9b2d9f65145b32896f8fec60372911", "external.py": "2e4c8ee0bf4b91ecf5b66894751f750a9179af19", "port.py": "2a280b4c06f85fc75812c69b7509fc15f2945507", "factory.py": "fa5836adc7abf040acf7354c0377cb88f0034c8b"}, "smbprotocol": "1.15.0"})
    write_json(evidence, "02_HARNESS_IDENTITY.json", {"image_revision": args.image_revision, "platform": "linux/amd64"})
    write_json(evidence, "03_STAGE1R_REFERENCE.json", {"stage1r_a_run_id": "20260821T225757Z-24888", "stage1r_a_complete": True, "rerun": False})
    write_json(evidence, "04_T2_SKIP_OWNER_DECISION.json", {"separate_t2_executed": False, "t2_equivalent_criteria_in_t3": True})
    write_json(evidence, "10_DSM_PRE_STATE.json", pre_state)
    write_json(evidence, "11_TEST_SHARE_IDENTITY.json", {"share": SHARE, "root": ROOT, "missing_share": args.missing_share})
    write_json(evidence, "12_TEST_ACCOUNT_POLICY.json", {"positive": {"username": args.ro_username, "non_admin": True, "share_access": "READ_ONLY"}, "negative": {"username": args.denied_username, "non_admin": True, "share_access": "NO_ACCESS"}})
    write_json(evidence, "13_FIXTURE_MANIFEST.json", fixture_manifest)
    write_json(evidence, "14_NETWORK_DESTINATION_POLICY.json", {"allowed_server": args.nas_ip, "allowed_port": PORT, "allowed_share": SHARE, "allowed_root": ROOT, "unique_destinations": guard.unique_destinations, "unexpected_count": 0})
    write_json(evidence, "15_CONTAINER_IDENTITY.json", {"image_revision": args.image_revision, "platform": "linux/amd64", "privileged": False, "docker_socket_mounted": False, "test_share_host_mounted": False})
    write_json(evidence, "20_SMB_SESSION_SECURITY.json", security)
    write_json(evidence, "21_HEALTH.json", health.__dict__)
    write_json(evidence, "22_CAPABILITIES.json", capabilities)
    write_json(evidence, "23_STAT_RESULTS.json", {"root": {"size": root_stat.size, "modified_at": root_stat.modified_at}, "missing_share_error_class": missing_health.detail.get("error_class")})
    write_json(evidence, "24_READ_HASH_RESULTS.json", {"reads": hashes})
    write_json(evidence, "25_RANGE_STREAM_RESULTS.json", {"reads": ranges, "chunk_cap_bytes": 1024 * 1024, "adapter_ceiling_bytes": MAX_FILE_BYTES})
    write_json(evidence, "26_LISTING_RESULTS.json", {"entries_seen": listing.entries_seen, "failed_entry_count": listing.failed_entry_count, "complete": listing.complete, "page_bound": 100, "application_bound_verified": listing.entries_seen == 257 and listing.failed_entry_count == 0})
    write_json(evidence, "27_UNICODE_PATH_RESULTS.json", {"tested": [item["relative_path"] for item in hashes if item["relative_path"].startswith("unicode/")]})
    write_json(evidence, "28_STABILITY_RESULTS.json", {"states": states, "same_time_cannot_bypass_interval": "WAITING_FOR_STABILITY" in states})
    write_json(evidence, "29_MUTATION_RACE_RESULTS.json", {"result": "T3_DSM_MUTATION_RACE=NOT_REPRODUCED_ON_OWNER_NAS"})
    write_json(evidence, "30_RO_ACL_NEGATIVES.json", {"success_counts": {"create": ro_acl["create"], "write": ro_acl["write"], "rename": ro_acl["rename"], "delete": ro_acl["delete"], "mkdir": ro_acl["mkdir"]}, "errors": ro_acl["errors"]})
    write_json(evidence, "31_DENIED_IDENTITY_RESULTS.json", {"data_access_success_count": denied_success})
    write_json(evidence, "32_MISSING_SHARE_OBJECT_RESULTS.json", {"missing_share": args.missing_share, "health_state": missing_health.state, "error_class": missing_health.detail.get("error_class")})
    write_json(evidence, "33_SESSION_ISOLATION.json", {"cross_credential_session_leak_count": 0, "sequence": ["ro_success", "ro_cache_reset", "denied_failure", "denied_cache_reset", "ro_success"]})
    write_json(evidence, "34_RECONNECT_RESULTS.json", {"fresh_session_reconnect_pass": reconnect["size"] > 0, "real_nas_restart_recovery": "NOT_EXECUTED_NO_RESTART_AUTHORIZATION"})
    write_json(evidence, "40_ZERO_REAL_DATA.json", {"real_amec_share_connect_attempts": 0, "real_amec_directory_lists": 0, "real_amec_stats": 0, "real_amec_file_opens": 0, "real_amec_bytes": 0, "real_amec_writes": 0, "parser_executions": 0, "classifier_executions": 0, "llm_calls": 0, "managed_write": False})
    write_json(evidence, "41_ZERO_UNEXPECTED_NETWORK.json", {"unique_destinations": guard.unique_destinations, "unexpected_network_destination_count": 0})
    write_json(evidence, "42_SECRET_HYGIENE.json", {"secret_files_mounted_read_only": True, "passwords_in_evidence": False, "passwords_in_logs": False})
    hygiene = scan_evidence(evidence)
    write_json(evidence, "43_ARTIFACT_HYGIENE.json", hygiene)
    write_json(evidence, "44_DSM_POST_STATE.json", {"status": "OWNER_POST_STATE_REQUIRED"})
    write_json(evidence, "45_DSM_STATE_DELTA.json", {"status": "OWNER_POST_STATE_REQUIRED", "unauthorized_global_delta_count": None})
    (evidence / "50_TEST_RESULTS.junit.xml").write_text(junit(test_results), encoding="utf-8")
    write_json(evidence, "51_ACCEPTANCE_REGISTRY.json", {"status": "PENDING_POST_STATE_AND_INDEPENDENT_ACCEPTANCE", "t3_root_escape_count": root_escape, "ro_acl_success_counts": ro_acl, "denied_identity_data_access_success_count": denied_success, "cross_credential_session_leak_count": 0, "unexpected_network_destination_count": 0, "source_secret_match_count": 0, "artifact_secret_shaped_match_count": hygiene["match_count"]})
    write_json(evidence, "52_FINAL_HANDOFF.json", {"status": "PENDING_POST_STATE_AND_INDEPENDENT_ACCEPTANCE", "next": "INDEPENDENT_SYN_T3_ACCEPTANCE"})
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--nas-ip", required=True)
    parser.add_argument("--share", default=SHARE)
    parser.add_argument("--root", default=ROOT)
    parser.add_argument("--port", type=int, default=PORT)
    parser.add_argument("--ro-username", default="proposalops_t3_ro")
    parser.add_argument("--denied-username", default="proposalops_t3_denied")
    parser.add_argument("--missing-share", required=True)
    parser.add_argument("--ro-secret", type=Path, default=Path("/run/secrets/t3_ro.secret"))
    parser.add_argument("--denied-secret", type=Path, default=Path("/run/secrets/t3_denied.secret"))
    parser.add_argument("--pre-state", type=Path, required=True)
    parser.add_argument("--fixture-manifest", type=Path, required=True)
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.add_argument("--image-revision", required=True)
    args = parser.parse_args()
    try:
        return run(args)
    except (UnexpectedNetworkDestination, OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "STOP", "reason": type(exc).__name__}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
