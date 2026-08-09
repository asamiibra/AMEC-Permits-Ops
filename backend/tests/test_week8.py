"""Week 8 lineage, validity, staleness, corpus, and safety scenarios."""

from datetime import date, timedelta


def canonical_project(client):
    return next(item for item in client.get("/api/projects").json() if item["project_number"] == "GHCE-2026-0142")


def test_lineage_material_change_preserves_pinned_history(client):
    project = canonical_project(client); pid = project["id"]
    package = client.get(f"/api/projects/{pid}/package").json()["package"]
    revision_id = package.get("preparation_revision_id")
    precheck_run_id = None
    if revision_id:
        precheck_run_id = client.get(f"/api/preparation-revisions/{revision_id}/precheck").json().get("run", {}).get("id")
    lineage = client.get(f"/api/projects/{pid}/lineage")
    assert lineage.status_code == 200
    assert any(edge["upstream_type"] == "DocumentVersion" and edge["downstream_type"] == "Package" for edge in lineage.json()["edges"])
    assert any(edge["upstream_type"] == "Package" and edge["downstream_type"] == "PreparationRevision" for edge in lineage.json()["edges"])
    item = client.get(f"/api/packages/{package['id']}/manifest").json()["items"][0]
    changed = client.post("/api/material-changes/evaluate", json={"project_id": pid, "source_type": "DocumentVersion", "source_id": item["document_version_id"], "previous_version_or_hash": item["sha256"], "new_version_or_hash": "synthetic-new-hash", "change_type": "DOCUMENT_NEW_VERSION", "material": True, "metadata": {"semantic_change": True}})
    assert changed.status_code == 200, changed.text
    assert changed.json()["event"]["status"] == "APPLIED"
    package_state = client.get(f"/api/packages/{package['id']}/staleness").json()
    assert package_state["status"] == "STALE"
    stale = client.get(f"/api/projects/{pid}/stale-items").json()
    assert any(x["target_type"] == "Package" and x["target_id"] == package["id"] for x in stale["reasons"])
    if precheck_run_id:
        assert client.get(f"/api/precheck-runs/{precheck_run_id}/validity").json()["validity_status"] == "STALE"


def test_rebuild_creates_new_package_without_mutating_old_revision(client):
    project = canonical_project(client); pid = project["id"]
    old_package = client.get(f"/api/projects/{pid}/package").json()["package"]
    old_manifest = client.get(f"/api/packages/{old_package['id']}/manifest").json()["manifest"]["manifest_hash"]
    rebuilt = client.post(f"/api/packages/{old_package['id']}/rebuild", json={"created_by": "week8-test"})
    assert rebuilt.status_code == 200, rebuilt.text
    new_package = rebuilt.json()["package"]
    assert new_package["id"] != old_package["id"]
    assert old_manifest == client.get(f"/api/packages/{old_package['id']}/manifest").json()["manifest"]["manifest_hash"]
    assert new_package["status"] == "DRAFT"
    approved = client.post(f"/api/packages/{new_package['id']}/approve", json={"approved_by": "week8-test"})
    assert approved.status_code == 200, approved.text
    revision = client.post(f"/api/projects/{pid}/preparation-revisions", json={"package_id": new_package["id"], "created_by": "week8-test"})
    assert revision.status_code == 200, revision.text
    assert revision.json()["revision"]["package_id"] == new_package["id"]


def test_irrelevant_change_and_configuration_policy_are_deterministic(client):
    project = canonical_project(client); pid = project["id"]
    no_change = client.post("/api/material-changes/evaluate", json={"project_id": pid, "source_type": "DocumentVersion", "source_id": "metadata-only", "change_type": "METADATA_REFRESH", "material": False})
    assert no_change.status_code == 200
    assert no_change.json()["event"]["status"] == "NO_MATERIAL_CHANGE"
    config = client.get("/api/config/scenarios/DEMO_BUILDING_PERMIT_V1/requirements").json()["requirements"][0]
    impacted = client.post("/api/material-changes/evaluate", json={"project_id": pid, "source_type": "RequirementConfig", "source_id": config["id"], "change_type": "REQUIREMENT_CONFIG_CHANGED", "new_version_or_hash": "REQ-2"})
    assert impacted.status_code == 200
    assert impacted.json()["event"]["material"] is True


def test_validity_expiry_and_revalidation_are_explicit(client):
    project = canonical_project(client); pid = project["id"]
    dependency = client.get(f"/api/projects/{pid}/dependencies").json()["dependencies"][0]
    expired = client.post(f"/api/dependencies/{dependency['id']}/validity/evaluate", json={"status": "REVOKED"})
    assert expired.status_code == 200, expired.text
    assert expired.json()["validity"]["status"] == "REVOKED"
    document = next(x for x in client.get(f"/api/projects/{pid}/documents").json() if x["document_type"] == "TITLE_DEED")
    validity = client.post(f"/api/document-versions/{document['current_version_id']}/validity/evaluate", json={"valid_until": (date.today() - timedelta(days=1)).isoformat()})
    assert validity.status_code == 200, validity.text
    assert validity.json()["validity"]["validity_status"] == "EXPIRED"
    revalidated = client.post(f"/api/projects/{pid}/revalidate", json={"action": "RE_EVALUATE_READINESS"})
    assert revalidated.status_code == 200
    assert revalidated.json()["auto_approved"] is False
    assert revalidated.json()["evaluation"]["overall_status"] == "BLOCKED"


def test_corpus_and_shadow_correction_are_recorded(client):
    pid = canonical_project(client)["id"]
    run = client.post("/api/corpus-runs", json={"project_id": pid, "label": "SYNTHETIC / NON-CONTRACTUAL"})
    assert run.status_code == 200, run.text
    assert run.json()["run"]["status"] == "COMPLETED"
    assert "false_accept_count" in run.json()["run"]["metrics_json"]
    correction = client.post(f"/api/projects/{pid}/shadow-corrections", json={"entity_type": "VerifiedAssertion", "field_or_category": "PROPERTY.PLOT_NUMBER", "proposed_value": "001234", "approved_human_value": "001235", "correction_type": "VALUE_CORRECTION", "root_cause_category": "SOURCE_AMBIGUITY", "evidence_artifact_id": "synthetic://week8/correction/1"})
    assert correction.status_code == 200
    assert correction.json()["correction"]["root_cause_category"] == "SOURCE_AMBIGUITY"
