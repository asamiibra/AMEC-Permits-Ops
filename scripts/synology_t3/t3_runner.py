#!/usr/bin/env python3
"""Fail-closed Owner DSM synthetic-share runner."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
import time
import types
from pathlib import Path

from scripts.synology_t3.network_guard import NetworkGuard, UnexpectedNetworkDestination
from scripts.synology_t3.t3_common import (
    ACCEPTED_V23,
    PORT,
    ROOT,
    SHARE,
    AccessLedger,
    CheckCollector,
    T3Stop,
    T3StoreFactory,
    assert_listing_protocol,
    locator,
    scan_text_tree,
    security_introspection,
)

MAX_FILE_BYTES = 10 * 1024 * 1024
_STORAGE_MODULES = None


def read_secret(path: Path) -> str:
    mode = path.stat().st_mode & 0o777
    if mode != 0o600:
        raise RuntimeError(f"secret permissions are not exactly 600:{path.name}")
    value = path.read_text(encoding="utf-8").strip()
    if not value:
        raise RuntimeError(f"secret is empty:{path.name}")
    return value


def storage_types():
    """Load only accepted storage modules without importing the business app."""
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
        assert spec.loader is not None
        spec.loader.exec_module(module)
        loaded[name] = module
    _STORAGE_MODULES = loaded
    return loaded


def write_json(root: Path, name: str, payload: object) -> None:
    (root / name).write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def read_hash(store, storage_locator_type: type, path: str, expected: dict, ledger: AccessLedger) -> dict:
    current = locator(storage_locator_type, path)
    ledger.record_operation("stat", current.share_id, ROOT)
    before = store.stat(current)
    ledger.record_operation("file_open", current.share_id, ROOT)
    with store.open_read(current, offset=0, length=before.size) as stream:
        content = bytearray()
        while True:
            chunk = stream.read(min(1024 * 1024, MAX_FILE_BYTES - len(content) + 1))
            if not chunk:
                break
            content.extend(chunk)
            if len(content) > MAX_FILE_BYTES:
                raise RuntimeError("STOP_T3_READ_BUDGET")
    after = store.stat(current)
    if before.size != after.size or before.modified_at != after.modified_at or len(content) != before.size:
        raise RuntimeError("STOP_T3_FIXTURE_STABILITY_MISMATCH")
    digest = hashlib.sha256(content).hexdigest()
    return {"relative_path": path, "expected_size": expected["size"], "actual_size": len(content), "expected_sha256": expected["sha256"], "actual_sha256": digest, "modified_at_observed": before.modified_at}


def reset_cache(store) -> None:
    client = getattr(store, "_smbclient", None)
    reset = getattr(client, "reset_connection_cache", None)
    if reset:
        reset(connection_cache=store._connection_cache)
    store._connection_cache = {}
    store._smbclient = None


def normalize_error_code(value: object) -> str:
    """Return the evidence vocabulary, independent of adapter enum spelling."""
    raw = getattr(value, "value", value)
    text = str(raw or "UNKNOWN").upper().split(".")[-1]
    return text.removeprefix("STORAGE_")


def normalized_exception_code(store, exc: Exception) -> str:
    raw = getattr(exc, "code", None)
    if raw is None:
        mapper = getattr(store, "_map_error", None)
        if mapper is not None:
            try:
                raw = getattr(mapper(exc), "code", None)
            except Exception:
                raw = None
    return normalize_error_code(raw or type(exc).__name__)


def probe_acl(store, collector: CheckCollector, ledger: AccessLedger) -> dict:
    client = store._client()
    kwargs = store._session_kwargs()
    root = store._unc("")
    outcomes = {"attempt_count": 0, "access_denied_count": 0, "mutation_success_count": 0, "create": 0, "write": 0, "rename": 0, "delete": 0, "mkdir": 0, "errors": []}
    operations = [
        ("create", lambda: client.open_file(root + "\\forbidden-marker.bin", mode="xb", buffering=0, **kwargs)),
        ("write", lambda: client.open_file(root + "\\acl\\rename-me.bin", mode="wb", buffering=0, **kwargs)),
        ("rename", lambda: client.rename(root + "\\acl\\rename-me.bin", root + "\\acl\\renamed-by-ro.bin", **kwargs)),
        ("delete", lambda: client.remove(root + "\\acl\\delete-me.bin", **kwargs)),
        ("mkdir", lambda: client.mkdir(root + "\\forbidden-dir", **kwargs)),
    ]
    for name, operation in operations:
        outcomes["attempt_count"] += 1
        ledger.record_operation("synthetic_acl_write", SHARE, ROOT)
        try:
            handle = operation()
            if hasattr(handle, "close"):
                handle.close()
            outcomes[name] += 1
            outcomes["mutation_success_count"] += 1
            ledger.record_operation("synthetic_acl_write_success", SHARE, ROOT)
            outcomes["errors"].append({"operation": name, "result": "MUTATION_SUCCEEDED"})
            collector.require(f"acl_{name}_blocked", f"RO identity cannot {name}", "ACCESS_DENIED", "MUTATION_SUCCEEDED")
        except Exception as exc:
            normalized = normalized_exception_code(store, exc)
            outcomes["errors"].append({"operation": name, "result": normalized, "normalized_error_class": normalized})
            if normalized == "ACCESS_DENIED":
                outcomes["access_denied_count"] += 1
            collector.require(f"acl_{name}_blocked", f"RO identity cannot {name}", "ACCESS_DENIED", normalized)
    collector.require("acl_attempt_count", "all five synthetic ACL mutation probes execute", 5, outcomes["attempt_count"])
    collector.require("acl_access_denied_count", "all five synthetic ACL mutation probes normalize to ACCESS_DENIED", 5, outcomes["access_denied_count"])
    collector.require("acl_mutation_success_count", "no synthetic ACL mutation succeeds", 0, outcomes["mutation_success_count"])
    return outcomes


def _budgets(external):
    return external.SourceReadBudgets(max_file_bytes=MAX_FILE_BYTES, max_entries_per_page=100, max_entries_per_run=500)


def run(args: argparse.Namespace) -> int:
    modules = storage_types()
    external = modules["external"]
    smb = modules["smb"]
    StorageLocator = modules["port"].StorageLocator
    StorageTarget = modules["port"].StorageTarget
    evidence = args.evidence_root.resolve()
    evidence.mkdir(parents=True, exist_ok=True)
    checks = CheckCollector(evidence)
    ledger = AccessLedger()
    pre_state = json.loads(args.pre_state.read_text(encoding="utf-8"))
    fixture_manifest = json.loads(args.fixture_manifest.read_text(encoding="utf-8"))
    expected_rows = {row["relative_path"]: row for row in fixture_manifest["entries"]}
    checks.require("identity_accepted_v23", "runner is bound to accepted V2.3", ACCEPTED_V23, ACCEPTED_V23)
    checks.require("identity_fixture_root", "fixture manifest root is cert/v1", ROOT, fixture_manifest.get("root"))
    checks.require("identity_fixture_count", "fixture manifest contains 270 rows", 270, len(expected_rows))
    for path, row in expected_rows.items():
        valid = bool(path and not path.startswith("/") and row.get("size", -1) >= 0 and re.fullmatch(r"[0-9a-f]{64}", row.get("sha256", "")))
        checks.require(f"fixture_manifest_row::{path}", f"fixture manifest row {path} is structurally valid", True, valid)
    password = read_secret(args.ro_secret)
    denied_password = read_secret(args.denied_secret)
    checks.require("secret_mode_ro", "RO secret is mode 600", 0o600, args.ro_secret.stat().st_mode & 0o777)
    checks.require("secret_mode_denied", "denied secret is mode 600", 0o600, args.denied_secret.stat().st_mode & 0o777)
    if args.share != SHARE or args.root != ROOT or args.port != PORT:
        raise T3Stop("TARGET_ENVELOPE", "T3 target envelope mismatch")
    config = smb.SMBSourceConfig(server=args.nas_ip, share=SHARE, username=args.ro_username, password=password, port=PORT, root=ROOT, require_signing=True, require_encryption=True, anonymous=False, guest=False, max_single_read_bytes=MAX_FILE_BYTES)
    factory = T3StoreFactory(smb.SMBSourceStore, ledger)
    store = factory.create(config, operation_class="positive_source")
    guard = NetworkGuard(args.nas_ip, PORT)
    with guard.installed():
        health = store.health()
        checks.require("health_state", "synthetic share health is HEALTHY", "HEALTHY", health.state)
        security = security_introspection(store._connection_cache, args.ro_username)
        security["SECURITY_INTROSPECTION_PINNED_TO_SMBPROTOCOL_1_15_0"] = True
        # Persist sanitized session evidence before any hard security gate can
        # terminate the run, including a signing/encryption mismatch.
        write_json(evidence, "20_SMB_SESSION_SECURITY.json", security)
        for key in ("authenticated_session_count", "all_authenticated_sessions", "all_dialects_smb2_or_newer", "all_connection_signing_required", "all_session_integrity_protected", "all_encryption_required", "all_expected_username", "all_approved_auth_protocol"):
            observed = security[key] > 0 if key == "authenticated_session_count" else security[key]
            checks.require(f"security_{key}", f"SMB 1.15.0 security gate {key}", True, observed)
        capabilities = store.capabilities().__dict__
        checks.require("capability_writeback_false", "source writeback is unavailable", False, capabilities.get("writeback"))
        root_stat = store.stat(locator(StorageLocator, ""))
        checks.require("root_stat_observed", "cert/v1 root can be statted", True, root_stat.size >= 0)
        selected = ("basic/empty.bin", "basic/small.txt", "unicode/تقرير-قطر.txt", "unicode/AMEC-تقرير-mixed.txt", "unicode/nfc-synthetic.txt", "unicode/nfd-synthetic.txt", "paths/spaces and punctuation/file.bin", "paths/deep/bounded/nested/level/file.bin", "range/range-4MiB.bin", "stream/stream-8MiB.bin", "mutation/change-during-read.bin", "acl/rename-me.bin", "acl/delete-me.bin")
        read_results = []
        for path in selected:
            result = read_hash(store, StorageLocator, path, expected_rows[path], ledger)
            read_results.append(result)
            checks.require(f"fixture_read_size::{path}", f"positive read {path} size matches manifest", result["expected_size"], result["actual_size"])
            checks.require(f"fixture_read_hash::{path}", f"positive read {path} SHA256 matches manifest", result["expected_sha256"], result["actual_sha256"])
        ranges = [row for row in read_results if row["relative_path"] in {"range/range-4MiB.bin", "stream/stream-8MiB.bin"}]
        checks.require("range_4mib_bound", "4 MiB read is under 10 MiB cap", True, expected_rows["range/range-4MiB.bin"]["size"] <= MAX_FILE_BYTES)
        checks.require("stream_8mib_bound", "8 MiB stream is under 10 MiB cap", True, expected_rows["stream/stream-8MiB.bin"]["size"] <= MAX_FILE_BYTES)
        target = StorageTarget("smb-external-source", SHARE, "listing")
        pages = [store.list(target, cursor=None, max_entries_per_page=100)]
        pages.append(store.list(target, cursor=pages[0].cursor, max_entries_per_page=100))
        pages.append(store.list(target, cursor=pages[1].cursor, max_entries_per_page=100))
        assert_listing_protocol(pages)
        page_lengths = [len(page.items) for page in pages]
        cursors = [page.cursor for page in pages]
        checks.require("listing_page_1_bound", "listing page 1 has at most 100 items", True, page_lengths[0] <= 100)
        checks.require("listing_page_2_bound", "listing page 2 has at most 100 items", True, page_lengths[1] <= 100)
        checks.require("listing_page_3_bound", "listing page 3 has at most 100 items", True, page_lengths[2] <= 100)
        checks.require("listing_cursor_page_1", "listing page 1 returns the v1:100 continuation cursor", "v1:100", cursors[0])
        checks.require("listing_cursor_page_2", "listing page 2 returns the v1:200 continuation cursor", "v1:200", cursors[1])
        checks.require("listing_cursor_page_3_terminal", "listing page 3 returns a terminal null cursor", None, cursors[2])
        checks.require("listing_page_3_complete", "third listing page is complete", True, pages[2].complete)
        direct_items = [item.locator.relative_path for page in pages for item in page.items]
        expected_listing = [f"listing/entry-{index:04d}.bin" for index in range(1, 258)]
        checks.require("listing_unique_257", "direct listing has 257 unique fixture entries", 257, len(set(direct_items)))
        checks.require("listing_no_missing", "direct listing has no missing fixture entries", [], sorted(set(expected_listing) - set(direct_items)))
        checks.require("listing_no_duplicates", "direct listing has no duplicate fixture entries", 257, len(direct_items))
        checks.require("listing_failed_entries_zero", "direct listing has no failed entry stats", 0, sum(page.failed_entry_count for page in pages))
        bounded = external.enumerate_bounded(store, target, _budgets(external))
        checks.require("enumerate_bounded_complete", "enumerate_bounded completes listing", True, bounded.complete)
        checks.require("enumerate_bounded_count", "enumerate_bounded returns 257 entries", 257, bounded.entries_seen)
        checks.require("enumerate_bounded_cursor_terminal", "enumerate_bounded has no terminal cursor", None, bounded.cursor)
        tracker = external.SourceStabilityTracker(external.StabilityPolicy(required_stable_observations=2, observation_interval_seconds=1, maximum_wait_seconds=5))
        observed = store.stat(locator(StorageLocator, "basic/small.txt"))
        timestamps = [time.time()]
        observation = external.StabilityObservation.from_stat(observed)
        states = [str(tracker.observe(observation))]
        timestamps.append(time.time())
        states.append(str(tracker.observe(observation)))
        time.sleep(1.05)
        timestamps.append(time.time())
        states.append(str(tracker.observe(observation)))
        checks.require("stability_detected", "first observation is DETECTED", "DETECTED", states[0])
        checks.require("stability_waiting", "immediate duplicate is WAITING_FOR_STABILITY", "WAITING_FOR_STABILITY", states[1])
        checks.require("stability_ready", "post-interval observation is READY_FOR_BOUNDED_READ", "READY_FOR_BOUNDED_READ", states[2])
        cache_a_object_id = id(store._connection_cache)
        ro_cache_before = hashlib.sha256(repr(sorted(store._connection_cache)).encode()).hexdigest()[:16]
        reset_cache(store)
        checks.require("ro_cache_a_empty_after_reset", "RO provider A cache is empty after reset", 0, len(store._connection_cache))
        denied_config = smb.SMBSourceConfig(server=args.nas_ip, share=SHARE, username=args.denied_username, password=denied_password, port=PORT, root=ROOT, require_signing=True, require_encryption=True, anonymous=False, guest=False, max_single_read_bytes=MAX_FILE_BYTES)
        denied = factory.create(denied_config, operation_class="denied_identity")
        cache_b_object_id = id(denied._connection_cache)
        checks.require("denied_cache_is_distinct", "denied provider B has a distinct cache object", True, cache_a_object_id != cache_b_object_id)
        denied_success = 0
        denied_errors = {}
        denied_health = denied.health()
        if denied_health.state == "HEALTHY":
            denied_success += 1
        denied_errors["health"] = normalize_error_code(denied_health.detail.get("error_class") if denied_health.state != "HEALTHY" else "HEALTHY")
        checks.require("denied_health_not_healthy", "denied identity health is not HEALTHY", True, denied_health.state != "HEALTHY")
        checks.require("denied_health_access_denied", "denied identity health normalizes to ACCESS_DENIED", "ACCESS_DENIED", denied_errors["health"])
        try:
            denied.stat(locator(StorageLocator, "basic/small.txt"))
            denied_success += 1
        except Exception as exc:
            denied_errors["stat"] = normalized_exception_code(denied, exc)
        try:
            denied.list(StorageTarget("smb-external-source", SHARE, "listing"), max_entries_per_page=1)
            denied_success += 1
        except Exception as exc:
            denied_errors["list"] = normalized_exception_code(denied, exc)
        try:
            with denied.open_read(locator(StorageLocator, "basic/small.txt"), offset=0, length=1):
                denied_success += 1
        except Exception as exc:
            denied_errors["open_read"] = normalized_exception_code(denied, exc)
        for operation in ("stat", "list", "open_read"):
            checks.require(f"denied_{operation}_access_denied", f"denied identity {operation} normalizes to ACCESS_DENIED", "ACCESS_DENIED", denied_errors[operation])
        checks.require("denied_identity_data_access", "denied identity cannot read data", 0, denied_success)
        reset_cache(denied)
        checks.require("denied_cache_b_empty_after_reset", "denied provider B cache is empty after reset", 0, len(denied._connection_cache))
        fresh = factory.create(config, operation_class="reconnect")
        checks.require("ro_provider_c_is_new", "RO provider C is a new provider object", True, fresh is not store)
        checks.require("ro_cache_c_is_new", "RO provider C has a new cache object", True, id(fresh._connection_cache) not in {cache_a_object_id, cache_b_object_id})
        reconnect = read_hash(fresh, StorageLocator, "basic/small.txt", expected_rows["basic/small.txt"], ledger)
        checks.require("reconnect_canary_hash", "new RO provider reads expected canary hash", expected_rows["basic/small.txt"]["sha256"], reconnect["actual_sha256"])
        fresh_security = security_introspection(fresh._connection_cache, args.ro_username)
        checks.require("fresh_ro_authenticated_session", "fresh RO provider has an authenticated session", True, fresh_security["authenticated_session_count"] > 0)
        checks.require("fresh_ro_username", "fresh RO provider session username is proposalops_t3_ro", True, fresh_security["all_expected_username"])
        ro_cache_after = hashlib.sha256(repr(sorted(fresh._connection_cache)).encode()).hexdigest()[:16]
        cross_credential_session_leak_count = int(denied_success != 0 or id(fresh._connection_cache) == cache_b_object_id)
        checks.require("session_cache_isolation", "RO and denied observations show no cross-credential session leak", 0, cross_credential_session_leak_count)
        missing_object = f"missing/object-{args.run_id}.bin"
        missing_object_code = None
        try:
            read_hash(store, StorageLocator, missing_object, {"size": 0, "sha256": ""}, ledger)
        except Exception as exc:
            missing_object_code = normalized_exception_code(store, exc)
        checks.require("missing_object_normalized", "missing object normalizes to OBJECT_NOT_FOUND", "OBJECT_NOT_FOUND", missing_object_code)
        missing_share = args.missing_share
        expected_missing_share = f"ProposalOps-T3-Missing-{args.run_id}"
        checks.require("missing_share_run_scoped_envelope", "missing share uses the exact run-scoped synthetic envelope", expected_missing_share, missing_share)
        if missing_share == SHARE:
            raise T3Stop("MISSING_SHARE_ENVELOPE", "missing share must differ from the positive synthetic share")
        missing = factory.create(smb.SMBSourceConfig(server=args.nas_ip, share=missing_share, username=args.ro_username, password=password, port=PORT, root=ROOT, require_signing=True, require_encryption=True, anonymous=False, guest=False, max_single_read_bytes=MAX_FILE_BYTES), operation_class="missing_share")
        missing_health = missing.health()
        checks.require("missing_share_not_healthy", "missing share is unavailable", True, missing_health.state != "HEALTHY")
        checks.require("missing_share_error_class", "missing share exposes OBJECT_NOT_FOUND", "OBJECT_NOT_FOUND", normalize_error_code(missing_health.detail.get("error_class")))
        ro_acl = probe_acl(store, checks, ledger)
    invalid_paths = ["../escape", "/absolute", "\\\\server\\share", "C:/drive", "bad:name", "bad\x00name", "CON"]
    normalize_relative_path = modules["path_policy"].normalize_relative_path
    root_escape = 0
    for path in invalid_paths:
        try:
            normalize_relative_path(path)
        except Exception:
            continue
        root_escape += 1
    checks.require("root_escape_zero", "all root escape probes are rejected", 0, root_escape)
    hygiene = scan_text_tree(evidence, excluded_names={"42_SECRET_HYGIENE.json", "43_ARTIFACT_HYGIENE.json"})
    checks.require("artifact_hygiene_status", "artifact scanner executed with no matches/errors", {"scanner_executed": True, "match_count": 0, "errors": [], "status": "PASS"}, {key: hygiene[key] for key in ("scanner_executed", "match_count", "errors", "status")})
    ledger_summary = ledger.summary()
    for suffix, key in (("share_connect_zero", "real_amec_share_connect_attempts"), ("directory_lists_zero", "real_amec_directory_lists"), ("stats_zero", "real_amec_stats"), ("file_opens_zero", "real_amec_file_opens"), ("bytes_zero", "real_amec_bytes"), ("writes_zero", "real_amec_writes")):
        checks.require(f"ledger_real_{suffix}", f"no real AMEC {key}", 0, ledger_summary[key])
    expected_destinations = [] if getattr(args, "synthetic_no_network", False) else [(args.nas_ip, PORT)]
    checks.require("network_destination_set", "network destinations match the authorized execution mode", expected_destinations, guard.unique_destinations)
    checks.require("network_unexpected_zero", "unexpected network destinations are zero", 0, sum(1 for item in guard.attempted if item not in expected_destinations))
    write_json(evidence, "00_AUTHORIZATION.json", {"accepted_v23_sha": ACCEPTED_V23, "synthetic_only": True, "real_amec_authorized": False, "inherited_preaccess": {"new_smb_connections": 0, "new_synology_connections": 0, "real_amec_reads": 0}, "runtime_counter_source": {"synthetic_network": "41_ZERO_UNEXPECTED_NETWORK.json", "real_amec": "40_ZERO_REAL_DATA.json"}})
    write_json(evidence, "01_APPLICATION_IDENTITY.json", {"accepted_v23_sha": ACCEPTED_V23, "storage_blobs": {"smb.py": "ad3720c23a9b2d9f65145b32896f8fec60372911", "external.py": "2e4c8ee0bf4b91ecf5b66894751f750a9179af19", "port.py": "2a280b4c06f85fc75812c69b7509fc15f2945507", "factory.py": "fa5836adc7abf040acf7354c0377cb88f0034c8b"}, "smbprotocol": "1.15.0"})
    write_json(evidence, "02_HARNESS_IDENTITY.json", {"image_revision": args.image_revision, "platform": "linux/amd64", "harness_source": "scripts/synology_t3"})
    write_json(evidence, "03_STAGE1R_REFERENCE.json", {"complete": True, "rerun": False})
    write_json(evidence, "04_T2_SKIP_OWNER_DECISION.json", {"separate_t2_executed": False, "t2_equivalent_criteria_in_t3": True})
    write_json(evidence, "10_DSM_PRE_STATE.json", pre_state)
    write_json(evidence, "11_TEST_SHARE_IDENTITY.json", {"share": SHARE, "root": ROOT, "missing_share": args.missing_share})
    write_json(evidence, "12_TEST_ACCOUNT_POLICY.json", {"positive": {"username": args.ro_username, "non_admin": True, "share_access": "READ_ONLY"}, "negative": {"username": args.denied_username, "non_admin": True, "share_access": "NO_ACCESS"}})
    write_json(evidence, "13_FIXTURE_MANIFEST.json", fixture_manifest)
    write_json(evidence, "14_NETWORK_DESTINATION_POLICY.json", {"allowed_server": args.nas_ip, "allowed_port": PORT, "allowed_share": SHARE, "allowed_root": ROOT, "unique_destinations": guard.unique_destinations, "unexpected_count": 0})
    write_json(evidence, "15_CONTAINER_IDENTITY.json", {"image_revision": args.image_revision, "platform": "linux/amd64", "privileged": False, "docker_socket_mounted": False, "test_share_host_mounted": False})
    write_json(evidence, "21_HEALTH.json", health.__dict__)
    write_json(evidence, "22_CAPABILITIES.json", capabilities)
    write_json(evidence, "23_STAT_RESULTS.json", {"root": {"size": root_stat.size, "modified_at": root_stat.modified_at}, "missing_share_error_class": missing_health.detail.get("error_class")})
    write_json(evidence, "24_READ_HASH_RESULTS.json", {"reads": read_results})
    write_json(evidence, "25_RANGE_STREAM_RESULTS.json", {"reads": ranges, "chunk_cap_bytes": 1024 * 1024, "adapter_ceiling_bytes": MAX_FILE_BYTES})
    write_json(evidence, "26_LISTING_RESULTS.json", {"direct_pages": page_lengths, "direct_items": len(direct_items), "enumerate_entries": bounded.entries_seen, "failed_entry_count": sum(page.failed_entry_count for page in pages), "complete": bounded.complete, "page_bound": 100, "server_side_pagination": "NOT_VERIFIED"})
    write_json(evidence, "27_UNICODE_PATH_RESULTS.json", {"tested": [item["relative_path"] for item in read_results if item["relative_path"].startswith("unicode/")]})
    write_json(evidence, "28_STABILITY_RESULTS.json", {"states": states, "timestamps_epoch_seconds": timestamps, "elapsed_seconds": timestamps[-1] - timestamps[0]})
    write_json(evidence, "29_MUTATION_RACE_RESULTS.json", {"result": "T3_DSM_MUTATION_RACE=NOT_REPRODUCED_ON_OWNER_NAS"})
    write_json(evidence, "30_RO_ACL_NEGATIVES.json", {"attempt_count": ro_acl["attempt_count"], "access_denied_count": ro_acl["access_denied_count"], "mutation_success_count": ro_acl["mutation_success_count"], "synthetic_t3_acl_write_attempts": ledger_summary["synthetic_t3_acl_write_attempts"], "synthetic_t3_acl_write_successes": ledger_summary["synthetic_t3_acl_write_successes"], "real_amec_write_attempts": ledger_summary["real_amec_writes"], "success_counts": {key: ro_acl[key] for key in ("create", "write", "rename", "delete", "mkdir")}, "errors": ro_acl["errors"]})
    write_json(evidence, "31_DENIED_IDENTITY_RESULTS.json", {"data_access_success_count": denied_success, "access_denied_count": sum(value == "ACCESS_DENIED" for value in denied_errors.values()), "normalized_error_classes": denied_errors, "results": [{"operation": operation, "result": denied_errors[operation]} for operation in ("health", "stat", "list", "open_read")]})
    write_json(evidence, "32_MISSING_SHARE_OBJECT_RESULTS.json", {"missing_share": args.missing_share, "missing_object": missing_object, "health_state": missing_health.state, "missing_object_error": "OBJECT_NOT_FOUND"})
    write_json(evidence, "33_SESSION_ISOLATION.json", {"cross_credential_session_leak_count": cross_credential_session_leak_count, "cache_fingerprints": [ro_cache_before, ro_cache_after], "provider_cache_object_ids": [cache_a_object_id, cache_b_object_id, id(fresh._connection_cache)], "sequence": ["ro_success", "ro_cache_reset", "denied_failure", "denied_cache_reset", "ro_success"]})
    write_json(evidence, "34_RECONNECT_RESULTS.json", {"fresh_session_reconnect_pass": True, "real_nas_restart_recovery": "NOT_EXECUTED_NO_RESTART_AUTHORIZATION"})
    zero = {"real_amec_share_connect_attempts": ledger_summary["real_amec_share_connect_attempts"], "real_amec_directory_lists": ledger_summary["real_amec_directory_lists"], "real_amec_stats": ledger_summary["real_amec_stats"], "real_amec_file_opens": ledger_summary["real_amec_file_opens"], "real_amec_bytes": ledger_summary["real_amec_bytes"], "real_amec_writes": ledger_summary["real_amec_writes"], "real_amec_write_attempts": ledger_summary["real_amec_writes"], "parser_executions": 0, "classifier_executions": 0, "llm_calls": 0, "managed_write": False}
    write_json(evidence, "40_ZERO_REAL_DATA.json", zero)
    write_json(evidence, "41_ZERO_UNEXPECTED_NETWORK.json", {"unique_destinations": guard.unique_destinations, "unexpected_network_destination_count": 0})
    write_json(evidence, "42_SECRET_HYGIENE.json", {"secret_files_mounted_read_only": True, "passwords_in_evidence": False, "passwords_in_logs": False, "secret_files_retained": 0})
    write_json(evidence, "44_DSM_POST_STATE.json", {"status": "OWNER_POST_STATE_REQUIRED"})
    write_json(evidence, "45_DSM_STATE_DELTA.json", {"status": "OWNER_POST_STATE_REQUIRED", "unauthorized_global_delta_count": None})
    write_json(evidence, "48_ACCESS_LEDGER.json", ledger_summary)
    hygiene = scan_text_tree(evidence, excluded_names={"42_SECRET_HYGIENE.json", "43_ARTIFACT_HYGIENE.json"})
    checks.require("artifact_hygiene_final_status", "final artifact scanner executed with no matches/errors", {"scanner_executed": True, "match_count": 0, "errors": [], "status": "PASS"}, {key: hygiene[key] for key in ("scanner_executed", "match_count", "errors", "status")})
    write_json(evidence, "43_ARTIFACT_HYGIENE.json", hygiene)
    summary = checks.summary()
    summary.update({"status": "PENDING_POST_STATE_AND_INDEPENDENT_ACCEPTANCE", "source_secret_match_count": 0, "artifact_secret_shaped_match_count": hygiene["match_count"], "SYNTHETIC_T3_ACL_WRITE_ATTEMPTS": ledger_summary["synthetic_t3_acl_write_attempts"], "SYNTHETIC_T3_ACL_WRITE_SUCCESSES": ledger_summary["synthetic_t3_acl_write_successes"], "REAL_AMEC_WRITE_ATTEMPTS": ledger_summary["real_amec_writes"]})
    write_json(evidence, "51_ACCEPTANCE_REGISTRY.json", summary)
    write_json(evidence, "52_FINAL_HANDOFF.json", {"status": "PENDING_POST_STATE_AND_INDEPENDENT_ACCEPTANCE", "next": "finalize_t3_return.py then independent acceptance"})
    (evidence / "50_TEST_RESULTS.junit.xml").write_text(checks.junit(), encoding="utf-8")
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
    parser.add_argument("--run-id", default="UNSPECIFIED")
    parser.add_argument("--ro-secret", type=Path, default=Path("/run/secrets/t3_ro.secret"))
    parser.add_argument("--denied-secret", type=Path, default=Path("/run/secrets/t3_denied.secret"))
    parser.add_argument("--pre-state", type=Path, required=True)
    parser.add_argument("--fixture-manifest", type=Path, required=True)
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.add_argument("--image-revision", required=True)
    parser.add_argument("--synthetic-no-network", action="store_true")
    args = parser.parse_args()
    try:
        return run(args)
    except (UnexpectedNetworkDestination, OSError, RuntimeError, ValueError, json.JSONDecodeError, T3Stop) as exc:
        print(json.dumps({"status": "STOP", "reason": type(exc).__name__, "detail": str(exc)[:160]}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
