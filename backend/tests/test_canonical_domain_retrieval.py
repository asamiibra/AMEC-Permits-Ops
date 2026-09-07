"""Synthetic proof for canonical domain boundaries and governed retrieval."""

from __future__ import annotations

import io
import sys
import tempfile
import zipfile
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from pydantic import ValidationError
import pytest
from fastapi.testclient import TestClient

from backend.app.db import SessionLocal, get_db
from backend.app.models import (
    Base,
    ClassificationReviewStatus,
    ConsultancyOffice,
    Criticality,
    DataType,
    Document,
    DocumentApprovalState,
    DocumentClassification,
    DocumentType,
    DocumentVersion,
    FieldDefinition,
    FieldObservation,
    MasterContentItem,
    MasterContentReferenceSequence,
    Project,
    Role,
    SourceIntakeItem,
    VerifiedAssertion,
    VerificationMethod,
)
from backend.app.services.forms_governance import add_provenance, set_currentness
from backend.app.services.governed_retrieval import (
    GovernedRetrievalEnvelope,
    RetrievalAccessContext,
    RetrievalQuery,
    access_context_for_role,
    answer_from_retrieval,
    governed_retrieve,
)
from backend.app.services.master_content import create_master_content
from backend.app.services.source_intake import SourceIntakeService
from backend.app.services.week2_workflows import classify_version, verify_observation


OWNER = {"X-Dev-Role": "OWNER_SPONSOR"}


@pytest.fixture(scope="module")
def canonical_session_factory():
    path = Path(tempfile.gettempdir()) / f"permitops_canonical_retrieval_{uuid4().hex}.db"
    engine = create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False}, future=True)
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    with factory() as db:
        office = ConsultancyOffice(office_code="QEC-DOHA", name_en="Synthetic AMEC Office", name_ar="مكتب اصطناعي", status="ACTIVE")
        db.add(office)
        db.add(FieldDefinition(field_code="PERMIT.TYPE", name_en="Permit type", data_type=DataType.STRING, criticality=Criticality.CRITICAL, normalization_rule="TEXT", description="Synthetic permit type"))
        db.add_all([
            MasterContentReferenceSequence(content_type="FORM", prefix="F", padding=4, scope="GLOBAL", active=True, current_value=0),
            MasterContentReferenceSequence(content_type="REPORT", prefix="R", padding=4, scope="GLOBAL", active=True, current_value=0),
            MasterContentReferenceSequence(content_type="ENGINEERING_WORK", prefix="E", padding=4, scope="GLOBAL", active=True, current_value=0),
            MasterContentReferenceSequence(content_type="DEFINITION", prefix="D", padding=4, scope="GLOBAL", active=True, current_value=0),
        ])
        db.commit()
    yield factory
    engine.dispose()
    if path.exists():
        path.unlink()


@pytest.fixture
def canonical_client(canonical_session_factory, monkeypatch):
    monkeypatch.setattr(sys.modules[__name__], "SessionLocal", canonical_session_factory)

    def override_get_db():
        with canonical_session_factory() as db:
            yield db

    from backend.app.main import app
    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as value:
            yield value
    finally:
        app.dependency_overrides.pop(get_db, None)


def _archive() -> tuple[bytes, bytes]:
    source = b"SYNTHETIC REUSABLE FORM\nFORM_CODE: SYN-F-001\nAPPROVED USE: PERMIT"
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr("FORME/Synthetic Reusable Form.txt", source)
    return stream.getvalue(), source


def _archive_with_source(source: bytes) -> bytes:
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr("FORME/Observed Reference.txt", source)
    return stream.getvalue()


def _observed_manifest(source: bytes, ref: str) -> dict:
    import hashlib

    return {"version": "reference-authority-proof-v1", "items": [{
        "relative_path": "Observed Reference.txt",
        "sha256": hashlib.sha256(source).hexdigest(),
        "v1_4_disposition": "PROMOTE_MASTER_CURRENT",
        "dashboard_mapping": "Forms",
        "category": "Synthetic observed reference",
        "used_in": ["PERMIT"],
        "ref": ref,
    }]}


def _promote_observed_source(source: bytes, ref: str, location: str, *, actor: str = "synthetic-reference-auditor") -> tuple[str, str, str]:
    payload = _archive_with_source(source)
    with SessionLocal() as db:
        service = SourceIntakeService(db, actor=actor)
        batch = service.ingest_zip(payload, source_display_name="synthetic observed reference", source_location_reference=location)
        service.promote_batch(batch, payload, _observed_manifest(source, ref))
        row = db.scalar(select(SourceIntakeItem).where(SourceIntakeItem.batch_id == batch.id))
        item = db.get(MasterContentItem, row.target_master_content_id)
        return item.id, item.current_document_version_id, row.id


def _manifest(source: bytes, ref: str) -> dict:
    import hashlib

    return {"version": "canonical-proof-v1", "items": [{
        "relative_path": "Synthetic Reusable Form.txt",
        "sha256": hashlib.sha256(source).hexdigest(),
        "v1_4_disposition": "PROMOTE_MASTER_CURRENT",
        "dashboard_mapping": "Forms",
        "category": "Synthetic governed form",
        "used_in": ["PERMIT", "ENGINEERING"],
        "ref": ref,
    }]}


def _proof_fixture() -> dict[str, str]:
    payload, source = _archive()
    with SessionLocal() as db:
        office = db.scalar(select(ConsultancyOffice).where(ConsultancyOffice.office_code == "QEC-DOHA"))
        project = Project(project_number=f"SYN-CANON-{uuid4().hex[:8]}", project_name="Synthetic canonical retrieval project", office_id=office.id, workstream="PROOF", status="ACTIVE", municipality="Synthetic", permit_type="Synthetic Permit")
        wrong_project = Project(project_number=f"SYN-WRONG-{uuid4().hex[:8]}", project_name="Synthetic unrelated project", office_id=office.id, workstream="PROOF", status="ACTIVE", municipality="Synthetic", permit_type="Synthetic Permit")
        db.add_all([project, wrong_project])
        db.flush()

        intake = SourceIntakeService(db, actor="synthetic-authorized-owner")
        batch = intake.ingest_zip(payload, source_display_name="synthetic DSM/SOR export", source_location_reference=f"synthetic://canonical-proof/{uuid4()}")
        master_ref = f"SYN-FORM-{uuid4().hex[:8]}"
        intake.promote_batch(batch, payload, _manifest(source, master_ref))
        item_row = db.scalar(select(SourceIntakeItem).where(SourceIntakeItem.batch_id == batch.id))
        item = db.get(MasterContentItem, item_row.target_master_content_id)
        v1 = db.get(DocumentVersion, item.current_document_version_id)
        v1.metadata_json = {**(v1.metadata_json or {}), "synthetic_text": source.decode()}
        db.flush()
        add_provenance(db, item, v1, {"obtained_from": "SYNTHETIC_DSM_SOR", "source_reference": f"archive://{batch.source_archive_hash}/Synthetic Reusable Form.txt", "ingest_batch": batch.id, "evidence_reference": f"synthetic://evidence/{batch.id}"}, actor="synthetic-authorized-owner", correlation_id=f"proof:{batch.id}")
        set_currentness(db, item, action="VERIFY_CURRENT", actor="synthetic-authorized-owner", note="Synthetic authorized verification", correlation_id=f"proof:{batch.id}")
        classification = classify_version(db, v1, f"proof:{batch.id}")
        classification.final_type = "APPLICATION_FORM"
        classification.review_status = ClassificationReviewStatus.HUMAN_CONFIRMED

        field = db.scalar(select(FieldDefinition).where(FieldDefinition.field_code == "PERMIT.TYPE"))
        observation = FieldObservation(project_id=project.id, field_definition_id=field.id, document_version_id=v1.id, raw_value="Synthetic Permit", normalized_candidate_value="Synthetic Permit", structured_value_json={"value": "Synthetic Permit"}, page_number=1, source_region_text="PERMIT_TYPE: Synthetic Permit", extraction_method="RULE", extractor_version="CANONICAL-PROOF-1", confidence=0.99, correlation_id=f"proof:{batch.id}")
        db.add(observation)
        db.flush()
        assertion = verify_observation(db, observation, actor_id="synthetic-owner", method=VerificationMethod.HUMAN_VERIFIED, correction=None, correlation_id=f"proof:{batch.id}")
        db.commit()
        return {"item_id": item.id, "document_id": item.document_id, "v1_id": v1.id, "project_id": project.id, "wrong_project_id": wrong_project.id, "assertion_id": assertion.id, "batch_id": batch.id}


def _transactional_fixture(project_id: str) -> str:
    source = b"SYNTHETIC FILLED PROJECT FORM\nPROJECT: PRIVATE-CONTEXT-001\nPERMIT_TYPE: Synthetic Permit"
    with SessionLocal() as db:
        document = Document(project_id=project_id, document_type=DocumentType.APPLICATION_FORM, logical_name="Synthetic filled project form", language="en", source_system="SYNTHETIC_DSM_SOR")
        db.add(document)
        db.flush()
        version = DocumentVersion(document_id=document.id, version_number=1, source_filename="filled-project-form.txt", source_path_or_reference="synthetic://project-form", sha256=__import__("hashlib").sha256(source).hexdigest(), mime_type="text/plain", file_size=len(source), language="en", approval_state=DocumentApprovalState.REVIEWED, source_system="SYNTHETIC_DSM_SOR", metadata_json={"synthetic_text": source.decode(), "classification": "PROJECT_SPECIFIC"})
        document.current_version_id = version.id
        db.add(version)
        db.flush()
        db.add(DocumentClassification(document_version_id=version.id, predicted_type="APPLICATION_FORM", classification_method="RULE", model_or_rule_version="CANONICAL-PROOF-1", confidence=0.99, final_type="APPLICATION_FORM", review_status=ClassificationReviewStatus.HUMAN_CONFIRMED, evidence_json={"synthetic": True}))
        field = db.scalar(select(FieldDefinition).where(FieldDefinition.field_code == "PERMIT.TYPE"))
        observation = FieldObservation(project_id=project_id, field_definition_id=field.id, document_version_id=version.id, raw_value="Synthetic Permit", normalized_candidate_value="Synthetic Permit", structured_value_json={"value": "Synthetic Permit"}, page_number=1, source_region_text="PERMIT_TYPE: Synthetic Permit", extraction_method="RULE", extractor_version="CANONICAL-PROOF-1", confidence=0.99, correlation_id=f"proof:{project_id}")
        db.add(observation)
        db.flush()
        verify_observation(db, observation, actor_id="synthetic-owner", method=VerificationMethod.HUMAN_VERIFIED, correction=None, correlation_id=f"proof:{project_id}")
        db.commit()
        return version.id


def test_complete_synthetic_vertical_proof(canonical_client):
    fixture = _proof_fixture()
    transactional_version_id = _transactional_fixture(fixture["project_id"])
    with SessionLocal() as db:
        owner = access_context_for_role(Role.OWNER_SPONSOR, caller_id="synthetic-owner", project_ids=(fixture["project_id"],))
        master = governed_retrieve(db, RetrievalQuery(master_content_id=fixture["item_id"], query="SYN-F-001"), owner)
        assert len(master) == 1
        envelope = master[0].envelope
        assert envelope.master_content_id == fixture["item_id"]
        assert envelope.document_id == fixture["document_id"]
        assert envelope.document_version_id == fixture["v1_id"]
        assert envelope.citation.document_version_id == fixture["v1_id"]
        assert envelope.verification_state == "VERIFIED_CURRENT"
        assert envelope.canonical_domain == "MASTER_CONTENT"
        assert envelope.canonical_entity_type == "MasterContentItem"
        assert envelope.transactional_entity_id is None

        authorized = governed_retrieve(db, RetrievalQuery(document_version_id=transactional_version_id, query="PRIVATE-CONTEXT-001"), owner)
        assert len(authorized) == 1
        assert authorized[0].envelope.canonical_domain == "TRANSACTIONAL_EVIDENCE"
        assert authorized[0].envelope.transactional_entity_id == fixture["project_id"]
        assert authorized[0].envelope.relationship_context["verified_assertion_ids"]

        read_only = access_context_for_role(Role.PERMIT_PREPARER, caller_id="synthetic-preparer", project_ids=(fixture["project_id"],))
        assert governed_retrieve(db, RetrievalQuery(master_content_id=fixture["item_id"]), read_only)
        assert governed_retrieve(db, RetrievalQuery(document_version_id=transactional_version_id), read_only)
        assert not governed_retrieve(db, RetrievalQuery(document_version_id=transactional_version_id), access_context_for_role(Role.PERMIT_PREPARER, caller_id="synthetic-unauthorized"))
        assert not governed_retrieve(db, RetrievalQuery(document_version_id=transactional_version_id, project_id=fixture["wrong_project_id"]), owner)

        answer = answer_from_retrieval("What does the synthetic form say?", master)
        assert answer.canonical_state_mutated is False
        assert answer.authoritative_fact is True
        assert answer.citations[0].document_version_id == fixture["v1_id"]
        assert "approval" not in answer.answer.casefold()

        item = db.get(MasterContentItem, fixture["item_id"])
        v1 = db.get(DocumentVersion, fixture["v1_id"])
        assert db.scalar(select(func.count(DocumentVersion.id)).where(DocumentVersion.document_id == fixture["document_id"])) == 1
        assert db.scalar(select(func.count(MasterContentItem.id)).where(MasterContentItem.id == fixture["item_id"])) == 1
        assert v1.metadata_json["synthetic_text"].startswith("SYNTHETIC REUSABLE FORM")
        assert item.current_document_version_id == fixture["v1_id"]

    with SessionLocal() as db:
        item = db.get(MasterContentItem, fixture["item_id"])
        v1 = db.get(DocumentVersion, fixture["v1_id"])
        from backend.app.services.master_content import create_master_content_version

        updated = create_master_content_version(db, item_id=item.id, expected_current_version=1, filename="synthetic-v2.txt", mime_type="text/plain", content=b"SYNTHETIC REUSABLE FORM V2\nFORM_CODE: SYN-F-001\nAPPROVED USE: PERMIT", title=None, category_id=None, description=None, change_reason="Synthetic version authority proof", actor="synthetic-authorized-owner", idempotency_key=f"canonical-proof-v2:{item.id}", correlation_id=f"proof-v2:{item.id}", source_surface="SYNTHETIC_PROOF")
        v2_id = updated["current_version_id"]
        assert v2_id != v1.id
        assert v1.approval_state == DocumentApprovalState.SUPERSEDED
        assert db.scalar(select(func.count(DocumentVersion.id)).where(DocumentVersion.document_id == item.document_id)) == 2
        assert db.scalar(select(func.count(MasterContentItem.id)).where(MasterContentItem.document_id == item.document_id)) == 1
        historical = governed_retrieve(db, RetrievalQuery(master_content_id=item.id, document_version_id=v1.id, query="SYN-F-001"), access_context_for_role(Role.OWNER_SPONSOR, caller_id="synthetic-owner"))
        current = governed_retrieve(db, RetrievalQuery(master_content_id=item.id, query="SYN-F-001"), access_context_for_role(Role.OWNER_SPONSOR, caller_id="synthetic-owner"))
        assert historical[0].envelope.document_version_id == v1.id
        assert historical[0].envelope.superseded is True
        assert current[0].envelope.document_version_id == v2_id


def test_retrieval_api_is_read_only_and_returns_citations(canonical_client):
    fixture = _proof_fixture()
    response = canonical_client.get("/api/retrieval/query", params={"master_content_id": fixture["item_id"], "query": "SYN-F-001"}, headers=OWNER)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body[0]["envelope"]["master_content_id"] == fixture["item_id"]
    assert body[0]["envelope"]["citation"]["document_version_id"] == fixture["v1_id"]
    answer = canonical_client.post("/api/retrieval/answer", json={"question": "What is the form code?", "query": {"master_content_id": fixture["item_id"], "query": "SYN-F-001"}}, headers=OWNER)
    assert answer.status_code == 200, answer.text
    assert answer.json()["canonical_state_mutated"] is False
    assert canonical_client.post("/api/retrieval/answer", json={"question": "No access", "query": {"document_version_id": fixture["v1_id"]}}, headers={"X-Dev-Role": "PERMIT_PREPARER"}).json()["citations"] == []


def test_envelope_and_access_context_are_frozen(canonical_client):
    context = RetrievalAccessContext(caller_id="synthetic", role=Role.OWNER_SPONSOR)
    assert context.model_config["frozen"] is True
    try:
        context.caller_id = "changed"
    except (TypeError, ValidationError):
        pass
    else:
        raise AssertionError("retrieval access context must be immutable")
    assert GovernedRetrievalEnvelope.model_config["frozen"] is True


def test_source_intake_reference_authority_is_separate_from_observed_metadata(canonical_client):
    cases = (
        (b"MALFORMED OBSERVED REF", "not a canonical ref", "synthetic://observed-malformed"),
        (b"WRONG TYPE OBSERVED REF", "R-9999", "synthetic://observed-wrong-type"),
        (b"ORDINARY SOURCE OBSERVED REF", "F-ORD-001", "smb://ordinary-source"),
    )
    promoted = []
    for source, observed_ref, location in cases:
        item_id, version_id, row_id = _promote_observed_source(source, observed_ref, location, actor="ordinary-source-worker" if location.startswith("smb:") else "synthetic-reference-auditor")
        promoted.append((item_id, version_id, row_id, observed_ref))

    with SessionLocal() as db:
        for item_id, version_id, row_id, observed_ref in promoted:
            item = db.get(MasterContentItem, item_id)
            version = db.get(DocumentVersion, version_id)
            row = db.get(SourceIntakeItem, row_id)
            assert item.content_type == "FORM"
            assert item.ref != observed_ref
            assert item.ref.startswith("F-")
            assert row.metadata_json["manifest"]["ref"] == observed_ref
            assert version.metadata_json["engineering_metadata"]["source_observed_reference"] == observed_ref


def test_governed_canonical_reference_and_hash_reuse_preserve_single_identity(canonical_client):
    with SessionLocal() as db:
        first = create_master_content(db, content_type="FORM", ref="F-9001", title="Governed official form", category_id=None, description="Synthetic governed reference", filename="official.txt", mime_type="text/plain", content=b"official governed source", actor="OWNER_SPONSOR", idempotency_key=f"governed-reference:{uuid4()}", correlation_id="reference-authority-proof", source_surface="DASHBOARD", used_in=["PERMIT"])
        assert first["ref"] == "F-9001"
        try:
            create_master_content(db, content_type="FORM", ref="F-9001", title="Different source", category_id=None, description="Collision", filename="collision.txt", mime_type="text/plain", content=b"different source", actor="OWNER_SPONSOR", idempotency_key=f"governed-collision:{uuid4()}", correlation_id="reference-authority-proof", source_surface="DASHBOARD", used_in=["PERMIT"])
        except HTTPException as exc:
            assert exc.status_code == 409
            assert exc.detail["code"] == "MASTER_CONTENT_REF_CONFLICT"
        else:
            raise AssertionError("canonical reference collision must be rejected")

    source = b"same source hash cannot fork canonical identity"
    first_id, first_version, _ = _promote_observed_source(source, "F-HASH-A", "synthetic://same-hash-a")
    second_id, second_version, _ = _promote_observed_source(source, "F-HASH-B", "synthetic://same-hash-b")
    assert second_id == first_id
    assert second_version == first_version
    with SessionLocal() as db:
        assert db.scalar(select(func.count(MasterContentItem.id)).where(MasterContentItem.id == first_id)) == 1
