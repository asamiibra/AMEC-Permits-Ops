from __future__ import annotations

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.app.models import (
    AuthorityCase,
    Base,
    Document,
    DocumentApprovalState,
    DocumentType,
    DocumentVersion,
    MasterContentGovernanceProfile,
    MasterContentItem,
    Source18WorkflowTransaction,
)
from backend.app.services.master_content import assert_content_library_authority_write_allowed
from backend.app.services.master_content import archive_master_content, create_master_content_version
from backend.app.services.forms_governance import set_currentness, update_governance
from backend.app.services.source18_form_projection import (
    resolve_source18_official_form,
    source18_authority_item_ids,
    source18_official_form_projection,
)


@pytest.fixture()
def db():
    engine = create_engine("sqlite://", future=True)
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as session:
        yield session


def _authority_form(db: Session, *, suffix: str, currentness: str = "CURRENT") -> tuple[AuthorityCase, Source18WorkflowTransaction, DocumentVersion]:
    document = Document(
        document_type=DocumentType.APPLICATION_FORM,
        logical_name=f"source18-{suffix}.pdf",
        language="EN",
        source_system="SOURCE18",
    )
    db.add(document)
    db.flush()
    version = DocumentVersion(
        document_id=document.id,
        version_number=1,
        source_filename=f"source18-{suffix}.pdf",
        source_path_or_reference=f"synthetic://source18/{suffix}",
        sha256=(suffix * 64)[:64],
        mime_type="application/pdf",
        file_size=12,
        language="EN",
        approval_state=DocumentApprovalState.REVIEWED,
        source_system="SOURCE18",
        metadata_json={"official_form_currentness": currentness},
    )
    db.add(version)
    db.flush()
    document.current_version_id = version.id
    case = AuthorityCase(
        case_reference=f"CASE-{suffix}",
        external_body_id=f"body-{suffix}",
        service_type_id=f"service-{suffix}",
        jurisdiction_id=f"jurisdiction-{suffix}",
        transaction_type="SOURCE18_FORM_REVIEW",
        current_official_form_verified="true" if currentness == "CURRENT" else "false",
        official_form_version_id=version.id,
        official_form_publisher="Synthetic Authority",
        official_form_number=f"FORM-{suffix}",
        official_form_revision="2026.1",
        field_authority_schema_json={"authority_only_fields": ["authority_stamp"]},
        created_by="source18-test",
    )
    db.add(case)
    db.flush()
    transaction = Source18WorkflowTransaction(
        authority_case_id=case.id,
        office_id=f"office-{suffix}",
        transaction_type="ENGINEER_UPDATE",
        processing_mode="COUNTER_PROCESS",
        state="UPDATED_CREDENTIAL_VERIFIED",
        official_form_version_id=version.id,
        currentness_state=currentness,
        idempotency_key=f"idem-{suffix}",
        actor_ref="source18-test",
        source_snapshot_json={},
    )
    db.add(transaction)
    db.flush()
    return case, transaction, version


def test_source18_form_is_a_typed_read_only_projection_with_exact_hash_and_version(db):
    case, transaction, version = _authority_form(db, suffix="a")
    db.commit()

    rows = source18_official_form_projection(db)
    assert len(rows) == 1
    row = rows[0]
    assert row["projection_type"] == "SOURCE18_OFFICIAL_FORM_READ_ONLY"
    assert row["read_only"] is True
    assert row["authority_owner"] == "SOURCE18"
    assert row["source18"]["transaction_id"] == transaction.id
    assert row["source18"]["authority_case_id"] == case.id
    assert row["document_version"]["id"] == version.id
    assert row["document_version"]["sha256"] == version.sha256
    assert row["authority"]["field_authority_fields"] == ["authority_stamp"]
    assert row["reuse"]["allowed"] is True
    assert source18_authority_item_ids(db) == set()
    assert resolve_source18_official_form(db, transaction_id=transaction.id)["status"] == "RESOLVED"


def test_unknown_currentness_fails_closed(db):
    case, transaction, version = _authority_form(db, suffix="u")
    transaction.currentness_state = "CURRENT"
    version.metadata_json = {"official_form_currentness": "CURRENT"}
    case.current_official_form_verified = "UNKNOWN"
    db.commit()

    row = next(row for row in source18_official_form_projection(db) if row["source18"]["transaction_id"] == transaction.id)
    assert row["currentness"]["state"] == "UNVERIFIED"
    assert row["reuse"]["allowed"] is False
    assert resolve_source18_official_form(db, transaction_id=transaction.id)["status"] == "UNRESOLVED"


def test_case_transaction_version_and_source18_identity_must_agree(db):
    case, transaction, version = _authority_form(db, suffix="b")
    _, _, other_version = _authority_form(db, suffix="c")
    case.official_form_version_id = other_version.id
    db.commit()

    row = next(row for row in source18_official_form_projection(db) if row["source18"]["transaction_id"] == transaction.id)
    assert row["binding"]["case_version_matches_transaction"] is False
    assert row["reuse"]["allowed"] is False
    assert resolve_source18_official_form(db, transaction_id=transaction.id)["status"] == "UNRESOLVED"

    case.official_form_version_id = version.id
    version.source_system = "AMEC"
    db.commit()
    row = next(row for row in source18_official_form_projection(db) if row["source18"]["transaction_id"] == transaction.id)
    assert row["binding"]["document_version_source_system_is_source18"] is False
    assert row["reuse"]["allowed"] is False


def test_official_form_projection_routes_require_explicit_read_capability(client):
    headers = {"X-Dev-Role": "SYSTEM_ADMIN"}
    listing = client.get("/api/master-content/official-forms", headers=headers)
    resolving = client.get("/api/master-content/official-forms/resolve", headers=headers)
    assert listing.status_code == resolving.status_code == 200
    assert listing.json()["projection_type"] == "SOURCE18_OFFICIAL_FORM_READ_ONLY"
    assert resolving.json()["truth"] == "SOURCE18"


def test_stale_source18_form_is_visible_for_audit_but_cannot_resolve_as_current(db):
    _, transaction, _ = _authority_form(db, suffix="s", currentness="STALE")
    db.commit()

    row = source18_official_form_projection(db)[0]
    assert row["currentness"]["state"] == "STALE"
    assert row["reuse"]["allowed"] is False
    assert resolve_source18_official_form(db, transaction_id=transaction.id)["status"] == "UNRESOLVED"
    assert source18_official_form_projection(db, include_non_current=False) == []


def test_ambiguous_current_source18_forms_fail_closed(db):
    _authority_form(db, suffix="x")
    _authority_form(db, suffix="y")
    db.commit()
    result = resolve_source18_official_form(db)
    assert result["status"] == "AMBIGUOUS"
    assert result["item"] is None
    assert result["canonical_count"] == 2


def test_content_library_cannot_mutate_source18_bound_document(db):
    case, transaction, version = _authority_form(db, suffix="m")
    item = MasterContentItem(
        ref="F-SOURCE18-M",
        content_type="FORM",
        title="Source18 projection fixture",
        document_id=version.document_id,
        current_document_version_id=version.id,
        created_by="source18-test",
    )
    db.add(item)
    db.flush()
    db.add(MasterContentGovernanceProfile(master_content_item_id=item.id, content_ownership_class="AMEC_OWNED"))
    db.commit()

    with pytest.raises(HTTPException) as error:
        assert_content_library_authority_write_allowed(db, item)
    assert error.value.detail["code"] == "SOURCE18_OFFICIAL_FORM_READ_ONLY"
    assert error.value.detail["source18_transaction_id"] == transaction.id
    assert error.value.detail["authority_case_id"] == case.id
    assert error.value.detail["document_version_id"] == version.id


def test_all_content_library_authority_mutation_seams_fail_without_state_change(db):
    case, transaction, version = _authority_form(db, suffix="z")
    item = MasterContentItem(
        ref="F-SOURCE18-Z",
        content_type="FORM",
        title="Source18 projection fixture",
        document_id=version.document_id,
        current_document_version_id=version.id,
        created_by="source18-test",
    )
    db.add(item)
    db.flush()
    db.add(MasterContentGovernanceProfile(master_content_item_id=item.id, content_ownership_class="AMEC_OWNED"))
    db.commit()
    before = {"status": item.status, "current_document_version_id": item.current_document_version_id}

    calls = [
        lambda: create_master_content_version(
            db,
            item_id=item.id,
            expected_current_version=1,
            filename="replacement.txt",
            mime_type="text/plain",
            content=b"replacement",
            title=None,
            category_id=None,
            description=None,
            change_reason="unauthorized synthetic mutation",
            actor="SYSTEM_ADMIN",
            idempotency_key="source18-z-version",
            correlation_id="source18-z-version",
        ),
        lambda: archive_master_content(db, item_id=item.id, actor="SYSTEM_ADMIN", correlation_id="source18-z-archive"),
        lambda: update_governance(db, item, {"official_form_no": "FORGED"}, actor="SYSTEM_ADMIN", correlation_id="source18-z-governance"),
        lambda: set_currentness(db, item, action="MARK_NOT_CURRENT", actor="SYSTEM_ADMIN", note="forged", correlation_id="source18-z-currentness"),
    ]
    for call in calls:
        with pytest.raises(HTTPException) as error:
            call()
        assert error.value.detail["code"] == "SOURCE18_OFFICIAL_FORM_READ_ONLY"
        db.rollback()

    assert {"status": item.status, "current_document_version_id": item.current_document_version_id} == before


def test_stale_manually_persisted_content_library_binding_remains_protected(db):
    _, transaction, version = _authority_form(db, suffix="stale-binding")
    document = db.get(Document, version.document_id)
    newer = DocumentVersion(
        document_id=document.id,
        version_number=2,
        source_filename="source18-stale-binding-v2.pdf",
        source_path_or_reference="synthetic://source18/stale-binding/v2",
        sha256="b" * 64,
        mime_type="application/pdf",
        file_size=12,
        language="EN",
        approval_state=DocumentApprovalState.REVIEWED,
        source_system="SOURCE18",
        metadata_json={"official_form_currentness": "CURRENT"},
    )
    db.add(newer)
    db.flush()
    document.current_version_id = newer.id
    item = MasterContentItem(
        ref="CL-SOURCE18-STALE-BINDING",
        content_type="FORM",
        title="Stale Source18 binding",
        description="Synthetic stale binding audit fixture",
        used_in=["PERMIT"],
        status="ACTIVE",
        needs_review=False,
        document_id=document.id,
        current_document_version_id=newer.id,
        created_by="controlled-test-persistence",
    )
    db.add(item)
    db.flush()
    db.add(MasterContentGovernanceProfile(master_content_item_id=item.id, content_ownership_class="AMEC_OWNED", artifact_kind="AMEC_FORM"))
    db.commit()

    with pytest.raises(HTTPException) as error:
        assert_content_library_authority_write_allowed(db, item)
    assert error.value.detail["code"] == "SOURCE18_OFFICIAL_FORM_READ_ONLY"
    assert source18_authority_item_ids(db) == {item.id}
