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
from backend.app.services.source18_form_projection import (
    resolve_source18_official_form,
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
    assert resolve_source18_official_form(db, transaction_id=transaction.id)["status"] == "RESOLVED"


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
