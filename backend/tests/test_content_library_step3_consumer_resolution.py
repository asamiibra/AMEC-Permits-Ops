"""Step 3 proofs for deterministic consumer resolution and exact lineage."""

from __future__ import annotations

import json
from uuid import uuid4

import pytest
from sqlalchemy import select

from backend.app.db import SessionLocal
from backend.app.models import DocumentVersion, MasterContentItem, MasterContentReferenceSequence, Opportunity
from backend.app.services.master_content import canonical_master_content_candidates
from backend.app.services.proposal_final_hardening import master_content_fingerprint
from backend.app.services.proposal_workspace import engineering_references_for_proposal


OWNER = {"X-Dev-Role": "SYSTEM_ADMIN"}
BD = {"X-Dev-Role": "PROCESS_CHAMPION"}


@pytest.fixture(autouse=True)
def isolate_step3_synthetic_state():
    with SessionLocal() as db:
        sequence_snapshot = {row.id: row.current_value for row in db.scalars(select(MasterContentReferenceSequence)).all()}
        sequence_ids = set(sequence_snapshot)
    yield
    with SessionLocal() as db:
        for item in db.scalars(select(MasterContentItem).where(MasterContentItem.ref.like("STEP3-%"))).all():
            item.status = "ARCHIVED"
        for row in db.scalars(select(MasterContentReferenceSequence)).all():
            if row.id in sequence_snapshot:
                row.current_value = sequence_snapshot[row.id]
            elif row.id not in sequence_ids:
                db.delete(row)
        db.commit()


def _master(client, content_type: str = "ENGINEERING_WORK", *, needs_review: bool = False, module: str = "ENGINEERING", purpose: str = "AVAILABLE"):
    ref = f"STEP3-{content_type[:1]}-{uuid4().hex[:8]}"
    response = client.post(
        "/api/master-content",
        data={
            "content_type": content_type,
            "ref": ref,
            "title": f"Step 3 source {ref}",
            "description": "Synthetic Step 3 consumer source",
            "used_in": json.dumps([module]),
            "source_type_code": "QCS",
            "engineering_metadata": json.dumps({"discipline": "STRUCTURAL"}),
            "needs_review": str(needs_review).lower(),
        },
        files={"file": (f"{ref}.txt", b"step 3 source", "text/plain")},
        headers=OWNER,
    )
    assert response.status_code == 200, response.text
    item = response.json()
    governed = client.patch(
        f"/api/master-content/{item['id']}/governance",
        json={"content_ownership_class": "AMEC_OWNED", "artifact_kind": "TECHNICAL_WORKSHEET", "language_profile": "EN"},
        headers=OWNER,
    )
    assert governed.status_code == 200, governed.text
    provenance = client.post(
        f"/api/master-content/{item['id']}/provenance",
        json={"obtained_from": "Synthetic Step 3 fixture"},
        headers=OWNER,
    )
    assert provenance.status_code == 200, provenance.text
    bound = client.put(
        f"/api/master-content/{item['id']}/module-bindings",
        json=[{"module": module, "usage_type": purpose}],
        headers=OWNER,
    )
    assert bound.status_code == 200, bound.text
    return item


def test_shared_resolver_is_exact_current_and_fail_closed_for_eligibility(client):
    eligible = _master(client)
    needs_review = _master(client, needs_review=True)
    inactive = _master(client)
    assert client.post(f"/api/master-content/{inactive['id']}/archive", headers=OWNER).status_code == 200
    superseded = _master(client)
    with SessionLocal() as db:
        version = db.get(DocumentVersion, superseded["current_version_id"])
        version.metadata_json = {**version.metadata_json, "master_status": "SUPERSEDED"}
        version.approval_state = "SUPERSEDED"
        db.commit()
        rows = canonical_master_content_candidates(db, module="ENGINEERING", usage_type="AVAILABLE", content_type="ENGINEERING_WORK")
        projection = engineering_references_for_proposal(db, Opportunity(status="PROPOSAL_PREPARATION"))
    ids = {row["id"] for row in rows}
    assert eligible["id"] in ids
    assert needs_review["id"] not in ids
    assert inactive["id"] not in ids
    assert superseded["id"] not in ids
    reference = next(row for row in projection["items"] if row["id"] == eligible["id"])
    selected = next(row for row in rows if row["id"] == eligible["id"])
    assert reference["version_id"] == selected["version_id"] == eligible["current_version_id"]
    assert reference["hash"] == selected["hash"]


def test_ambiguous_and_wrong_purpose_never_auto_select(client):
    first = _master(client)
    second = _master(client)
    resolved = client.get("/api/master-content/resolvers/ENGINEERING/AVAILABLE", headers=OWNER)
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "AMBIGUOUS"
    assert resolved.json()["item"] is None
    assert {first["id"], second["id"]}.issubset({row["id"] for row in resolved.json()["candidates"]})

    wrong_purpose = _master(client, module="PERMIT", purpose="AVAILABLE")
    proposal_resolution = client.get("/api/master-content/resolvers/BD/PROPOSAL_TEMPLATE", headers=OWNER)
    assert proposal_resolution.status_code == 200
    assert wrong_purpose["id"] not in {row["id"] for row in proposal_resolution.json()["candidates"]}


def test_consumer_access_and_arbitrary_version_injection_fail_closed(client):
    denied = client.get("/api/master-content/resolvers/ENGINEERING/AVAILABLE", headers=BD)
    assert denied.status_code == 403

    first = _master(client, content_type="FORM", module="BD", purpose="AVAILABLE")
    second = _master(client, content_type="FORM", module="BD", purpose="AVAILABLE")
    profile = client.post(
        "/api/form-automation/profiles",
        json={"master_content_item_id": first["id"], "source_document_version_id": first["current_version_id"], "renderer_type": "SYNTHETIC_JSON"},
        headers=OWNER,
    )
    assert profile.status_code == 200, profile.text
    mismatch = client.post(
        "/api/form-automation/instances",
        json={"profile_id": profile.json()["id"], "master_content_item_id": second["id"], "source_document_version_id": first["current_version_id"], "context_type": "SYNTHETIC", "context_id": str(uuid4())},
        headers=OWNER,
    )
    assert mismatch.status_code == 409
    assert mismatch.json()["detail"]["code"] == "FORM_INSTANCE_MASTER_CONTENT_MISMATCH"
    arbitrary_version = client.post(
        "/api/form-automation/instances",
        json={"profile_id": profile.json()["id"], "master_content_item_id": first["id"], "source_document_version_id": second["current_version_id"], "context_type": "SYNTHETIC", "context_id": str(uuid4())},
        headers=OWNER,
    )
    assert arbitrary_version.status_code == 409
    assert arbitrary_version.json()["detail"]["code"] == "FORM_INSTANCE_SOURCE_VERSION_MISMATCH"


def test_proposal_master_fingerprint_changes_on_new_canonical_version_without_rewriting_history(client):
    before = _master(client, content_type="FORM", module="BD", purpose="PROPOSAL_TEMPLATE")
    with SessionLocal() as db:
        first_fingerprint = master_content_fingerprint(db)
        item = db.get(MasterContentItem, before["id"])
        item.status = "ARCHIVED"
        db.commit()
    after = _master(client, content_type="FORM", module="BD", purpose="PROPOSAL_TEMPLATE")
    with SessionLocal() as db:
        second_fingerprint = master_content_fingerprint(db)
    assert first_fingerprint != second_fingerprint
    assert before["id"] != after["id"]
