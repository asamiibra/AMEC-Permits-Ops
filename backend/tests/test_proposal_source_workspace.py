import json
import hashlib
import io
import zipfile
from pathlib import Path

from backend.app.services.proposal_source_workspace import projects, tree
from backend.app.api.proposal_source_routers import _baseline_identity_matches
from backend.app.models import DocumentVersion


def test_explicit_454_create_proposal_persists_source_set(client):
    response = client.post(
        "/api/proposals/sources/2026/projects/454/create-proposal",
        headers={"X-Dev-Role": "SYSTEM_ADMIN"},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["result"] == "CREATED"
    # The stale Q-498-named source remains evidence; the governed Proposal
    # template is added as the editable baseline, so the promoted set has one
    # additional server-owned source version.
    assert payload["source_count"] == 14
    assert payload["capture"]["synology_write_count"] == 0
    assert payload["editor_ready"] is True
    assert payload["editor_revision_id"]
    assert payload["editor_baseline_hash"]
    assert payload["ai_generation"]["status"] == "SUCCEEDED"
    assert payload["ai_generation"]["mutation_count"] >= 1
    generated = client.get(
        f"/api/proposals-v1/editor/proposals/{payload['proposal_id']}/revisions/{payload['editor_revision_id']}/document",
        headers={"X-Dev-Role": "SYSTEM_ADMIN"},
    )
    assert generated.status_code == 200
    from backend.app.services.proposal_document_package import document_map
    generated_text = "\n".join(block.text for block in document_map(generated.content))
    assert "Q-498" not in generated_text
    assert "Al Watan Center" in generated_text
    assert "QAR 40,000" not in generated_text
    assert "discounted QAR 36,000" not in generated_text
    assert "Duration: 3 months" not in generated_text
    assert "Needs Owner Review" in generated_text
    revision = client.get(
        f"/api/proposals-v1/editor/proposals/{payload['proposal_id']}/revisions/{payload['editor_revision_id']}",
        headers={"X-Dev-Role": "SYSTEM_ADMIN"},
    )
    revision_payload = revision.json()
    assert revision_payload["baseline_selection_method"] == "GOVERNED_MASTER_CONTENT_TEMPLATE"
    assert revision_payload["editor_document_version_id"]
    downloaded = client.get(
        f"/api/proposals-v1/editor/proposals/{payload['proposal_id']}/revisions/{payload['editor_revision_id']}/document",
        headers={"X-Dev-Role": "SYSTEM_ADMIN"},
    )
    assert downloaded.status_code == 200
    assert downloaded.headers["x-proposal-document-version-id"] == revision_payload["editor_document_version_id"]
    assert downloaded.headers["x-proposal-document-sha256"] == hashlib.sha256(downloaded.content).hexdigest()
    expected_parts = set(zipfile.ZipFile(io.BytesIO(Path("backend/app/fixtures/AMEC-P-D-2026-Q-454.docx").read_bytes())).namelist())
    actual_zip = zipfile.ZipFile(io.BytesIO(downloaded.content))
    assert set(actual_zip.namelist()) == expected_parts
    for part in ("word/header1.xml", "word/footer1.xml", "word/styles.xml", "word/media/logo.png"):
        assert actual_zip.read(part) == zipfile.ZipFile(io.BytesIO(Path("backend/app/fixtures/AMEC-P-D-2026-Q-454.docx").read_bytes())).read(part)
    rendered = client.get(
        f"/api/proposals-v1/editor/proposals/{payload['proposal_id']}/revisions/{payload['editor_revision_id']}/render",
        headers={"X-Dev-Role": "SYSTEM_ADMIN"},
    )
    assert rendered.status_code == 200
    assert rendered.headers["x-proposal-document-version-id"] == revision_payload["editor_document_version_id"]
    assert rendered.headers["x-proposal-document-sha256"] == downloaded.headers["x-proposal-document-sha256"]
    revision = client.get(
        f"/api/proposals-v1/editor/proposals/{payload['proposal_id']}/revisions/{payload['editor_revision_id']}",
        headers={"X-Dev-Role": "SYSTEM_ADMIN"},
    )
    assert revision.status_code == 200, revision.text
    mutation = revision.json()["change_plan"]["mutations"][0]
    assert mutation["before"]
    assert mutation["after"]
    assert mutation["section"]
    assert mutation["reason"]


def test_source_create_applies_owner_exclusions_without_mutating_synology(client):
    entries = tree(454)["entries"]
    excluded = next(entry for entry in entries if not entry["is_directory"])
    response = client.post(
        "/api/proposals/sources/2026/projects/454/create-proposal",
        headers={"X-Dev-Role": "SYSTEM_ADMIN"},
        json={"excluded_source_paths": [excluded["path"]]},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["source_count"] == 13
    assert payload["excluded_source_count"] == 1
    assert payload["capture"]["synology_write_count"] == 0


def test_cross_project_docx_body_cannot_become_project_454_baseline():
    stale_path = Path(
        "mock-systems/proposal-sources/Tenders/1- Proposal/2026/"
        "454 - Al Watan Center/AMEC-P-D-2026-Q-454.docx"
    )
    template_path = Path("backend/app/fixtures/AMEC-P-D-2026-Q-454.docx")
    expected = {"project_number": "454", "project_name": "al watan center", "client_name": "al watan center"}
    stale = DocumentVersion(
        source_filename=stale_path.name,
        source_path_or_reference="synthetic://stale",
        synthetic_content=stale_path.read_bytes(),
        sha256=hashlib.sha256(stale_path.read_bytes()).hexdigest(),
    )
    template = DocumentVersion(
        source_filename=template_path.name,
        source_path_or_reference="synthetic://template",
        synthetic_content=template_path.read_bytes(),
        sha256=hashlib.sha256(template_path.read_bytes()).hexdigest(),
        metadata_json={"template_baseline": True},
    )
    assert _baseline_identity_matches(stale, expected) is False
    assert _baseline_identity_matches(template, expected) is True


def test_synology_draft_520_uses_universal_template_generation(client):
    response = client.post(
        "/api/proposals/sources/2026/projects/520/create-proposal",
        headers={"X-Dev-Role": "SYSTEM_ADMIN"},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["result"] == "CREATED"
    assert payload["generation_state"] == "READY_FOR_EDIT"
    document = client.get(
        f"/api/proposals-v1/editor/proposals/{payload['proposal_id']}/revisions/{payload['editor_revision_id']}/document",
        headers={"X-Dev-Role": "SYSTEM_ADMIN"},
    )
    assert document.status_code == 200
    from backend.app.services.proposal_document_package import document_map
    text = "\n".join(block.text for block in document_map(document.content))
    assert "Q-520" in text
    assert "Future Draft" in text
    assert "Q-454" not in text


def test_source_create_seeds_canonical_editor_and_owner_save_roundtrip(client):
    created = client.post(
        "/api/proposals/sources/2026/projects/454/create-proposal",
        headers={"X-Dev-Role": "SYSTEM_ADMIN"},
    ).json()
    proposal_id = created["proposal_id"]
    revision_id = created["editor_revision_id"]
    headers = {"X-Dev-Role": "SYSTEM_ADMIN"}
    loaded = client.get(
        f"/api/proposals-v1/editor/proposals/{proposal_id}/revisions/{revision_id}",
        headers=headers,
    )
    assert loaded.status_code == 200, loaded.text
    baseline = loaded.json()
    assert baseline["source_set_hash"] == created["source_set_hash"]
    assert baseline["editor_model"]["editable_node_count"] > 0
    baseline_document = client.get(
        f"/api/proposals-v1/editor/proposals/{proposal_id}/revisions/{revision_id}/document",
        headers=headers,
    )
    assert baseline_document.status_code == 200, baseline_document.text
    assert baseline_document.headers["content-type"].startswith("application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    assert baseline_document.content[:2] == b"PK"

    intake = client.post(
        f"/api/bd/proposals/{proposal_id}/intelligence",
        headers=headers,
        json={
            "operation": "tender-intake-analysis",
            "idempotency_key": "source-workspace-ai-intake-454",
        },
    )
    assert intake.status_code == 200, intake.text
    intake_payload = intake.json()
    assert intake_payload["status"] == "SUCCEEDED"
    assert intake_payload["output"]["summary"] == "Synthetic governed Proposal intake analysis."
    assert intake_payload["citations"]
    assert intake_payload["human_review_required"] is True

    source_docx = Path(
        "mock-systems/proposal-sources/Tenders/1- Proposal/2026/"
        "454 - Al Watan Center/AMEC-P-D-2026-Q-454.docx"
    )
    imported = client.post(
        "/api/proposals-v1/editor/import",
        headers=headers,
        files={"file": (source_docx.name, source_docx.read_bytes(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert imported.status_code == 200, imported.text
    imported_model = imported.json()
    current_model = json.loads(json.dumps(imported_model))
    target = next(node for node in current_model["nodes"] if node["editable"] and "Q-498" in node["text"])
    target["text"] = target["text"].replace("Q-498", "Q-454").replace("Rev 01", "Rev 01 · Al Watan Center")
    saved = client.post(
        f"/api/proposals-v1/editor/proposals/{proposal_id}/revisions/{revision_id}/save",
        headers=headers,
        files={"file": (source_docx.name, source_docx.read_bytes(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        data={
            "imported_model": json.dumps(imported_model),
            "current_model": json.dumps(current_model),
            "change_plan": json.dumps({"mode": "SYNTHETIC_DETERMINISTIC", "anchors": [target["id"]]}),
            "evidence_refs": json.dumps([created["source_set_hash"]]),
        },
    )
    assert saved.status_code == 200, saved.text
    result = saved.json()
    assert result["result"] == "SAVED"
    assert result["working_hash"] != result["baseline_hash"]
    assert result["ai_provenance"]["provenance_state"] == "RECORDED"
    revised_document = client.get(
        f"/api/proposals-v1/editor/proposals/{proposal_id}/revisions/{revision_id}/document",
        headers=headers,
    )
    assert revised_document.status_code == 200, revised_document.text
    assert revised_document.headers["x-proposal-document-sha256"] == result["working_hash"]
    assert revised_document.content[:2] == b"PK"

    reopened = client.get(
        f"/api/proposals-v1/editor/proposals/{proposal_id}/revisions/{revision_id}",
        headers=headers,
    )
    assert reopened.status_code == 200, reopened.text
    reopened_model = reopened.json()["editor_model"]
    assert any("Q-454" in node["text"] and "Al Watan Center" in node["text"] for node in reopened_model["nodes"])


def test_owner_added_source_is_read_back_and_regenerates_ai_revision(client):
    headers = {"X-Dev-Role": "SYSTEM_ADMIN"}
    created = client.post(
        "/api/proposals/sources/2026/projects/454/create-proposal",
        headers=headers,
    )
    assert created.status_code == 200, created.text
    proposal_id = created.json()["proposal_id"]
    owner_source = b"OWNER REVIEW: confirm the tender programme and client contact before issue.\n"
    added = client.post(
        f"/api/bd/proposals/{proposal_id}/sources",
        headers=headers,
        files={"file": ("owner-review.txt", owner_source, "text/plain")},
        data={"source_type": "TENDER_DOCUMENT", "logical_category": "TENDER_DOCUMENTS"},
    )
    assert added.status_code == 200, added.text
    source = added.json()["source"]
    assert source["verification_state"] == "READ_BACK_VERIFIED"
    source_readback = client.get(
        f"/api/bd/proposals/{proposal_id}/sources/{source['id']}/content",
        headers=headers,
    )
    assert source_readback.status_code == 200, source_readback.text
    assert source_readback.content == owner_source
    regenerated = client.post(
        f"/api/proposals/sources/proposals/{proposal_id}/regenerate",
        headers=headers,
    )
    assert regenerated.status_code == 200, regenerated.text
    payload = regenerated.json()
    assert payload["result"] == "REGENERATED"
    assert payload["source_count"] == created.json()["source_count"] + 1
    assert payload["ai_generation"]["status"] == "SUCCEEDED"
    assert payload["ai_generation"]["mutation_count"] >= 1


def test_source_routes_require_authenticated_owner(client):
    denied = {"X-Dev-Role": "NOT_A_ROLE"}
    assert client.get("/api/proposals/sources/2026/projects", headers=denied).status_code in {401, 403}
    assert client.post("/api/proposals/sources/2026/sync", headers=denied).status_code in {401, 403}
    # Every synced Draft is manually promotable; 520 is no longer a special
    # blocked case and remains idempotent on repeat promotion.
    assert client.post("/api/proposals/sources/2026/projects/520/create-proposal", headers={"X-Dev-Role": "SYSTEM_ADMIN"}).status_code == 200


def test_workspace_sync_is_scoped_to_selected_project(client, monkeypatch):
    from backend.app.api import proposal_source_routers
    discovered = [
        {"number": 454, "name": "454 - Al Watan Center"},
        {"number": 520, "name": "520 - Romana Hypermarket"},
    ]
    monkeypatch.setattr(proposal_source_routers, "projects", lambda db: discovered)
    monkeypatch.setattr(proposal_source_routers, "capture", lambda db, number, actor: {"project_number": number, "captured_count": 0, "unchanged_count": 1})
    monkeypatch.setattr(proposal_source_routers, "source_manifest", lambda db, number: {"source_manifest_hash": f"hash-{number}", "source_project_identity": f"identity-{number}"})
    monkeypatch.setattr(proposal_source_routers, "_mark_bound_proposals_stale", lambda *args, **kwargs: None)
    response = client.post(
        "/api/proposals/sources/2026/sync?project=520",
        headers={"X-Dev-Role": "SYSTEM_ADMIN"},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert [run["project_number"] for run in payload["runs"]] == [520]
    assert payload["synology_write_count"] == 0


def test_fixture_discovers_pilot_and_520_draft_only():
    rows = projects()
    assert {row["number"] for row in rows} >= {454, 520}
    assert next(row for row in rows if row["number"] == 454)["state"] == "ACTIVE_PILOT"
    assert next(row for row in rows if row["number"] == 520)["state"] == "DRAFT_SYNCED"


def test_pilot_tree_keeps_expected_exact_names_and_nested_paths():
    entries = tree(454)["entries"]
    names = {entry["name"] for entry in entries}
    assert {"Client data", "Email", "Photo", "Project Information", "Tender Document"} <= names
    assert any(entry["path"].endswith("/client.txt") for entry in entries)
    assert any(entry["path"].endswith("/AMEC-P-D-2026-Q-454.pdf") for entry in entries)


def test_file_ids_are_path_bound_and_not_raw_paths():
    entries = tree(454)["entries"]
    files = [entry for entry in entries if not entry["is_directory"]]
    assert files and all(len(entry["id"]) == 24 and "/" not in entry["id"] for entry in files)


def test_synthetic_preview_sources_are_real_document_bytes(client):
    headers = {"X-Dev-Role": "SYSTEM_ADMIN"}
    created = client.post(
        "/api/proposals/sources/2026/projects/454/create-proposal",
        headers=headers,
    )
    assert created.status_code == 200, created.text
    entries = tree(454)["entries"]
    pdf = next(entry for entry in entries if entry["name"] == "AMEC-P-D-2026-Q-454.pdf")
    image = next(entry for entry in entries if entry["name"] == "site-photo.jpg")
    pdf_response = client.get(
        f"/api/proposals/sources/2026/projects/454/files/{pdf['id']}/content",
        headers=headers,
    )
    image_response = client.get(
        f"/api/proposals/sources/2026/projects/454/files/{image['id']}/content",
        headers=headers,
    )
    assert pdf_response.status_code == 200 and pdf_response.content.startswith(b"%PDF")
    assert image_response.status_code == 200 and image_response.content.startswith(b"\xff\xd8\xff")
    assert pdf_response.headers["x-source-content-sha256"]
    assert image_response.headers["x-source-content-sha256"]
