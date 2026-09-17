import json
from pathlib import Path

from backend.app.services.proposal_source_workspace import projects, tree


def test_explicit_454_create_proposal_persists_source_set(client):
    response = client.post(
        "/api/proposals/sources/2026/projects/454/create-proposal",
        headers={"X-Dev-Role": "SYSTEM_ADMIN"},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["result"] == "CREATED"
    assert payload["source_count"] == 13
    assert payload["capture"]["synology_write_count"] == 0
    assert payload["editor_ready"] is True
    assert payload["editor_revision_id"]
    assert payload["editor_baseline_hash"]


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


def test_source_routes_require_authenticated_owner(client):
    denied = {"X-Dev-Role": "NOT_A_ROLE"}
    assert client.get("/api/proposals/sources/2026/projects", headers=denied).status_code in {401, 403}
    assert client.post("/api/proposals/sources/2026/sync", headers=denied).status_code in {401, 403}
    assert client.post("/api/proposals/sources/2026/projects/520/create-proposal", headers={"X-Dev-Role": "SYSTEM_ADMIN"}).status_code == 409


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
