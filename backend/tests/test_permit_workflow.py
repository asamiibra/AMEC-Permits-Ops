from fastapi.testclient import TestClient


def _project(client: TestClient):
    return next(item for item in client.get("/api/projects").json() if item["project_number"] == "GHCE-2026-0142")


def test_stage_one_projection_exposes_real_sources_and_backend_office(client: TestClient):
    project = _project(client)
    detail = client.get(f"/api/projects/{project['id']}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["office"]["name_en"]
    assert body["workflow"]["stage"] == "PROJECT_AND_SOURCES"
    assert body["workflow"]["next_action"]["action_code"] == "ESTABLISH_PROJECT_SOURCES"
    assert sorted(item["system_type"] for item in body["workflow"]["sources"]["bindings"]) == ["EXCEL", "MUNICIPALITY", "SYNOLOGY"]
    assert body["workflow"]["task"]["title"] == "Confirm project & sources"


def test_confirm_project_sources_persists_advances_tasks_and_is_idempotent(client: TestClient):
    project = _project(client)
    headers = {"X-Dev-Role": "SYSTEM_ADMIN"}
    first = client.post(
        f"/api/projects/{project['id']}/confirm-project-sources",
        json={"project_reference": project["project_number"]},
        headers=headers,
    )
    assert first.status_code == 200, first.text
    first_body = first.json()
    assert first_body["result"] == "COMPLETED"
    assert first_body["workflow"]["stage"] == "VERIFY_DATA"
    assert first_body["workflow"]["next_action"]["action_code"] == "VERIFY_PROJECT_DATA"
    assert first_body["application"]["workflow_stage"] == "VERIFY_DATA"

    refreshed = client.get(f"/api/projects/{project['id']}").json()
    assert refreshed["workflow"]["stage"] == "VERIFY_DATA"
    assert refreshed["workflow"]["confirmed_at"]
    assert refreshed["workflow"]["confirmed_by"]

    tasks = client.get("/api/tasks", params={"project_id": project["id"]}).json()["tasks"]
    stage_one = [task for task in tasks if task["task_type"] == "CONFIRM_PROJECT_SOURCES"]
    verify = [task for task in tasks if task["task_type"] == "VERIFY_PROJECT_DATA"]
    assert len(stage_one) == 1 and stage_one[0]["status"] == "COMPLETED"
    assert len(verify) == 1 and verify[0]["status"] == "OPEN"

    second = client.post(
        f"/api/projects/{project['id']}/confirm-project-sources",
        json={"project_reference": project["project_number"]},
        headers=headers,
    )
    assert second.status_code == 200
    assert second.json()["result"] == "IDEMPOTENT"
    tasks_after = client.get("/api/tasks", params={"project_id": project["id"]}).json()["tasks"]
    assert len([task for task in tasks_after if task["task_type"] == "VERIFY_PROJECT_DATA"]) == 1


def test_confirm_project_sources_rejects_reference_mismatch_and_capability(client: TestClient):
    project = next(item for item in client.get("/api/projects").json() if item["project_number"] == "GHCE-2026-0187")
    mismatch = client.post(
        f"/api/projects/{project['id']}/confirm-project-sources",
        json={"project_reference": "WRONG-REFERENCE"},
        headers={"X-Dev-Role": "SYSTEM_ADMIN"},
    )
    assert mismatch.status_code == 409
    assert mismatch.json()["detail"]["code"] == "PROJECT_REFERENCE_MISMATCH"

    denied = client.post(
        f"/api/projects/{project['id']}/confirm-project-sources",
        json={"project_reference": project["project_number"]},
        headers={"X-Dev-Role": "FINAL_SUBMITTER"},
    )
    assert denied.status_code == 403
    assert denied.json()["detail"]["code"] == "CAPABILITY_DENIED"
