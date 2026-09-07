"""Step 3 proofs for shared deterministic consumer selection and binding."""

from __future__ import annotations

import json
from uuid import uuid4

from sqlalchemy import select

from backend.app.db import SessionLocal
from backend.app.models import DocumentVersion, MasterContentItem, Opportunity
from backend.app.services.master_content import canonical_master_content_candidates
from backend.app.services.proposal_workspace import engineering_references_for_proposal


OWNER = {"X-Dev-Role": "SYSTEM_ADMIN"}
BD = {"X-Dev-Role": "PROCESS_CHAMPION"}


def _engineering(client, *, needs_review: bool = False):
    ref = f"STEP3-E-{uuid4().hex[:8]}"
    response = client.post(
        "/api/master-content",
        data={
            "content_type": "ENGINEERING_WORK",
            "ref": ref,
            "title": f"Step 3 engineering source {ref}",
            "description": "Synthetic Step 3 consumer source",
            "used_in": json.dumps(["ENGINEERING"]),
            "source_type_code": "QCS",
            "engineering_metadata": json.dumps({"discipline": "STRUCTURAL"}),
            "needs_review": str(needs_review).lower(),
        },
        files={"file": (f"{ref}.txt", b"step 3 engineering source", "text/plain")},
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
    return item


def test_engineering_proposal_consumer_uses_shared_exact_current_resolver(client):
    item = _engineering(client)
    with SessionLocal() as db:
        candidates = canonical_master_content_candidates(db, module="ENGINEERING", usage_type="AVAILABLE", content_type="ENGINEERING_WORK")
        candidate = next(row for row in candidates if row["id"] == item["id"])
        projection = engineering_references_for_proposal(db, Opportunity(status="PROPOSAL_PREPARATION"))
    reference = next(row for row in projection["items"] if row["id"] == item["id"])
    assert reference["version_id"] == candidate["version_id"] == item["current_version_id"]
    assert reference["hash"] == candidate["hash"]
    assert reference["source_type"] == "QCS"
    assert reference["discipline"] == "STRUCTURAL"


def test_shared_resolver_excludes_review_inactive_superseded_and_ambiguous_sources(client):
    needs_review = _engineering(client, needs_review=True)
    inactive = _engineering(client)
    assert client.post(f"/api/master-content/{inactive['id']}/archive", headers=OWNER).status_code == 200
    pending = _engineering(client)
    with SessionLocal() as db:
        version = db.get(DocumentVersion, pending["current_version_id"])
        version.metadata_json = {**version.metadata_json, "master_status": "SUPERSEDED"}
        version.approval_state = "SUPERSEDED"
        db.commit()
        candidates = canonical_master_content_candidates(db, module="ENGINEERING", usage_type="AVAILABLE", content_type="ENGINEERING_WORK")
    ids = {row["id"] for row in candidates}
    assert needs_review["id"] not in ids
    assert inactive["id"] not in ids
    assert pending["id"] not in ids

    first = _engineering(client)
    second = _engineering(client)
    resolved = client.get("/api/master-content/resolvers/ENGINEERING/AVAILABLE", headers=OWNER)
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "AMBIGUOUS"
    assert {first["id"], second["id"]}.issubset({row["id"] for row in resolved.json()["candidates"]})


def test_master_content_consumer_authorization_and_exact_form_binding_fail_closed(client):
    denied = client.get("/api/master-content/resolvers/ENGINEERING/AVAILABLE", headers=BD)
    assert denied.status_code == 403

    wrong_type = client.post(
        "/api/master-content",
        data={"content_type": "REPORT", "ref": f"STEP3-R-{uuid4().hex[:8]}", "title": "Step 3 wrong purpose type", "used_in": '["BD"]'},
        files={"file": ("report.txt", b"report", "text/plain")},
        headers=OWNER,
    )
    assert wrong_type.status_code == 200, wrong_type.text
    assert client.put(
        f"/api/master-content/{wrong_type.json()['id']}/module-bindings",
        json=[{"module": "BD", "usage_type": "PROPOSAL_TEMPLATE"}],
        headers=OWNER,
    ).status_code == 200
    proposal_resolution = client.get("/api/master-content/resolvers/BD/PROPOSAL_TEMPLATE", headers=OWNER)
    assert proposal_resolution.status_code == 200
    assert wrong_type.json()["id"] not in {row["id"] for row in proposal_resolution.json()["candidates"]}

    form_one = client.post(
        "/api/master-content",
        data={"content_type": "FORM", "ref": f"STEP3-F-{uuid4().hex[:8]}", "title": "Step 3 form one", "used_in": '["BD"]'},
        files={"file": ("form-one.txt", b"form one", "text/plain")},
        headers=OWNER,
    )
    form_two = client.post(
        "/api/master-content",
        data={"content_type": "FORM", "ref": f"STEP3-F-{uuid4().hex[:8]}", "title": "Step 3 form two", "used_in": '["BD"]'},
        files={"file": ("form-two.txt", b"form two", "text/plain")},
        headers=OWNER,
    )
    assert form_one.status_code == form_two.status_code == 200
    one, two = form_one.json(), form_two.json()
    profile = client.post(
        "/api/form-automation/profiles",
        json={"master_content_item_id": one["id"], "source_document_version_id": one["current_version_id"], "renderer_type": "SYNTHETIC_JSON"},
        headers=OWNER,
    )
    assert profile.status_code == 200, profile.text
    mismatch = client.post(
        "/api/form-automation/instances",
        json={"profile_id": profile.json()["id"], "master_content_item_id": two["id"], "source_document_version_id": one["current_version_id"], "context_type": "SYNTHETIC", "context_id": str(uuid4())},
        headers=OWNER,
    )
    assert mismatch.status_code == 409
    assert mismatch.json()["detail"]["code"] == "FORM_INSTANCE_MASTER_CONTENT_MISMATCH"
