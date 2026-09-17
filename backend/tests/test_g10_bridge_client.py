from __future__ import annotations

import base64
import hashlib

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from backend.app import g10_bridge_client as bridge
from backend.app.storage.external import StableSourceRead
from backend.app.storage.proposal_source_tree import SourceEntry, SourceProject


def test_live_attempt_id_is_stable_for_retries_and_changes_with_version():
    first = bridge._live_attempt_id("synology://qatar/path/a.pdf", "1:abc")
    assert first == bridge._live_attempt_id("synology://qatar/path/a.pdf", "1:abc")
    assert first != bridge._live_attempt_id("synology://qatar/path/a.pdf", "2:def")


@pytest.mark.parametrize("value", ["maybe", "", "2"])
def test_env_bool_rejects_ambiguous_values(monkeypatch, value):
    monkeypatch.setenv("G10_CONTINUOUS_SYNC", value)
    with pytest.raises(ValueError, match="must be a boolean"):
        bridge._env_bool("G10_CONTINUOUS_SYNC")


def test_sync_interval_is_bounded(monkeypatch):
    monkeypatch.setenv("G10_SYNC_INTERVAL_SECONDS", "4")
    with pytest.raises(ValueError, match="between 5 and 86400"):
        bridge._sync_interval_seconds()
    monkeypatch.setenv("G10_SYNC_INTERVAL_SECONDS", "60")
    assert bridge._sync_interval_seconds() == 60


def test_project_map_accepts_number_and_folder_keys(monkeypatch):
    monkeypatch.setenv("G10_PROJECT_ID_MAP_JSON", '{"454":"project-454", "520 - Draft":"project-520"}')
    monkeypatch.delenv("G10_PROJECT_ID", raising=False)
    assert bridge._project_id_map() == {"454": "project-454", "520 - Draft": "project-520"}


def test_sync_live_once_posts_stable_id_and_reports_unmapped(monkeypatch):
    content = b"one source file"
    project = SourceProject(454, "454 - Al Watan Center", "PROPOSALS_V1_ACTIVE_PILOT")
    draft = SourceProject(520, "520 - Draft", "DRAFT_SOURCE_PROJECT")
    entry = SourceEntry("454 - Al Watan Center/Tender/file.pdf", "file.pdf", False, len(content), 123)

    class Reader:
        def discover(self):
            return [project, draft]

        def inventory(self, folder):
            return [entry] if folder == project.folder_name else []

        def capture(self, relative):
            assert relative == entry.relative_path
            return StableSourceRead(content, len(content), hashlib.sha256(content).hexdigest(), "123", "123")

    private_key = Ed25519PrivateKey.generate()
    monkeypatch.setenv("G10_PROJECT_ID_MAP_JSON", '{"454":"project-454"}')
    monkeypatch.setenv("G10_FIELD_DEFINITION_ID", "field-1")
    monkeypatch.setenv("G10_API_URL", "https://api.example.test")
    monkeypatch.setenv("BRIDGE_SIGNING_PRIVATE_KEY_B64", base64.b64encode(private_key.private_bytes_raw()).decode())
    monkeypatch.setattr(bridge, "_live_token", lambda: "token")
    seen = []

    class Response:
        def raise_for_status(self):
            return None

    def post(url, **kwargs):
        seen.append(kwargs["json"])
        return Response()

    monkeypatch.setattr(bridge.httpx, "post", post)
    result = bridge.sync_live_once(Reader())
    assert result["packages_sent"] == 1
    assert result["projects_unmapped"] == [520]
    assert result["synology_write_count"] == 0
    assert seen[0]["attempt_id"] == bridge._live_attempt_id(seen[0]["source_path_snapshot"], seen[0]["source_version_token"])


def test_sync_live_once_can_fail_closed_when_mapping_is_incomplete(monkeypatch):
    class Reader:
        def discover(self):
            return [SourceProject(520, "520 - Draft", "DRAFT_SOURCE_PROJECT")]

    monkeypatch.setenv("G10_PROJECT_ID_MAP_JSON", "{}")
    monkeypatch.setenv("G10_REQUIRE_ALL_PROJECT_MAPPINGS", "true")
    with pytest.raises(RuntimeError, match="LIVE_PROJECT_MAPPING_INCOMPLETE:520"):
        bridge.sync_live_once(Reader())
