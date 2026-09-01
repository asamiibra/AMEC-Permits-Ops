from __future__ import annotations

import hashlib
import io
import json
import zipfile
from uuid import uuid4

from sqlalchemy import delete, select

from backend.app.db import SessionLocal
from backend.app.models import ContentCategory, MasterContentItem, MasterContentReferenceSequence
from backend.app.services.source_intake import SourceIntakeService

OWNER = {"X-Dev-Role": "OWNER_SPONSOR"}


def _category() -> tuple[str, str]:
    row = ContentCategory(code=f"STEP2_{uuid4().hex[:8]}", label=f"Step 2 category {uuid4().hex[:4]}", allowed_content_types=["FORM"], sort_order=999, source_kind="TEST")
    with SessionLocal() as db:
        db.add(row)
        db.commit()
        return row.id, row.label


def _form(client, *, category_id: str, title: str, used_in: list[str], needs_review: bool = False):
    response = client.post(
        "/api/master-content",
        data={
            "content_type": "FORM",
            "ref": f"STEP2-{uuid4().hex[:8]}",
            "title": title,
            "description": "Step 2 canonical read fixture",
            "category_id": category_id,
            "used_in": json.dumps(used_in),
            "needs_review": str(needs_review).lower(),
        },
        files={"file": ("step2.txt", b"step 2 canonical fixture", "text/plain")},
        headers={**OWNER, "Idempotency-Key": str(uuid4())},
    )
    assert response.status_code == 200, response.text
    return response.json()


def _governance(client, item_id: str, **values):
    response = client.patch(f"/api/master-content/{item_id}/governance", json=values, headers=OWNER)
    assert response.status_code == 200, response.text


def test_canonical_and_v2_reads_keep_all_filters_composable(client):
    category_id, category_label = _category()
    item = _form(client, category_id=category_id, title="Step 2 authority service form", used_in=["BD"])
    _governance(client, item["id"], content_ownership_class="EXTERNAL_OFFICIAL", artifact_kind="AUTHORITY_FORM", language_profile="EN", publisher_name="Step 2 Authority")
    suffix = uuid4().hex[:8]
    jurisdiction = client.post("/api/regulatory/jurisdictions", json={"code": f"STEP2-J-{suffix}", "country_code": "ZZ", "name_en": "Step 2 Locality", "level": "LOCALITY"}, headers=OWNER).json()["id"]
    body = client.post("/api/regulatory/external-bodies", json={"code": f"STEP2-B-{suffix}", "name_en": "Step 2 Authority", "body_type": "AUTHORITY", "jurisdiction_id": jurisdiction, "verification_state": "SYNTHETIC_UNVERIFIED"}, headers=OWNER).json()["id"]
    service = client.post("/api/regulatory/service-types", json={"code": f"STEP2-S-{suffix}", "name_en": "Step 2 Service", "description": "Step 2 governance fixture"}, headers=OWNER).json()["id"]
    phase = client.post("/api/regulatory/lifecycle-phases", json={"code": f"STEP2-P-{suffix}", "name_en": "Step 2 Application", "sort_order": 30}, headers=OWNER).json()["id"]
    applicability = client.post("/api/dashboard-v2/applicability", json={"master_content_item_id": item["id"], "source_document_version_id": item["current_version_id"], "external_body_id": body, "jurisdiction_id": jurisdiction, "service_type_id": service, "lifecycle_phase_id": phase, "status": "ACTIVE"}, headers=OWNER)
    assert applicability.status_code == 200, applicability.text

    params = {"content_type": "FORM", "category_label": category_label, "owner_status": "CURRENT", "module": "BD", "ownership": "EXTERNAL_OFFICIAL", "artifact_kind": "AUTHORITY_FORM", "publisher": "authority", "language": "EN", "external_body_id": body, "jurisdiction_id": jurisdiction, "service_type_id": service, "lifecycle_phase_id": phase, "applicability_status": "ACTIVE"}
    canonical = client.get("/api/master-content", params=params, headers=OWNER)
    v2 = client.get("/api/dashboard-v2/forms", params={key: value for key, value in params.items() if key != "content_type"}, headers=OWNER)
    assert canonical.status_code == 200, canonical.text
    assert v2.status_code == 200, v2.text
    assert [row["id"] for row in canonical.json()] == [item["id"]]
    assert [row["id"] for row in v2.json()] == [item["id"]]
    assert canonical.json()[0]["current_version_id"] == v2.json()[0]["current_version_id"] == item["current_version_id"]

    filter_combinations = [
        {"q": "authority", "category_label": category_label, "owner_status": "CURRENT"},
        {"owner_status": "CURRENT", "module": "BD"},
        {"ownership": "EXTERNAL_OFFICIAL", "currentness": "UNVERIFIED", "quality_state": "OPEN"},
        {"external_body_id": body, "service_type_id": service},
        {"external_body_id": body, "jurisdiction_id": jurisdiction, "lifecycle_phase_id": phase},
        {"applicability_status": "ACTIVE", "automation_readiness": "BLOCKED"},
        {"q": "authority", "category_label": category_label, "applicability_status": "ACTIVE"},
        {"module": "BD", "ownership": "EXTERNAL_OFFICIAL", "applicability_status": "ACTIVE"},
        {"owner_status": "NEEDS_REVIEW", "applicability_status": "ACTIVE"},
        {"owner_status": "INACTIVE", "external_body_id": body},
    ]
    for combination in filter_combinations:
        canonical_combo = client.get("/api/master-content", params={"content_type": "FORM", **combination}, headers=OWNER)
        v2_combo = client.get("/api/dashboard-v2/forms", params=combination, headers=OWNER)
        assert canonical_combo.status_code == v2_combo.status_code == 200
        assert [row["id"] for row in canonical_combo.json()] == [row["id"] for row in v2_combo.json()]

    canonical_catalogs = client.get("/api/master-content/catalogs", headers=OWNER)
    v2_catalogs = client.get("/api/dashboard-v2/catalogs", headers=OWNER)
    assert canonical_catalogs.status_code == v2_catalogs.status_code == 200
    assert canonical_catalogs.json() == v2_catalogs.json()


def test_owner_status_filters_preserve_inactive_discoverability_and_history(client):
    category_id, category_label = _category()
    needs_review = _form(client, category_id=category_id, title="Step 2 needs review", used_in=["BD"], needs_review=True)
    current = client.get("/api/master-content", params={"content_type": "FORM", "owner_status": "NEEDS_REVIEW", "category_label": category_label, "module": "BD"}, headers=OWNER)
    assert any(row["id"] == needs_review["id"] for row in current.json())

    inactive = _form(client, category_id=category_id, title="Step 2 inactive", used_in=["BD"])
    archived = client.post(f"/api/master-content/{inactive['id']}/archive", headers=OWNER)
    assert archived.status_code == 200, archived.text
    inactive_rows = client.get("/api/master-content", params={"content_type": "FORM", "owner_status": "INACTIVE", "category_label": category_label, "module": "BD"}, headers=OWNER)
    assert [row["id"] for row in inactive_rows.json()] == [inactive["id"]]

    detail = client.get(f"/api/master-content/{needs_review['id']}", headers=OWNER)
    v2_detail = client.get(f"/api/dashboard-v2/forms/{needs_review['id']}", headers=OWNER)
    assert detail.status_code == v2_detail.status_code == 200
    assert detail.json()["id"] == v2_detail.json()["id"] == needs_review["id"]
    assert detail.json()["current_version_id"] == v2_detail.json()["current_version_id"]
    assert [version["id"] for version in detail.json()["versions"]] == [version["id"] for version in v2_detail.json()["versions"]]


def test_promoted_source_intake_is_visible_in_owner_discovery_but_transactional_source_is_not(client):
    promoted_bytes = b"promoted source intake form"
    historical_bytes = b"transactional history source"
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as zipped:
        zipped.writestr("FORME/Promoted Intake Form.pdf", promoted_bytes)
        zipped.writestr("FORME/Project History.pdf", historical_bytes)
    payload = archive.getvalue()
    digest = hashlib.sha256(payload).hexdigest()
    with SessionLocal() as db:
        original_sequences = {
            row.content_type: row.current_value
            for row in db.scalars(select(MasterContentReferenceSequence).where(MasterContentReferenceSequence.scope == "GLOBAL")).all()
        }
    manifest = {"version": "step2", "items": [
        {"relative_path": "Promoted Intake Form.pdf", "sha256": hashlib.sha256(promoted_bytes).hexdigest(), "v1_4_disposition": "PROMOTE_MASTER_CURRENT", "dashboard_mapping": "Forms"},
        {"relative_path": "Project History.pdf", "sha256": hashlib.sha256(historical_bytes).hexdigest(), "v1_4_disposition": "TRANSACTIONAL_OR_HISTORICAL_SOURCE"},
    ]}
    with SessionLocal() as db:
        service = SourceIntakeService(db)
        batch = service.ingest_zip(payload, source_display_name="step2-source.zip", source_location_reference=f"test://{uuid4()}")
        counts = service.promote_batch(batch, payload, manifest)
        assert counts["PROMOTE_MASTER_CURRENT"] == 1
        assert counts["TRANSACTIONAL_OR_HISTORICAL_SOURCE"] == 1
        promoted = db.scalar(select(MasterContentItem).where(MasterContentItem.title == "Promoted Intake Form"))
        assert promoted is not None
        assert db.scalar(select(MasterContentItem).where(MasterContentItem.title == "Project History")) is None
        promoted_id = promoted.id

    dashboard_rows = client.get("/api/master-content", params={"content_type": "FORM", "q": "Promoted Intake Form"}, headers=OWNER)
    assert dashboard_rows.status_code == 200, dashboard_rows.text
    assert [row["id"] for row in dashboard_rows.json()] == [promoted_id]
    governed_rows = client.get("/api/retrieval/query", params={"query": "Promoted Intake Form", "limit": 8}, headers=OWNER)
    assert governed_rows.status_code == 200, governed_rows.text
    assert any(row["envelope"]["canonical_entity_id"] == promoted_id for row in governed_rows.json())

    # This test exercises real promotion and therefore allocates a canonical
    # F-reference. Remove only the synthetic row before the shared test DB is
    # reused by the repository's exact reference-numbering assertion.
    with SessionLocal() as db:
        db.execute(delete(MasterContentItem).where(MasterContentItem.id == promoted_id))
        if original_sequences:
            db.execute(delete(MasterContentReferenceSequence).where(MasterContentReferenceSequence.scope == "GLOBAL", MasterContentReferenceSequence.content_type.not_in(original_sequences)))
            for content_type, current_value in original_sequences.items():
                sequence = db.scalar(select(MasterContentReferenceSequence).where(MasterContentReferenceSequence.content_type == content_type, MasterContentReferenceSequence.scope == "GLOBAL"))
                if sequence:
                    sequence.current_value = current_value
        else:
            db.execute(delete(MasterContentReferenceSequence).where(MasterContentReferenceSequence.scope == "GLOBAL"))
        db.commit()
        assert db.scalar(select(MasterContentItem).where(MasterContentItem.id == promoted_id)) is None
