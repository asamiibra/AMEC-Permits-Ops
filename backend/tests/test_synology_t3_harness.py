from __future__ import annotations

import json
from pathlib import Path

from scripts.synology_t3.build_handoff import ACCEPTED_V23, create_bundle
from scripts.synology_t3.fixture_manifest import fixture_bytes, fixture_paths
from scripts.synology_t3.network_guard import NetworkGuard, UnexpectedNetworkDestination
from scripts.synology_t3.validate_t3_return import scan, validate_return


def test_fixture_manifest_has_exact_deterministic_corpus():
    paths = fixture_paths()
    assert len(paths) == 270
    assert paths[-1] == "listing/entry-0257.bin"
    assert fixture_bytes("range/range-4MiB.bin") == fixture_bytes("range/range-4MiB.bin")
    assert len(fixture_bytes("stream/stream-8MiB.bin")) == 8 * 1024 * 1024


def test_network_guard_rejects_every_non_target_tuple():
    guard = NetworkGuard("192.0.2.10")
    guard.check(("192.0.2.10", 445))
    try:
        guard.check(("192.0.2.11", 445))
    except UnexpectedNetworkDestination:
        pass
    else:
        raise AssertionError("unexpected destination was not rejected")
    assert guard.unique_destinations == [("192.0.2.10", 445), ("192.0.2.11", 445)]


def test_return_validator_fails_closed_on_missing_post_state(tmp_path):
    result = validate_return(tmp_path)
    assert result["status"] == "FAIL" and result["errors"]


def test_handoff_builder_binds_accepted_v23_and_has_no_secrets(tmp_path):
    repo = Path(__file__).resolve().parents[2]
    bundle = create_bundle(repo, tmp_path, "SYN-T3-TEST")
    identity = json.loads((bundle / "01_APPLICATION_IDENTITY.json").read_text(encoding="utf-8"))
    assert identity["accepted_v23_sha"] == ACCEPTED_V23
    assert (bundle / "13_FIXTURE_MANIFEST.json").is_file()
    assert not list(bundle.rglob("*.secret"))
    assert scan(bundle)["match_count"] == 0
