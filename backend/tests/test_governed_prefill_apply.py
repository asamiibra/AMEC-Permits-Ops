"""Step 4 governed FormInstance draft-apply command tests."""

from uuid import uuid4

from sqlalchemy import func, select

from backend.app.db import SessionLocal
from backend.app.models import (
    AuditEvent,
    Document,
    DocumentApprovalState,
    DocumentVersion,
    FormInstance,
    FormInstanceApply,
    FormMappingRelease,
    FormMappingRule,
    GeneratedArtifact,
    MasterContentItem,
    SemanticKeyDefinition,
    SemanticValueAssertion,
)
from backend.app.services.dashboard_v2_governance import release_checksum
from backend.tests.test_governed_prefill import _fixture


OWNER = {"X-Dev-Role": "SYSTEM_ADMIN"}


def _preview(client, fixture, **overrides):
    payload = {
        "master_content_id": fixture["item_id"],
        "form_instance_id": fixture["instance_id"],
        "context_entity_type": "AuthorityCase",
        "context_entity_id": fixture["case_id"],
        "purpose": "FORM_PREPARATION",
        **overrides,
    }
    response = client.post("/api/governed-prefill/preview", json=payload, headers=OWNER)
    assert response.status_code == 200, response.text
    return payload, response.json()


def _apply(client, fixture, preview, *, idempotency_key=None, expected_revision=0, selected_field_keys=None, headers=None):
    payload = {
        "form_instance_id": fixture["instance_id"],
        "context_entity_type": "AuthorityCase",
        "context_entity_id": fixture["case_id"],
        "purpose": "FORM_PREPARATION",
        "preview_fingerprint": preview["preview_fingerprint"],
        "expected_draft_revision": expected_revision,
        "idempotency_key": idempotency_key or f"step4-apply-{uuid4()}",
    }
    if selected_field_keys is not None:
        payload["selected_field_keys"] = selected_field_keys
    return client.post("/api/governed-prefill/apply", json=payload, headers=headers or OWNER)


def _code(response):
    body = response.json()
    detail = body.get("detail")
    return detail.get("code") if isinstance(detail, dict) else detail


def test_clean_apply_persists_exact_provenance_and_is_idempotent(client):
    fixture = _fixture()
    _payload, preview = _preview(client, fixture)
    assert preview["preview_status"] == "READY"
    before = _counts()
    first = _apply(client, fixture, preview, idempotency_key="step4-idempotent-clean")
    assert first.status_code == 200, first.text
    result = first.json()
    assert result["apply_status"] == "APPLIED"
    assert result["changed_field_keys"] == [fixture["semantic_key"]]
    draft = result["form_instance"]
    logical_key = next(iter(draft["resolved_values"]))
    assert draft["draft_revision"] == 1
    assert draft["status"] == "DRAFT"
    evidence = draft["field_provenance_json"][logical_key]
    assert evidence["target_form"]["document_version_id"] == fixture["version_id"]
    assert evidence["value_evidence"]["citations"][0]["document_version_id"] == fixture["evidence_version_id"]
    assert evidence["value_evidence"]["citations"][0]["source_hash"] == "c" * 64
    after_first = _counts()
    assert after_first == (before[0], before[1] + 1, before[2] + 1, before[3], before[4])

    duplicate = _apply(client, fixture, preview, idempotency_key="step4-idempotent-clean")
    assert duplicate.status_code == 200, duplicate.text
    assert duplicate.json()["idempotent_replay"] is True
    assert duplicate.json()["form_instance"]["draft_revision"] == 1
    assert _counts() == after_first

    different_request = _apply(client, fixture, preview, idempotency_key="step4-idempotent-clean", expected_revision=1, selected_field_keys=["other-field"])
    assert different_request.status_code == 409
    assert _code(different_request) == "IDEMPOTENCY_CONFLICT"


def test_apply_rejects_target_mapping_source_assertion_and_access_changes(client):
    fixture = _fixture()

    _payload, preview = _preview(client, fixture)
    with SessionLocal() as db:
        item = db.get(MasterContentItem, fixture["item_id"])
        assert item
        item.current_document_version_id = str(uuid4())
        db.commit()
    target_changed = _apply(client, fixture, preview, idempotency_key="step4-target-change")
    assert target_changed.status_code == 409 and _code(target_changed) == "TARGET_FORM_CHANGED"
    with SessionLocal() as db:
        db.get(MasterContentItem, fixture["item_id"]).current_document_version_id = fixture["version_id"]
        db.commit()

    _payload, preview = _preview(client, fixture)
    with SessionLocal() as db:
        release = db.get(FormMappingRelease, fixture["release_id"])
        assert release
        release.status = "REVIEW"
        db.commit()
    mapping_changed = _apply(client, fixture, preview, idempotency_key="step4-mapping-change")
    assert mapping_changed.status_code == 409 and _code(mapping_changed) == "MAPPING_RELEASE_CHANGED"
    with SessionLocal() as db:
        db.get(FormMappingRelease, fixture["release_id"]).status = "RELEASED"
        db.commit()

    _payload, preview = _preview(client, fixture)
    with SessionLocal() as db:
        source = db.get(DocumentVersion, fixture["evidence_version_id"])
        assert source
        source.sha256 = "d" * 64
        db.commit()
    source_changed = _apply(client, fixture, preview, idempotency_key="step4-source-change")
    assert source_changed.status_code == 409 and _code(source_changed) == "STALE_PREVIEW"
    with SessionLocal() as db:
        db.get(DocumentVersion, fixture["evidence_version_id"]).sha256 = "c" * 64
        assertion = db.scalar(select(SemanticValueAssertion).where(SemanticValueAssertion.id == fixture["assertion_id"]))
        assert assertion
        assertion.verification_status = "REVOKED"
        db.commit()
    assertion_changed = _apply(client, fixture, preview, idempotency_key="step4-assertion-change")
    assert assertion_changed.status_code == 409 and _code(assertion_changed) == "STALE_PREVIEW"

    with SessionLocal() as db:
        assertion = db.scalar(select(SemanticValueAssertion).where(SemanticValueAssertion.id == fixture["assertion_id"]))
        assert assertion
        assertion.verification_status = "VERIFIED"
        db.commit()
    _payload, preview = _preview(client, fixture)
    revoked = _apply(client, fixture, preview, idempotency_key="step4-access-revoked", headers={"X-Dev-Role": "PERMIT_PREPARER", "X-Dev-Actor": "unassigned-step4-caller"})
    assert revoked.status_code == 404


def test_unverified_conflicted_and_wrong_case_previews_never_apply(client):
    fixture = _fixture()
    _payload, preview = _preview(client, fixture)
    with SessionLocal() as db:
        assertion = db.get(SemanticValueAssertion, fixture["assertion_id"])
        assert assertion
        assertion.verification_status = "OBSERVED"
        db.commit()
    unverified = _apply(client, fixture, preview, idempotency_key="step4-unverified")
    assert unverified.status_code == 409 and _code(unverified) == "STALE_PREVIEW"
    with SessionLocal() as db:
        assertion = db.get(SemanticValueAssertion, fixture["assertion_id"])
        assert assertion
        assertion.verification_status = "VERIFIED"
        db.add(SemanticValueAssertion(semantic_key_id=assertion.semantic_key_id, context_type="AuthorityCase", context_id=fixture["case_id"], value_json="conflicting-value", value_type="STRING", source_type="AuthorityCase", source_id=fixture["case_id"], source_version="CURRENT", verification_status="VERIFIED", authority="OWNER", asserted_by="step4-test"))
        db.commit()
    conflicted = _apply(client, fixture, preview, idempotency_key="step4-conflicted")
    assert conflicted.status_code == 409 and _code(conflicted) == "STALE_PREVIEW"
    wrong_case = client.post(
        "/api/governed-prefill/apply",
        json={
            "form_instance_id": fixture["instance_id"],
            "context_entity_type": "AuthorityCase",
            "context_entity_id": str(uuid4()),
            "purpose": "FORM_PREPARATION",
            "preview_fingerprint": preview["preview_fingerprint"],
            "expected_draft_revision": 0,
            "idempotency_key": "step4-wrong-case",
        },
        headers=OWNER,
    )
    assert wrong_case.status_code == 404


def test_human_edit_and_concurrent_apply_never_use_last_write_wins(client):
    fixture = _fixture()
    _payload, preview = _preview(client, fixture)
    with SessionLocal() as db:
        instance = db.get(FormInstance, fixture["instance_id"])
        assert instance
        instance.resolved_values = {fixture["semantic_key"]: "human-edit"}
        db.commit()
    human_conflict = _apply(client, fixture, preview, idempotency_key="step4-human-conflict")
    assert human_conflict.status_code == 409 and _code(human_conflict).startswith("HUMAN_EDIT_CONFLICT")

    with SessionLocal() as db:
        instance = db.get(FormInstance, fixture["instance_id"])
        assert instance
        instance.resolved_values = {}
        db.commit()
    first = _apply(client, fixture, preview, idempotency_key="step4-concurrent-winner")
    assert first.status_code == 200, first.text
    second = _apply(client, fixture, preview, idempotency_key="step4-concurrent-loser")
    assert second.status_code == 409 and _code(second) == "CONCURRENT_MODIFICATION"


def test_batch_validation_rolls_back_all_fields_when_one_human_edit_conflicts(client):
    fixture = _fixture()
    second_key_name = f"permit.second.field.{uuid4().hex[:8]}"
    with SessionLocal() as db:
        release = db.get(FormMappingRelease, fixture["release_id"])
        assertion = db.scalar(select(SemanticValueAssertion).where(SemanticValueAssertion.id == fixture["assertion_id"]))
        assert release and assertion
        key = SemanticKeyDefinition(semantic_key=second_key_name, value_type="STRING", description="Second Step 4 field")
        db.add(key)
        db.flush()
        db.add(SemanticValueAssertion(semantic_key_id=key.id, context_type="AuthorityCase", context_id=fixture["case_id"], value_json="second-value", value_type="STRING", source_type="DocumentVersion", source_id=assertion.source_id, source_version=assertion.source_version, verification_status="VERIFIED", authority="OWNER", asserted_by="step4-test"))
        db.add(FormMappingRule(mapping_release_id=release.id, logical_field_key=second_key_name, target_key="second_target", transform_type="SCALAR", target_writer="SYSTEM"))
        db.flush()
        release.mapping_checksum = release_checksum(db, release)
        db.commit()
    _payload, preview = _preview(client, fixture)
    assert len(preview["fields"]) == 2
    with SessionLocal() as db:
        instance = db.get(FormInstance, fixture["instance_id"])
        assert instance
        instance.resolved_values = {second_key_name: "human-edit"}
        db.commit()
    failed = _apply(client, fixture, preview, idempotency_key="step4-atomic-batch")
    assert failed.status_code == 409 and _code(failed).startswith("HUMAN_EDIT_CONFLICT")
    with SessionLocal() as db:
        instance = db.get(FormInstance, fixture["instance_id"])
        assert instance and instance.draft_revision == 0
        assert fixture["semantic_key"] not in (instance.resolved_values or {})
        assert db.scalar(select(FormInstanceApply).where(FormInstanceApply.idempotency_key == "step4-atomic-batch")) is None


def test_structured_provenance_persists_without_fake_document_citation(client):
    fixture = _fixture()
    structured_key_name = f"permit.structured.field.{uuid4().hex[:8]}"
    with SessionLocal() as db:
        release = db.get(FormMappingRelease, fixture["release_id"])
        assert release
        key = SemanticKeyDefinition(semantic_key=structured_key_name, value_type="STRING", description="Structured Step 4 field")
        db.add(key)
        db.flush()
        db.add(SemanticValueAssertion(semantic_key_id=key.id, context_type="AuthorityCase", context_id=fixture["case_id"], value_json="structured-value", value_type="STRING", source_type="AuthorityCase", source_id=fixture["case_id"], source_version="CURRENT", verification_status="VERIFIED", authority="OWNER", asserted_by="step4-test"))
        db.add(FormMappingRule(mapping_release_id=release.id, logical_field_key=structured_key_name, target_key="structured_target", transform_type="SCALAR", target_writer="SYSTEM"))
        db.flush()
        release.mapping_checksum = release_checksum(db, release)
        db.commit()
    _payload, preview = _preview(client, fixture)
    structured = next(field for field in preview["fields"] if field["logical_field_key"] == structured_key_name)
    applied = _apply(client, fixture, preview, idempotency_key="step4-structured", selected_field_keys=[structured_key_name])
    assert applied.status_code == 200, applied.text
    persisted = applied.json()["form_instance"]
    citation = persisted["field_provenance_json"][structured_key_name]["value_evidence"]["citations"][0]
    assert structured["citations"][0]["canonical_entity_type"] == "AuthorityCase"
    assert citation["canonical_entity_type"] == "AuthorityCase"
    assert citation["document_version_id"] is None
    assert citation["source_hash"] is None


def test_historical_draft_replay_keeps_original_target_and_value_pins(client):
    fixture = _fixture()
    _payload, preview = _preview(client, fixture)
    applied = _apply(client, fixture, preview, idempotency_key="step4-historical-replay")
    assert applied.status_code == 200, applied.text
    with SessionLocal() as db:
        target_document = db.get(Document, fixture["version_document_id"])
        evidence_document = db.get(Document, fixture["evidence_document_id"])
        item = db.get(MasterContentItem, fixture["item_id"])
        assert target_document and evidence_document and item
        later_target = DocumentVersion(document_id=target_document.id, version_number=2, source_filename="later-form.txt", source_path_or_reference="synthetic://later-form", sha256="e" * 64, mime_type="text/plain", file_size=10, language="en", approval_state=DocumentApprovalState.REVIEWED, source_system="MASTER_CONTENT", synthetic_content=b"later form")
        later_evidence = DocumentVersion(document_id=evidence_document.id, version_number=2, source_filename="later-evidence.txt", source_path_or_reference="synthetic://later-evidence", sha256="f" * 64, mime_type="text/plain", file_size=12, language="en", approval_state=DocumentApprovalState.REVIEWED, source_system="PROJECT_EVIDENCE", synthetic_content=b"later evidence")
        db.add_all([later_target, later_evidence])
        db.flush()
        target_document.current_version_id = later_target.id
        evidence_document.current_version_id = later_evidence.id
        item.current_document_version_id = later_target.id
        db.commit()
    with SessionLocal() as db:
        instance = db.get(FormInstance, fixture["instance_id"])
        apply = db.scalar(select(FormInstanceApply).where(FormInstanceApply.idempotency_key == "step4-historical-replay"))
        assert instance and apply
        logical_key = next(iter(instance.field_provenance_json))
        lineage = instance.field_provenance_json[logical_key]
        assert instance.source_document_version_id == fixture["version_id"]
        assert lineage["target_form"]["document_version_id"] == fixture["version_id"]
        assert lineage["value_evidence"]["citations"][0]["document_version_id"] == fixture["evidence_version_id"]
        assert lineage["value_evidence"]["citations"][0]["source_hash"] == "c" * 64
        assert apply.preview_fingerprint == preview["preview_fingerprint"]


def _counts():
    with SessionLocal() as db:
        return (
            db.scalar(select(func.count()).select_from(FormInstance)),
            db.scalar(select(func.count()).select_from(FormInstanceApply)),
            db.scalar(select(func.count()).select_from(AuditEvent).where(AuditEvent.event_type == "GOVERNED_PREFILL_APPLIED")),
            db.scalar(select(func.count()).select_from(GeneratedArtifact)),
            db.scalar(select(func.count()).select_from(MasterContentItem)),
        )
