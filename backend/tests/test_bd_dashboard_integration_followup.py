"""Dashboard -> BD canonical consumption and boundary contracts."""

from uuid import uuid4

from sqlalchemy import select

from backend.app.db import SessionLocal
from backend.app.models import MasterContentItem, MasterContentModuleBinding


OWNER = {"X-Dev-Role": "SYSTEM_ADMIN"}
BD = {"X-Dev-Role": "PROCESS_CHAMPION"}


def test_proposal_configuration_consumes_dashboard_truth_without_duplicate_write(client):
    created = client.post(
        "/api/bd/proposals",
        json={"proposal_description": "Synthetic Dashboard seam Proposal", "client_name": "Synthetic Dashboard Client"},
        headers=BD,
    )
    assert created.status_code == 200, created.text
    proposal_id = created.json()["id"]

    detail = client.get(f"/api/bd/proposals/{proposal_id}", headers=BD)
    assert detail.status_code == 200, detail.text
    configuration = detail.json()["configuration"]
    assert configuration["proposal_template"]["managed_in"] == "/dashboard"
    assert configuration["proposal_checklist"]["managed_in"] == "/dashboard"
    assert configuration["definitions"]["truth"] == "DASHBOARD_DEFINITION_SEMANTIC_ONLY"
    assert configuration["engineering_references"]["status"] == "DEFERRED"

    direct_write = client.post(
        "/api/master-content",
        data={"content_type": "FORM", "ref": f"BD-DENIED-{uuid4().hex[:8]}", "title": "BD must not create global master", "used_in": '["BD"]'},
        files={"file": ("denied.txt", b"synthetic", "text/plain")},
        headers=BD,
    )
    assert direct_write.status_code == 403


def test_purpose_binding_and_applicability_are_not_name_based(client):
    ref = f"PERMIT-LIKE-{uuid4().hex[:8]}"
    created = client.post(
        "/api/master-content",
        data={"content_type": "FORM", "ref": ref, "title": "Proposal Template sounding Permit Form", "used_in": '["PERMIT"]'},
        files={"file": (f"{ref}.txt", b"permit-only synthetic", "text/plain")},
        headers=OWNER,
    )
    assert created.status_code == 200, created.text
    item = created.json()
    binding = client.put(
        f"/api/master-content/{item['id']}/module-bindings",
        json=[{"module": "PERMIT", "usage_type": "AVAILABLE"}],
        headers=OWNER,
    )
    assert binding.status_code == 200, binding.text
    resolved = client.get("/api/master-content/resolvers/BD/PROPOSAL_TEMPLATE", headers=BD)
    assert resolved.status_code == 200
    assert item["id"] not in {row["id"] for row in resolved.json()["candidates"]}


def test_engineering_references_are_deferred_until_preparation(client):
    created = client.post(
        "/api/bd/proposals",
        json={"proposal_description": "Synthetic Engineering reference Proposal", "client_name": "Synthetic Engineering Client"},
        headers=BD,
    )
    assert created.status_code == 200
    detail = client.get(f"/api/bd/proposals/{created.json()['id']}", headers=BD)
    assert detail.json()["configuration"]["engineering_references"]["status"] == "DEFERRED"


def test_template_and_checklist_resolve_exact_dashboard_identity_and_version(client):
    resolved_items = {}
    prior_statuses = {}
    with SessionLocal() as db:
        existing = db.scalars(
            select(MasterContentItem)
            .join(MasterContentModuleBinding, MasterContentModuleBinding.master_content_id == MasterContentItem.id)
            .where(
                MasterContentModuleBinding.module == "BD",
                MasterContentModuleBinding.usage_type.in_(["PROPOSAL_TEMPLATE", "PROPOSAL_CHECKLIST"]),
                MasterContentModuleBinding.active.is_(True),
            )
        ).all()
        prior_statuses = {row.id: row.status for row in existing}
        for row in existing:
            row.status = "ARCHIVED"
        db.commit()
    for purpose, title in (("PROPOSAL_TEMPLATE", "Synthetic canonical Proposal Template"), ("PROPOSAL_CHECKLIST", "Synthetic canonical Proposal Checklist")):
        ref = f"BD-{purpose}-{uuid4().hex[:8]}"
        created = client.post(
            "/api/master-content",
            data={"content_type": "FORM", "ref": ref, "title": title, "description": title, "used_in": '["BD"]'},
            files={"file": (f"{ref}.txt", b"canonical synthetic master", "text/plain")},
            headers=OWNER,
        )
        assert created.status_code == 200, created.text
        item = created.json()
        governed = client.patch(
            f"/api/master-content/{item['id']}/governance",
            json={"content_ownership_class": "AMEC_OWNED", "artifact_kind": "AMEC_FORM", "language_profile": "EN"},
            headers=OWNER,
        )
        assert governed.status_code == 200, governed.text
        bound = client.put(
            f"/api/master-content/{item['id']}/module-bindings",
            json=[{"module": "BD", "usage_type": purpose}],
            headers=OWNER,
        )
        assert bound.status_code == 200, bound.text
        resolved_items[purpose] = item

    proposal = client.post(
        "/api/bd/proposals",
        json={"proposal_description": "Exact canonical resolver Proposal", "client_name": "Synthetic Resolver Client"},
        headers=BD,
    )
    assert proposal.status_code == 200
    try:
        configuration = client.get(f"/api/bd/proposals/{proposal.json()['id']}/configuration", headers=BD)
        assert configuration.status_code == 200, configuration.text
        payload = configuration.json()
        assert payload["proposal_template"]["master_content_id"] == resolved_items["PROPOSAL_TEMPLATE"]["id"]
        assert payload["proposal_template"]["document_version_id"] == resolved_items["PROPOSAL_TEMPLATE"]["current_version_id"]
        assert payload["proposal_checklist"]["master_content_id"] == resolved_items["PROPOSAL_CHECKLIST"]["id"]
        assert payload["proposal_checklist"]["document_version_id"] == resolved_items["PROPOSAL_CHECKLIST"]["current_version_id"]
    finally:
        with SessionLocal() as db:
            for item_id in resolved_items.values():
                row = db.get(MasterContentItem, item_id["id"])
                if row:
                    row.status = "ARCHIVED"
            for item_id, status in prior_statuses.items():
                row = db.get(MasterContentItem, item_id)
                if row:
                    row.status = status
            db.commit()
