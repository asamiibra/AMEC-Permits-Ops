"""Wave A governance contract tests using sanitized synthetic sources only."""

from uuid import uuid4


OWNER = {"X-Dev-Role": "SYSTEM_ADMIN"}
BD = {"X-Dev-Role": "PROCESS_CHAMPION"}


def _create(client, title=None, content=b"wave-a-synthetic-source"):
    ref = f"WA-{uuid4().hex[:8]}"
    response = client.post("/api/master-content", data={"content_type": "FORM", "ref": ref, "title": title or ref, "description": "Synthetic Wave A source", "used_in": '["BD"]'}, files={"file": (f"{ref}.txt", content, "text/plain")}, headers=OWNER)
    assert response.status_code == 200, response.text
    return response.json()


def test_external_official_readiness_currentness_and_version_history(client):
    item = _create(client, "Synthetic external authority form")
    updated = client.patch(f"/api/master-content/{item['id']}/governance", json={"content_ownership_class": "EXTERNAL_OFFICIAL", "artifact_kind": "AUTHORITY_FORM", "publisher_name": "Synthetic Authority", "official_form_no": "SYN-F-01", "official_issue_no": "1", "language_profile": "EN"}, headers=OWNER)
    assert updated.status_code == 200, updated.text
    assert updated.json()["readiness"]["state"] == "BLOCKED"
    assert client.post(f"/api/master-content/{item['id']}/provenance", json={"obtained_from": "Synthetic intake fixture", "provenance_note": "Synthetic evidence only"}, headers=OWNER).status_code == 200
    verified = client.post(f"/api/master-content/{item['id']}/currentness", json={"action": "VERIFY_CURRENT", "note": "Synthetic verification evidence"}, headers=OWNER)
    assert verified.status_code == 200, verified.text
    assert verified.json()["readiness"]["state"] == "MANUAL_USE_READY"
    replaced = client.post(f"/api/master-content/{item['id']}/versions", data={"expected_current_version": "1", "change_reason": "New synthetic official version"}, files={"file": ("v2.txt", b"wave-a-synthetic-source-v2", "text/plain")}, headers=OWNER)
    assert replaced.status_code == 200, replaced.text
    history = client.get(f"/api/master-content/{item['id']}/versions", headers=OWNER).json()
    assert [row["version"] for row in history] == [2, 1]
    assert history[1]["status"] == "SUPERSEDED"


def test_restricted_sample_is_excluded_from_resolver_and_download_is_capability_gated(client):
    item = _create(client, "Synthetic restricted reference sample", b"dummy PII-like value 0000")
    updated = client.patch(f"/api/master-content/{item['id']}/governance", json={"content_ownership_class": "REFERENCE_SAMPLE", "artifact_kind": "AUTHORITY_FORM", "restricted_reference_sample": True, "contains_pii": True}, headers=OWNER)
    assert updated.status_code == 200, updated.text
    assert updated.json()["readiness"]["state"] == "REFERENCE_ONLY"
    resolved = client.get("/api/master-content/resolvers/BD/AVAILABLE", headers=BD).json()
    assert item["id"] not in {row["id"] for row in resolved["candidates"]}
    denied = client.get(f"/api/master-content/{item['id']}/download", headers=BD)
    assert denied.status_code == 403
    allowed = client.get(f"/api/master-content/{item['id']}/download", headers=OWNER)
    assert allowed.status_code == 200


def test_quality_flag_and_exact_source_section_are_immutable_lineage_seams(client):
    item = _create(client)
    governed = client.patch(f"/api/master-content/{item['id']}/governance", json={"content_ownership_class": "AMEC_OWNED", "artifact_kind": "AMEC_FORM", "language_profile": "EN"}, headers=OWNER).json()
    assert client.post(f"/api/master-content/{item['id']}/provenance", json={"obtained_from": "Synthetic intake fixture"}, headers=OWNER).status_code == 200
    version_id = governed["readiness"]["document_version_id"]
    section = client.post(f"/api/master-content/{item['id']}/source-sections", json={"document_version_id": version_id, "section_key": "purpose", "label": "Purpose", "locator_type": "PAGE_RANGE", "page_start": 1, "page_end": 1}, headers=OWNER)
    assert section.status_code == 200, section.text
    flag = client.post(f"/api/master-content/{item['id']}/quality-flags", json={"code": "CLEAN_MASTER_REQUIRED", "severity": "BLOCKING", "description": "Synthetic clean master blocker"}, headers=OWNER)
    assert flag.status_code == 200, flag.text
    assert client.get(f"/api/master-content/{item['id']}", headers=OWNER).json()["governance"]["readiness"]["state"] == "BLOCKED"
    resolved = client.patch(f"/api/master-content/{item['id']}/quality-flags/{flag.json()['id']}", json={"status": "RESOLVED", "resolution": "Synthetic clean source supplied"}, headers=OWNER)
    assert resolved.status_code == 200
    detail = client.get(f"/api/master-content/{item['id']}", headers=OWNER).json()
    assert detail["governance"]["source_sections"][0]["document_version_id"] == version_id
    assert detail["governance"]["readiness"]["state"] == "MANUAL_USE_READY"


def test_wave_a_governance_writes_are_denied_to_bd(client):
    item = _create(client)
    for method, path, kwargs in (
        (client.patch, f"/api/master-content/{item['id']}/governance", {"json": {"content_ownership_class": "EXTERNAL_OFFICIAL"}}),
        (client.post, f"/api/master-content/{item['id']}/currentness", {"json": {"action": "VERIFY_CURRENT"}}),
        (client.post, f"/api/master-content/{item['id']}/quality-flags", {"json": {"code": "CURRENTNESS_UNVERIFIED", "description": "Synthetic"}}),
    ):
        response = method(path, headers=BD, **kwargs)
        assert response.status_code == 403, response.text


def test_equal_hashes_do_not_merge_logical_master_items(client):
    first = _create(client, content=b"identical-synthetic-bytes")
    second = _create(client, content=b"identical-synthetic-bytes")
    assert first["id"] != second["id"]
    assert first["current_version_id"] != second["current_version_id"]
