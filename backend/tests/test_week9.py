"""Week 9 attachment, grid identity, persistence, drift, and portal-derived tests."""

from datetime import date, timedelta

from sqlalchemy import select

from backend.app.db import SessionLocal
from backend.app.models import *


def canonical_project(client):
    return next(item for item in client.get("/api/projects").json() if item["project_number"] == "GHCE-2026-0142")


def viable_revision():
    """Restore the synthetic Week 9 exercise fixture after Week 8 invalidation tests."""
    with SessionLocal() as db:
        project = db.scalar(select(Project).where(Project.project_number == "GHCE-2026-0142"))
        package = db.scalar(select(Package).where(Package.project_id == project.id).order_by(Package.created_at.desc()))
        revision = db.scalar(select(PreparationRevision).where(PreparationRevision.project_id == project.id).order_by(PreparationRevision.sequence.desc()))
    if not package or not revision:
        # Week 9 is independently executable. The full-suite order normally
        # leaves a package behind, but a Week 9-only run must create its own
        # canonical preparation evidence instead of relying on history.
        from backend.scripts.golden_path_v1 import run as golden_path_v1
        golden_path_v1()
        with SessionLocal() as db:
            project = db.scalar(select(Project).where(Project.project_number == "GHCE-2026-0142"))
            package = db.scalar(select(Package).where(Package.project_id == project.id).order_by(Package.created_at.desc()))
            revision = db.scalar(select(PreparationRevision).where(PreparationRevision.project_id == project.id).order_by(PreparationRevision.sequence.desc()))
    with SessionLocal() as db:
        project = db.scalar(select(Project).where(Project.project_number == "GHCE-2026-0142"))
        package = db.scalar(select(Package).where(Package.project_id == project.id).order_by(Package.created_at.desc()))
        revision = db.scalar(select(PreparationRevision).where(PreparationRevision.project_id == project.id).order_by(PreparationRevision.sequence.desc()))
        package.status = "APPROVED"; revision.status = "READY_FOR_ASSISTED_PREPARATION"; revision.package_id = package.id; package.preparation_revision_id = revision.id
        for dependency in db.scalars(select(ApprovalDependency).where(ApprovalDependency.project_id == project.id)).all():
            dependency.status = "CURRENT"; dependency.valid_until = date.today() + timedelta(days=365)
            validity = db.scalar(select(AuthorityApprovalValidity).where(AuthorityApprovalValidity.approval_dependency_id == dependency.id))
            if validity: validity.status = "VALID"; validity.valid_until = None
        for version in db.scalars(select(DocumentVersion).join(Document).where(Document.project_id == project.id)).all():
            if version.id in {x.document_version_id for x in db.scalars(select(PackageItem).where(PackageItem.package_id == package.id)).all()}:
                version.approval_state = DocumentApprovalState.APPROVED; version.superseded_by = None
                validity = db.scalar(select(DocumentValidity).where(DocumentValidity.document_version_id == version.id))
                if validity: validity.validity_status = "VALID"; validity.expires_at = None
        db.commit()
    return revision.id


def test_attachment_manifest_exact_versions_and_idempotent_persistence(client):
    revision_id = viable_revision()
    manifest = client.post(f"/api/preparation-revisions/{revision_id}/attachment-manifest/refresh", json={"actor": "week9-test"})
    assert manifest.status_code == 200, manifest.text
    body = manifest.json(); assert body["manifest"]["status"] == "LOCKED"; assert len(body["categories"]) == 17
    ready = [x for x in body["items"] if x["status"] == "READY"]
    assert ready and all(x["document_version_id"] and x["file_sha256"] for x in ready)
    for item in ready:
        intent = client.post(f"/api/preparation-revisions/{revision_id}/attachments/associate", json={"category_code": item["category_code"], "document_version_id": item["document_version_id"], "idempotency_key": f"w9:{item['category_code']}"})
        assert intent.status_code == 200, intent.text
        retry = client.post(f"/api/preparation-revisions/{revision_id}/attachments/associate", json={"category_code": item["category_code"], "document_version_id": item["document_version_id"], "idempotency_key": f"w9:{item['category_code']}"})
        assert retry.status_code == 200 and retry.json()["intent"]["id"] == intent.json()["intent"]["id"]
    observed = [{"category_code": x["category_code"], "files": [{"filename": x["intended_portal_filename"], "size": x["file_size_bytes"], "document_version_id": x["document_version_id"]}]} for x in ready]
    captured = client.post(f"/api/preparation-revisions/{revision_id}/attachments/capture-state", json={"phase": "REOPENED", "attachment_state": observed})
    assert captured.status_code == 200
    reconciled = client.post(f"/api/preparation-revisions/{revision_id}/attachments/reconcile", json={"portal_snapshot_id": captured.json()["snapshot"]["id"]})
    assert reconciled.status_code == 200, reconciled.text
    assert reconciled.json()["status"] == "MATCH"
    assert all(x["result"] == "PERSISTED_MATCH" for x in client.get(f"/api/preparation-revisions/{revision_id}/attachments/persistence").json()["evidence"])


def test_attachment_wrong_category_missing_and_structure_drift_are_explicit(client):
    revision_id = viable_revision(); manifest = client.get(f"/api/preparation-revisions/{revision_id}/attachment-manifest").json(); item = next(x for x in manifest["items"] if x["status"] == "READY")
    wrong = client.post(f"/api/preparation-revisions/{revision_id}/attachments/associate", json={"category_code": item["category_code"], "document_version_id": item["document_version_id"], "idempotency_key": "w9-wrong-category"})
    assert wrong.status_code == 200
    state = [{"category_code": "OTHER_APPROVALS", "files": [{"filename": item["intended_portal_filename"], "size": item["file_size_bytes"], "document_version_id": item["document_version_id"]}]}]
    captured = client.post(f"/api/preparation-revisions/{revision_id}/attachments/capture-state", json={"attachment_state": state}).json()
    mismatch = client.post(f"/api/preparation-revisions/{revision_id}/attachments/reconcile", json={"portal_snapshot_id": captured["snapshot"]["id"]})
    assert mismatch.status_code == 200 and any(x["status"] == "WRONG_CATEGORY" for x in mismatch.json()["results"])
    drift = client.post(f"/api/preparation-revisions/{revision_id}/portal-structure-fingerprint/capture", json={"scope": "ATTACHMENT_TREE", "observed_structure": {"categories": [{"code": "UNSIGNED_NEW_CATEGORY"}]}})
    assert drift.status_code == 200 and drift.json()["fingerprint"]["status"] == "DRIFTED" and drift.json()["assisted_fallback"] is True


def test_grid_identity_reorder_missing_duplicate_parent_and_persistence(client):
    revision_id = viable_revision(); intents = client.get(f"/api/preparation-revisions/{revision_id}/grids/BUILDING_FLOOR_UNIT/intent").json()["intents"]
    assert intents and all(x["canonical_row_id"] and x["business_key"] for x in intents)
    observed = [{"portal_row_id": f"portal-{x['canonical_row_id']}", "business_key": x["business_key"], "observed_values": x["target_values"]} for x in reversed(intents)]
    captured = client.post(f"/api/preparation-revisions/{revision_id}/grids/BUILDING_FLOOR_UNIT/capture", json={"observed_rows": observed})
    assert captured.status_code == 200, captured.text
    matched = client.post(f"/api/preparation-revisions/{revision_id}/grids/BUILDING_FLOOR_UNIT/reconcile", json={"portal_snapshot_id": captured.json()["snapshot"]["id"]})
    assert matched.status_code == 200 and matched.json()["run"]["result"] == "MATCH"
    missing = client.post(f"/api/preparation-revisions/{revision_id}/grids/BUILDING_FLOOR_UNIT/capture", json={"observed_rows": observed[:-1]}).json()
    missing_result = client.post(f"/api/preparation-revisions/{revision_id}/grids/BUILDING_FLOOR_UNIT/reconcile", json={"portal_snapshot_id": missing["snapshot"]["id"]}).json()
    assert any(x["status"] == "MISSING" for x in missing_result["results"])
    duplicate_rows = observed + [observed[0]]
    duplicate = client.post(f"/api/preparation-revisions/{revision_id}/grids/BUILDING_FLOOR_UNIT/capture", json={"observed_rows": duplicate_rows}).json()
    duplicate_result = client.post(f"/api/preparation-revisions/{revision_id}/grids/BUILDING_FLOOR_UNIT/reconcile", json={"portal_snapshot_id": duplicate["snapshot"]["id"]}).json()
    assert any(x["status"] == "DUPLICATE_KEY" for x in duplicate_result["results"])
    parent = next((x for x in observed if x["observed_values"].get("building_ref") and x["business_key"] != x["observed_values"].get("building_ref")), None)
    if parent:
        parent["observed_values"]["building_ref"] = "wrong-building"
        parent_snapshot = client.post(f"/api/preparation-revisions/{revision_id}/grids/BUILDING_FLOOR_UNIT/capture", json={"observed_rows": observed}).json()
        parent_result = client.post(f"/api/preparation-revisions/{revision_id}/grids/BUILDING_FLOOR_UNIT/reconcile", json={"portal_snapshot_id": parent_snapshot["snapshot"]["id"]}).json()
        assert any(x["status"] == "PARENT_MISMATCH" for x in parent_result["results"])


def test_portal_derived_value_never_overwrites_office_truth_and_report(client):
    revision_id = viable_revision()
    result = client.post(f"/api/preparation-revisions/{revision_id}/portal-derived-fields/reconcile", json={"portal_field_code": "GIS_AREA", "semantic_field_code": "PROPERTY.LAND_AREA", "purpose": "PORTAL_DERIVED", "source_mode": "PORTAL_DERIVED", "expected_office_value": 250, "observed_portal_value": 252, "evidence": ["synthetic://gis/1"]})
    assert result.status_code == 200
    assert result.json()["reconciliation"]["result"] == "LEGITIMATE_SOURCE_DIFFERENCE"
    assert result.json()["canonical_overwrite"] is False
    report = client.get("/api/week9/report")
    assert report.status_code == 200 and report.json()["label"].startswith("DEMONSTRATION BASELINE")
