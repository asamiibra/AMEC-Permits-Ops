from __future__ import annotations

import base64
import hashlib
from types import SimpleNamespace

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from backend.app.models import (
    AssertionStatus,
    AuditEvent,
    Base,
    Criticality,
    DataType,
    Document,
    DocumentApprovalState,
    DocumentType,
    DocumentVersion,
    FieldDefinition,
    FieldObservation,
    NotificationEvent,
    Project,
    VerifiedAssertion,
    WorkflowTask,
)
from backend.app.auth.bridge import BridgeIdentity
from backend.app.schemas.bridge_intake import BridgePackageIn
from backend.app.schemas.classifier_v2 import ClassifierV2Request
from backend.app.services.bridge_intake import canonical_signature_payload, ingest_bridge_package
from backend.app.services.classifier_v2 import (
    CLASSIFIER_VERSION,
    RULES_VERSION,
    TAXONOMY_REVISION,
    classify_document,
)
from backend.app.services.document_intelligence import (
    DocumentIntelligenceService,
    normalize_classifier_proposal,
    normalize_field_observation,
)
from backend.app.services.intelligence_contracts import IntelligenceContractError


@pytest.fixture
def db(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'document-intelligence.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
        session.rollback()
    engine.dispose()


def _document_fixture(db: Session, *, project_id: str = "project-a") -> tuple[Document, FieldDefinition, FieldObservation]:
    document = Document(
        project_id=project_id,
        document_type=DocumentType.OTHER,
        logical_name=f"synthetic://document-intelligence/{project_id}",
        language="EN",
        source_system="CONTROLLED_SYNTHETIC",
    )
    definition = FieldDefinition(
        field_code="PROPERTY.PLOT_NUMBER",
        name_en="Plot number",
        data_type=DataType.STRING,
        criticality=Criticality.NORMAL,
        normalization_rule="IDENTIFIER",
        description="Synthetic plot number",
        active=True,
    )
    db.add_all([document, definition])
    db.flush()
    version = DocumentVersion(
        document_id=document.id,
        version_number=1,
        source_filename="synthetic-title.txt",
        source_path_or_reference="synthetic://document-intelligence/v1",
        sha256="a" * 64,
        mime_type="text/plain",
        file_size=4,
        language="EN",
        approval_state=DocumentApprovalState.WORKING,
        source_system="CONTROLLED_SYNTHETIC",
        metadata_json={"synthetic_non_business_fixture": True},
    )
    db.add(version)
    db.flush()
    document.current_version_id = version.id
    observation = FieldObservation(
        project_id=project_id,
        field_definition_id=definition.id,
        document_version_id=version.id,
        raw_value="A-001",
        normalized_candidate_value="A-001",
        structured_value_json={"value": "A-001"},
        extraction_method="RULE",
        extractor_version="synthetic-extractor-v1",
        confidence=0.91,
        correlation_id="di-test-correlation",
    )
    db.add(observation)
    db.flush()
    return document, definition, observation


def _next_observation(db: Session, document: Document, definition: FieldDefinition, *, value: str, version_number: int, project_id: str = "project-a", extractor_version: str = "synthetic-extractor-v1") -> FieldObservation:
    version = DocumentVersion(
        document_id=document.id,
        version_number=version_number,
        source_filename=f"synthetic-title-v{version_number}.txt",
        source_path_or_reference=f"synthetic://document-intelligence/v{version_number}",
        sha256=(str(version_number) * 64)[:64],
        mime_type="text/plain",
        file_size=len(value),
        language="EN",
        approval_state=DocumentApprovalState.WORKING,
        source_system="CONTROLLED_SYNTHETIC",
        metadata_json={"synthetic_non_business_fixture": True},
    )
    db.add(version)
    db.flush()
    observation = FieldObservation(
        project_id=project_id,
        field_definition_id=definition.id,
        document_version_id=version.id,
        raw_value=value,
        normalized_candidate_value=value,
        structured_value_json={"value": value},
        extraction_method="RULE",
        extractor_version=extractor_version,
        confidence=0.88,
        correlation_id="di-test-correlation",
    )
    db.add(observation)
    db.flush()
    return observation


def test_field_observation_is_normalized_with_exact_lineage_and_no_authority(db):
    document, definition, observation = _document_fixture(db)
    before_verified = db.scalar(select(func.count(VerifiedAssertion.id))) or 0
    before_tasks = db.scalar(select(func.count(WorkflowTask.id))) or 0
    before_notifications = db.scalar(select(func.count(NotificationEvent.id))) or 0
    candidate = normalize_field_observation(db, observation, target_module="PERMIT")
    assert candidate.scope_type == "PROJECT"
    assert candidate.scope_id == "project-a"
    assert candidate.project_id == "project-a"
    assert candidate.subject_type == "PROJECT"
    assert candidate.subject_id == "project-a"
    assert candidate.assertion_code == definition.field_code
    assert candidate.producer_kind == "FIELD_OBSERVATION"
    assert candidate.source_document_version_id == observation.document_version_id
    assert candidate.source_observation_id == observation.id
    assert candidate.value_hash == hashlib.sha256(b'{"value":"A-001"}').hexdigest()
    assert candidate.status == "CURRENT"
    assert candidate.promoted_verified_assertion_id is None
    assert (db.scalar(select(func.count(VerifiedAssertion.id))) or 0) == before_verified
    assert (db.scalar(select(func.count(WorkflowTask.id))) or 0) == before_tasks
    assert (db.scalar(select(func.count(NotificationEvent.id))) or 0) == before_notifications
    assert document.current_version_id == observation.document_version_id


def test_exact_replay_and_new_source_version_supersession(db):
    document, definition, first_observation = _document_fixture(db)
    first = normalize_field_observation(db, first_observation)
    replay = normalize_field_observation(db, first_observation)
    assert replay.id == first.id
    second_observation = _next_observation(db, document, definition, value="A-002", version_number=2)
    second = normalize_field_observation(db, second_observation)
    db.flush()
    assert first.status == "SUPERSEDED"
    assert second.status == "CURRENT"
    assert second.supersedes_candidate_assertion_id == first.id
    assert db.get(type(first), first.id) is not None
    assert (db.scalar(select(func.count()).select_from(type(first))) or 0) == 2


def test_different_producers_coexist_without_silent_supersession(db):
    document, definition, first_observation = _document_fixture(db)
    first = normalize_field_observation(db, first_observation)
    other_observation = _next_observation(db, document, definition, value="A-003", version_number=2, extractor_version="other-producer-v1")
    other = normalize_field_observation(db, other_observation)
    assert first.status == "CURRENT"
    assert other.status == "CURRENT"
    assert other.supersedes_candidate_assertion_id is None


def test_supersession_rolls_back_as_one_unit(db, monkeypatch):
    document, definition, first_observation = _document_fixture(db)
    first = normalize_field_observation(db, first_observation)
    second_observation = _next_observation(db, document, definition, value="A-004", version_number=2)
    service = DocumentIntelligenceService(db)

    def fail_after_family_resolution(_prior):
        raise RuntimeError("forced supersession failure")

    monkeypatch.setattr(service, "_mark_superseded", fail_after_family_resolution)
    with pytest.raises(RuntimeError, match="forced supersession failure"):
        service.from_field_observation(second_observation)
    db.expire_all()
    assert db.get(type(first), first.id).status == "CURRENT"
    assert (db.scalar(select(func.count()).select_from(type(first))) or 0) == 1


def test_classifier_adapter_preserves_envelope_and_controls(db):
    payload = ClassifierV2Request(
        fixture_id="classifier-adapter-fixture",
        source_artifact_id="synthetic-artifact://classifier/document-1",
        source_version_token="v1",
        source_mode="MOVE_RENAME_CANDIDATE",
        scope_type="PROJECT",
        scope_id="project-a",
        correlation_id="classifier-adapter-correlation",
        evidence_ids=["synthetic-evidence://classifier/1"],
        candidate_entity_id="project-a",
        contradiction_families=["CURRENTNESS_CONFLICT"],
    )
    proposal = classify_document(payload)
    before = db.scalar(select(func.count(VerifiedAssertion.id))) or 0
    candidates = normalize_classifier_proposal(
        db,
        scope_type=payload.scope_type,
        scope_id=payload.scope_id,
        correlation_id=payload.correlation_id,
        source_artifact_id=payload.source_artifact_id,
        proposal=proposal,
        classifier_version=CLASSIFIER_VERSION,
        rules_version=RULES_VERSION,
        taxonomy_revision=TAXONOMY_REVISION,
        evidence_envelope_id="evidence-classifier-1",
    )
    assert len(candidates) == 2
    assert {candidate.assertion_code for candidate in candidates} == {"DOCUMENT_CLASSIFICATION_CANDIDATE", "DOCUMENT_RELATIONSHIP_CANDIDATE"}
    assert all(candidate.producer_kind == "DOCUMENT_CLASSIFIER" for candidate in candidates)
    assert all(candidate.evidence_envelope_id == "evidence-classifier-1" for candidate in candidates)
    assert proposal["auto_promotion_allowed"] is False
    assert proposal["projection_allowed"] is False
    assert proposal["llm"]["real_content_mode"] == "DISABLED"
    assert (db.scalar(select(func.count(VerifiedAssertion.id))) or 0) == before
    assert (db.scalar(select(func.count(WorkflowTask.id))) or 0) == 0
    assert (db.scalar(select(func.count(NotificationEvent.id))) or 0) == 0


def test_cross_project_source_binding_fails_closed(db):
    document, definition, observation = _document_fixture(db, project_id="project-a")
    with pytest.raises(IntelligenceContractError, match="DOCUMENT_INTELLIGENCE_SOURCE_PROJECT_MISMATCH"):
        mismatched = _next_observation(db, document, definition, value="B-001", version_number=2, project_id="project-b")
        normalize_field_observation(db, mismatched)


def test_bridge_creates_governed_objects_and_candidates_without_promotion(db):
    project = Project(
        project_number="SYN-P03-001",
        project_name="Synthetic P03 Project",
        office_id="synthetic-office",
        workstream="ENGINEERING",
        status="ACTIVE",
        municipality="Doha",
        permit_type="Building Permit",
    )
    definition = FieldDefinition(
        field_code="P03.FIELD",
        name_en="P03 field",
        data_type=DataType.STRING,
        criticality=Criticality.NORMAL,
        normalization_rule="IDENTIFIER",
        description="Synthetic P03 bridge field",
        active=True,
    )
    db.add_all([project, definition])
    db.flush()
    private_key = Ed25519PrivateKey.generate()
    content = b"synthetic-p03-bridge"
    values = {
        "attempt_id": "p03-bridge-attempt-001",
        "source_identity": "QATAR_SYNOLOGY_SYNTHETIC_FIXTURE",
        "source_path_snapshot": "synthetic://qatar-synology/p03-001.bin",
        "size_bytes": len(content),
        "mtime_utc": "2026-09-13T00:00:00Z",
        "payload_sha256": hashlib.sha256(content).hexdigest(),
        "payload_b64": base64.b64encode(content).decode(),
        "signature_b64": "pending",
        "source_version_token": "p03-v1",
        "correlation_id": "p03-bridge-correlation",
        "scope_type": "PROJECT",
        "scope_id": project.id,
        "project_id": project.id,
        "field_definition_id": definition.id,
        "field_raw_value": "P03-VALUE",
    }
    unsigned = BridgePackageIn(**values)
    values["signature_b64"] = base64.b64encode(private_key.sign(canonical_signature_payload(unsigned))).decode()
    payload = BridgePackageIn(**values)
    settings = SimpleNamespace(
        bridge_package_signing_public_key=base64.b64encode(private_key.public_key().public_bytes_raw()).decode(),
        bridge_allowed_source_identities="QATAR_SYNOLOGY_SYNTHETIC_FIXTURE",
        bridge_allowed_source_path_prefixes="synthetic://qatar-synology/",
        bridge_max_payload_bytes=1024,
    )
    identity = BridgeIdentity("tenant", "client", "bridge-object", "audience", "proposalops.source-intake")
    result = ingest_bridge_package(db, payload, identity, settings)
    assert result["verified_assertion_created"] is False
    assert result["projection_created"] is False
    assert len(result["candidate_assertion_ids"]) == 2
    replay = ingest_bridge_package(db, payload, identity, settings)
    assert replay["result"] == "IDEMPOTENT"
    assert replay["candidate_assertion_ids"] == result["candidate_assertion_ids"]
    assert (db.scalar(select(func.count(VerifiedAssertion.id))) or 0) == 0
    assert (db.scalar(select(func.count(WorkflowTask.id))) or 0) == 0
    assert (db.scalar(select(func.count(NotificationEvent.id))) or 0) == 0
