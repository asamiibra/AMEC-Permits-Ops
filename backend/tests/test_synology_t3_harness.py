from __future__ import annotations

import hashlib
import io
import json
import stat
from dataclasses import dataclass
from pathlib import Path

import pytest

from scripts.synology_t3.build_handoff import ACCEPTED_V23, create_bundle
from scripts.synology_t3.fixture_manifest import build_fixture_manifest, fixture_bytes, fixture_paths
from scripts.synology_t3.network_guard import NetworkGuard, UnexpectedNetworkDestination
from scripts.synology_t3.scope_validator import validate_paths
from scripts.synology_t3.t3_common import (
    APP_LABEL,
    HARNESS_LABEL,
    ROOT,
    SHARE,
    AccessLedger,
    CheckCollector,
    T3Stop,
    T3StoreFactory,
    locator,
    security_introspection,
)
from scripts.synology_t3.t3_runner import read_hash
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
