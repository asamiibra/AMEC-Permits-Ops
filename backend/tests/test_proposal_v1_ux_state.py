def test_owner_category_save_is_durable_and_source_project_leaves_queue(client):
    headers = {"X-Dev-Role": "SYSTEM_ADMIN"}
    before = client.get("/api/proposals/sources/2026/projects/520/tree", headers=headers)
    assert before.status_code == 200, before.text
    entry = next(item for item in before.json()["entries"] if not item["is_directory"])

    saved = client.patch(
        f"/api/proposals/sources/2026/projects/520/files/{entry['id']}/category",
        headers=headers,
        json={"logical_category": "CLIENT_DATA"},
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["logical_category"] == "CLIENT_DATA"
    assert saved.json()["category_source"] == "OWNER_OVERRIDE"

    reloaded = client.get("/api/proposals/sources/2026/projects/520/tree", headers=headers)
    assert reloaded.status_code == 200, reloaded.text
    persisted = next(item for item in reloaded.json()["entries"] if item["id"] == entry["id"])
    assert persisted["logical_category"] == "CLIENT_DATA"
    assert persisted["category_source"] == "OWNER_OVERRIDE"

    created = client.post("/api/proposals/sources/2026/projects/520/create-proposal", headers=headers)
    assert created.status_code == 200, created.text
    projects = client.get("/api/proposals/sources/2026/projects", headers=headers)
    assert projects.status_code == 200, projects.text
    assert 520 not in {row["number"] for row in projects.json()["projects"]}


def test_proposal_v1_entry_resolves_only_to_canonical_editor_revision(client):
    headers = {"X-Dev-Role": "SYSTEM_ADMIN"}
    created = client.post("/api/proposals/sources/2026/projects/454/create-proposal", headers=headers)
    assert created.status_code == 200, created.text
    payload = created.json()
    entry = client.get(f"/api/proposals-v1/editor/proposals/{payload['proposal_id']}/entry", headers=headers)
    assert entry.status_code == 200, entry.text
    assert entry.json()["revision_id"] == payload["editor_revision_id"]
    assert entry.json()["route"].endswith("/editor")
