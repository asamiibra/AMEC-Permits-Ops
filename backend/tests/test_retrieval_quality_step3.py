"""Step 3 synthetic golden-query and consumer-boundary proof.

The fixture is isolated, deterministic, and deliberately exercises the
retrieval seam without creating a second store or invoking a protected write.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, event, select, text
from sqlalchemy.orm import sessionmaker

from backend.app.models import (AssertionStatus, Base, ConsultancyOffice, Criticality,
    DataType, DefinitionEntry, DefinitionRevision, Document, DocumentApprovalState,
    DocumentType, DocumentVersion, ExtractionMethod, FieldDefinition, FieldObservation,
    MasterContentGovernanceProfile, MasterContentItem, MasterContentModuleBinding,
    MasterContentSourceProvenance, Project, Role, VerifiedAssertion, VerificationMethod)
from backend.app.services.governed_retrieval import RetrievalQuery, access_context_for_role, answer_from_retrieval, governed_retrieve

def _sha(value: bytes) -> str: return hashlib.sha256(value).hexdigest()

@pytest.fixture(scope="module")
def quality_corpus():
    with TemporaryDirectory(prefix="proposalops-step3-quality-") as folder:
        path = Path(folder) / "quality.db"
        engine = create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False}, future=True)
        Base.metadata.create_all(bind=engine)
        factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
        with factory() as db:
            office = ConsultancyOffice(office_code=f"S3-{uuid4().hex[:8]}", name_en="Synthetic office", name_ar="مكتب اصطناعي", status="ACTIVE")
            project = Project(project_number=f"S3-P-{uuid4().hex[:8]}", project_name="Synthetic retrieval project", office=office, workstream="QUALITY", status="ACTIVE", municipality="Synthetic", permit_type="Building Permit")
            other = Project(project_number=f"S3-X-{uuid4().hex[:8]}", project_name="Other project", office=office, workstream="QUALITY", status="ACTIVE", municipality="Synthetic", permit_type="Building Permit")
            field = FieldDefinition(field_code=f"S3.FIELD.{uuid4().hex[:8]}", name_en="Plot number", name_ar="رقم القسيمة", data_type=DataType.STRING, criticality=Criticality.CRITICAL, normalization_rule="TEXT", description="Synthetic plot")
            db.add_all([office, project, other, field]); db.flush()
            ids = {"project": project.id, "other": other.id}
            def master(ref, title, used, body, source=None, *, currentness="VERIFIED_CURRENT", restricted=False):
                doc = Document(project_id=None, document_type=DocumentType.OTHER, logical_name=title, language="en", source_system="S3")
                db.add(doc); db.flush(); payload = body.encode()
                version = DocumentVersion(document_id=doc.id, version_number=1, source_filename=f"{ref}.txt", source_path_or_reference=source or f"synthetic://s3/{ref}", sha256=_sha(payload), mime_type="text/plain", file_size=len(payload), language="en", approval_state=DocumentApprovalState.REVIEWED, source_system="S3", metadata_json={"synthetic_text": body}, synthetic_content=payload)
                db.add(version); db.flush(); doc.current_version_id = version.id
                item = MasterContentItem(ref=ref, content_type="FORM", title=title, description=f"Synthetic {title} guidance", used_in=used, engineering_metadata={}, source_type_code="SYNTHETIC", status="ACTIVE", needs_review=False, document_id=doc.id, current_document_version_id=version.id, created_by="step3")
                db.add(item); db.flush(); db.add(MasterContentGovernanceProfile(master_content_item_id=item.id, content_ownership_class="AUTHORITY", artifact_kind="FORM", official_form_no=ref, sensitivity_class="RESTRICTED" if restricted else "NONE", restricted_reference_sample=restricted, currentness_status=currentness))
                if source: db.add(MasterContentSourceProvenance(document_version_id=version.id, obtained_from="SYNTHETIC_AUTHORITY", obtained_by="step3", source_reference=source))
                for module in used: db.add(MasterContentModuleBinding(master_content_id=item.id, module=module, usage_type="REFERENCE", active=True, created_by="step3"))
                db.flush(); return item, version
            form, form_v = master("S3-F-001", "Building Permit Application", ["BD", "PERMIT"], "Building permit application form", "official://authority/forms/FORM-77/issue-2")
            engineering, _ = master("S3-E-001", "Engineering Works Guidance", ["ENGINEERING"], "Engineering works guidance")
            arabic, _ = master("S3-F-AR", "طلب تصريح مبنى", ["PERMIT"], "إرشادات طلب تصريح مبنى")
            restricted, _ = master("S3-F-RES", "Restricted Reference", ["PERMIT"], "Restricted sample", restricted=True)
            amb_a, _ = master("S3-F-A", "Submission Guidance", ["BD"], "Route A submission guidance")
            amb_b, _ = master("S3-F-B", "Submission Guidance", ["BD"], "Route B submission guidance")
            history_doc = Document(project_id=None, document_type=DocumentType.OTHER, logical_name="Versioned Permit Form", language="en", source_system="S3")
            db.add(history_doc); db.flush(); p1, p2 = b"Building permit historical one", b"Building permit current two"
            v1 = DocumentVersion(document_id=history_doc.id, version_number=1, source_filename="v1.txt", source_path_or_reference="official://history/v1", sha256=_sha(p1), mime_type="text/plain", file_size=len(p1), language="en", approval_state=DocumentApprovalState.SUPERSEDED, source_system="S3", metadata_json={"synthetic_text": p1.decode()}, synthetic_content=p1)
            v2 = DocumentVersion(document_id=history_doc.id, version_number=2, source_filename="v2.txt", source_path_or_reference="official://history/v2", sha256=_sha(p2), mime_type="text/plain", file_size=len(p2), language="en", approval_state=DocumentApprovalState.REVIEWED, source_system="S3", metadata_json={"synthetic_text": p2.decode()}, synthetic_content=p2)
            db.add_all([v1, v2]); db.flush(); history_doc.current_version_id = v2.id; v1.superseded_by = v2.id
            historical = MasterContentItem(ref="S3-F-HIST", content_type="FORM", title="Versioned Permit Form", description="Historical test", used_in=["BD"], engineering_metadata={}, source_type_code="SYNTHETIC", status="ACTIVE", document_id=history_doc.id, current_document_version_id=v2.id, created_by="step3")
            db.add(historical); db.flush(); db.add_all([MasterContentGovernanceProfile(master_content_item_id=historical.id, content_ownership_class="AUTHORITY", artifact_kind="FORM", currentness_status="VERIFIED_CURRENT"), MasterContentSourceProvenance(document_version_id=v1.id, obtained_from="SYNTHETIC", obtained_by="step3", source_reference="official://history/v1"), MasterContentSourceProvenance(document_version_id=v2.id, obtained_from="SYNTHETIC", obtained_by="step3", source_reference="official://history/v2"), MasterContentModuleBinding(master_content_id=historical.id, module="BD", usage_type="REFERENCE", active=True, created_by="step3")])
            definition = DefinitionEntry(ref="S3-D-001", term="Gross Floor Area", category="Building measurement", used_in=["BD", "ENGINEERING"], status="ACTIVE", created_by="step3")
            db.add(definition); db.flush(); revision = DefinitionRevision(definition_id=definition.id, revision_number=1, term=definition.term, description="Total constructed floor area for permit review.", category=definition.category, used_in=definition.used_in, aliases=["GFA", "المساحة المبنية"], changed_by="step3", status="CURRENT")
            db.add(revision); db.flush(); definition.current_revision_id = revision.id
            def evidence(name, value, project_id, verified):
                doc = Document(project_id=project_id, document_type=DocumentType.APPLICATION_FORM, logical_name=name, language="en", source_system="S3"); db.add(doc); db.flush(); payload = f"{name}: {value}".encode()
                version = DocumentVersion(document_id=doc.id, version_number=1, source_filename=f"{name}.txt", source_path_or_reference=f"synthetic://{name}", sha256=_sha(payload), mime_type="text/plain", file_size=len(payload), language="en", approval_state=DocumentApprovalState.REVIEWED, source_system="S3", metadata_json={"synthetic_text": f"{name} {value}"}, synthetic_content=payload); db.add(version); db.flush(); doc.current_version_id = version.id
                observation = FieldObservation(project_id=project_id, field_definition_id=field.id, document_version_id=version.id, raw_value=value, normalized_candidate_value=value, structured_value_json={"value": value}, page_number=1, source_region_text=value, extraction_method=ExtractionMethod.RULE, extractor_version="S3", confidence=.99, correlation_id="s3")
                db.add(observation); db.flush()
                if verified: db.add(VerifiedAssertion(project_id=project_id, field_definition_id=field.id, semantic_value_json={"value": value}, display_value=value, status=AssertionStatus.CURRENT, source_observation_id=observation.id, verification_method=VerificationMethod.HUMAN_VERIFIED, verified_by="step3", reason="synthetic"))
                db.flush(); return version.id
            ids.update({"form": form.id, "form_v": form_v.id, "engineering": engineering.id, "engineering_doc": engineering.document_id, "arabic": arabic.id, "restricted": restricted.id, "amb_a": amb_a.id, "amb_b": amb_b.id, "historical": historical.id, "v1": v1.id, "v2": v2.id, "definition": definition.id, "revision": revision.id, "verified": evidence("Verified plot evidence", "Plot 42", project.id, True), "observed": evidence("Observed plot evidence", "Plot 43", project.id, False), "conflict_a": evidence("Conflict lot A", "Lot 11", project.id, True), "conflict_b": evidence("Conflict lot B", "Lot 12", project.id, True), "corpus_size": 16})
            db.commit()
        yield factory, engine, ids, path
        engine.dispose()

def test_golden_query_matrix_q1_to_q16(quality_corpus):
    factory, _, ids, _ = quality_corpus
    owner = access_context_for_role(Role.OWNER_SPONSOR, caller_id="owner", project_ids=(ids["project"],))
    preparer = access_context_for_role(Role.PERMIT_PREPARER, caller_id="preparer", project_ids=(ids["project"],))
    cases = [
        ("Q1", RetrievalQuery(master_content_id=ids["form"]), owner, ids["form"]), ("Q2", RetrievalQuery(query="S3-F-001"), owner, ids["form"]), ("Q3", RetrievalQuery(query="official://authority/forms/FORM-77/issue-2"), owner, ids["form"]), ("Q4", RetrievalQuery(query="Gross Floor Area"), owner, ids["definition"]), ("Q5", RetrievalQuery(query="permit application"), owner, ids["form"]), ("Q6", RetrievalQuery(query="engineering works"), owner, ids["engineering"]), ("Q7", RetrievalQuery(query="طلب تصريح مبنى"), preparer, ids["arabic"]), ("Q8", RetrievalQuery(document_version_id=ids["verified"], query="Plot 42"), owner, ids["verified"]), ("Q9", RetrievalQuery(master_content_id=ids["historical"], query="Building permit"), owner, ids["historical"]), ("Q10", RetrievalQuery(document_version_id=ids["verified"], project_id=ids["other"], query="Plot 42"), owner, None), ("Q11", RetrievalQuery(master_content_id=ids["restricted"]), owner, ids["restricted"]), ("Q12", RetrievalQuery(query="Submission Guidance"), owner, None), ("Q13", RetrievalQuery(query="Conflict lot"), owner, None), ("Q14", RetrievalQuery(query="not in corpus"), owner, None), ("Q15", RetrievalQuery(master_content_id=ids["engineering"], query="Engineering"), preparer, None), ("Q16", RetrievalQuery(document_version_id=ids["observed"], query="Plot 43"), owner, ids["observed"]),
    ]
    assert {case[0] for case in cases} == {f"Q{i}" for i in range(1, 17)}
    with factory() as db:
        for case_id, query, access, expected in cases:
            results = governed_retrieve(db, query, access); envelopes = [r.envelope for r in results]
            if expected is None and case_id not in {"Q12", "Q13"}: assert results == (), case_id
            elif case_id == "Q9": assert envelopes[0].document_version_id == ids["v2"], case_id
            elif case_id in {"Q12", "Q13"}: assert len(envelopes) == 2, case_id
            else: assert expected in {e.canonical_entity_id if e.canonical_domain != "TRANSACTIONAL_EVIDENCE" else e.document_version_id for e in envelopes}, case_id
            assert len({(e.canonical_domain, e.canonical_entity_type, e.canonical_entity_id, e.document_version_id or e.definition_revision_id) for e in envelopes}) == len(envelopes)
            if case_id == "Q3": assert envelopes[0].source_artifact_id == "official://authority/forms/FORM-77/issue-2"
            if case_id == "Q12": assert len(envelopes) == 2 and all(e.relationship_context.get("ambiguity_state") == "AMBIGUOUS" for e in envelopes)
            if case_id == "Q13": assert len(envelopes) == 2 and all(e.relationship_context.get("conflict_state") == "CONFLICTING" for e in envelopes)
            if case_id == "Q16": assert envelopes[0].verification_state == "OBSERVED"

def test_historical_replay_restricted_answer_and_citation(quality_corpus):
    factory, _, ids, _ = quality_corpus; owner = access_context_for_role(Role.OWNER_SPONSOR, project_ids=(ids["project"],))
    with factory() as db:
        current = governed_retrieve(db, RetrievalQuery(master_content_id=ids["historical"], query="Building permit"), owner)[0]
        old = governed_retrieve(db, RetrievalQuery(master_content_id=ids["historical"], document_version_id=ids["v1"], query="Building permit"), owner)[0]
        assert current.envelope.document_version_id == ids["v2"] and old.envelope.document_version_id == ids["v1"] and old.envelope.superseded
        restricted = governed_retrieve(db, RetrievalQuery(master_content_id=ids["restricted"]), owner)[0]
        assert restricted.envelope.sensitivity_class == "RESTRICTED" and restricted.envelope.citation.source_hash
        assert answer_from_retrieval("conflict", governed_retrieve(db, RetrievalQuery(query="Conflict lot"), owner)).authoritative_fact is False

def test_access_filter_precedes_source_context(quality_corpus, monkeypatch):
    factory, _, ids, _ = quality_corpus; access = access_context_for_role(Role.PERMIT_PREPARER, project_ids=(ids["project"],)); reads = []
    import backend.app.services.governed_retrieval as module
    def forbidden(*args, **kwargs): reads.append(args[1].document_id); raise AssertionError("unauthorized bytes loaded")
    monkeypatch.setattr(module, "read_master_content_bytes", forbidden)
    with factory() as db: assert governed_retrieve(db, RetrievalQuery(master_content_id=ids["engineering"], query="Engineering"), access) == ()
    assert ids["engineering_doc"] not in reads

def test_governance_filters_archived_review_and_restricted_content_and_purpose(quality_corpus):
    factory, _, ids, _ = quality_corpus
    owner = access_context_for_role(Role.OWNER_SPONSOR, project_ids=(ids["project"],))
    preparer = access_context_for_role(Role.PERMIT_PREPARER, project_ids=(ids["project"],))
    with factory() as db:
        db.get(DefinitionEntry, ids["definition"]).status = "ARCHIVED"
        db.get(MasterContentItem, ids["engineering"]).needs_review = True
        db.commit()
        assert governed_retrieve(db, RetrievalQuery(definition_entry_id=ids["definition"], query="Gross Floor Area"), owner) == ()
        assert governed_retrieve(db, RetrievalQuery(master_content_id=ids["engineering"], query="Engineering"), owner) == ()
        restricted = governed_retrieve(db, RetrievalQuery(master_content_id=ids["restricted"]), owner)
        assert restricted and restricted[0].envelope.verification_state == "RESTRICTED_REFERENCE"
        assert governed_retrieve(db, RetrievalQuery(master_content_id=ids["restricted"]), preparer) == ()
        assert governed_retrieve(db, RetrievalQuery(master_content_id=ids["form"]), access_context_for_role(Role.OWNER_SPONSOR, purpose="UNSUPPORTED_CAPABILITY")) == ()

def test_performance_measurement_is_bounded_and_indexable(quality_corpus, capsys):
    factory, engine, ids, path = quality_corpus; access = access_context_for_role(Role.OWNER_SPONSOR, project_ids=(ids["project"],)); statements = []
    def count(*args): statements.append(args[2])
    event.listen(engine, "before_cursor_execute", count)
    try:
        with factory() as db:
            results = governed_retrieve(db, RetrievalQuery(query="Building Permit", limit=10), access)
            plan = db.execute(text("EXPLAIN QUERY PLAN SELECT id FROM master_content_items WHERE ref = :ref"), {"ref": "S3-F-001"}).all()
    finally: event.remove(engine, "before_cursor_execute", count)
    assert path.exists() and results and len(statements) < 100 and plan and any("SEARCH" in str(row).upper() or "SCAN" in str(row).upper() for row in plan)
    print(f"STEP3_PERFORMANCE corpus={ids['corpus_size']} statements={len(statements)} candidates={len(results)} plan={plan}")
