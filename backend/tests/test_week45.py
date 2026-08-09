"""Week 4–5 deterministic package and assisted municipality acceptance slice."""

from backend.app.seed.cli import seed


def canonical_project(client):
    return next(item for item in client.get("/api/projects").json() if item["project_number"] == "GHCE-2026-0142")


def test_week45_canonical_package_and_assisted_preparation(client):
    seed()
    project = canonical_project(client)
    pid = project["id"]

    initial = client.post(f"/api/projects/{pid}/readiness/evaluate")
    assert initial.status_code == 200
    assert initial.json()["evaluation"]["overall_status"] == "BLOCKED"

    documents = client.get(f"/api/projects/{pid}/documents").json()
    required = {"TITLE_DEED", "OWNER_QID", "DRAWING_SET"}
    for document in documents:
        if document["document_type"] in required:
            assert client.patch(f"/api/document-versions/{document['current_version_id']}/approval-state", json={"approval_state": "APPROVED"}).status_code == 200
    title_deed = next(document for document in documents if document["document_type"] == "TITLE_DEED")
    keyed = client.post(f"/api/projects/{pid}/manual-observations", json={"document_version_id": title_deed["current_version_id"], "field_code": "PROPERTY.PLOT_NUMBER", "raw_value": "001234", "source_region_text": "Synthetic canonical title deed evidence"})
    assert keyed.status_code == 200
    assert client.post(f"/api/observations/{keyed.json()['id']}/verify", json={"method": "HUMAN_VERIFIED"}).status_code == 200
    drawing = next(document for document in documents if document["document_type"] == "DRAWING_SET")
    observations = client.get(f"/api/document-versions/{drawing['current_version_id']}/observations").json()
    revision_observations = [item for item in observations if item["field_code"] == "DRAWING.REVISION"]
    for observation in revision_observations:
        assert client.post(f"/api/observations/{observation['id']}/verify", json={"method": "HUMAN_VERIFIED"}).status_code == 200

    ready = client.post(f"/api/projects/{pid}/readiness/evaluate").json()
    assert ready["evaluation"]["overall_status"] in {"READY", "READY_WITH_NONBLOCKING_WARNINGS"}
    package_response = client.post(f"/api/projects/{pid}/package")
    assert package_response.status_code == 200
    package = package_response.json()
    assert package["manifest"]["manifest_hash"]
    assert all(len(item["file_sha256"]) == 64 for item in package["items"])
    assert client.post(f"/api/projects/{pid}/forms/OWNER_UNDERTAKING/render").status_code == 200

    blocked_projection = client.post(f"/api/projects/{pid}/excel-projections", json={"target_column": "Human Notes", "ownership": "HUMAN_OWNED", "rendered_value": "must not write"}).json()
    assert client.post(f"/api/excel-projections/{blocked_projection['id']}/apply").status_code == 409
    system_projection = client.post(f"/api/projects/{pid}/excel-projections", json={"target_column": "Canonical Plot Number", "ownership": "PERMITOPS_OWNED", "rendered_value": "001234"}).json()
    assert client.post(f"/api/excel-projections/{system_projection['id']}/apply").status_code == 200

    assert client.post(f"/api/projects/{pid}/approvals", json={"approval_type": "DATA_VERIFICATION_COMPLETE", "role_at_decision": "REQUIREMENT_STEWARD"}).status_code == 200
    assert client.post(f"/api/projects/{pid}/approvals", json={"approval_type": "TECHNICAL_REVIEW_COMPLETE", "role_at_decision": "RESPONSIBLE_ENGINEER", "decided_by": "Omar Haddad"}).status_code == 200
    approved = client.post(f"/api/packages/{package['package']['id']}/approve", json={"approved_by": "Noura Salem"})
    assert approved.status_code == 200

    revision = client.post(f"/api/projects/{pid}/preparation-revisions", json={"package_id": package["package"]["id"], "created_by": "Rana Faisal"})
    assert revision.status_code == 200
    revision_id = revision.json()["revision"]["id"]
    application_id = revision.json()["revision"]["application_id"]
    grids = client.get(f"/api/preparation-revisions/{revision_id}/municipality/grids").json()["rows"]
    attachments = client.get(f"/api/preparation-revisions/{revision_id}/municipality/attachments").json()["attachments"]
    assert client.post(f"/api/preparation-revisions/{revision_id}/intended-state", json={"fields": {"plot_number": "001234", "owner_name": "Yousef Ahmed Ali"}, "repeating_rows": grids, "attachments": attachments}).status_code == 200
    assert client.put(f"/mock-authority/applications/{application_id}/draft", json={"state_json": {"plot_number": "999999", "owner_name": "Yousef Ahmed Ali", "buildings": grids}}).status_code == 200
    bad_snapshot = client.post(f"/api/preparation-revisions/{revision_id}/portal-snapshots", json={"snapshot_type": "REOPENED", "capture_method": "SIMULATOR_READ", "grid_state": grids, "attachment_state": attachments}).json()
    bad_reconciliation = client.post(f"/api/preparation-revisions/{revision_id}/reconcile", json={"portal_snapshot_id": bad_snapshot["id"]})
    assert bad_reconciliation.status_code == 200
    assert any(item["status"] == "MISMATCH" for item in bad_reconciliation.json()["results"])
    assert client.put(f"/mock-authority/applications/{application_id}/draft", json={"state_json": {"plot_number": "001234", "owner_name": "Yousef Ahmed Ali", "buildings": grids}}).status_code == 200
    snapshot = client.post(f"/api/preparation-revisions/{revision_id}/portal-snapshots", json={"snapshot_type": "REOPENED", "capture_method": "SIMULATOR_READ", "grid_state": grids, "attachment_state": attachments}).json()
    reconciliation = client.post(f"/api/preparation-revisions/{revision_id}/reconcile", json={"portal_snapshot_id": snapshot["id"]})
    assert reconciliation.status_code == 200
    assert reconciliation.json()["revision"]["status"] == "VERIFIED_DRAFT"
    assert client.post(f"/api/preparation-revisions/{revision_id}/precheck/capture").status_code == 200
    assert client.post(f"/api/preparation-revisions/{revision_id}/session/attendance", json={"human_attendance_confirmed": True}).status_code == 200
    handoff = client.post(f"/api/preparation-revisions/{revision_id}/handoff", json={})
    assert handoff.status_code == 200
    assert handoff.json()["statement"] == "HUMAN SUBMISSION REQUIRED"
    assert client.post(f"/api/preparation-revisions/{revision_id}/submission-confirmation", json={"method": "HUMAN_EVIDENCE", "observed_status": "SUBMITTED_CONFIRMED", "evidence_artifact_id": "synthetic://submission-evidence/1"}).status_code == 200
