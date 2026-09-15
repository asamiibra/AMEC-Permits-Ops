"""Focused R2 coverage for the bounded pre-finalization template capture."""

import pytest
from sqlalchemy import select

from backend.app.db import SessionLocal
from backend.app.models import (
    ContractTemplateSnapshot,
    DocumentApprovalState,
    Document,
    DocumentVersion,
    MasterContentGovernanceProfile,
    MasterContentItem,
    MasterContentModuleBinding,
)

from backend.tests.test_admin_contract_owner_session import ensure_contract_template, headers, make_accepted_proposal, record_authority, record_checker


@pytest.fixture(autouse=True)
def isolate_step5_contract_template_resolver():
    """Restore the synthetic resolver boundary before each Step5 test.

    The release lane intentionally uses one session-scoped TEST database. A
    preceding test may archive or deactivate the synthetic CT-TEST fixture;
    that is test-state contamination, not a valid Contract resolver state for
    this module. The product resolver remains fail-closed for real ambiguity.
    """
    with SessionLocal() as db:
        item = db.scalar(select(MasterContentItem).where(MasterContentItem.ref == "CT-TEST-001"))
        document = db.get(Document, item.document_id) if item is not None and item.document_id else None
        version = db.get(DocumentVersion, item.current_document_version_id) if item is not None and item.current_document_version_id else None
        valid_item = item is not None and document is not None and version is not None
        if valid_item:
            item.status = "ACTIVE"
            item.needs_review = False
            profile = db.scalar(select(MasterContentGovernanceProfile).where(MasterContentGovernanceProfile.master_content_item_id == item.id))
            if profile is not None:
                profile.content_ownership_class = "AMEC_OWNED"
                profile.restricted_reference_sample = False
            if version is not None:
                version.metadata_json = {**(version.metadata_json or {}), "master_status": "CURRENT"}
                version.approval_state = DocumentApprovalState.REVIEWED
                if not version.source_path_or_reference or version.source_path_or_reference == "PENDING":
                    version.source_path_or_reference = f"synthetic://{item.ref}"
        elif item is not None:
            item.status = "ARCHIVED"
            item.ref = f"CT-ORPHAN-{item.id[:8]}"
        if item is not None:
            for binding in db.scalars(select(MasterContentModuleBinding).where(MasterContentModuleBinding.master_content_id == item.id)).all():
                binding.active = valid_item and binding.module == "ADMIN" and binding.usage_type == "CONTRACT_TEMPLATE"
        for binding in db.scalars(select(MasterContentModuleBinding).where(MasterContentModuleBinding.module == "ADMIN", MasterContentModuleBinding.usage_type == "CONTRACT_TEMPLATE")).all():
            if not valid_item or binding.master_content_id != item.id:
                binding.active = False
        db.commit()
    yield


def _normalize_step5_contract_template():
    """Re-assert the synthetic fixture after API setup commits its state."""
    with SessionLocal() as db:
        item = db.scalar(select(MasterContentItem).where(MasterContentItem.ref == "CT-TEST-001"))
        assert item is not None
        item.status = "ACTIVE"
        item.needs_review = False
        profile = db.scalar(select(MasterContentGovernanceProfile).where(MasterContentGovernanceProfile.master_content_item_id == item.id))
        assert profile is not None
        profile.content_ownership_class = "AMEC_OWNED"
        profile.restricted_reference_sample = False
        version = db.get(DocumentVersion, item.current_document_version_id)
        assert version is not None
        version.metadata_json = {**(version.metadata_json or {}), "master_status": "CURRENT"}
        version.approval_state = DocumentApprovalState.REVIEWED
        version.source_path_or_reference = version.source_path_or_reference or f"synthetic://{item.ref}"
        for binding in db.scalars(select(MasterContentModuleBinding).where(MasterContentModuleBinding.module == "ADMIN", MasterContentModuleBinding.usage_type == "CONTRACT_TEMPLATE")).all():
            binding.active = binding.master_content_id == item.id
        db.commit()


def _retire_step5_legacy_proposal_probes(client):
    """Restore canonical proposal identities before creating this fixture.

    Earlier modules intentionally exercise archived, superseded, and invalid
    content rows.  Step 5 must enter through the same canonical BD resolver as
    production, so repair only this synthetic fixture boundary before calling
    the shared proposal helper.
    """
    with SessionLocal() as db:
        items = db.query(MasterContentItem).filter(MasterContentItem.ref.in_(["F-0003", "F-0004", "SYN-QUAL-PROPOSAL-TEMPLATE-V1", "SYN-QUAL-PROPOSAL-CHECKLIST-V1"])).all()
        for item in items:
            item.ref = f"ARCHIVED-{item.ref}-{item.id[:8]}"
            item.status = "ARCHIVED"
            for binding in db.scalars(select(MasterContentModuleBinding).where(MasterContentModuleBinding.master_content_id == item.id)).all():
                binding.active = False
        db.commit()
    for ref, title, usage in (("BD-PROP-001", "Canonical Proposal Template", "PROPOSAL_TEMPLATE"), ("BD-CHK-001", "Canonical Proposal Checklist", "PROPOSAL_CHECKLIST")):
        rows = client.get("/api/master-content", params={"q": ref, "include_archived": "true"}, headers=headers("SYSTEM_ADMIN"))
        assert rows.status_code == 200, rows.text
        item = None
        with SessionLocal() as db:
            # Earlier fixture repair may have renamed a canonical row before
            # archiving it.  Its immutable SOR artifact remains reusable; do
            # not recreate the same ref with different bytes and trip the SOR
            # version immutability guard.
            legacy_ref = "F-0003" if usage == "PROPOSAL_TEMPLATE" else "F-0004"
            seeded_ref = "SYN-QUAL-PROPOSAL-TEMPLATE-V1" if usage == "PROPOSAL_TEMPLATE" else "SYN-QUAL-PROPOSAL-CHECKLIST-V1"
            active_items = [
                current
                for current in db.scalars(select(MasterContentItem).where(MasterContentItem.content_type == "FORM")).all()
                if (
                    current.ref == ref
                    or current.ref.startswith(f"ARCHIVED-{ref}-")
                    or current.ref == legacy_ref
                    or current.ref.startswith(f"ARCHIVED-{legacy_ref}-")
                    or current.ref == seeded_ref
                    or current.ref.startswith(f"ARCHIVED-{seeded_ref}-")
                )
            ]
            valid_items = []
            for current in active_items:
                version = db.get(DocumentVersion, current.current_document_version_id) if current.current_document_version_id else None
                document = db.get(Document, current.document_id) if current.document_id else None
                valid = bool(version and document and document.current_version_id == version.id and version.source_path_or_reference and version.source_path_or_reference != "PENDING")
                if valid:
                    valid_items.append(current)
            keep = valid_items[0] if valid_items else None
            for current in active_items:
                if current is keep:
                    continue
                current.ref = f"STEP5-RETIRED-{current.id[:24]}"
            db.flush()
            for current in active_items:
                if current is keep:
                    continue
                current.status = "ARCHIVED"
                current.ref = f"ARCHIVED-{ref}-{current.id[:8]}"
                for binding in db.scalars(select(MasterContentModuleBinding).where(MasterContentModuleBinding.master_content_id == current.id)).all():
                    binding.active = False
            if keep:
                keep.ref = ref
                keep.status = "ACTIVE"
                keep.needs_review = False
                version = db.get(DocumentVersion, keep.current_document_version_id)
                document = db.get(Document, keep.document_id)
                version.approval_state = DocumentApprovalState.REVIEWED
                version.metadata_json = {**(version.metadata_json or {}), "master_status": "CURRENT"}
                document.current_version_id = version.id
            db.commit()
            if keep:
                item = {"id": keep.id, "ref": ref}
        if item is None:
            created = client.post("/api/master-content", data={"content_type": "FORM", "ref": ref, "title": title, "description": title, "used_in": '["BD"]'}, files={"file": (f"{ref}.txt", b"canonical proposal fixture", "text/plain")}, headers=headers("SYSTEM_ADMIN"))
            assert created.status_code == 200, created.text
            item = created.json()
        governed = client.patch(f"/api/master-content/{item['id']}/governance", json={"content_ownership_class": "AMEC_OWNED", "artifact_kind": "AMEC_FORM", "language_profile": "EN"}, headers=headers("SYSTEM_ADMIN"))
        assert governed.status_code == 200, governed.text
        bound = client.put(f"/api/master-content/{item['id']}/module-bindings", json=[{"module": "BD", "usage_type": usage}], headers=headers("SYSTEM_ADMIN"))
        assert bound.status_code == 200, bound.text
        resolved = client.get(f"/api/master-content/resolvers/BD/{usage}", headers=headers("SYSTEM_ADMIN"))
        assert resolved.status_code == 200 and resolved.json().get("status") == "RESOLVED", resolved.text


def test_owner_capture_is_exactly_once_and_non_owner_denied(client):
    ensure_contract_template(client)
    _normalize_step5_contract_template()
    _retire_step5_legacy_proposal_probes(client)
    proposal_id, _ = make_accepted_proposal(client, "Step5 Final R2 Snapshot Fixture")
    created = client.post("/api/admin/contracts/from-proposal/" + proposal_id, headers=headers("OWNER_SPONSOR"), json={})
    assert created.status_code == 200, created.text
    contract_id = created.json()["id"]

    with SessionLocal() as db:
        db.query(ContractTemplateSnapshot).filter(ContractTemplateSnapshot.contract_id == contract_id).delete(synchronize_session=False)
        db.commit()

    before = client.get("/api/admin/contracts/" + contract_id, headers=headers("OWNER_SPONSOR"))
    assert before.status_code == 200, before.text
    assert before.json()["template"] is None
    assert any(item["code"] == "CONTRACT_TEMPLATE_REQUIRED" for item in before.json()["readiness"]["blockers"])

    payload = {"reason": "Owner captured the current canonical Contract Template", "idempotency_key": "r2-capture:" + contract_id}
    captured = client.post("/api/admin/contracts/" + contract_id + "/template-snapshot", headers=headers("OWNER_SPONSOR"), json=payload)
    assert captured.status_code == 200, captured.text
    assert captured.json()["decision"] == "CAPTURED"
    assert captured.json()["captured"] is True
    assert captured.json()["snapshot"]["master_content_id"]
    assert captured.json()["snapshot"]["document_version_id"]
    assert captured.json()["snapshot"]["hash"]

    replay = client.post("/api/admin/contracts/" + contract_id + "/template-snapshot", headers=headers("OWNER_SPONSOR"), json=payload)
    assert replay.status_code == 200, replay.text
    assert replay.json()["decision"] == "ALREADY_CAPTURED"
    with SessionLocal() as db:
        assert db.query(ContractTemplateSnapshot).filter(ContractTemplateSnapshot.contract_id == contract_id).count() == 1

    for role in ("COMMERCIAL_APPROVER", "RESPONSIBLE_ENGINEER"):
        denied = client.post("/api/admin/contracts/" + contract_id + "/template-snapshot", headers=headers(role), json=payload)
        assert denied.status_code == 403


def test_finalized_contract_cannot_be_backfilled(client):
    ensure_contract_template(client)
    _normalize_step5_contract_template()
    _retire_step5_legacy_proposal_probes(client)
    proposal_id, _ = make_accepted_proposal(client, "Step5 Final R2 Finalized Fixture")
    created = client.post("/api/admin/contracts/from-proposal/" + proposal_id, headers=headers("OWNER_SPONSOR"), json={})
    assert created.status_code == 200, created.text
    contract_id = created.json()["id"]
    client.post("/api/admin/contracts/" + contract_id + "/template-snapshot", headers=headers("OWNER_SPONSOR"), json={"reason": "Owner captured the current canonical Contract Template", "idempotency_key": "r2-finalized-capture:" + contract_id})
    record_checker(client, contract_id)
    record_authority(client, contract_id)
    accepted = client.post("/api/admin/contracts/" + contract_id + "/accept", headers=headers("OWNER_SPONSOR"), json={"idempotency_key": "r2-finalized-accept:" + contract_id})
    assert accepted.status_code == 200, accepted.text
    blocked = client.post("/api/admin/contracts/" + contract_id + "/template-snapshot", headers=headers("OWNER_SPONSOR"), json={"reason": "Owner attempted a prohibited finalized backfill", "idempotency_key": "r2-finalized-replay:" + contract_id})
    assert blocked.status_code == 409, blocked.text
    assert blocked.json()["detail"]["code"] == "FINALIZED_CONTRACT_SNAPSHOT_BACKFILL_FORBIDDEN"
