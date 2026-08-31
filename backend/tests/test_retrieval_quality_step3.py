"""Deterministic Step 3 retrieval-quality and consumer-integration proof."""

from __future__ import annotations

import hashlib
import time
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, event, select, text
from sqlalchemy.orm import sessionmaker

from backend.app.db import SessionLocal, engine as repository_engine
from backend.app.models import (
    AssertionStatus,
    Base,
    ConsultancyOffice,
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
    MasterContentSourceProvenance,
    Project,
    Role,
    VerifiedAssertion,
    VerificationMethod,
)
from backend.app.services.governed_retrieval import (
    RetrievalQuery,
    access_context_for_role,
    answer_from_retrieval,
    governed_retrieve,
)
from backend.app.services.master_content import resolve_master_content_purpose


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


@pytest.fixture(scope="module")
def quality_corpus():
    with TemporaryDirectory(prefix="proposalops-step3-quality-") as directory:
        path = Path(directory) / "quality.db"
        engine = create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False}, future=True)
        Base.metadata.create_all(bind=engine)
        factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
        with factory() as db:
            office = ConsultancyOffice(office_code=f"STEP3-{uuid4().hex[:8]}", name_en="Synthetic quality office", name_ar="مكتب اصطناعي", status="ACTIVE")
            project = Project(project_number=f"STEP3-P-{uuid4().hex[:8]}", project_name="Synthetic retrieval project", office=office, workstream="QUALITY", status="ACTIVE", municipality="Synthetic", permit_type="Building Permit")
            other_project = Project(project_number=f"STEP3-X-{uuid4().hex[:8]}", project_name="Synthetic other project", office=office, workstream="QUALITY", status="ACTIVE", municipality="Synthetic", permit_type="Building Permit")
            field = FieldDefinition(field_code=f"STEP3.FIELD.{uuid4().hex[:8]}", name_en="Plot number", name_ar="رقم القسيمة", data_type=DataType.STRING, criticality=Criticality.CRITICAL, normalization_rule="TEXT", description="Synthetic plot number")
            db.add_all([office, project, other_project, field])
            db.flush()

            def master(
                content_type: str,
                ref: str,
                title: str,
                used_in: list[str],
                content: str,
                *,
                source_reference: str | None = None,
                ownership: str = "AMEC_OWNED",
                currentness: str = "VERIFIED_CURRENT",
                status: str = "ACTIVE",
                needs_review: bool = False,
                restricted: bool = False,
                aliases: list[str] | None = None,
            ) -> dict[str, str]:
                document = Document(project_id=None, document_type=DocumentType.OTHER, logical_name=title, language="en", source_system="SYNTHETIC_STEP3")
                db.add(document)
                db.flush()
                payload = content.encode()
                version = DocumentVersion(document_id=document.id, version_number=1, source_filename=f"{ref}.txt", source_path_or_reference=source_reference or f"synthetic://step3/{ref}", sha256=_sha(payload), mime_type="text/plain", file_size=len(payload), language="en", approval_state=DocumentApprovalState.REVIEWED, source_system="SYNTHETIC_STEP3", metadata_json={"synthetic_text": content}, synthetic_content=payload)
                db.add(version)
                db.flush()
                document.current_version_id = version.id
                item = MasterContentItem(ref=ref, content_type=content_type, title=title, description=f"Synthetic {title} guidance", used_in=used_in, engineering_metadata={}, source_type_code="SYNTHETIC", status=status, needs_review=needs_review, document_id=document.id, current_document_version_id=version.id, created_by="step3-test")
                db.add(item)
                db.flush()
                db.add(MasterContentGovernanceProfile(master_content_item_id=item.id, content_ownership_class=ownership, artifact_kind=content_type, official_form_no=ref if content_type == "FORM" else None, sensitivity_class="RESTRICTED" if restricted else "NONE", restricted_reference_sample=restricted, currentness_status=currentness))
                if source_reference:
                    db.add(MasterContentSourceProvenance(document_version_id=version.id, obtained_from="SYNTHETIC_AUTHORITY", obtained_by="step3-test", source_reference=source_reference, evidence_reference=f"synthetic://evidence/{ref}"))
                for module, purpose in ((module, f"{content_type}_REFERENCE") for module in used_in):
                    db.add(MasterContentModuleBinding(master_content_id=item.id, module=module, usage_type=purpose, active=True, created_by="step3-test"))
                return {"id": item.id, "document_id": document.id, "version_id": version.id, "ref": ref}

            form = master("FORM", "STEP3-F-0001", "Building Permit Application", ["BD", "PERMIT"], "Building permit application form for synthetic authority review", source_reference="official://authority/forms/FORM-77/issue-2")
            report = master("REPORT", "STEP3-R-0001", "Permit Readiness Report", ["BD"], "Synthetic permit readiness report")
            engineering = master("ENGINEERING_WORK", "STEP3-E-0001", "Engineering Works Guidance", ["ENGINEERING"], "Engineering works and structural review guidance")
            arabic = master("FORM", "STEP3-F-AR01", "طلب تصريح مبنى", ["PERMIT"], "إرشادات طلب تصريح مبنى")
            restricted = master("FORM", "STEP3-F-RES1", "Restricted Reference Sample", ["PERMIT"], "Restricted synthetic sample", restricted=True)
            review = master("FORM", "STEP3-F-REV1", "Needs Review Source", ["BD"], "Needs review synthetic source", currentness="UNVERIFIED", needs_review=True)
            inactive = master("FORM", "STEP3-F-IN01", "Inactive Source", ["BD"], "Inactive synthetic source", status="INACTIVE")
            ambiguous_a = master("FORM", "STEP3-F-AMB1", "Submission Guidance", ["BD"], "Submission guidance for route A")
            ambiguous_b = master("FORM", "STEP3-F-AMB2", "Submission Guidance", ["BD"], "Submission guidance for route B")

            # V1 remains a real, cited historical DocumentVersion of the same
            # canonical item. Normal lookup must choose V2.
            historic_document = Document(project_id=None, document_type=DocumentType.OTHER, logical_name="Versioned authority form", language="en", source_system="SYNTHETIC_STEP3")
            db.add(historic_document)
            db.flush()
            v1_payload = b"Building permit historical version one"
            v1 = DocumentVersion(document_id=historic_document.id, version_number=1, source_filename="history-v1.txt", source_path_or_reference="official://history/form-v1", sha256=_sha(v1_payload), mime_type="text/plain", file_size=len(v1_payload), language="en", approval_state=DocumentApprovalState.SUPERSEDED, source_system="SYNTHETIC_STEP3", metadata_json={"synthetic_text": v1_payload.decode()}, synthetic_content=v1_payload)
            v2_payload = b"Building permit current version two"
            v2 = DocumentVersion(document_id=historic_document.id, version_number=2, source_filename="history-v2.txt", source_path_or_reference="official://history/form-v2", sha256=_sha(v2_payload), mime_type="text/plain", file_size=len(v2_payload), language="en", approval_state=DocumentApprovalState.REVIEWED, source_system="SYNTHETIC_STEP3", metadata_json={"synthetic_text": v2_payload.decode()}, synthetic_content=v2_payload)
            db.add_all([v1, v2])
            db.flush()
            historic_document.current_version_id = v2.id
            v1.superseded_by = v2.id
            versioned = MasterContentItem(ref="STEP3-F-HIST", content_type="FORM", title="Versioned Permit Form", description="Synthetic historical version test", used_in=["BD"], engineering_metadata={}, source_type_code="SYNTHETIC", status="ACTIVE", needs_review=False, document_id=historic_document.id, current_document_version_id=v2.id, created_by="step3-test")
            db.add(versioned)
            db.flush()
            db.add_all([
                MasterContentGovernanceProfile(master_content_item_id=versioned.id, content_ownership_class="AMEC_OWNED", artifact_kind="FORM", currentness_status="VERIFIED_CURRENT"),
                MasterContentSourceProvenance(document_version_id=v1.id, obtained_from="SYNTHETIC_AUTHORITY", obtained_by="step3-test", source_reference="official://history/form-v1"),
                MasterContentSourceProvenance(document_version_id=v2.id, obtained_from="SYNTHETIC_AUTHORITY", obtained_by="step3-test", source_reference="official://history/form-v2"),
                MasterContentModuleBinding(master_content_id=versioned.id, module="BD", usage_type="PROPOSAL_TEMPLATE", active=True, created_by="step3-test"),
                MasterContentModuleBinding(master_content_id=versioned.id, module="ADMIN", usage_type="CONTRACT_TEMPLATE", active=True, created_by="step3-test"),
                MasterContentModuleBinding(master_content_id=form["id"], module="BD", usage_type="PROPOSAL_CHECKLIST", active=True, created_by="step3-test"),
            ])

            definition = DefinitionEntry(ref="STEP3-D-0001", term="Gross Floor Area", category="Building measurement", used_in=["BD", "ENGINEERING"], status="ACTIVE", created_by="step3-test")
            db.add(definition)
            db.flush()
            revision = DefinitionRevision(definition_id=definition.id, revision_number=1, term=definition.term, description="The total constructed floor area used for synthetic permit review.", category=definition.category, used_in=definition.used_in, aliases=["GFA", "المساحة المبنية"], changed_by="step3-test", status="CURRENT")
            db.add(revision)
            db.flush()
            definition.current_revision_id = revision.id

            def evidence(logical_name: str, value: str, *, verified: bool, project_id: str = project.id, conflict: bool = False) -> str:
                document = Document(project_id=project_id, document_type=DocumentType.APPLICATION_FORM, logical_name=logical_name, language="en", source_system="SYNTHETIC_STEP3")
                db.add(document)
                db.flush()
                payload = f"{logical_name}: {value}".encode()
                version = DocumentVersion(document_id=document.id, version_number=1, source_filename=f"{logical_name}.txt", source_path_or_reference=f"synthetic://evidence/{logical_name}", sha256=_sha(payload), mime_type="text/plain", file_size=len(payload), language="en", approval_state=DocumentApprovalState.REVIEWED, source_system="SYNTHETIC_STEP3", metadata_json={"synthetic_text": f"{logical_name} {value}"}, synthetic_content=payload)
                db.add(version)
                db.flush()
                document.current_version_id = version.id
                observation = FieldObservation(project_id=project_id, field_definition_id=field.id, document_version_id=version.id, raw_value=value, normalized_candidate_value=value, structured_value_json={"value": value}, page_number=1, source_region_text=value, extraction_method=ExtractionMethod.RULE, extractor_version="STEP3", confidence=0.99, correlation_id="step3-evidence")
                db.add(observation)
                db.flush()
                if verified:
                    db.add(VerifiedAssertion(project_id=project_id, field_definition_id=field.id, semantic_value_json={"value": value}, display_value=value, status=AssertionStatus.CURRENT, source_observation_id=observation.id, verification_method=VerificationMethod.HUMAN_VERIFIED, verified_by="step3-owner", reason="Synthetic verified evidence"))
                db.flush()
                return version.id

            verified_version = evidence("Verified plot evidence", "Plot 42", verified=True)
            observed_version = evidence("Observed only evidence", "Plot 43", verified=False)
            conflict_a = evidence("Conflict lot evidence A", "Lot 11", verified=True, conflict=True)
            conflict_b = evidence("Conflict lot evidence B", "Lot 12", verified=True, conflict=True)
            for index in range(48):
                master("REPORT", f"STEP3-C-{index:04d}", f"Bounded corpus guidance {index:02d}", ["BD"], f"Bounded corpus guidance permit route {index:02d}")

            db.commit()
            ids = {"form": form["id"], "form_version": form["version_id"], "report": report["id"], "engineering": engineering["id"], "engineering_document": engineering["document_id"], "arabic": arabic["id"], "restricted": restricted["id"], "review": review["id"], "inactive": inactive["id"], "ambiguous_a": ambiguous_a["id"], "ambiguous_b": ambiguous_b["id"], "versioned": versioned.id, "v1": v1.id, "v2": v2.id, "definition": definition.id, "definition_revision": revision.id, "verified_version": verified_version, "observed_version": observed_version, "conflict_a": conflict_a, "conflict_b": conflict_b, "project": project.id, "other_project": other_project.id, "corpus_size": 57}
        yield factory, engine, ids, path
        engine.dispose()


def test_golden_query_matrix_covers_all_required_classes(quality_corpus):
    factory, _, ids, _ = quality_corpus
    owner = access_context_for_role(Role.OWNER_SPONSOR, caller_id="step3-owner", project_ids=(ids["project"],))
    preparer = access_context_for_role(Role.PERMIT_PREPARER, caller_id="step3-preparer", project_ids=(ids["project"],))
    queries = [
        {"id": "Q1", "access": owner, "query": RetrievalQuery(master_content_id=ids["form"]), "allowed": {"MASTER_CONTENT"}, "expected": {ids["form"]}, "top": ids["form"], "citation": ids["form_version"]},
        {"id": "Q2", "access": owner, "query": RetrievalQuery(query="STEP3-F-0001"), "allowed": {"MASTER_CONTENT"}, "expected": {ids["form"]}, "top": ids["form"], "citation": ids["form_version"]},
        {"id": "Q3", "access": owner, "query": RetrievalQuery(query="official://authority/forms/FORM-77/issue-2"), "allowed": {"MASTER_CONTENT"}, "expected": {ids["form"]}, "top": ids["form"], "citation": ids["form_version"]},
        {"id": "Q4", "access": owner, "query": RetrievalQuery(query="Gross Floor Area"), "allowed": {"MASTER_CONTENT"}, "expected": {ids["definition"]}, "top": ids["definition"], "citation": ids["definition_revision"]},
        {"id": "Q5", "access": owner, "query": RetrievalQuery(query="permit application"), "allowed": {"MASTER_CONTENT"}, "expected": {ids["form"]}, "top": ids["form"], "citation": ids["form_version"]},
        {"id": "Q6", "access": owner, "query": RetrievalQuery(query="engineering works"), "allowed": {"MASTER_CONTENT"}, "expected": {ids["engineering"]}, "top": ids["engineering"], "citation": None},
        {"id": "Q7", "access": preparer, "query": RetrievalQuery(query="building permit"), "allowed": {"MASTER_CONTENT", "TRANSACTIONAL_EVIDENCE"}, "expected": {ids["form"]}, "top": ids["form"], "citation": ids["form_version"]},
        {"id": "Q8", "access": owner, "query": RetrievalQuery(document_version_id=ids["verified_version"], query="Plot 42"), "allowed": {"TRANSACTIONAL_EVIDENCE"}, "expected": {ids["verified_version"]}, "top": ids["verified_version"], "citation": ids["verified_version"]},
        {"id": "Q9", "access": owner, "query": RetrievalQuery(master_content_id=ids["versioned"], query="Building permit"), "allowed": {"MASTER_CONTENT"}, "expected": {ids["versioned"]}, "top": ids["v2"], "citation": ids["v2"]},
        {"id": "Q10", "access": owner, "query": RetrievalQuery(query="permit"), "allowed": {"MASTER_CONTENT", "TRANSACTIONAL_EVIDENCE"}, "expected": set(), "top": None, "citation": None},
        {"id": "Q11", "access": owner, "query": RetrievalQuery(query="Submission Guidance"), "allowed": {"MASTER_CONTENT"}, "expected": {ids["ambiguous_a"], ids["ambiguous_b"]}, "top": None, "citation": None},
        {"id": "Q12", "access": owner, "query": RetrievalQuery(query="Conflict lot"), "allowed": {"TRANSACTIONAL_EVIDENCE"}, "expected": {ids["conflict_a"], ids["conflict_b"]}, "top": None, "citation": None},
        {"id": "Q13", "access": preparer, "query": RetrievalQuery(master_content_id=ids["engineering"], query="Engineering"), "allowed": set(), "expected": set(), "top": None, "citation": None},
        {"id": "Q14", "access": owner, "query": RetrievalQuery(document_version_id=ids["verified_version"], project_id=ids["other_project"], query="Plot 42"), "allowed": set(), "expected": set(), "top": None, "citation": None},
        {"id": "Q15", "access": owner, "query": RetrievalQuery(query="does not exist in synthetic corpus"), "allowed": set(), "expected": set(), "top": None, "citation": None},
        {"id": "Q16", "access": preparer, "query": RetrievalQuery(query="طلب تصريح مبنى"), "allowed": {"MASTER_CONTENT"}, "expected": {ids["arabic"]}, "top": ids["arabic"], "citation": None},
    ]
    assert {row["id"] for row in queries} == {f"Q{index}" for index in range(1, 17)}
    with factory() as db:
        for case in queries:
            results = governed_retrieve(db, case["query"], case["access"])
            envelopes = [result.envelope for result in results]
            result_keys = [(envelope.canonical_domain, envelope.canonical_entity_type, envelope.canonical_entity_id, envelope.document_version_id or envelope.definition_revision_id) for envelope in envelopes]
            assert len(result_keys) == len(set(result_keys)), case["id"]
            assert {envelope.canonical_domain for envelope in envelopes}.issubset(case["allowed"]), case["id"]
            ids_found = {envelope.canonical_entity_id if envelope.canonical_domain != "TRANSACTIONAL_EVIDENCE" else envelope.document_version_id for envelope in envelopes}
            if case["expected"]:
                assert case["expected"].issubset(ids_found), case["id"]
            if case["top"]:
                assert envelopes[0].canonical_entity_id == case["top"] or envelopes[0].document_version_id == case["top"], case["id"]
            if case["citation"]:
                citation_ids = {envelope.citation.document_version_id or envelope.definition_revision_id for envelope in envelopes}
                assert case["citation"] in citation_ids, case["id"]
            if case["id"] == "Q3":
                assert envelopes[0].source_artifact_id == "official://authority/forms/FORM-77/issue-2"
            if case["id"] in {"Q11", "Q12"}:
                assert len(envelopes) == 2, case["id"]
                if case["id"] == "Q11":
                    assert all(envelope.relationship_context.get("ambiguity_state") == "AMBIGUOUS" for envelope in envelopes)
                else:
                    assert all(envelope.relationship_context.get("conflict_state") == "CONFLICTING" for envelope in envelopes)
            if case["id"] in {"Q13", "Q14", "Q15"}:
                assert results == (), case["id"]


def test_current_historical_conflict_and_answer_boundaries(quality_corpus):
    factory, _, ids, _ = quality_corpus
    owner = access_context_for_role(Role.OWNER_SPONSOR, caller_id="step3-owner", project_ids=(ids["project"],))
    with factory() as db:
        current = governed_retrieve(db, RetrievalQuery(master_content_id=ids["versioned"], query="Building permit"), owner)
        historical = governed_retrieve(db, RetrievalQuery(master_content_id=ids["versioned"], document_version_id=ids["v1"], query="Building permit"), owner)
        assert current[0].envelope.document_version_id == ids["v2"]
        assert historical[0].envelope.document_version_id == ids["v1"]
        assert historical[0].envelope.superseded is True
        observed = governed_retrieve(db, RetrievalQuery(document_version_id=ids["observed_version"], query="Plot 43"), owner)
        assert observed[0].envelope.verification_state == "OBSERVED"
        assert governed_retrieve(db, RetrievalQuery(master_content_id=ids["inactive"]), owner) == ()
        restricted = governed_retrieve(db, RetrievalQuery(master_content_id=ids["restricted"]), owner)
        assert restricted[0].envelope.sensitivity_class == "RESTRICTED"
        assert governed_retrieve(db, RetrievalQuery(definition_entry_id=ids["definition"], query="GFA"), owner)[0].envelope.definition_revision_id == ids["definition_revision"]
        assert answer_from_retrieval("conflict", governed_retrieve(db, RetrievalQuery(query="Conflict lot"), owner)).authoritative_fact is False
        assert answer_from_retrieval("none", governed_retrieve(db, RetrievalQuery(query="not present"), owner)).answer.startswith("No authorized")


def test_access_filter_precedes_source_context_and_citations(quality_corpus, monkeypatch):
    factory, _, ids, _ = quality_corpus
    preparer = access_context_for_role(Role.PERMIT_PREPARER, caller_id="step3-preparer", project_ids=(ids["project"],))
    reads: list[str] = []

    def forbidden_source_read(*_args, **_kwargs):
        reads.append(_args[1].document_id)
        raise AssertionError("unauthorized source bytes were loaded")

    import backend.app.services.governed_retrieval as retrieval_module
    monkeypatch.setattr(retrieval_module, "read_master_content_bytes", forbidden_source_read)
    with factory() as db:
        assert governed_retrieve(db, RetrievalQuery(master_content_id=ids["engineering"], query="Engineering"), preparer) == ()
        assert governed_retrieve(db, RetrievalQuery(query="engineering"), preparer) == ()
    assert ids["engineering_document"] not in reads


def test_consumer_resolvers_use_one_canonical_master_item(quality_corpus):
    factory, _, ids, _ = quality_corpus
    with factory() as db:
        proposal = resolve_master_content_purpose(db, module="BD", usage_type="PROPOSAL_TEMPLATE")
        contract = resolve_master_content_purpose(db, module="ADMIN", usage_type="CONTRACT_TEMPLATE")
        assert proposal["status"] == "RESOLVED"
        assert contract["status"] == "RESOLVED"
        assert proposal["item"]["id"] == contract["item"]["id"] == ids["versioned"]
        assert proposal["item"]["version_id"] == contract["item"]["version_id"] == ids["v2"]


def test_performance_and_query_plan_are_bounded(quality_corpus, capsys):
    factory, engine, ids, path = quality_corpus
    owner = access_context_for_role(Role.OWNER_SPONSOR, caller_id="step3-owner", project_ids=(ids["project"],))
    statements: list[str] = []

    def count_statement(_connection, _cursor, statement, _parameters, _context, _executemany):
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", count_statement)
    timings: list[float] = []
    try:
        with factory() as db:
            for _ in range(5):
                start = time.perf_counter()
                governed_retrieve(db, RetrievalQuery(query="bounded corpus guidance", limit=10), owner)
                timings.append((time.perf_counter() - start) * 1000)
            plan = db.execute(text("EXPLAIN QUERY PLAN SELECT id FROM master_content_items WHERE ref = :ref"), {"ref": "STEP3-F-0001"}).all()
    finally:
        event.remove(engine, "before_cursor_execute", count_statement)
    ordered = sorted(timings)
    p50 = ordered[len(ordered) // 2]
    p95 = ordered[-1]
    assert path.exists()
    assert len(statements) / 5 < 100
    assert plan and any("INDEX" in str(row).upper() or "SEARCH" in str(row).upper() for row in plan)
    print(f"STEP3_PERFORMANCE corpus={ids['corpus_size']} statements={len(statements)} p50_ms={p50:.3f} p95_ms={p95:.3f} plan={plan}")


def test_quality_fixture_isolated_from_repository_database(quality_corpus):
    _, _, ids, path = quality_corpus
    repository_path = str(repository_engine.url.database)
    assert str(path) != repository_path
    assert ids["corpus_size"] == 57
