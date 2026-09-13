from __future__ import annotations

from copy import deepcopy

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from backend.app.models import (
    AssertionStatus,
    ConsultancyOffice,
    ContentCategory,
    ContextDependency,
    ContextSnapshot,
    Criticality,
    DataType,
    DefinitionEntry,
    DefinitionRevision,
    Document,
    DocumentApprovalState,
    DocumentType,
    DocumentVersion,
    ExtractionMethod,
    FieldDefinition,
    FieldObservation,
    MasterContentGovernanceProfile,
    MasterContentItem,
    MasterContentModuleBinding,
    NotificationEvent,
    Phase4DocumentEvidenceEnvelope,
    Phase4ProjectionPlan,
    Phase4ProjectionReceipt,
    Phase4ReviewDecision,
    Project,
    Role,
    User,
    VerifiedAssertion,
    WorkflowTask,
)
from backend.app.models.intelligence_entities import CandidateAssertion
from backend.app.services import backend_realignment
from backend.app.services.context_compiler import (
    ContextCompileRequest,
    ContextSourceSpec,
    ContextCompiler,
    compile_context,
)
from backend.app.services.intelligence_contracts import (
    IntelligenceContractError,
    build_skill_manifest,
    stable_hash,
)


@pytest.fixture
def db(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'context-compiler.db'}")
    from backend.app.models import Base

    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
        session.rollback()
    engine.dispose()


@pytest.fixture
def corpus(db):
    office = ConsultancyOffice(id="office-a", office_code="SYN-OFFICE", name_en="Synthetic Office", name_ar="مكتب اصطناعي", status="ACTIVE")
    project_a = Project(id="project-a", project_number="SYN-001", project_name="Synthetic Project A", office_id=office.id, workstream="PERMIT", status="ACTIVE", municipality="Doha", permit_type="BUILDING", project_code="SYNTHETIC-A")
    project_b = Project(id="project-b", project_number="SYN-002", project_name="Synthetic Project B", office_id=office.id, workstream="PERMIT", status="ACTIVE", municipality="Doha", permit_type="BUILDING", project_code="SYNTHETIC-B")
    owner = User(id="user-owner", email="owner@example.test", display_name="Synthetic Owner", role=Role.OWNER_SPONSOR, active=True, office_id=office.id)
    inactive = User(id="user-inactive", email="inactive@example.test", display_name="Inactive User", role=Role.OWNER_SPONSOR, active=False, office_id=office.id)
    engineer = User(id="user-engineer", email="engineer@example.test", display_name="Synthetic Engineer", role=Role.RESPONSIBLE_ENGINEER, active=True, office_id=office.id)
    field = FieldDefinition(id="field-area", field_code="PLOT_AREA", name_en="Plot area", name_ar="مساحة الأرض", data_type=DataType.NUMBER, criticality=Criticality.NORMAL, normalization_rule="DECIMAL", description="Synthetic plot area", active=True)
    db.add_all([office, project_a, project_b, owner, inactive, engineer, field])
    db.flush()

    document = Document(id="doc-a", project_id=project_a.id, document_type=DocumentType.TITLE_DEED, logical_name="Synthetic title deed", language="en", source_system="SYNTHETIC_FIXTURE")
    version = DocumentVersion(id="version-a", document_id=document.id, version_number=1, source_filename="title-deed.txt", source_path_or_reference="synthetic-db://project-a/title-deed.txt", sha256="a" * 64, mime_type="text/plain", file_size=10, language="en", approval_state=DocumentApprovalState.REVIEWED, source_system="SYNTHETIC_FIXTURE", metadata_json={"synthetic_non_business_fixture": True})
    document.current_version_id = version.id
    observation = FieldObservation(id="observation-a", project_id=project_a.id, field_definition_id=field.id, document_version_id=version.id, raw_value="100", normalized_candidate_value="100", structured_value_json={"value": 100}, extraction_method=ExtractionMethod.RULE, extractor_version="fixture-v1", confidence=0.9, correlation_id="fixture-observation")
    db.add_all([document, version, observation])
    db.flush()

    candidate = CandidateAssertion(id="candidate-a", idempotency_key="fixture-candidate-a", correlation_id="candidate-correlation", scope_type="PROJECT", scope_id=project_a.id, project_id=project_a.id, target_module="ENGINEERING", subject_type="PROJECT", subject_id=project_a.id, assertion_code="PLOT_AREA", field_definition_id=field.id, value_json={"value": 100}, display_value="100", value_hash=stable_hash({"value": 100}), confidence=0.9, producer_kind="FIXTURE", producer_version="1", producer_hash="b" * 64, source_document_version_id=version.id, source_observation_id=observation.id, data_classification="SYNTHETIC", contains_sensitive_data=False, status="CURRENT")
    verified = VerifiedAssertion(id="verified-a", scope_type="PROJECT", scope_id=project_a.id, project_id=project_a.id, subject_type="PROJECT", subject_id=project_a.id, field_definition_id=field.id, semantic_value_json={"value": 100}, display_value="100", status=AssertionStatus.CURRENT, source_observation_id=observation.id, verification_method="HUMAN_VERIFIED", verified_by=owner.id, verified_by_capability="PROMOTE_SOR", verification_origin_module="ENGINEERING", review_decision_reference="fixture-review")
    evidence = Phase4DocumentEvidenceEnvelope(id="evidence-a", root_event_id="root-event-a", source_artifact_id="synthetic-artifact-a", source_version_id=version.id, source_version_token="version-a", source_surface="CONTROLLED_SYNTHETIC_FIXTURE", evidence_envelope_sha256="c" * 64, document_intelligence_runtime_version="fixture-runtime-v1", runtime_sha256="d" * 64, capability_id="PHASE5_METADATA_CLASSIFICATION", handler_parser_identity="fixture-parser-v1", metering_json={"external_calls": 0}, warnings_json=["SYNTHETIC_METADATA_ONLY"], content_retention_class="METADATA_ONLY", evidence_json={"evidence_ids": ["synthetic-evidence"]})
    db.add_all([candidate, verified, evidence])
    db.flush()

    master_document = Document(id="master-doc-a", project_id=None, document_type=DocumentType.OTHER, logical_name="Synthetic proposal template", language="en", source_system="MASTER_CONTENT")
    master_version = DocumentVersion(id="master-version-a", document_id=master_document.id, version_number=1, source_filename="proposal-template.txt", source_path_or_reference="synthetic-db://master/proposal-template.txt", sha256="e" * 64, mime_type="text/plain", file_size=10, language="en", approval_state=DocumentApprovalState.REVIEWED, source_system="MASTER_CONTENT", metadata_json={"master_status": "CURRENT", "synthetic_only": True})
    master_document.current_version_id = master_version.id
    category = ContentCategory(id="category-form", code="FORM", label="Forms", allowed_content_types=["FORM"], source_kind="SYNTHETIC_CONFIGURABLE")
    master_item = MasterContentItem(id="master-item-a", ref="SYN-FORM-001", content_type="FORM", title="Synthetic Proposal Template", category_id=category.id, used_in=["BD"], status="ACTIVE", needs_review=False, document_id=master_document.id, current_document_version_id=master_version.id, created_by="fixture")
    profile = MasterContentGovernanceProfile(master_content_item_id=master_item.id, content_ownership_class="AMEC_OWNED", artifact_kind="FORM", sensitivity_class="NONE", currentness_status="VERIFIED_CURRENT", restricted_reference_sample=False)
    binding = MasterContentModuleBinding(master_content_id=master_item.id, module="BD", usage_type="PROPOSAL_TEMPLATE", active=True, created_by="fixture")
    db.add_all([master_document, master_version, category, master_item, profile, binding])
    db.flush()

    definition = DefinitionEntry(id="definition-a", ref="SYN-DEF-001", term="Synthetic permit", category="PERMIT", used_in=["ENGINEERING"], status="ACTIVE", current_revision_id="definition-revision-a", created_by="fixture")
    revision = DefinitionRevision(id="definition-revision-a", definition_id=definition.id, revision_number=1, term="Synthetic permit", description="Synthetic permit definition", category="PERMIT", used_in=["ENGINEERING"], aliases=[], changed_by="fixture", status="CURRENT")
    db.add_all([definition, revision])
    db.flush()
    return {"office": office, "project_a": project_a, "project_b": project_b, "owner": owner, "inactive": inactive, "engineer": engineer, "field": field, "document": document, "version": version, "observation": observation, "candidate": candidate, "verified": verified, "evidence": evidence, "master_item": master_item, "master_version": master_version, "master_document": master_document, "profile": profile, "definition": definition, "revision": revision}


def manifest(*, contexts, floor="CANDIDATE", module="ENGINEERING", scopes=("PROJECT",), **overrides):
    values = {
        "skill_id": "fixture.skill",
        "version": "1.0",
        "owning_module": module,
        "input_schema_version": "1",
        "output_schema_version": "1",
        "allowed_scope_types": list(scopes),
        "allowed_context_types": list(contexts),
        "input_trust_floor": floor,
        "allowed_tools": [],
        "model_policy": {"provider": "NONE"},
        "output_class": "ANALYSIS",
        "review_trigger": "ALWAYS",
        "dependency_capture": {"required": True},
        "invalidation": {"on": list(contexts)},
        "eval_pack_version": "fixture-v1",
    }
    values.update(overrides)
    return build_skill_manifest(**values)


def request(manifest_value, *sources, actor="user-owner", project="project-a", **overrides):
    values = {
        "correlation_id": "compile-correlation",
        "actor_user_id": actor,
        "scope_type": "PROJECT",
        "scope_id": project,
        "project_id": project,
        "context_schema_version": "1",
        "policy_version": "policy-v1",
        "skill_manifest": manifest_value,
        "sources": list(sources),
    }
    values.update(overrides)
    return ContextCompileRequest(**values)


def source(key, context_type, selector, required=True):
    return ContextSourceSpec(key=key, context_type=context_type, selector=selector, required=required)


def counts(db):
    return {model.__tablename__: db.scalar(select(func.count()).select_from(model)) for model in (ContextSnapshot, ContextDependency, VerifiedAssertion, Phase4ReviewDecision, Phase4ProjectionPlan, Phase4ProjectionReceipt, WorkflowTask, NotificationEvent)}


def test_candidate_dependency_vocabulary_and_positive_candidate_context(db, corpus):
    req = request(manifest(contexts=("CANDIDATE_ASSERTION",)), source("candidate", "CANDIDATE_ASSERTION", {"id": corpus["candidate"].id}))
    compiled = compile_context(db, req)
    assert compiled.items[0].dependency_type == "CANDIDATE_ASSERTION"
    dependency = db.scalar(select(ContextDependency).where(ContextDependency.context_snapshot_id == compiled.context_snapshot_id))
    assert dependency.dependency_id == corpus["candidate"].id
    assert dependency.dependency_version_or_hash
    assert dependency.trust_state == "CANDIDATE"
    assert dependency.metadata_json["candidate_value_hash"] == corpus["candidate"].value_hash
    assert compiled.synthetic_only is True


def test_verified_business_context_reuses_authoritative_sources(db, corpus):
    m = manifest(contexts=("VERIFIED_ASSERTION", "MASTER_CONTENT", "DOMAIN_ENTITY_REVISION"), floor="VERIFIED")
    compiled = compile_context(db, request(m,
        source("project", "DOMAIN_ENTITY_REVISION", {"entity_type": "PROJECT", "entity_id": "project-a"}),
        source("master", "MASTER_CONTENT", {"master_content_item_id": "master-item-a", "document_version_id": "master-version-a", "content_type": "FORM"}),
        source("verified", "VERIFIED_ASSERTION", {"id": "verified-a"}),
    ))
    assert {item.dependency_type for item in compiled.items} == {"DOMAIN_ENTITY_REVISION", "MASTER_CONTENT_VERSION", "VERIFIED_ASSERTION"}
    assert all(item.trust_state in {"VERIFIED", "CANONICAL"} for item in compiled.items)
    assert db.scalar(select(ContextSnapshot).where(ContextSnapshot.id == compiled.context_snapshot_id)).dependency_count == 3
    assert compiled.contains_sensitive_data is False


def test_actor_is_server_derived_and_authorization_hash_changes_with_capability_state(db, corpus, monkeypatch):
    m = manifest(contexts=("DOMAIN_ENTITY_REVISION",))
    first = compile_context(db, request(m, source("project", "DOMAIN_ENTITY_REVISION", {"entity_type": "PROJECT", "entity_id": "project-a"})))
    second = compile_context(db, request(m, source("project", "DOMAIN_ENTITY_REVISION", {"entity_type": "PROJECT", "entity_id": "project-a"}), correlation_id="different-correlation"))
    assert first.actor_persona == "OWNER"
    assert first.authorization_context_hash == second.authorization_context_hash
    original = set(backend_realignment.CAPABILITY_MATRIX["OWNER"])
    monkeypatch.setitem(backend_realignment.CAPABILITY_MATRIX, "OWNER", original | {"P04_TEST_CAPABILITY"})
    third = compile_context(db, request(m, source("project", "DOMAIN_ENTITY_REVISION", {"entity_type": "PROJECT", "entity_id": "project-a"})))
    assert first.context_hash == second.context_hash
    assert first.context_snapshot_id == second.context_snapshot_id
    assert third.authorization_context_hash != first.authorization_context_hash
    assert third.context_hash != first.context_hash


def test_context_hash_is_source_order_independent_and_dependencies_are_idempotent(db, corpus):
    m = manifest(contexts=("CANDIDATE_ASSERTION", "DOCUMENT_VERSION"))
    a = source("candidate", "CANDIDATE_ASSERTION", {"id": "candidate-a"})
    b = source("document", "DOCUMENT_VERSION", {"id": "version-a"})
    first = compile_context(db, request(m, a, b))
    second = compile_context(db, request(m, b, a))
    assert first.context_hash == second.context_hash
    assert first.context_snapshot_id == second.context_snapshot_id
    assert db.scalar(select(ContextSnapshot).where(ContextSnapshot.id == first.context_snapshot_id)).dependency_count == 2
    assert db.scalar(select(func.count()).select_from(ContextSnapshot)) == 1
    assert db.scalar(select(func.count()).select_from(ContextDependency)) == 2


@pytest.mark.parametrize("status", ["SUPERSEDED", "STALE", "REJECTED", "PROMOTED"])
def test_non_current_candidate_states_fail_closed(db, corpus, status):
    corpus["candidate"].status = status
    before = counts(db)
    with pytest.raises(IntelligenceContractError, match="CONTEXT_CANDIDATE_NOT_CURRENT"):
        compile_context(db, request(manifest(contexts=("CANDIDATE_ASSERTION",)), source("candidate", "CANDIDATE_ASSERTION", {"id": "candidate-a"})))
    assert counts(db) == before


def test_candidate_trust_floor_and_target_module_are_enforced(db, corpus):
    with pytest.raises(IntelligenceContractError, match="CONTEXT_TRUST_FLOOR_NOT_MET"):
        compile_context(db, request(manifest(contexts=("CANDIDATE_ASSERTION",), floor="VERIFIED"), source("candidate", "CANDIDATE_ASSERTION", {"id": "candidate-a"})))
    corpus["candidate"].target_module = "BD"
    with pytest.raises(IntelligenceContractError, match="CONTEXT_CANDIDATE_MODULE_MISMATCH"):
        compile_context(db, request(manifest(contexts=("CANDIDATE_ASSERTION",), module="ENGINEERING"), source("candidate", "CANDIDATE_ASSERTION", {"id": "candidate-a"})))


def test_source_specific_restricted_capability_is_not_inferred_from_read_all(db, corpus):
    corpus["candidate"].contains_sensitive_data = True
    corpus["candidate"].data_classification = "RESTRICTED"
    before = {
        "context_snapshots": db.scalar(select(func.count()).select_from(ContextSnapshot)),
        "context_dependencies": db.scalar(select(func.count()).select_from(ContextDependency)),
    }
    with pytest.raises(IntelligenceContractError, match="CONTEXT_SOURCE_CAPABILITY_DENIED"):
        compile_context(db, request(manifest(contexts=("CANDIDATE_ASSERTION",), module="ENGINEERING"), source("candidate", "CANDIDATE_ASSERTION", {"id": "candidate-a"}), actor="user-engineer"))
    assert {
        "context_snapshots": db.scalar(select(func.count()).select_from(ContextSnapshot)),
        "context_dependencies": db.scalar(select(func.count()).select_from(ContextDependency)),
    } == before


@pytest.mark.parametrize("actor,code", [("missing-user", "CONTEXT_ACTOR_NOT_FOUND"), ("user-inactive", "CONTEXT_ACTOR_INACTIVE")])
def test_actor_existence_and_active_state_are_required(db, corpus, actor, code):
    with pytest.raises(IntelligenceContractError, match=code):
        compile_context(db, request(manifest(contexts=("POLICY_VERSION",)), source("policy", "POLICY_VERSION", {}), actor=actor))


def test_caller_cannot_spoof_persona_or_capabilities(db, corpus):
    values = request(manifest(contexts=("POLICY_VERSION",)), source("policy", "POLICY_VERSION", {})).model_dump()
    values["actor_persona"] = "ENGINEERING"
    with pytest.raises(IntelligenceContractError, match="CONTEXT_REQUEST_INVALID"):
        compile_context(db, values)


def test_manifest_scope_context_and_authority_controls(db, corpus):
    with pytest.raises(IntelligenceContractError, match="CONTEXT_SCOPE_TYPE_NOT_ALLOWED"):
        compile_context(db, request(manifest(contexts=("POLICY_VERSION",), scopes=("GLOBAL",)), source("policy", "POLICY_VERSION", {})))
    with pytest.raises(IntelligenceContractError, match="CONTEXT_TYPE_NOT_ALLOWED"):
        compile_context(db, request(manifest(contexts=("POLICY_VERSION",)), source("candidate", "CANDIDATE_ASSERTION", {"id": "candidate-a"})))
    with pytest.raises(ValueError, match="INTELLIGENCE_CANONICAL_WRITE_AUTHORITY_FORBIDDEN"):
        manifest(contexts=("POLICY_VERSION",), canonical_or_protected_authority="CANONICAL")


@pytest.mark.parametrize("kind", ["candidate", "document", "verified", "domain"])
def test_cross_project_sources_fail_closed(db, corpus, kind):
    if kind == "candidate":
        source_spec = source("candidate", "CANDIDATE_ASSERTION", {"id": "candidate-b"})
        other = CandidateAssertion(id="candidate-b", idempotency_key="fixture-candidate-b", correlation_id="b", scope_type="PROJECT", scope_id="project-b", project_id="project-b", subject_type="PROJECT", subject_id="project-b", assertion_code="PLOT_AREA", value_json={"value": 200}, value_hash=stable_hash({"value": 200}), producer_kind="FIXTURE", producer_version="1", producer_hash="f" * 64, data_classification="SYNTHETIC", status="CURRENT")
        db.add(other)
        db.flush()
        m = manifest(contexts=("CANDIDATE_ASSERTION",))
    elif kind == "document":
        document = Document(id="doc-b", project_id="project-b", document_type=DocumentType.TITLE_DEED, logical_name="B", language="en", source_system="SYNTHETIC_FIXTURE")
        version = DocumentVersion(id="version-b", document_id=document.id, version_number=1, source_filename="b.txt", source_path_or_reference="synthetic-db://b", sha256="b" * 64, mime_type="text/plain", file_size=1, language="en", approval_state=DocumentApprovalState.REVIEWED, source_system="SYNTHETIC_FIXTURE", metadata_json={"synthetic_only": True})
        document.current_version_id = version.id
        db.add_all([document, version])
        db.flush()
        source_spec = source("document", "DOCUMENT_VERSION", {"id": "version-b"})
        m = manifest(contexts=("DOCUMENT_VERSION",))
    elif kind == "verified":
        other_obs = FieldObservation(id="observation-b", project_id="project-b", field_definition_id="field-area", document_version_id="version-b", raw_value="200", normalized_candidate_value="200", structured_value_json={"value": 200}, extraction_method=ExtractionMethod.RULE, extractor_version="fixture-v1", correlation_id="b")
        other = VerifiedAssertion(id="verified-b", scope_type="PROJECT", scope_id="project-b", project_id="project-b", subject_type="PROJECT", subject_id="project-b", field_definition_id="field-area", semantic_value_json={"value": 200}, display_value="200", status=AssertionStatus.CURRENT, source_observation_id="observation-b", verification_method="HUMAN_VERIFIED", verified_by="user-owner")
        document = Document(id="doc-b", project_id="project-b", document_type=DocumentType.TITLE_DEED, logical_name="B", language="en", source_system="SYNTHETIC_FIXTURE")
        version = DocumentVersion(id="version-b", document_id=document.id, version_number=1, source_filename="b.txt", source_path_or_reference="synthetic-db://b", sha256="b" * 64, mime_type="text/plain", file_size=1, language="en", approval_state=DocumentApprovalState.REVIEWED, source_system="SYNTHETIC_FIXTURE", metadata_json={"synthetic_only": True})
        document.current_version_id = version.id
        db.add_all([document, version, other_obs, other])
        db.flush()
        source_spec = source("verified", "VERIFIED_ASSERTION", {"id": "verified-b"})
        m = manifest(contexts=("VERIFIED_ASSERTION",), floor="VERIFIED")
    else:
        source_spec = source("project", "DOMAIN_ENTITY_REVISION", {"entity_type": "PROJECT", "entity_id": "project-b"})
        m = manifest(contexts=("DOMAIN_ENTITY_REVISION",))
    before = counts(db)
    with pytest.raises(IntelligenceContractError, match="CONTEXT_CROSS_PROJECT_SOURCE"):
        compile_context(db, request(m, source_spec))
    assert counts(db) == before


def test_current_document_and_evidence_lineage_are_required(db, corpus):
    m = manifest(contexts=("DOCUMENT_VERSION", "PHASE4_DOCUMENT_EVIDENCE_ENVELOPE"), floor="GOVERNED_EVIDENCE")
    compiled = compile_context(db, request(m, source("document", "DOCUMENT_VERSION", {"id": "version-a"}), source("evidence", "PHASE4_DOCUMENT_EVIDENCE_ENVELOPE", {"id": "evidence-a"})))
    assert {item.dependency_type for item in compiled.items} == {"DOCUMENT_VERSION", "EVIDENCE_ENVELOPE"}
    corpus["document"].current_version_id = None
    with pytest.raises(IntelligenceContractError, match="CONTEXT_CURRENTNESS"):
        compile_context(db, request(m, source("document", "DOCUMENT_VERSION", {"id": "version-a"})))
    assert compiled.context_snapshot_id


def test_verified_assertion_consumption_is_current_lineage_bound_and_read_only(db, corpus):
    before = counts(db)
    compiled = compile_context(db, request(manifest(contexts=("VERIFIED_ASSERTION",), floor="VERIFIED"), source("verified", "VERIFIED_ASSERTION", {"id": "verified-a"})))
    assert compiled.items[0].dependency_type == "VERIFIED_ASSERTION"
    assert counts(db)["verified_assertions"] == before["verified_assertions"]
    corpus["verified"].status = AssertionStatus.SUPERSEDED
    with pytest.raises(IntelligenceContractError, match="CONTEXT_VERIFIED_ASSERTION_NOT_CURRENT"):
        compile_context(db, request(manifest(contexts=("VERIFIED_ASSERTION",), floor="VERIFIED"), source("verified", "VERIFIED_ASSERTION", {"id": "verified-a"}), policy_version="policy-v2"))


def test_master_content_exact_binding_and_ambiguity_fail_closed(db, corpus):
    m = manifest(contexts=("MASTER_CONTENT",), floor="CANONICAL")
    compiled = compile_context(db, request(m, source("master", "MASTER_CONTENT", {"master_content_item_id": "master-item-a", "document_version_id": "master-version-a", "content_type": "FORM"})))
    assert compiled.items[0].dependency_type == "MASTER_CONTENT_VERSION"
    second_document = Document(id="master-doc-b", project_id=None, document_type=DocumentType.OTHER, logical_name="Second", language="en", source_system="MASTER_CONTENT")
    second_version = DocumentVersion(id="master-version-b", document_id=second_document.id, version_number=1, source_filename="second.txt", source_path_or_reference="synthetic-db://master/second", sha256="1" * 64, mime_type="text/plain", file_size=1, language="en", approval_state=DocumentApprovalState.REVIEWED, source_system="MASTER_CONTENT", metadata_json={"master_status": "CURRENT", "synthetic_only": True})
    second_document.current_version_id = second_version.id
    second_item = MasterContentItem(id="master-item-b", ref="SYN-FORM-002", content_type="FORM", title="Second", category_id="category-form", used_in=["BD"], status="ACTIVE", needs_review=False, document_id=second_document.id, current_document_version_id=second_version.id, created_by="fixture")
    second_profile = MasterContentGovernanceProfile(master_content_item_id=second_item.id, content_ownership_class="AMEC_OWNED", artifact_kind="FORM", sensitivity_class="NONE", currentness_status="VERIFIED_CURRENT")
    second_binding = MasterContentModuleBinding(master_content_id=second_item.id, module="BD", usage_type="PROPOSAL_TEMPLATE", active=True, created_by="fixture")
    db.add_all([second_document, second_version, second_item, second_profile, second_binding])
    db.flush()
    with pytest.raises(IntelligenceContractError, match="CONTEXT_MASTER_CONTENT_AMBIGUOUS"):
        compile_context(db, request(m, source("master", "MASTER_CONTENT", {"module": "BD", "usage_type": "PROPOSAL_TEMPLATE"}), policy_version="policy-v2"))
    corpus["master_version"].approval_state = DocumentApprovalState.WORKING
    with pytest.raises(IntelligenceContractError, match="CONTEXT_MASTER_CONTENT_DOCUMENT_VERSION_NOT_REVIEWED"):
        compile_context(db, request(m, source("master", "MASTER_CONTENT", {"master_content_item_id": "master-item-a", "document_version_id": "master-version-a", "content_type": "FORM"}), policy_version="policy-v3"))


def test_optional_absence_is_deterministic_but_optional_bad_source_is_not_omitted(db, corpus):
    m = manifest(contexts=("CANDIDATE_ASSERTION",))
    optional_missing = source("optional", "CANDIDATE_ASSERTION", {"id": "missing"}, required=False)
    first = compile_context(db, request(m, optional_missing))
    present = compile_context(db, request(m, source("optional", "CANDIDATE_ASSERTION", {"id": "candidate-a"})))
    assert first.omissions[0].reason == "ABSENT"
    assert first.context_hash != present.context_hash
    corpus["candidate"].status = "STALE"
    with pytest.raises(IntelligenceContractError, match="CONTEXT_CANDIDATE_NOT_CURRENT"):
        compile_context(db, request(m, source("optional", "CANDIDATE_ASSERTION", {"id": "candidate-a"}, required=False), policy_version="policy-v2"))


def test_policy_version_is_exact_and_source_order_does_not_allow_arbitrary_queries(db, corpus):
    with pytest.raises(IntelligenceContractError, match="CONTEXT_POLICY_VERSION_MISMATCH"):
        compile_context(db, request(manifest(contexts=("POLICY_VERSION",)), source("policy", "POLICY_VERSION", {"version": "policy-v2"})))
    with pytest.raises(ValueError, match="CONTEXT_SELECTOR_ARBITRARY_PAYLOAD_FORBIDDEN"):
        ContextSourceSpec(key="bad", context_type="POLICY_VERSION", selector={"raw_sql": "SELECT 1"})


def test_privacy_minimization_and_no_authority_side_effects(db, corpus):
    before = counts(db)
    corpus["candidate"].value_json = {"raw_text": "synthetic source text"}
    with pytest.raises(IntelligenceContractError, match="CONTEXT_RAW_SOURCE_FORBIDDEN"):
        compile_context(db, request(manifest(contexts=("CANDIDATE_ASSERTION",)), source("candidate", "CANDIDATE_ASSERTION", {"id": "candidate-a"})))
    assert counts(db) == before
    corpus["candidate"].value_json = {"value": 100}
    compiled = compile_context(db, request(manifest(contexts=("CANDIDATE_ASSERTION",)), source("candidate", "CANDIDATE_ASSERTION", {"id": "candidate-a"})))
    dependency = db.scalar(select(ContextDependency).where(ContextDependency.context_snapshot_id == compiled.context_snapshot_id))
    assert not {"raw", "text", "bytes", "prompt", "output", "secret", "token", "authorization"} & {key.lower() for key in dependency.metadata_json}
    assert counts(db)["verified_assertions"] == before["verified_assertions"]
    assert counts(db)["phase4_review_decisions"] == before["phase4_review_decisions"]
    assert counts(db)["phase4_projection_plans"] == before["phase4_projection_plans"]
    assert counts(db)["phase4_projection_receipts"] == before["phase4_projection_receipts"]
    assert counts(db)["workflow_tasks"] == before["workflow_tasks"]
    assert counts(db)["notification_events"] == before["notification_events"]


def test_required_missing_source_and_persistence_failure_leave_no_partial_snapshot(db, corpus, monkeypatch):
    before = {
        "context_snapshots": db.scalar(select(func.count()).select_from(ContextSnapshot)),
        "context_dependencies": db.scalar(select(func.count()).select_from(ContextDependency)),
    }
    with pytest.raises(IntelligenceContractError, match="CONTEXT_REQUIRED_SOURCE_MISSING"):
        compile_context(db, request(manifest(contexts=("CANDIDATE_ASSERTION",)), source("missing", "CANDIDATE_ASSERTION", {"id": "missing"})))
    assert {
        "context_snapshots": db.scalar(select(func.count()).select_from(ContextSnapshot)),
        "context_dependencies": db.scalar(select(func.count()).select_from(ContextDependency)),
    } == before

    import backend.app.services.context_compiler as compiler_module

    def fail(*args, **kwargs):
        raise IntelligenceContractError("P04_TEST_PERSISTENCE_FAILURE")

    monkeypatch.setattr(compiler_module, "record_context_dependency", fail)
    with pytest.raises(IntelligenceContractError, match="P04_TEST_PERSISTENCE_FAILURE"):
        compile_context(db, request(manifest(contexts=("CANDIDATE_ASSERTION",)), source("candidate", "CANDIDATE_ASSERTION", {"id": "candidate-a"}), policy_version="policy-v2"))
    db.rollback()
    assert {
        "context_snapshots": db.scalar(select(func.count()).select_from(ContextSnapshot)),
        "context_dependencies": db.scalar(select(func.count()).select_from(ContextDependency)),
    } == before


def test_definition_revision_and_project_projection_are_explicit_and_current(db, corpus):
    m = manifest(contexts=("DEFINITION_REVISION", "DOMAIN_ENTITY_REVISION"), floor="CANONICAL")
    compiled = compile_context(db, request(m, source("definition", "DEFINITION_REVISION", {"id": "definition-revision-a"}), source("project", "DOMAIN_ENTITY_REVISION", {"entity_type": "PROJECT", "entity_id": "project-a"})))
    assert {item.dependency_type for item in compiled.items} == {"DEFINITION_REVISION", "DOMAIN_ENTITY_REVISION"}
    assert "__dict__" not in str(compiled.items)
    corpus["revision"].status = "STALE"
    with pytest.raises(IntelligenceContractError, match="CONTEXT_DEFINITION_REVISION_NOT_CURRENT"):
        compile_context(db, request(m, source("definition", "DEFINITION_REVISION", {"id": "definition-revision-a"}), policy_version="policy-v2"))


def test_context_source_schema_rejects_arbitrary_model_and_payload_fields():
    with pytest.raises(ValueError, match="CONTEXT_SELECTOR_ARBITRARY_PAYLOAD_FORBIDDEN"):
        ContextSourceSpec(key="bad", context_type="DOMAIN_ENTITY_REVISION", selector={"model": "Project"})
    with pytest.raises(ValueError):
        ContextCompileRequest.model_validate({"correlation_id": "c", "actor_user_id": "a", "scope_type": "PROJECT", "scope_id": "p", "project_id": "p", "context_schema_version": "1", "policy_version": "1", "skill_manifest": {}, "sources": [], "synthetic_only": True})
