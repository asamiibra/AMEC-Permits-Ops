"""Evidence -> deterministic prefill proposal proof for AuthorityCase."""
from uuid import uuid4

from sqlalchemy import func, select

from backend.app.db import SessionLocal
from backend.app.models import (AuthorityCase, ConsultancyOffice, Document,
    DocumentApprovalState, DocumentType, ExternalBody, FieldObservation,
    FormAutomationProfile, FormInstance, FormMappingRelease, FormMappingRule,
    FormMappingReleaseQAGate, FormQARun, GeneratedArtifact, Jurisdiction,
    MasterContentApplicability, MasterContentGovernanceProfile, MasterContentItem,
    MasterContentSourceProvenance, Project, RegulatoryJourney, SemanticKeyDefinition,
    SemanticValueAssertion, ServiceType, DocumentVersion)
from backend.app.services.dashboard_v2_governance import release_checksum

def _fixture():
    suffix = uuid4().hex[:8]
    with SessionLocal() as db:
        office = db.scalar(select(ConsultancyOffice)); body = db.scalar(select(ExternalBody)) or ExternalBody(code=f"LG-B-{suffix}", name_en="Synthetic authority", body_type="AUTHORITY", status="ACTIVE")
        jurisdiction = db.scalar(select(Jurisdiction)) or Jurisdiction(code=f"LG-J-{suffix}", country_code="QA", name_en="Synthetic locality", level="LOCALITY", status="ACTIVE")
        service = db.scalar(select(ServiceType)) or ServiceType(code=f"LG-S-{suffix}", name_en="Synthetic permit", status="ACTIVE")
        db.add_all([r for r in (body, jurisdiction, service) if r.id is None]); db.flush()
        project = Project(project_number=f"LG-P-{suffix}", project_name="Lineage project", office_id=office.id, workstream="BUILDING_PERMIT", status="ACTIVE", municipality="Doha", permit_type="BUILDING"); db.add(project); db.flush()
        journey = RegulatoryJourney(journey_code=f"LG-JR-{suffix}", project_id=project.id, service_type_id=service.id, jurisdiction_id=jurisdiction.id, external_body_id=body.id, status="OPEN", created_by="step3"); db.add(journey); db.flush()
        case = AuthorityCase(case_reference=f"LG-C-{suffix}", regulatory_journey_id=journey.id, external_body_id=body.id, service_type_id=service.id, jurisdiction_id=jurisdiction.id, status="PREPARING", subject_type="Project", subject_id=project.id, created_by="step3"); db.add(case); db.flush()
        document = Document(document_type=DocumentType.APPLICATION_FORM, logical_name=f"Lineage form {suffix}", language="en", source_system="MASTER_CONTENT"); evidence_document = Document(project_id=project.id, document_type=DocumentType.OTHER, logical_name=f"Lineage evidence {suffix}", language="en", source_system="PROJECT_EVIDENCE"); db.add_all([document, evidence_document]); db.flush()
        version = DocumentVersion(id=str(uuid4()), document_id=document.id, version_number=1, source_filename="form.txt", source_path_or_reference="synthetic://lineage/form", sha256="a" * 64, mime_type="text/plain", file_size=10, language="en", approval_state=DocumentApprovalState.REVIEWED, source_system="MASTER_CONTENT", metadata_json={"master_status": "CURRENT", "synthetic_text": "Governed form"}, synthetic_content=b"Governed form")
        evidence_version = DocumentVersion(id=str(uuid4()), document_id=evidence_document.id, version_number=1, source_filename="evidence.txt", source_path_or_reference="synthetic://lineage/evidence", sha256="c" * 64, mime_type="text/plain", file_size=10, language="en", approval_state=DocumentApprovalState.REVIEWED, source_system="PROJECT_EVIDENCE", metadata_json={"synthetic_text": "QAT-LG-001"}, synthetic_content=b"QAT-LG-001"); db.add_all([version, evidence_version]); db.flush(); document.current_version_id = version.id; evidence_document.current_version_id = evidence_version.id
        item = MasterContentItem(ref=f"LG-F-{suffix}", content_type="FORM", title="Lineage permit form", description="Synthetic form", used_in=["PERMIT"], status="ACTIVE", needs_review=False, document_id=document.id, current_document_version_id=version.id, created_by="step3"); db.add(item); db.flush(); db.add_all([MasterContentGovernanceProfile(master_content_item_id=item.id, content_ownership_class="AMEC_OWNED", artifact_kind="AUTHORITY_FORM", currentness_status="VERIFIED_CURRENT"), MasterContentSourceProvenance(document_version_id=version.id, obtained_from="synthetic", obtained_by="step3", source_reference="LG-SOURCE"), MasterContentApplicability(master_content_item_id=item.id, source_document_version_id=version.id, external_body_id=body.id, jurisdiction_id=jurisdiction.id, service_type_id=service.id, status="ACTIVE", confirmed_by="step3")])
        profile = FormAutomationProfile(master_content_item_id=item.id, source_document_version_id=version.id, renderer_type="SYNTHETIC", automation_status="ACTIVE", semantic_contract_version="1.0", writer_policy_json={}, source_version_state="CURRENT", managed_by="step3"); db.add(profile); db.flush()
        key = SemanticKeyDefinition(semantic_key=f"lineage.key.{suffix}", value_type="STRING", description="Lineage value", consequential=True); db.add(key); db.flush()
        assertion = SemanticValueAssertion(semantic_key_id=key.id, context_type="AuthorityCase", context_id=case.id, value_json="QAT-LG-001", value_type="STRING", source_type="DocumentVersion", source_id=evidence_version.id, source_version=evidence_version.id, verification_status="VERIFIED", authority="OWNER", asserted_by="step3"); db.add(assertion)
        release = FormMappingRelease(profile_id=profile.id, version="LG-1", status="RELEASED", mapping_json={}, master_content_item_id=item.id, source_document_version_id=version.id, semantic_contract_version="1.0", renderer_type="SYNTHETIC", renderer_version="LG", normalized_rendition_ref="synthetic://lineage"); db.add(release); db.flush(); rule = FormMappingRule(mapping_release_id=release.id, logical_field_key=key.semantic_key, target_key="authority_reference", transform_type="SCALAR", target_writer="SYSTEM"); db.add(rule); db.flush()
        instance = FormInstance(master_content_item_id=item.id, source_document_version_id=version.id, profile_id=profile.id, mapping_release_id=release.id, context_type="AuthorityCase", context_id=case.id, created_by="step3"); db.add(instance); db.flush(); artifact = GeneratedArtifact(form_instance_id=instance.id, source_document_version_id=version.id, profile_id=profile.id, mapping_release_id=release.id, renderer_version="LG", artifact_type="JSON", generated_payload={}, content_hash="b" * 64, created_by="step3"); db.add(artifact); db.flush()
        for qa_type in ("STRUCTURAL_MAPPING", "SYNTHETIC_FILL", "READ_BACK", "WRITER_OWNERSHIP"):
            qa = FormQARun(generated_artifact_id=artifact.id, mapping_release_id=release.id, qa_type=qa_type, result="PASS", checks_json={}, created_by="step3"); db.add(qa); db.flush(); db.add(FormMappingReleaseQAGate(mapping_release_id=release.id, qa_run_id=qa.id, qa_type=qa_type, required=True))
        for qa_type in ("STRUCTURAL_MAPPING", "SYNTHETIC_FILL", "READ_BACK", "WRITER_OWNERSHIP"):
            qa = FormQARun(generated_artifact_id=artifact.id, mapping_release_id=release.id, qa_type=qa_type, result="PASS", checks_json={}, created_by="step3")
            db.add(qa); db.flush(); db.add(FormMappingReleaseQAGate(mapping_release_id=release.id, qa_run_id=qa.id, qa_type=qa_type, required=True))
        db.commit()
        release_id = release.id
    with SessionLocal() as db:
        release = db.get(FormMappingRelease, release_id)
        release.mapping_checksum = release_checksum(db, release)
        db.commit()
        return {"case": case.id, "item": item.id, "version": version.id, "evidence": evidence_version.id, "release": release.id, "project": project.id}

def test_evidence_to_prefill_proposal_is_exactly_lineaged_and_non_mutating(client):
    fixture = _fixture(); payload = {"master_content_id": fixture["item"], "context_entity_type": "AuthorityCase", "context_entity_id": fixture["case"], "purpose": "FORM_PREPARATION"}
    with SessionLocal() as db: before = (db.scalar(select(func.count()).select_from(FormInstance)), db.scalar(select(func.count()).select_from(GeneratedArtifact)))
    response = client.post("/api/governed-prefill/preview", json=payload, headers={"X-Dev-Role": "SYSTEM_ADMIN"})
    assert response.status_code == 200, response.text; result = response.json(); field = result["fields"][0]
    assert result["preview_status"] == "READY" and result["master_content_version_pin"]["document_version_id"] == fixture["version"]
    assert field["proposed_value"] == "QAT-LG-001" and field["provenance"][0]["document_version_id"] == fixture["evidence"]
    assert field["provenance"][0]["source_hash"] == "c" * 64 and field["provenance"][0]["document_version_id"] != fixture["version"]
    assert result["canonical_write_count"] == 0 and result["protected_human_action_count"] == 0 and result["draft_apply"].startswith("DEFERRED")
    with SessionLocal() as db: assert before == (db.scalar(select(func.count()).select_from(FormInstance)), db.scalar(select(func.count()).select_from(GeneratedArtifact)))

def test_prefill_fails_closed_for_unresolved_provenance_and_stale_pin(client):
    fixture = _fixture(); payload = {"master_content_id": fixture["item"], "context_entity_type": "AuthorityCase", "context_entity_id": fixture["case"], "purpose": "FORM_PREPARATION"}
    stale = client.post("/api/governed-prefill/preview", json={**payload, "expected_document_version_id": "old"}, headers={"X-Dev-Role": "SYSTEM_ADMIN"})
    assert stale.status_code == 200 and stale.json()["preview_status"] == "STALE"
    invalid_purpose = client.post("/api/governed-prefill/preview", json={**payload, "purpose": "READ"}, headers={"X-Dev-Role": "SYSTEM_ADMIN"})
    assert invalid_purpose.status_code == 409 and invalid_purpose.json()["detail"]["code"] == "PREFILL_PURPOSE_NOT_ALLOWED"
