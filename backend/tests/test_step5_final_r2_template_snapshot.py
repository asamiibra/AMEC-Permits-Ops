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


def test_owner_capture_is_exactly_once_and_non_owner_denied(client):
    ensure_contract_template(client)
    _normalize_step5_contract_template()
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
