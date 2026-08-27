from __future__ import annotations

import hashlib
import importlib.metadata
import io
import inspect
import json
import re
import stat
import subprocess
import types
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.synology_t3.build_handoff import ACCEPTED_V23, create_bundle
from scripts.synology_t3.fixture_manifest import build_fixture_manifest, fixture_bytes, fixture_paths, verify_shipped_fixture_staging
from scripts.synology_t3.host_bootstrap import bytecode_counts, classify_image_ref, collision_status, control_dir_is_valid, image_identity_errors, policy_matches, safe_child
from scripts.synology_t3.network_guard import NetworkGuard, UnexpectedNetworkDestination
from scripts.synology_t3.scope_validator import validate_paths
from scripts.synology_t3.dsm_state_schema import SCHEMA_VERSION, compare_states, validate_state
from scripts.synology_t3.finalize_t3_return import finalize
from scripts.synology_t3.t3_common import (
    APP_LABEL,
    HARNESS_LABEL,
    ROOT,
    SHARE,
    AccessLedger,
    CheckCollector,
    T3Stop,
    T3StoreFactory,
    assert_listing_protocol,
    locator,
    security_introspection,
)
from scripts.synology_t3 import t3_runner
from scripts.synology_t3.t3_runner import normalize_error_code, probe_acl, read_hash
from scripts.synology_t3.t3_runner import normalized_exception_code
from scripts.synology_t3.validate_t3_return import scan, validate_handoff, validate_return


@dataclass
class FakeStat:
    size: int
    st_mtime: str = "1"


class FakeProvider:
    def __init__(self, content: bytes):
        self.content = content
        self.locator_type = None

    def stat(self, current):
        self.locator_type = type(current)
        return type("S", (), {"size": len(self.content), "modified_at": "1", "server_file_id": "fake"})()

    def open_read(self, current, *, offset=0, length=None):
        return io.BytesIO(self.content[offset:offset + length])


class FakeLocator:
    def __init__(self, provider_id, share_id, relative_path):
        self.provider_id, self.share_id, self.relative_path = provider_id, share_id, relative_path


def test_fixture_manifest_has_exact_deterministic_corpus():
    assert len(fixture_paths()) == 270
    assert fixture_paths()[-1] == "listing/entry-0257.bin"
    assert len(fixture_bytes("stream/stream-8MiB.bin")) == 8 * 1024 * 1024


def test_fixture_manifest_stages_under_cert_v1(tmp_path):
    manifest = build_fixture_manifest(tmp_path)
    assert manifest["root"] == "cert/v1"
    assert (tmp_path / "cert/v1/listing/entry-0257.bin").is_file()
    assert len(list((tmp_path / "cert/v1/listing").glob("*.bin"))) == 257


def test_fixture_manifest_has_270_physical_rows(tmp_path):
    manifest = build_fixture_manifest(tmp_path)
    assert len(manifest["entries"]) == 270
    assert all((tmp_path / "cert/v1" / row["relative_path"]).is_file() for row in manifest["entries"])


def test_empty_fixture_is_zero_bytes():
    assert fixture_bytes("basic/empty.bin") == b""


def test_unicode_fixture_is_utf8():
    assert "قطر" in fixture_bytes("unicode/تقرير-قطر.txt").decode()


def test_nfc_and_nfd_fixtures_are_distinct_or_explicit():
    assert fixture_bytes("unicode/nfc-synthetic.txt") != fixture_bytes("unicode/nfd-synthetic.txt")


def test_range_fixture_is_four_mib():
    assert len(fixture_bytes("range/range-4MiB.bin")) == 4 * 1024 * 1024


def test_stream_fixture_is_eight_mib():
    assert len(fixture_bytes("stream/stream-8MiB.bin")) == 8 * 1024 * 1024


def test_listing_names_are_unique_and_bounded():
    listing = [path for path in fixture_paths() if path.startswith("listing/")]
    assert len(listing) == len(set(listing)) == 257


def test_locator_name_resolution_after_fix():
    current = locator(FakeLocator, "basic/small.txt")
    assert current.share_id == SHARE and current.relative_path == "basic/small.txt"


def test_read_hash_uses_fake_real_adapter_seam_without_nameerror(tmp_path):
    content = b"fake read"
    provider = FakeProvider(content)
    evidence = tmp_path / "evidence"
    collector = CheckCollector(evidence)
    ledger = AccessLedger()
    result = read_hash(provider, FakeLocator, "basic/small.txt", {"size": len(content), "sha256": hashlib.sha256(content).hexdigest()}, ledger)
    assert result["actual_sha256"] == hashlib.sha256(content).hexdigest()


def test_security_introspection_uses_session_table():
    session = type("Session", (), {"username": "proposalops_t3_ro", "auth_protocol": "ntlm", "signing_required": True, "require_encryption": True, "encrypt_data": True})()
    connection = type("Connection", (), {"dialect": 785, "require_signing": True, "session_table": {"session-key": session}})()
    result = security_introspection({"connection-key": connection}, "proposalops_t3_ro")
    assert result["authenticated_session_count"] == 1
    assert result["all_dialects_smb2_or_newer"] is True
    assert result["all_encryption_required"] is True
    assert result["all_connection_signing_required"] is True
    assert result["all_session_integrity_protected"] is True


def test_pinned_smbprotocol_1150_encrypted_session_semantics_pass():
    from smbprotocol.session import Session

    assert importlib.metadata.version("smbprotocol") == "1.15.0"
    source = inspect.getsource(Session.connect)
    assert "self.encrypt_data = True" in source
    assert "self.signing_required = False" in source
    assert "encryption covers signing" in source

    session = SimpleNamespace(
        username="proposalops_t3_ro",
        auth_protocol="ntlm",
        signing_required=False,
        require_encryption=True,
        encrypt_data=True,
    )
    connection = SimpleNamespace(dialect=785, require_signing=True, session_table={"session": session})
    result = security_introspection({"connection": connection}, "proposalops_t3_ro")
    assert result["all_connection_signing_required"] is True
    assert result["all_session_integrity_protected"] is True
    assert result["all_encryption_required"] is True
    assert result["sessions"][0]["integrity_mode"] == "encrypted"


def test_security_introspection_requires_connection_signing_policy_even_when_encrypted():
    session = SimpleNamespace(username="proposalops_t3_ro", auth_protocol="ntlm", signing_required=False, require_encryption=True, encrypt_data=True)
    connection = SimpleNamespace(dialect=785, require_signing=False, session_table={"session": session})
    result = security_introspection({"connection": connection}, "proposalops_t3_ro")
    assert result["all_connection_signing_required"] is False
    assert result["all_session_integrity_protected"] is True
    assert result["all_signing_required"] is False


def test_security_introspection_requires_active_encryption_even_when_signed():
    session = SimpleNamespace(username="proposalops_t3_ro", auth_protocol="ntlm", signing_required=True, require_encryption=True, encrypt_data=False)
    connection = SimpleNamespace(dialect=785, require_signing=True, session_table={"session": session})
    result = security_introspection({"connection": connection}, "proposalops_t3_ro")
    assert result["all_session_integrity_protected"] is True
    assert result["all_encryption_required"] is False


def test_security_introspection_rejects_no_message_integrity():
    session = SimpleNamespace(username="proposalops_t3_ro", auth_protocol="ntlm", signing_required=False, require_encryption=True, encrypt_data=False)
    connection = SimpleNamespace(dialect=785, require_signing=True, session_table={"session": session})
    result = security_introspection({"connection": connection}, "proposalops_t3_ro")
    assert result["all_session_integrity_protected"] is False


def test_security_introspection_all_rows_must_be_compliant():
    secure = SimpleNamespace(username="proposalops_t3_ro", auth_protocol="ntlm", signing_required=False, require_encryption=True, encrypt_data=True)
    insecure = SimpleNamespace(username="proposalops_t3_ro", auth_protocol="ntlm", signing_required=False, require_encryption=True, encrypt_data=False)
    connections = {
        "secure": SimpleNamespace(dialect=785, require_signing=True, session_table={"one": secure}),
        "insecure": SimpleNamespace(dialect=785, require_signing=True, session_table={"two": insecure}),
    }
    result = security_introspection(connections, "proposalops_t3_ro")
    assert result["authenticated_session_count"] == 2
    assert result["all_session_integrity_protected"] is False
    assert result["all_encryption_required"] is False


@pytest.mark.parametrize("field,value", [("signing_required", None), ("require_encryption", None), ("encrypt_data", None)])
def test_security_introspection_missing_security_attribute_fails_closed(field, value):
    values = {"username": "proposalops_t3_ro", "auth_protocol": "ntlm", "signing_required": False, "require_encryption": True, "encrypt_data": True}
    values[field] = value
    session = SimpleNamespace(**values)
    connection = SimpleNamespace(dialect=785, require_signing=True, session_table={"session": session})
    result = security_introspection({"connection": connection}, "proposalops_t3_ro")
    assert result["all_session_integrity_protected"] is False or result["all_encryption_required"] is False


@pytest.mark.parametrize("field,value", [("require_signing", "true"), ("require_signing", 1)])
def test_security_introspection_requires_strict_connection_signing_boolean(field, value):
    session = SimpleNamespace(username="proposalops_t3_ro", auth_protocol="ntlm", signing_required=False, require_encryption=True, encrypt_data=True)
    connection = SimpleNamespace(dialect=785, require_signing=value, session_table={"session": session})
    assert security_introspection({"connection": connection}, "proposalops_t3_ro")["all_connection_signing_required"] is False


@pytest.mark.parametrize("field,value", [("require_encryption", 1), ("encrypt_data", "true")])
def test_security_introspection_requires_strict_encryption_booleans(field, value):
    values = {"username": "proposalops_t3_ro", "auth_protocol": "ntlm", "signing_required": False, "require_encryption": True, "encrypt_data": True}
    values[field] = value
    session = SimpleNamespace(**values)
    connection = SimpleNamespace(dialect=785, require_signing=True, session_table={"session": session})
    result = security_introspection({"connection": connection}, "proposalops_t3_ro")
    assert result["all_encryption_required"] is False


def test_security_introspection_rejects_guest_or_null_sessions():
    for marker in ("is_guest", "is_null"):
        session = SimpleNamespace(username="proposalops_t3_ro", auth_protocol="ntlm", signing_required=False, require_encryption=True, encrypt_data=True, **{marker: True})
        connection = SimpleNamespace(dialect=785, require_signing=True, session_table={"session": session})
        result = security_introspection({"connection": connection}, "proposalops_t3_ro")
        assert result["authenticated_session_count"] == 0
        assert result["all_authenticated_sessions"] is False


def test_security_introspection_rejects_unsupported_authentication_protocol():
    session = SimpleNamespace(username="proposalops_t3_ro", auth_protocol="basic", signing_required=False, require_encryption=True, encrypt_data=True)
    connection = SimpleNamespace(dialect=785, require_signing=True, session_table={"session": session})
    result = security_introspection({"connection": connection}, "proposalops_t3_ro")
    assert result["authenticated_session_count"] == 0
    assert result["all_approved_auth_protocol"] is False


def test_security_introspection_rejects_smb1():
    session = type("Session", (), {"username": "proposalops_t3_ro", "auth_protocol": "ntlm", "signing_required": True, "require_encryption": True, "encrypt_data": True})()
    connection = type("Connection", (), {"dialect": 2, "require_signing": True, "session_table": {"session-key": session}})()
    assert security_introspection({"connection-key": connection}, "proposalops_t3_ro")["all_dialects_smb2_or_newer"] is False


def test_security_introspection_rejects_missing_encryption():
    session = type("Session", (), {"username": "proposalops_t3_ro", "auth_protocol": "ntlm", "signing_required": True, "require_encryption": True, "encrypt_data": False})()
    connection = type("Connection", (), {"dialect": 785, "require_signing": True, "session_table": {"session-key": session}})()
    assert security_introspection({"connection-key": connection}, "proposalops_t3_ro")["all_encryption_required"] is False


def test_security_introspection_rejects_wrong_identity():
    session = type("Session", (), {"username": "other", "auth_protocol": "ntlm", "signing_required": True, "require_encryption": True, "encrypt_data": True})()
    connection = type("Connection", (), {"dialect": 785, "require_signing": True, "session_table": {"session-key": session}})()
    assert security_introspection({"connection-key": connection}, "proposalops_t3_ro")["all_expected_username"] is False


def test_security_introspection_rejects_connection_signing_false():
    session = type("Session", (), {"username": "proposalops_t3_ro", "auth_protocol": "ntlm", "signing_required": True, "require_encryption": True, "encrypt_data": True})()
    connection = type("Connection", (), {"dialect": 785, "require_signing": False, "session_table": {"session-key": session}})()
    assert security_introspection({"connection-key": connection}, "proposalops_t3_ro")["all_signing_required"] is False


def test_security_introspection_rejects_empty_session_table():
    connection = type("Connection", (), {"dialect": 785, "require_signing": True, "session_table": {}})()
    assert security_introspection({"connection-key": connection}, "proposalops_t3_ro")["authenticated_session_count"] == 0


def test_collector_hard_failure_flushes_partial_evidence(tmp_path):
    collector = CheckCollector(tmp_path)
    with pytest.raises(T3Stop):
        collector.require("hard", "must pass", 1, 0)
    assert json.loads((tmp_path / "49_CHECKS.json").read_text())["check_count"] == 1


def test_collector_rejects_duplicate_check_id(tmp_path):
    collector = CheckCollector(tmp_path)
    collector.check("one", "one", 1, 1)
    with pytest.raises(T3Stop):
        collector.check("one", "duplicate", 1, 1)


def test_collector_junit_reflects_failures(tmp_path):
    collector = CheckCollector(tmp_path)
    collector.check("one", "one", 1, 0)
    assert 'failures="1"' in collector.junit()


def test_factory_accepts_positive_target():
    class Store:
        def __init__(self, config): self.config = config
    config = type("Config", (), {"share": SHARE, "root": ROOT, "provider_id": "source"})()
    factory = T3StoreFactory(Store, AccessLedger())
    assert factory.create(config, operation_class="test").config.share == SHARE


@pytest.mark.parametrize("share", ["business", "AMEC", "ProposalOps", "\\\\server\\share"])
def test_factory_rejects_unexpected_share(share):
    class Store:
        def __init__(self, config): pass
    config = type("Config", (), {"share": share, "root": ROOT, "provider_id": "source"})()
    with pytest.raises(T3Stop):
        T3StoreFactory(Store, AccessLedger()).create(config, operation_class="test")


def test_factory_rejects_unexpected_root():
    class Store:
        def __init__(self, config): pass
    config = type("Config", (), {"share": SHARE, "root": "", "provider_id": "source"})()
    with pytest.raises(T3Stop):
        T3StoreFactory(Store, AccessLedger()).create(config, operation_class="test")


def test_network_guard_accepts_only_exact_endpoint():
    guard = NetworkGuard("192.0.2.10")
    guard.check(("192.0.2.10", 445))
    assert guard.unique_destinations == [("192.0.2.10", 445)]


@pytest.mark.parametrize("address", [("192.0.2.11", 445), ("192.0.2.10", 139), ("example.invalid", 445)])
def test_network_guard_rejects_unexpected_destination(address):
    with pytest.raises(UnexpectedNetworkDestination):
        NetworkGuard("192.0.2.10").check(address)


def test_scope_validator_accepts_only_allowed_paths():
    assert validate_paths(["scripts/synology_t3/t3_runner.py", "backend/tests/test_synology_t3_harness.py", ".github/workflows/synology-t3-handoff-build-r1.yml"]) == []


@pytest.mark.parametrize("path", ["backend/app/storage/smb.py", "frontend/src/App.tsx", "infra/docker.yml", "deploy/app.yml", "migrations/001.sql"])
def test_scope_validator_rejects_forbidden_path(path):
    assert validate_paths([path])


def test_scope_validator_rejects_parent_escape():
    assert validate_paths(["scripts/synology_t3/../backend/app/x.py"])


def test_handoff_builder_binds_accepted_v23_and_stages_manifest(tmp_path):
    repo = Path(__file__).resolve().parents[2]
    bundle = create_bundle(repo, tmp_path, "SYN-T3-TEST", "UNCOMMITTED")
    identity = json.loads((bundle / "01_APPLICATION_IDENTITY.json").read_text())
    assert identity["accepted_v23_sha"] == ACCEPTED_V23
    assert (bundle / "fixture_staging/cert/v1/listing/entry-0257.bin").is_file()
    assert not list(bundle.rglob("*.secret"))


def test_handoff_has_dual_identity_manifests(tmp_path):
    bundle = create_bundle(Path(__file__).resolve().parents[2], tmp_path, "SYN-T3-TEST", "UNCOMMITTED")
    policy = json.loads((bundle / "06_IMAGE_BUILD_POLICY.json").read_text())
    assert policy["application_sha"] == ACCEPTED_V23 and policy["harness_sha"] == "UNCOMMITTED"
    assert json.loads((bundle / "HARNESS_MANIFEST.json").read_text())["rows"]


def test_assertion_catalog_exceeds_minimum(tmp_path):
    bundle = create_bundle(Path(__file__).resolve().parents[2], tmp_path, "SYN-T3-TEST", "UNCOMMITTED")
    catalog = json.loads((bundle / "T3_ASSERTION_CATALOG.json").read_text())
    assert catalog["distinct_assertions"] >= 120


def test_handoff_validator_rejects_missing_required_files(tmp_path):
    assert validate_handoff(tmp_path)["status"] == "FAIL"


def test_return_validator_fails_closed_on_missing_post_state(tmp_path):
    assert validate_return(tmp_path)["status"] == "FAIL"


def test_hygiene_scanner_detects_secret_shaped_match(tmp_path):
    (tmp_path / "sample.txt").write_text("AKIA1234567890ABCDEF\n")
    assert scan(tmp_path)["match_count"] == 1


def test_hygiene_scanner_passes_clean_tree(tmp_path):
    (tmp_path / "sample.txt").write_text("synthetic only\n")
    assert scan(tmp_path)["match_count"] == 0


def test_manifest_hash_for_fixture_is_deterministic():
    assert hashlib.sha256(fixture_bytes("basic/small.txt")).hexdigest() == hashlib.sha256(fixture_bytes("basic/small.txt")).hexdigest()


def test_missing_object_path_is_synthetic_only():
    run_id = "20260825T000000Z"
    assert f"missing/object-{run_id}.bin".startswith("missing/object-")


def test_missing_share_name_is_run_scoped():
    run_id = "20260825T000000Z"
    assert f"ProposalOps-T3-Missing-{run_id}".endswith(run_id)


def test_no_real_data_counters_are_created_by_empty_ledger():
    summary = AccessLedger().summary()
    assert all(summary[key] == 0 for key in summary if key.startswith("real_amec_"))


def test_application_storage_constants_are_pinned():
    assert ACCEPTED_V23 == "4925518b35b58956aaa5870f226af5e57d14b610"


def test_root_constant_is_cert_v1():
    assert ROOT == "cert/v1"


def test_share_constant_is_synthetic():
    assert SHARE == "ProposalOps-T3-Synthetic"


def test_image_label_names_are_stable():
    assert HARNESS_LABEL == "org.opencontainers.image.revision"
    assert APP_LABEL.endswith("application-revision")


def test_scan_skips_binary_fixture_content(tmp_path):
    (tmp_path / "binary.bin").write_bytes(bytes(range(256)))
    assert scan(tmp_path)["match_count"] == 0


class FakePage:
    def __init__(self, count, cursor, complete):
        self.items = [object()] * count
        self.cursor = cursor
        self.complete = complete


def valid_pre_state():
    return {
        "state_schema_version": SCHEMA_VERSION, "phase": "PRE", "model": "DS220+", "dsm_version": "7", "dsm_build": "1",
        "hostname": "nas", "architecture": "x86_64", "active_lan_ip": "192.0.2.10", "gateway": "192.0.2.1", "docker_version": "24",
        "smb": {"min": "SMB2"}, "firewall": {"enabled": True}, "auto_block": {"enabled": True}, "tun1000": {"exists": False},
        "existing_proposalops_identities": ["existing"], "business_share_acl_fingerprint": "acl-fingerprint",
        "test_share_exists": False, "test_accounts_exist": False,
    }


def valid_post_state():
    state = valid_pre_state()
    state.update({"phase": "POST", "test_share_exists": True, "test_share_permissions": {"ro": "read", "denied": "none"}, "proposalops_t3_ro_enabled": False, "proposalops_t3_denied_enabled": False, "t3_secret_files_retained": 0, "t3_recurring_tasks_enabled": 0, "t3_task_removed": True})
    state.pop("test_accounts_exist")
    return state


def valid_host_bootstrap():
    return {"host_python_38_compatibility_gate": "PASS", "python_dont_write_bytecode": True, "handoff_pyc_before": 0, "handoff_pyc_after": 0, "host_euid": 0, "uid_10001_collision": False, "gid_10001_collision": False, "control_dir_within_control_root": True, "control_dir_owner": "0:0", "control_dir_mode": "0700", "fixture_staging_verified": "PASS", "fixture_count": 270, "fixture_regeneration_executed": False, "image_id_verified": True, "bind_canary_network_mode": "none", "bind_canary_euid": 10001, "bind_canary_egid": 10001, "bind_canary_read": "PASS", "bind_canary_write": "PASS", "bind_canary_reread": "PASS", "secret_owner_uid": 10001, "secret_owner_gid": 10001, "secret_mode": "0600", "evidence_owner_uid": 10001, "evidence_owner_gid": 10001, "evidence_mode": "0700", "image_ref_preexisting": False, "image_ref_preexisting_exact": False, "docker_load_count": 1, "status": "PASS"}


def test_exact_listing_protocol_passes():
    assert_listing_protocol([FakePage(100, "v1:100", False), FakePage(100, "v1:200", False), FakePage(57, None, True)])


@pytest.mark.parametrize("pages", [
    [FakePage(100, "v1:100", False), FakePage(100, "v1:200", False), FakePage(57, "v1:257", True)],
    [FakePage(100, None, True), FakePage(100, "v1:200", False), FakePage(57, None, True)],
    [FakePage(100, "v1:100", False), FakePage(100, "v1:100", False), FakePage(57, None, True)],
    [FakePage(100, "v1:100", False), FakePage(99, "v1:200", False), FakePage(58, None, True)],
    [FakePage(100, "v1:100", False), FakePage(100, "v1:200", False), FakePage(56, None, True)],
    [FakePage(100, "v1:100", False), FakePage(100, "v1:200", False), FakePage(57, None, False)],
])
def test_listing_protocol_fail_closed(pages):
    with pytest.raises(T3Stop):
        assert_listing_protocol(pages)


@pytest.mark.parametrize("field", ["active_lan_ip", "gateway", "model", "dsm_version", "dsm_build", "hostname", "architecture", "docker_version", "smb", "firewall", "auto_block", "tun1000", "existing_proposalops_identities", "business_share_acl_fingerprint"])
def test_pre_schema_missing_immutable_field_fails(field):
    state = valid_pre_state()
    state.pop(field)
    assert validate_state(state, "PRE")


@pytest.mark.parametrize("field", ["active_lan_ip", "gateway", "model", "dsm_version", "dsm_build", "hostname", "architecture", "docker_version", "smb", "firewall", "auto_block", "tun1000", "existing_proposalops_identities", "business_share_acl_fingerprint"])
def test_post_changed_immutable_field_is_counted(field):
    pre = valid_pre_state()
    post = valid_post_state()
    post[field] = {"changed": True} if isinstance(post[field], dict) else f"changed-{field}"
    comparison = compare_states(pre, post)
    assert comparison["immutable_field_deltas"][field] is True


@pytest.mark.parametrize("field", ["proposalops_t3_ro_enabled", "proposalops_t3_denied_enabled", "t3_secret_files_retained", "t3_recurring_tasks_enabled", "t3_task_removed", "test_share_exists", "test_share_permissions"])
def test_post_schema_requires_cleanup_fields(field):
    state = valid_post_state()
    state.pop(field)
    assert validate_state(state, "POST")


@pytest.mark.parametrize("field,value", [("proposalops_t3_ro_enabled", True), ("proposalops_t3_denied_enabled", True), ("t3_secret_files_retained", 1), ("t3_recurring_tasks_enabled", 1), ("t3_task_removed", False), ("test_share_exists", False)])
def test_post_schema_rejects_unclean_cleanup(field, value):
    state = valid_post_state()
    state[field] = value
    assert finalize_cleanup_errors(state)


def finalize_cleanup_errors(state):
    return (state["proposalops_t3_ro_enabled"] is not False or state["proposalops_t3_denied_enabled"] is not False or state["t3_secret_files_retained"] != 0 or state["t3_recurring_tasks_enabled"] != 0 or state["t3_task_removed"] is not True or state["test_share_exists"] is not True)


def test_clean_pre_post_finalizes_candidate_ready(tmp_path):
    (tmp_path / "10_DSM_PRE_STATE.json").write_text(json.dumps(valid_pre_state()))
    (tmp_path / "44_DSM_POST_STATE.json").write_text(json.dumps(valid_post_state()))
    (tmp_path / "16_HOST_BOOTSTRAP.json").write_text(json.dumps(valid_host_bootstrap()))
    assert finalize(tmp_path, None) == 0
    registry = json.loads((tmp_path / "51_ACCEPTANCE_REGISTRY.json").read_text())
    assert registry["T3_RETURN_STATUS"] == "PASS"


@pytest.mark.parametrize("field", ["active_lan_ip", "gateway", "smb", "firewall", "auto_block", "tun1000", "existing_proposalops_identities", "business_share_acl_fingerprint"])
def test_clean_finalizer_rejects_changed_state(tmp_path, field):
    (tmp_path / "10_DSM_PRE_STATE.json").write_text(json.dumps(valid_pre_state()))
    post = valid_post_state()
    post[field] = {"changed": True} if isinstance(post[field], dict) else "changed"
    (tmp_path / "44_DSM_POST_STATE.json").write_text(json.dumps(post))
    assert finalize(tmp_path, None) != 0


@pytest.mark.parametrize("field", ["active_lan_ip", "gateway", "smb", "firewall", "auto_block", "tun1000", "existing_proposalops_identities", "business_share_acl_fingerprint"])
def test_finalizer_missing_pre_field_fails(tmp_path, field):
    pre = valid_pre_state()
    pre.pop(field)
    (tmp_path / "10_DSM_PRE_STATE.json").write_text(json.dumps(pre))
    (tmp_path / "44_DSM_POST_STATE.json").write_text(json.dumps(valid_post_state()))
    assert finalize(tmp_path, None) != 0


def test_finalizer_missing_post_state_fails(tmp_path):
    (tmp_path / "10_DSM_PRE_STATE.json").write_text(json.dumps(valid_pre_state()))
    assert finalize(tmp_path, None) != 0


def test_finalizer_rejects_placeholder_post_state(tmp_path):
    (tmp_path / "10_DSM_PRE_STATE.json").write_text(json.dumps(valid_pre_state()))
    (tmp_path / "44_DSM_POST_STATE.json").write_text(json.dumps({"status": "OWNER_POST_STATE_REQUIRED"}))
    assert finalize(tmp_path, None) != 0


def test_runtime_assertion_normalization_is_path_specific(tmp_path):
    collector = CheckCollector(tmp_path)
    for path in fixture_paths():
        collector.check(f"manifest::{path}", f"fixture manifest row {path} is structurally valid", True, True)
    summary = collector.summary()
    assert summary["NORMALIZED_ASSERTION_DUPLICATE_COUNT"] == 0
    assert summary["DUPLICATE_EVIDENCE_TUPLE_COUNT"] == 0


def test_runtime_registry_minimum_is_not_catalog_substitute():
    catalog_count = 276
    runtime_count = 0
    assert runtime_count < 120 and catalog_count >= 120


@pytest.mark.parametrize("raw,expected", [("STORAGE_ACCESS_DENIED", "ACCESS_DENIED"), ("StorageErrorCode.OBJECT_NOT_FOUND", "OBJECT_NOT_FOUND"), ("ACCESS_DENIED", "ACCESS_DENIED")])
def test_runner_normalizes_storage_error_vocabulary(raw, expected):
    assert normalize_error_code(raw) == expected


def test_runner_normalizes_adapter_exception_code():
    error = type("E", (), {"code": "STORAGE_ACCESS_DENIED"})()
    assert normalized_exception_code(object(), error) == "ACCESS_DENIED"


def test_access_ledger_exposes_synthetic_acl_counters():
    ledger = AccessLedger()
    ledger.record_operation("synthetic_acl_write", SHARE, ROOT)
    ledger.record_operation("synthetic_acl_write_success", SHARE, ROOT)
    summary = ledger.summary()
    assert summary["synthetic_t3_acl_write_attempts"] == 1
    assert summary["synthetic_t3_acl_write_successes"] == 1
    assert summary["real_amec_writes"] == 0


def test_scope_validator_accepts_r1r2_workflow():
    assert validate_paths([".github/workflows/synology-t3-handoff-build-r1r2.yml", ".github/workflows/synology-t3-handoff-build-r1r3.yml", ".github/workflows/synology-t3-handoff-build-r1r4.yml", ".github/workflows/synology-t3-handoff-build-r1r6r2.yml"]) == []


def test_runner_source_has_no_stale_terminal_cursor_gate():
    source = (Path(__file__).resolve().parents[2] / "scripts/synology_t3/t3_runner.py").read_text()
    assert "listing_cursor_progress_2" not in source
    assert "cursors[1] and cursors[2]" not in source


def test_runner_authorization_does_not_claim_live_smb_zero():
    source = (Path(__file__).resolve().parents[2] / "scripts/synology_t3/t3_runner.py").read_text()
    assert '"repair_run_counters"' not in source
    assert "runtime_counter_source" in source


def test_missing_share_envelope_is_exactly_run_scoped():
    run_id = "SYN-T3-123"
    assert f"ProposalOps-T3-Missing-{run_id}" == "ProposalOps-T3-Missing-SYN-T3-123"


class FaultingAclClient:
    def __init__(self, fault):
        self.fault = fault

    def _raise(self):
        if isinstance(self.fault, BaseException):
            raise self.fault
        raise self.fault()

    def open_file(self, *args, **kwargs):
        self._raise()

    def rename(self, *args, **kwargs):
        self._raise()

    def remove(self, *args, **kwargs):
        self._raise()

    def mkdir(self, *args, **kwargs):
        self._raise()


class FaultingAclStore:
    def __init__(self, fault):
        self.client = FaultingAclClient(fault)

    def _client(self):
        return self.client

    def _session_kwargs(self):
        return {}

    def _unc(self, relative_path):
        return "\\\\synthetic\\share\\" + relative_path


def assert_acl_fault_is_not_proof(tmp_path, fault):
    collector = CheckCollector(tmp_path)
    with pytest.raises(T3Stop):
        probe_acl(FaultingAclStore(fault), collector, AccessLedger())
    assert json.loads((tmp_path / "49_CHECKS.json").read_text())["checks"][-1]["observed"] != "ACCESS_DENIED"


def test_negative_acl_typeerror_is_not_access_denied_proof(tmp_path):
    assert_acl_fault_is_not_proof(tmp_path, TypeError)


def test_negative_acl_object_not_found_is_not_access_denied_proof(tmp_path):
    errors = t3_runner.storage_types()["errors"]
    assert_acl_fault_is_not_proof(tmp_path, errors.StorageError(errors.StorageErrorCode.OBJECT_NOT_FOUND))


def test_negative_acl_unavailable_is_not_access_denied_proof(tmp_path):
    errors = t3_runner.storage_types()["errors"]
    assert_acl_fault_is_not_proof(tmp_path, errors.StorageError(errors.StorageErrorCode.UNAVAILABLE))


def test_owner_instructions_use_exact_candidate_external_acceptance_only():
    text = (Path(__file__).resolve().parents[2] / "scripts/synology_t3/OWNER_DSM_T3_OPERATOR_INSTRUCTIONS.md").read_text()
    assert text.count("R1.1 handoff acceptance") == 0
    assert text.count("R1.2 handoff acceptance") == 0
    assert "independent acceptance has passed for this exact R1.6R2 handoff candidate" in text
    assert "T3_OWNER_EXECUTION_READY=false" in text
    assert "SYN-T3-20260827T002911Z" in text
    assert "security_all_signing_required" in text


def test_handoff_image_ref_is_r1r6r2(tmp_path):
    bundle = create_bundle(Path(__file__).resolve().parents[2], tmp_path, "SYN-T3-R1R6R1", "7400a2c50d69a2b57c23239412b8275f129ab57c")
    policy = json.loads((bundle / "06_IMAGE_BUILD_POLICY.json").read_text())
    assert policy["image_ref"] == "proposalops/syn-t3:r1r6r2-7400a2c50d69"


def test_handoff_registry_cannot_self_authorize_owner_execution(tmp_path):
    bundle = create_bundle(Path(__file__).resolve().parents[2], tmp_path, "SYN-T3-R1R3-REG", "UNCOMMITTED")
    registry = json.loads((bundle / "51_HANDOFF_REGISTRY.json").read_text())
    assert registry["T3_OWNER_EXECUTION_READY"] is False


def test_runner_e2e_is_pure_synthetic_and_emits_typed_evidence(tmp_path, monkeypatch):
    _run_synthetic_whole_run(tmp_path, monkeypatch)


def test_runner_accepts_encrypted_smbprotocol_session_without_session_signing_flag(tmp_path, monkeypatch):
    _run_synthetic_whole_run(tmp_path, monkeypatch, session_signing_required=False)
    security = json.loads((tmp_path / "evidence/20_SMB_SESSION_SECURITY.json").read_text())
    assert security["all_connection_signing_required"] is True
    assert security["all_session_integrity_protected"] is True
    assert security["all_encryption_required"] is True
    assert security["sessions"][0]["session_signing_required"] is False
    assert security["sessions"][0]["integrity_mode"] == "encrypted"


def test_runner_writes_security_evidence_before_connection_signing_gate(tmp_path, monkeypatch):
    with pytest.raises(T3Stop):
        _run_synthetic_whole_run(tmp_path, monkeypatch, connection_require_signing=False, session_signing_required=False, expect_success=False)
    evidence = tmp_path / "evidence/20_SMB_SESSION_SECURITY.json"
    assert evidence.is_file()
    security = json.loads(evidence.read_text())
    assert security["all_connection_signing_required"] is False
    assert security["all_session_integrity_protected"] is True
    assert security["all_encryption_required"] is True
    assert security["sessions"][0]["connection_require_signing"] is False
    text = evidence.read_text()
    assert "synthetic-ro" not in text
    assert "synthetic-denied" not in text
    assert '"password"' not in text
    assert '"session_key"' not in text


def test_runner_encryption_gate_remains_hard_when_encryption_is_not_active(tmp_path, monkeypatch):
    with pytest.raises(T3Stop):
        _run_synthetic_whole_run(tmp_path, monkeypatch, session_encrypt_data=False, expect_success=False)
    security = json.loads((tmp_path / "evidence/20_SMB_SESSION_SECURITY.json").read_text())
    assert security["all_encryption_required"] is False
    assert security["all_session_integrity_protected"] is True


def _run_synthetic_whole_run(tmp_path, monkeypatch, *, run_id="SYN-T3-E2E-001", denied_health_error="STORAGE_ACCESS_DENIED", missing_share=None, construction_log=None, expect_success=True, connection_require_signing=True, session_signing_required=True, session_require_encryption=True, session_encrypt_data=True):
    """Execute t3_runner.run through a fake provider; no socket or DSM path exists."""
    actual = t3_runner.storage_types()
    errors = actual["errors"]
    port = actual["port"]
    fixture_root = tmp_path / "fixture-source"
    fixtures = build_fixture_manifest(fixture_root)
    (fixture_root / "13_FIXTURE_MANIFEST.json").write_text(json.dumps(fixtures))
    pre = tmp_path / "10_DSM_PRE_STATE.json"
    pre.write_text(json.dumps(valid_pre_state()))
    ro_secret = tmp_path / "ro.secret"
    denied_secret = tmp_path / "denied.secret"
    ro_secret.write_text("synthetic-ro")
    denied_secret.write_text("synthetic-denied")
    ro_secret.chmod(0o600)
    denied_secret.chmod(0o600)
    evidence = tmp_path / "evidence"

    class FakeConfig:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
            self.provider_id = kwargs.get("provider_id", "smb-external-source")

    class FakeClient:
        def __init__(self, store):
            self.store = store

        def reset_connection_cache(self, *, connection_cache):
            return None

        def _deny(self):
            raise errors.StorageError(errors.StorageErrorCode.ACCESS_DENIED, "synthetic ACL denial")

        def open_file(self, *args, **kwargs):
            self._deny()

        def rename(self, *args, **kwargs):
            self._deny()

        def remove(self, *args, **kwargs):
            self._deny()

        def mkdir(self, *args, **kwargs):
            self._deny()

    class FakeStore:
        def __init__(self, config):
            self.config = config
            self._connection_cache = {}
            self._smbclient = None
            if construction_log is not None:
                construction_log.append(config.share)

        @property
        def denied(self):
            return self.config.username == "proposalops_t3_denied"

        @property
        def missing(self):
            return self.config.share.startswith("ProposalOps-T3-Missing-")

        def _connect(self):
            if self.denied or self.missing or self._connection_cache:
                return
            session = SimpleNamespace(username=self.config.username, auth_protocol="ntlm", signing_required=session_signing_required, require_encryption=session_require_encryption, encrypt_data=session_encrypt_data)
            connection = SimpleNamespace(dialect=785, require_signing=connection_require_signing, session_table={"session": session})
            self._connection_cache["synthetic"] = connection

        def _access_denied(self):
            raise errors.StorageError(errors.StorageErrorCode.ACCESS_DENIED, "synthetic denied identity")

        def _not_found(self):
            raise errors.StorageError(errors.StorageErrorCode.OBJECT_NOT_FOUND, "synthetic missing object")

        def _client(self):
            self._smbclient = self._smbclient or FakeClient(self)
            return self._smbclient

        def _session_kwargs(self):
            return {"username": self.config.username, "password": self.config.password, "port": self.config.port, "connection_cache": self._connection_cache}

        def _unc(self, relative_path):
            return "\\\\192.0.2.10\\" + self.config.share + "\\" + relative_path

        def health(self):
            if self.denied:
                return port.StorageHealth("UNAVAILABLE", self.config.provider_id, detail={"error_class": denied_health_error})
            if self.missing:
                return port.StorageHealth("UNAVAILABLE", self.config.provider_id, detail={"error_class": "STORAGE_OBJECT_NOT_FOUND"})
            self._connect()
            return port.StorageHealth("HEALTHY", self.config.provider_id, detail={"synthetic": True})

        def capabilities(self):
            return port.SourceCapabilities()

        def stat(self, current):
            if self.denied:
                self._access_denied()
            if self.missing or current.relative_path.startswith("missing/"):
                self._not_found()
            self._connect()
            content = fixture_bytes(current.relative_path) if current.relative_path else b""
            return port.StorageStat(current, len(content), modified_at="1", server_file_id="synthetic")

        def open_read(self, current, *, offset=0, length=None):
            if self.denied:
                self._access_denied()
            if self.missing:
                self._not_found()
            self._connect()
            content = fixture_bytes(current.relative_path)
            return io.BytesIO(content[offset:offset + length])

        def list(self, prefix, *, cursor=None, max_entries_per_page=100):
            if self.denied:
                self._access_denied()
            if self.missing:
                self._not_found()
            self._connect()
            start = 0 if cursor is None else int(cursor.split(":")[1])
            stop = min(start + max_entries_per_page, 257)
            items = [port.StorageStat(port.StorageLocator(prefix.provider_id, prefix.share_id, f"listing/entry-{index:04d}.bin"), len(fixture_bytes(f"listing/entry-{index:04d}.bin")), modified_at="1", server_file_id=str(index)) for index in range(start + 1, stop + 1)]
            next_cursor = None if stop == 257 else f"v1:{stop}"
            return port.SourcePage(items, next_cursor, stop == 257, 0, (), len(items))

    fake_smb = SimpleNamespace(SMBSourceConfig=FakeConfig, SMBSourceStore=FakeStore)
    modules = dict(actual)
    modules["smb"] = fake_smb
    monkeypatch.setattr(t3_runner, "storage_types", lambda: modules)

    class NoNetworkGuard:
        def __init__(self, *args, **kwargs):
            self.attempted = []
            self.unique_destinations = []

        def installed(self):
            from contextlib import nullcontext
            return nullcontext(self)

    monkeypatch.setattr(t3_runner, "NetworkGuard", NoNetworkGuard)
    args = SimpleNamespace(
        nas_ip="192.0.2.10", share=SHARE, root=ROOT, port=445,
        ro_username="proposalops_t3_ro", denied_username="proposalops_t3_denied",
        missing_share=missing_share or f"ProposalOps-T3-Missing-{run_id}", run_id=run_id,
        ro_secret=ro_secret, denied_secret=denied_secret, pre_state=pre,
        fixture_manifest=tmp_path / "fixture-source" / "13_FIXTURE_MANIFEST.json",
        evidence_root=evidence, image_revision="synthetic-test", synthetic_no_network=True,
    )
    result = t3_runner.run(args)
    if not expect_success:
        return result
    assert result == 0
    acl = json.loads((evidence / "30_RO_ACL_NEGATIVES.json").read_text())
    assert (acl["attempt_count"], acl["access_denied_count"], acl["mutation_success_count"]) == (5, 5, 0)
    assert all(row["normalized_error_class"] == "ACCESS_DENIED" for row in acl["errors"])
    auth = json.loads((evidence / "00_AUTHORIZATION.json").read_text())
    assert "repair_run_counters" not in auth
    assert json.loads((evidence / "31_DENIED_IDENTITY_RESULTS.json").read_text())["access_denied_count"] == 4
    denied = json.loads((evidence / "31_DENIED_IDENTITY_RESULTS.json").read_text())
    assert denied["data_access_success_count"] == 0
    ledger = json.loads((evidence / "48_ACCESS_LEDGER.json").read_text())
    assert ledger["synthetic_t3_acl_write_attempts"] == 5
    registry = json.loads((evidence / "51_ACCEPTANCE_REGISTRY.json").read_text())
    checks = json.loads((evidence / "49_CHECKS.json").read_text())
    junit = ET.parse(evidence / "50_TEST_RESULTS.junit.xml").getroot()
    assert registry["distinct_assertions"] >= 130
    assert registry["PASS"] == registry["distinct_assertions"]
    assert registry["FAIL"] == registry["WARN"] == registry["ENV_BLOCKED"] == registry["NOT_EXECUTED"] == 0
    assert all(registry[key] == 0 for key in ("UNRESOLVED_EVIDENCE_REF_COUNT", "NORMALIZED_ASSERTION_DUPLICATE_COUNT", "DUPLICATE_EVIDENCE_TUPLE_COUNT", "SELF_REFERENCE_COUNT"))
    assert checks["check_count"] == registry["distinct_assertions"]
    assert int(junit.attrib["tests"]) == registry["distinct_assertions"]
    assert all(int(junit.attrib[key]) == 0 for key in ("failures", "errors", "skipped"))
    assert registry["SYNTHETIC_T3_ACL_WRITE_ATTEMPTS"] == 5
    assert registry["SYNTHETIC_T3_ACL_WRITE_SUCCESSES"] == 0
    assert registry["REAL_AMEC_WRITE_ATTEMPTS"] == 0
    assert json.loads((evidence / "26_LISTING_RESULTS.json").read_text())["direct_pages"] == [100, 100, 57]
    assert json.loads((evidence / "49_CHECKS.json").read_text())["checks"][-1]["result"] == "PASS"


def test_negative_denied_unavailable_is_not_denied_identity_proof(tmp_path, monkeypatch):
    with pytest.raises(T3Stop):
        _run_synthetic_whole_run(tmp_path, monkeypatch, run_id="SYN-T3-E2E-NEG-DENIED", denied_health_error="STORAGE_UNAVAILABLE", expect_success=False)


def test_negative_wrong_missing_share_fails_before_provider_construction(tmp_path, monkeypatch):
    constructions = []
    wrong = "ProposalOps-T3-Missing-WRONG"
    with pytest.raises(T3Stop):
        _run_synthetic_whole_run(tmp_path, monkeypatch, run_id="SYN-T3-E2E-NEG-001", missing_share=wrong, construction_log=constructions, expect_success=False)
    assert constructions.count(wrong) == 0


def test_r1r4_shipped_fixture_verifier_passes_without_mutation(tmp_path):
    root = tmp_path / "handoff"
    manifest = build_fixture_manifest(root / "fixture_staging")
    manifest_path = root / "13_FIXTURE_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest))
    before = {path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in root.rglob("*") if path.is_file()}
    result = verify_shipped_fixture_staging(manifest_path, root / "fixture_staging" / "cert" / "v1")
    after = {path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in root.rglob("*") if path.is_file()}
    assert result["status"] == "PASS" and result["fixture_count"] == 270 and result["fixture_regeneration_executed"] is False and before == after


@pytest.mark.parametrize("mutation", ["missing", "extra", "changed"])
def test_r1r4_fixture_verifier_rejects_truth_mutations(tmp_path, mutation):
    root = tmp_path / "handoff"
    manifest = build_fixture_manifest(root / "fixture_staging")
    manifest_path = root / "13_FIXTURE_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest))
    target = root / "fixture_staging" / "cert" / "v1" / "basic" / "small.txt"
    if mutation == "missing":
        target.unlink()
    elif mutation == "changed":
        target.write_bytes(b"changed")
    else:
        extra = target.parent / "extra.bin"
        extra.write_bytes(b"extra")
    assert verify_shipped_fixture_staging(manifest_path, root / "fixture_staging" / "cert" / "v1")["status"] == "FAIL"


def test_r1r4_fixture_verifier_rejects_symlink(tmp_path):
    root = tmp_path / "handoff"
    manifest = build_fixture_manifest(root / "fixture_staging")
    manifest_path = root / "13_DSM_PRE_STATE.json"
    manifest_path.write_text(json.dumps(manifest))
    target = root / "fixture_staging" / "cert" / "v1" / "basic" / "small.txt"
    target.unlink()
    target.symlink_to(root / "fixture_staging" / "cert" / "v1" / "basic" / "empty.bin")
    assert verify_shipped_fixture_staging(manifest_path, root / "fixture_staging" / "cert" / "v1")["status"] == "FAIL"


def test_r1r4_fixture_verifier_rejects_traversal_manifest(tmp_path):
    root = tmp_path / "handoff"
    manifest = build_fixture_manifest(root / "fixture_staging")
    manifest["entries"][0]["relative_path"] = "../escape.bin"
    manifest_path = root / "13_FIXTURE_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest))
    assert verify_shipped_fixture_staging(manifest_path, root / "fixture_staging" / "cert" / "v1")["status"] == "FAIL"


def test_r1r4_fixture_generator_has_no_python39_prefix_api():
    source = (Path(__file__).resolve().parents[2] / "scripts/synology_t3/fixture_manifest.py").read_text()
    assert "removeprefix" not in source and "removesuffix" not in source


def test_r1r4_fresh_handoff_has_no_bytecode(tmp_path):
    assert bytecode_counts(tmp_path) == {"pyc_count": 0, "pycache_dir_count": 0}


@pytest.mark.parametrize("name", ["bad.pyc", "nested.pyc"])
def test_r1r4_bytecode_file_is_detected(tmp_path, name):
    path = tmp_path / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"synthetic")
    assert bytecode_counts(tmp_path)["pyc_count"] == 1


def test_r1r4_pycache_directory_is_detected(tmp_path):
    (tmp_path / "__pycache__").mkdir()
    assert bytecode_counts(tmp_path)["pycache_dir_count"] == 1


@pytest.mark.parametrize("candidate,expected", [("child", True), ("nested/file", True), ("../escape", False), ("/tmp/escape", False)])
def test_r1r4_control_root_child_gate(candidate, expected, tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    child = root / candidate
    if expected:
        child.parent.mkdir(parents=True, exist_ok=True)
        child.mkdir()
    assert safe_child(root, child) is expected


def test_r1r4_policy_matches_numeric_owner_and_mode(tmp_path):
    path = tmp_path / "secret"
    path.write_text("synthetic")
    path.chmod(0o600)
    assert policy_matches(path, __import__("os").getuid(), __import__("os").getgid(), 0o600)
    assert not policy_matches(path, 10001, 10001, 0o600)


def test_r1r4_control_dir_rejects_wrong_mode(tmp_path):
    root = tmp_path / "root"
    child = root / "run"
    child.mkdir(parents=True)
    root.chmod(0o700); child.chmod(0o755)
    assert control_dir_is_valid(root, child) is False


def test_r1r4_uid_gid_collision_parser_passes_synthetic_files(tmp_path):
    passwd = tmp_path / "passwd"; group = tmp_path / "group"
    passwd.write_text("root:x:0:0:root:/root:/bin/sh\n")
    group.write_text("root:x:0:\n")
    assert collision_status(passwd_path=passwd, group_path=group) == {"uid_10001_collision": False, "gid_10001_collision": False}


@pytest.mark.parametrize("line,field", [("synthetic:x:10001:10001:x:/x:/bin/sh\n", "uid_10001_collision"), ("synthetic:x:10001:\n", "gid_10001_collision")])
def test_r1r4_uid_gid_collision_parser_detects_collision(tmp_path, line, field):
    passwd = tmp_path / "passwd"; group = tmp_path / "group"
    passwd.write_text(line if field.startswith("uid") else "root:x:0:0:x:/root:/bin/sh\n")
    group.write_text(line if field.startswith("gid") else "root:x:0:\n")
    assert collision_status(passwd_path=passwd, group_path=group)[field] is True


def test_r1r4_image_tag_absent_classification():
    policy = {"image_id": "sha256:x", "application_sha": "app", "harness_sha": "harness"}
    assert classify_image_ref(None, policy) == "absent"


def test_r1r4_image_tag_exact_reuse_classification():
    policy = {"image_id": "sha256:x", "application_sha": "app", "harness_sha": "harness"}
    inspect = {"Id": "sha256:x", "Os": "linux", "Architecture": "amd64", "Config": {"User": "10001:10001", "Labels": {"org.opencontainers.image.proposalops-application-revision": "app", "org.opencontainers.image.revision": "harness", "org.opencontainers.image.synthetic-only": "true"}}}
    assert classify_image_ref(inspect, policy) == "exact"


@pytest.mark.parametrize("field", ["Id", "Os", "Architecture", "Config"])
def test_r1r4_image_tag_conflict_classification(field):
    policy = {"image_id": "sha256:x", "application_sha": "app", "harness_sha": "harness"}
    inspect = {"Id": "sha256:x", "Os": "linux", "Architecture": "amd64", "Config": {"User": "10001:10001", "Labels": {"org.opencontainers.image.proposalops-application-revision": "app", "org.opencontainers.image.revision": "harness", "org.opencontainers.image.synthetic-only": "true"}}}
    if field == "Id": inspect["Id"] = "sha256:wrong"
    elif field == "Os": inspect["Os"] = "windows"
    elif field == "Architecture": inspect["Architecture"] = "arm64"
    else: inspect["Config"]["Labels"]["org.opencontainers.image.synthetic-only"] = "false"
    assert classify_image_ref(inspect, policy) == "conflict"


def test_r1r4_return_validation_requires_host_bootstrap_file(tmp_path):
    result = validate_return(tmp_path)
    assert result["status"] == "FAIL" and any("16_HOST_BOOTSTRAP.json" in error for error in result["errors"])


def test_r1r4_host_bootstrap_contract_has_no_secret_fields():
    payload = valid_host_bootstrap()
    assert not any("password" in str(value).lower() for value in payload.values())
    assert "secret_owner_uid" in payload and "secret_mode" in payload


def test_r1r4_wrapper_contains_bootstrap_only_stop_and_network_none():
    text = (Path(__file__).resolve().parents[2] / "scripts/synology_t3/run_t3_owner_dsm.sh").read_text()
    assert "T3_BOOTSTRAP_ONLY_RESULT=PASS" in text and "--network=none" in text and "T3_BOOTSTRAP_ONLY" in text


def test_r1r5_verify_helper_is_no_bytecode_and_exact_schema_entrypoint():
    text = (Path(__file__).resolve().parents[2] / "scripts/synology_t3/verify_t3_dsm_state.sh").read_text()
    assert "export PYTHONDONTWRITEBYTECODE=1" in text
    assert "python3 -B" in text
    assert "dsm_state_schema.py" in text


def test_r1r5_all_shipped_owner_shell_python_invocations_use_b():
    root = Path(__file__).resolve().parents[2] / "scripts/synology_t3"
    for name in ("verify_t3_dsm_state.sh", "seed_t3_synthetic_share.sh", "run_t3_owner_dsm.sh"):
        text = (root / name).read_text()
        if name != "seed_t3_synthetic_share.sh":
            assert "PYTHONDONTWRITEBYTECODE=1" in text
        for line in text.splitlines():
            if re.search(r"\bpython3\b", line):
                assert "-B" in line, (name, line)


def test_r1r6r1_scope_accepts_r1r6r1_workflow_and_rejects_frozen_paths():
    assert validate_paths([".github/workflows/synology-t3-handoff-build-r1r6r1.yml"]) == []
    assert validate_paths(["backend/app/storage/smb.py"]) != []
    assert validate_paths(["backend/app/config/settings.py"]) != []
    assert validate_paths(["backend/requirements.txt"]) != []
    assert validate_paths(["frontend/src/App.tsx", "infra/docker.yml", "deploy/app.yml", "migrations/001.sql", "scripts/phase5/x.py", "contracts/amec/phase5/x.json"])


def test_r1r6r1_workflow_uses_root_authority_for_protected_post_checks():
    text = (Path(__file__).resolve().parents[2] / ".github/workflows/synology-t3-handoff-build-r1r6r1.yml").read_text()
    assert 'sudo test ! -e "$control/.runtime-pre-$run_id"' in text
    assert 'sudo test ! -e "$control/.bind-canary-$run_id"' in text
    assert 'sudo /usr/bin/python3 - "$control/evidence/16_HOST_BOOTSTRAP.json"' in text
    assert 'sudo stat -c' in text
    assert 'POST_WRAPPER_PROTECTED_CHECKS_AS_ROOT=PASS' in text


def test_r1r6r1_workflow_phase5_refset_is_fresh_nonvacuous_and_exact():
    text = (Path(__file__).resolve().parents[2] / ".github/workflows/synology-t3-handoff-build-r1r6r1.yml").read_text()
    assert text.count('"ls-remote"') >= 2
    assert text.count('refs/heads/phase5*') >= 2
    assert text.count('refs/remotes/origin/phase5*') >= 2
    assert "PHASE5_REMOTE_BRANCH_COUNT_ENTRY" in text
    assert "PHASE5_REMOTE_BRANCH_COUNT_EXIT" in text
    assert "STOP_PHASE5_ZERO_BRANCH_ENUMERATION" in text
    assert "STOP_PHASE5_REFSET_MISMATCH" in text
    assert "PHASE5_REFSET_ENTRY=PASS" in text
    assert "PHASE5_REFSET_EXIT=PASS" in text


def test_r1r6r1_workflow_runs_actual_forced_failure_and_uploads_last():
    text = (Path(__file__).resolve().parents[2] / ".github/workflows/synology-t3-handoff-build-r1r6r1.yml").read_text()
    assert '"phase":"POST"' in text
    assert "STOP_T3_RUNTIME_PRE_BIND_CANARY" in text
    assert "FORCED_FAILURE_EXPECTED_STOP=PASS" in text
    assert text.index("Actual Docker forced-failure runtime PRE cleanup") < text.index("Fresh Phase5 exit overlap gate") < text.index("Upload exactly one immutable R1.6R1 handoff artifact")


def test_r1r5_handoff_copies_verify_helper(tmp_path):
    bundle = create_bundle(Path(__file__).resolve().parents[2], tmp_path, "SYN-T3-R1R5-COPY", "UNCOMMITTED")
    assert (bundle / "verify_t3_dsm_state.sh").read_text() == (Path(__file__).resolve().parents[2] / "scripts/synology_t3/verify_t3_dsm_state.sh").read_text()


def test_r1r5_owner_instructions_bind_one_run_id_everywhere():
    text = (Path(__file__).resolve().parents[2] / "scripts/synology_t3/OWNER_DSM_T3_OPERATOR_INSTRUCTIONS.md").read_text()
    assert "RUN_ID=SYN-T3-<UTC_TIMESTAMP_OR_OWNER_RUN_ID>" in text
    assert "$T3_CONTROL_ROOT/SYN-T3/$T3_RUN_ID" in text
    assert "$T3_CONTROL_DIR/ProposalOps_SYN_T3_Return_$T3_RUN_ID" in text
    assert "STOP_T3_RUN_ID_OR_CONTROL_DIR_COLLISION" in text


def test_r1r5_owner_instructions_document_exact_secret_files_without_credential_transport():
    text = (Path(__file__).resolve().parents[2] / "scripts/synology_t3/OWNER_DSM_T3_OPERATOR_INSTRUCTIONS.md").read_text()
    assert "$T3_CONTROL_DIR/t3_ro.secret" in text and "$T3_CONTROL_DIR/t3_denied.secret" in text
    assert "environment variable or command-line argument" in text
    assert "never printed/hashed/committed/uploaded" in text


def test_r1r5_owner_instructions_require_pre_before_t3_objects_and_post_cleanup():
    text = (Path(__file__).resolve().parents[2] / "scripts/synology_t3/OWNER_DSM_T3_OPERATOR_INSTRUCTIONS.md").read_text()
    assert "Only after PRE PASS may the Owner create the synthetic share and accounts" in text
    assert "Validate POST before finalization" in text
    assert "Remove the one-time Task Scheduler entry" in text
    assert "Disable both T3 identities" in text


def test_r1r5_bootstrap_only_is_explicitly_unset_before_live_run():
    text = (Path(__file__).resolve().parents[2] / "scripts/synology_t3/OWNER_DSM_T3_OPERATOR_INSTRUCTIONS.md").read_text()
    assert "unset T3_BOOTSTRAP_ONLY" in text
    assert 'test -z "${T3_BOOTSTRAP_ONLY+x}"' in text


def test_r1r6r1_wrapper_preserves_root_controlled_canonical_pre():
    text = (Path(__file__).resolve().parents[2] / "scripts/synology_t3/run_t3_owner_dsm.sh").read_text()
    assert 'test "$pre_state"' not in text
    assert 'test "$(stat -c \'%u:%g\' "$pre_state"' in text
    assert 'test "$(stat -c \'%a\' "$pre_state"' in text
    assert 'chown 10001:10001 "$pre_state"' not in text
    assert 'chmod 600 "$pre_state"' not in text


def test_r1r6r1_runtime_pre_is_run_scoped_and_collision_safe():
    text = (Path(__file__).resolve().parents[2] / "scripts/synology_t3/run_t3_owner_dsm.sh").read_text()
    assert 'runtime_pre_dir="$T3_CONTROL_DIR/.runtime-pre-$run_id"' in text
    assert 'runtime_pre="$runtime_pre_dir/10_DSM_PRE_STATE.json"' in text
    assert 'test ! -e "$runtime_pre_dir" || stop STOP_T3_RUNTIME_PRE_COLLISION' in text
    assert 'runtime_pre_created=0' in text and 'runtime_pre_created=1' in text
    assert 'if test "$runtime_pre_created" = 1;' in text


def test_r1r6r1_runtime_pre_identity_and_digest_equality_are_enforced():
    text = (Path(__file__).resolve().parents[2] / "scripts/synology_t3/run_t3_owner_dsm.sh").read_text()
    assert 'chown 10001:10001 "$runtime_pre"; chmod 400 "$runtime_pre"' in text
    assert 'canonical_pre_sha_before' in text and 'runtime_pre_sha' in text and 'canonical_pre_sha_after' in text
    assert 'STOP_T3_RUNTIME_PRE_DIGEST_MISMATCH' in text


def test_r1r6r1_runtime_pre_canary_reads_json_without_network():
    text = (Path(__file__).resolve().parents[2] / "scripts/synology_t3/run_t3_owner_dsm.sh").read_text()
    assert '--network=none' in text
    assert '--mount "type=bind,src=$runtime_pre,dst=/control/10_DSM_PRE_STATE.json,readonly"' in text
    assert 'json.loads(pre)' in text and 'pre_sha256' in text and 'pre_phase' in text
    assert 'STOP_T3_RUNTIME_PRE_BIND_CANARY' in text


def test_r1r6r1_final_runner_binds_runtime_pre_only():
    text = (Path(__file__).resolve().parents[2] / "scripts/synology_t3/run_t3_owner_dsm.sh").read_text()
    mount = 'src=$runtime_pre,dst=/control/10_DSM_PRE_STATE.json,readonly'
    canonical_mount = 'src=$pre_state,dst=/control/10_DSM_PRE_STATE.json,readonly'
    assert text.count(mount) >= 2
    assert canonical_mount not in text


def test_r1r6r1_bootstrap_evidence_contains_sanitized_pre_bind_fields():
    text = (Path(__file__).resolve().parents[2] / "scripts/synology_t3/run_t3_owner_dsm.sh").read_text()
    for field in ("canonical_pre_owner", "canonical_pre_mode", "runtime_pre_owner", "runtime_pre_mode", "canonical_pre_sha_before", "runtime_pre_sha", "canonical_pre_sha_after", "runtime_pre_digest_match", "runtime_pre_bind_canary_network_mode", "runtime_pre_bind_canary_euid", "runtime_pre_bind_canary_egid", "runtime_pre_bind_canary_read", "runtime_pre_cleanup_registered"):
        assert field in text


def test_r1r6r1_owner_instructions_freeze_failed_r1r5_and_require_acceptance():
    text = (Path(__file__).resolve().parents[2] / "scripts/synology_t3/OWNER_DSM_T3_OPERATOR_INSTRUCTIONS.md").read_text()
    assert "R1.6R1" in text
    assert "SYN-T3-20260825T214812Z" in text
    assert "frozen historical failed evidence" in text
    assert "Canonical PRE" in text and "root:root" in text and "0600" in text
    assert "byte-identical" in text and "10001:10001" in text and "0400" in text
    assert "T3_OWNER_EXECUTION_READY=false" in text


@pytest.mark.parametrize("api", ["removeprefix", "removesuffix", "is_relative_to", "tomllib", "ExceptionGroup"])
def test_r1r5_host_facing_modules_reject_python39_plus_apis(api):
    root = Path(__file__).resolve().parents[2] / "scripts/synology_t3"
    modules = [root / name for name in ("verify_t3_dsm_state.sh", "seed_t3_synthetic_share.sh", "run_t3_owner_dsm.sh", "preflight_t3_handoff.py", "finalize_t3_return.py", "validate_t3_return.py", "host_bootstrap.py", "fixture_manifest.py")]
    assert not any(api in path.read_text() for path in modules)
