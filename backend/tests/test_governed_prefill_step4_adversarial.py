"""Step 4 adversarial matrix for governed draft apply."""

from uuid import uuid4

from sqlalchemy import func, select

from backend.app.db import SessionLocal
from backend.app.models import (
    AuditEvent,
    FormInstance,
    FormInstanceApply,
    FormMappingRelease,
    FormMappingRule,
    GeneratedArtifact,
    MasterContentGovernanceProfile,
    MasterContentItem,
    SemanticValueAssertion,
    SubmissionAttempt,
    SubmissionPackage,
    AuthoritySubmissionCycle,
)
from backend.app.services.dashboard_v2_governance import release_checksum
from backend.tests.test_governed_prefill import _fixture


OWNER = {"X-Dev-Role": "SYSTEM_ADMIN", "X-Dev-Actor": "step4-human"}


def _preview(client, fixture, **overrides):
    response = client.post(
        "/api/governed-prefill/preview",
        json={
            "master_content_id": fixture["item_id"],
            "form_instance_id": fixture["instance_id"],
            "context_entity_type": "AuthorityCase",
            "context_entity_id": fixture["case_id"],
            "purpose": "FORM_PREPARATION",
            **overrides,
        },
        headers=OWNER,
    )
    assert response.status_code == 200, response.text
    return response.json()


def _apply(client, fixture, preview, **overrides):
    payload = {
        "form_instance_id": fixture["instance_id"],
        "context_entity_type": "AuthorityCase",
        "context_entity_id": fixture["case_id"],
        "purpose": "FORM_PREPARATION",
        "preview_fingerprint": preview["preview_fingerprint"],
        "expected_draft_revision": preview["draft_revision"],
        "idempotency_key": f"step4-adversarial-{uuid4()}",
        **overrides,
    }
    return client.post("/api/governed-prefill/apply", json=payload, headers=OWNER)


def _code(response):
    detail = response.json().get("detail")
    return detail.get("code") if isinstance(detail, dict) else detail


def test_writer_policy_rejects_authority_locked_and_protected_targets(client):
    fixture = _fixture()
    with SessionLocal() as db:
        release = db.get(FormMappingRelease, fixture["release_id"])
        rule = db.scalar(select(FormMappingRule).where(FormMappingRule.mapping_release_id == release.id))
        assert release and rule
        rule_id = rule.id
        from backend.app.models import FormAutomationProfile
        profile = db.get(FormAutomationProfile, db.get(FormMappingRelease, fixture["release_id"]).profile_id)
        assert profile
        profile.writer_policy_json = {rule.logical_field_key: {"writer": "AUTHORITY_ONLY"}}
        db.commit()
    preview = _preview(client, fixture)
    assert preview["preview_status"] == "REVIEW_REQUIRED"
    assert preview["fields"][0]["write_eligibility"] == "REJECTED"
    rejected = _apply(client, fixture, preview, selected_field_keys=[fixture["semantic_key"]])
    assert rejected.status_code == 409
    assert _code(rejected).startswith("FIELD_SELECTION_REJECTED")
    with SessionLocal() as db:
        from backend.app.models import FormAutomationProfile
        profile = db.get(FormAutomationProfile, db.get(FormMappingRelease, fixture["release_id"]).profile_id)
        assert profile
        profile.writer_policy_json = {}
        db.commit()


def test_master_and_draft_lifecycle_fail_closed(client):
    fixture = _fixture()
    with SessionLocal() as db:
        item = db.get(MasterContentItem, fixture["item_id"])
        assert item
        item.needs_review = True
        db.commit()
    response = client.post(
        "/api/governed-prefill/preview",
        json={"master_content_id": fixture["item_id"], "context_entity_type": "AuthorityCase", "context_entity_id": fixture["case_id"], "purpose": "FORM_PREPARATION"},
        headers=OWNER,
    )
    assert response.status_code == 409 and _code(response) == "PREFILL_MASTER_NOT_CURRENT_OR_NEEDS_REVIEW"
    with SessionLocal() as db:
        item = db.get(MasterContentItem, fixture["item_id"])
        item.needs_review = False
        item.status = "ARCHIVED"
        db.commit()
    response = client.post(
        "/api/governed-prefill/preview",
        json={"master_content_id": fixture["item_id"], "context_entity_type": "AuthorityCase", "context_entity_id": fixture["case_id"], "purpose": "FORM_PREPARATION"},
        headers=OWNER,
    )
    assert response.status_code == 409
    with SessionLocal() as db:
        item = db.get(MasterContentItem, fixture["item_id"])
        item.status = "ACTIVE"
        instance = db.get(FormInstance, fixture["instance_id"])
        instance.status = "SUBMITTED"
        db.commit()
    apply = client.post(
        "/api/governed-prefill/apply",
        json={"form_instance_id": fixture["instance_id"], "context_entity_type": "AuthorityCase", "context_entity_id": fixture["case_id"], "purpose": "FORM_PREPARATION", "preview_fingerprint": "0" * 64, "expected_draft_revision": 0, "idempotency_key": "step4-nondraft"},
        headers=OWNER,
    )
    assert apply.status_code == 409 and _code(apply) == "DRAFT_NOT_EDITABLE"


def test_restricted_source_and_invalid_selection_do_not_mutate(client):
    fixture = _fixture()
    with SessionLocal() as db:
        profile = db.scalar(select(MasterContentGovernanceProfile).where(MasterContentGovernanceProfile.master_content_item_id == fixture["item_id"]))
        assert profile
        profile.restricted_reference_sample = True
        db.commit()
    restricted = client.post(
        "/api/governed-prefill/preview",
        json={"master_content_id": fixture["item_id"], "context_entity_type": "AuthorityCase", "context_entity_id": fixture["case_id"], "purpose": "FORM_PREPARATION"},
        headers=OWNER,
    )
    assert restricted.status_code == 409 and _code(restricted) == "PREFILL_RESTRICTED_REFERENCE_SAMPLE"
    with SessionLocal() as db:
        profile = db.scalar(select(MasterContentGovernanceProfile).where(MasterContentGovernanceProfile.master_content_item_id == fixture["item_id"]))
        profile.restricted_reference_sample = False
        before = tuple(db.scalar(select(func.count()).select_from(model)) for model in (FormInstanceApply, GeneratedArtifact, SubmissionPackage, SubmissionAttempt, AuthoritySubmissionCycle))
        db.commit()
    preview = _preview(client, fixture)
    invalid = _apply(client, fixture, preview, selected_field_keys=["not-in-preview"])
    assert invalid.status_code == 409 and _code(invalid) == "INVALID_FIELD_SELECTION"
    with SessionLocal() as db:
        after = tuple(db.scalar(select(func.count()).select_from(model)) for model in (FormInstanceApply, GeneratedArtifact, SubmissionPackage, SubmissionAttempt, AuthoritySubmissionCycle))
    assert after == before


def test_apply_records_human_audit_without_protected_action_side_effects(client):
    fixture = _fixture()
    preview = _preview(client, fixture)
    with SessionLocal() as db:
        before = tuple(db.scalar(select(func.count()).select_from(model)) for model in (SubmissionPackage, SubmissionAttempt, AuthoritySubmissionCycle))
    applied = _apply(client, fixture, preview, selected_field_keys=[fixture["semantic_key"]])
    assert applied.status_code == 200, applied.text
    with SessionLocal() as db:
        event = db.scalar(select(AuditEvent).where(AuditEvent.event_type == "GOVERNED_PREFILL_APPLIED", AuditEvent.entity_id == fixture["instance_id"]).order_by(AuditEvent.occurred_at.desc()))
        after = tuple(db.scalar(select(func.count()).select_from(model)) for model in (SubmissionPackage, SubmissionAttempt, AuthoritySubmissionCycle))
    assert event and event.after_json["draft_revision"] == 1
    assert event.metadata_json["protected_actions_triggered"] is False
    assert after == before
