"""Integrated synthetic contract for Dashboard V2 Waves B+C."""

from uuid import uuid4

from sqlalchemy import delete

from backend.app.db import SessionLocal
from backend.app.models import (
    AutomationReadinessAssessment,
    ExternalBody,
    FormAutomationProfile,
    FormMappingRelease,
    FormMappingReleaseQAGate,
    FormMappingRule,
    FormQARun,
    FormInstance,
    FormValidationResult,
    GeneratedArtifact,
    Jurisdiction,
    MasterContentApplicability,
    MasterContentItem,
    MasterContentSourceSection,
    RequirementPolicyLineage,
    RequirementPolicyVersion,
    SemanticKeyDefinition,
    ServiceType,
    TechnicalRule,
    TechnicalRuleLineage,
    TechnicalRuleSetVersion,
    RegulatoryLifecyclePhase,
)


OWNER = {"X-Dev-Role": "SYSTEM_ADMIN"}
BD = {"X-Dev-Role": "PROCESS_CHAMPION"}


def _post(client, path, payload=None, headers=OWNER):
    response = client.post(path, json=payload or {}, headers=headers)
    assert response.status_code in {200, 201}, f"{path}: {response.status_code} {response.text}"
    return response.json()


def _form_source(client):
    ref = f"SYN-V2-BC-{uuid4().hex[:8]}"
    response = client.post(
        "/api/master-content",
        data={"content_type": "FORM", "ref": ref, "title": "Synthetic V2 governed form", "description": "Wave B+C source", "used_in": '["BD"]'},
        files={"file": (f"{ref}.txt", b"synthetic governed form", "text/plain")},
        headers=OWNER,
    )
    assert response.status_code == 200, response.text
    item = response.json()
    return item["id"], item["current_version_id"]


def test_dashboard_v2_waves_b_c_governed_vertical_slice(client):
    suffix = uuid4().hex[:8]
    item_id, version_id = _form_source(client)
    ids = {"item": item_id, "version": version_id}
    try:
        jurisdiction = _post(client, "/api/regulatory/jurisdictions", {"code": f"V2-J-{suffix}", "country_code": "ZZ", "name_en": "V2 Synthetic Locality", "level": "LOCALITY"})
        body = _post(client, "/api/regulatory/external-bodies", {"code": f"V2-B-{suffix}", "name_en": "V2 Synthetic Authority", "body_type": "AUTHORITY", "jurisdiction_id": jurisdiction["id"], "verification_state": "SYNTHETIC_UNVERIFIED"})
        service = _post(client, "/api/regulatory/service-types", {"code": f"V2-S-{suffix}", "name_en": "V2 Synthetic Service", "description": "V2 governance fixture"})
        phase = _post(client, "/api/regulatory/lifecycle-phases", {"code": f"V2-P-{suffix}", "name_en": "V2 Application", "sort_order": 30})
        ids.update({"jurisdiction": jurisdiction["id"], "body": body["id"], "service": service["id"], "phase": phase["id"]})

        # Exact source sections are version-pinned and can support multiple
        # policy/technical sources without inferring applicability.
        section_a = _post(client, f"/api/master-content/{item_id}/source-sections", {"document_version_id": version_id, "section_key": "authority-scope", "label": "Authority scope", "page_start": 1})
        section_b = _post(client, f"/api/master-content/{item_id}/source-sections", {"document_version_id": version_id, "section_key": "service-scope", "label": "Service scope", "page_start": 2})
        _post(client, f"/api/master-content/{item_id}/provenance", {"document_version_id": version_id, "obtained_from": "SYNTHETIC_AUTHORITY_SOURCE", "source_reference": "V2-BC-SYNTHETIC"})
        governance = client.patch(f"/api/master-content/{item_id}/governance", json={"content_ownership_class": "AMEC_OWNED", "artifact_kind": "AUTHORITY_FORM", "language_profile": "EN"}, headers=OWNER)
        assert governance.status_code == 200, governance.text

        applicability = _post(client, "/api/dashboard-v2/applicability", {"master_content_item_id": item_id, "source_document_version_id": version_id, "external_body_id": body["id"], "jurisdiction_id": jurisdiction["id"], "service_type_id": service["id"], "lifecycle_phase_id": phase["id"], "status": "DRAFT"})
        ids["applicability"] = applicability["id"]
        assert applicability["status"] == "DRAFT"
        assert client.post("/api/dashboard-v2/applicability", json={"master_content_item_id": item_id, "external_body_id": body["id"], "service_type_id": service["id"], "status": "ACTIVE"}, headers=BD).status_code == 403
        active_applicability = client.patch(f"/api/dashboard-v2/applicability/{applicability['id']}", json={"status": "ACTIVE"}, headers=OWNER)
        assert active_applicability.status_code == 200, active_applicability.text

        policy = _post(client, "/api/requirements/policies", {"service_type_id": service["id"], "jurisdiction_id": jurisdiction["id"], "external_body_id": body["id"], "version": f"V2-{suffix}", "purpose": "AUTHORITY_SUBMISSION"})
        ids["policy"] = policy["id"]
        policy_lineage = _post(client, "/api/dashboard-v2/policy-lineage", {"policy_version_id": policy["id"], "master_content_item_id": item_id, "document_version_id": version_id, "source_section_id": section_a["id"], "source_role": "PRIMARY"})
        ids["policy_lineage"] = policy_lineage["id"]
        assert client.patch(f"/api/dashboard-v2/policy-lineage/{policy_lineage['id']}", json={"governance_status": "ACTIVE"}, headers=OWNER).status_code == 200
        assert client.patch(f"/api/dashboard-v2/policy-lineage/{policy_lineage['id']}", json={"governance_status": "ACTIVE"}, headers=BD).status_code == 403

        rule_set = _post(client, "/api/technical-rules/sets", {"code": f"V2-RS-{suffix}", "name": "V2 Synthetic Rule Set", "version": "1", "service_type_id": service["id"], "jurisdiction_id": jurisdiction["id"], "external_body_id": body["id"]})
        rule = _post(client, f"/api/technical-rules/sets/{rule_set['id']}/rules", {"code": "V2-REQ", "name": "V2 technical rule", "rule_type": "THRESHOLD", "expression_json": {"input_key": "x", "operator": ">", "threshold": 1}})
        ids.update({"ruleset": rule_set["id"], "rule": rule["id"]})
        technical_lineage = _post(client, "/api/dashboard-v2/technical-lineage", {"technical_rule_set_version_id": rule_set["id"], "technical_rule_id": rule["id"], "master_content_item_id": item_id, "document_version_id": version_id, "source_section_id": section_b["id"], "source_role": "SUPPORTING"})
        ids["technical_lineage"] = technical_lineage["id"]
        assert client.patch(f"/api/dashboard-v2/technical-lineage/{technical_lineage['id']}", json={"governance_status": "ACTIVE"}, headers=OWNER).status_code == 200
        assert client.post(f"/api/technical-rules/sets/{rule_set['id']}/activate", json={"approved_by": "synthetic-professional"}, headers=OWNER).status_code == 200

        resolved_source = client.get(f"/api/dashboard-v2/resolve-source?external_body_id={body['id']}&jurisdiction_id={jurisdiction['id']}&service_type_id={service['id']}&lifecycle_phase_id={phase['id']}", headers=OWNER)
        assert resolved_source.status_code == 200, resolved_source.text
        assert resolved_source.json()["applicability"]["source_document_version_id"] == version_id
        wrong_context = client.get(f"/api/dashboard-v2/resolve-source?external_body_id={body['id']}&jurisdiction_id={jurisdiction['id']}&service_type_id={service['id']}&lifecycle_phase_id=wrong-phase", headers=OWNER)
        assert wrong_context.status_code == 409

        profile = _post(client, f"/api/dashboard-v2/forms/{item_id}/automation-profile", {"renderer_type": "SYNTHETIC_JSON", "semantic_contract_version": "1.0"})
        ids["profile"] = profile["id"]
        semantic = _post(client, "/api/form-automation/semantic-keys", {"semantic_key": f"v2.bc.reference.{suffix}", "value_type": "STRING", "consequential": True})
        ids["semantic"] = semantic["id"]
        release = _post(client, f"/api/dashboard-v2/forms/{item_id}/mapping-releases", {"version": f"V2-{suffix}", "mapping_json": {"contract": "synthetic"}})
        ids["release"] = release["id"]
        _post(client, f"/api/dashboard-v2/mapping-releases/{release['id']}/rules", {"logical_field_key": semantic["semantic_key"], "target_key": "system_reference", "transform_type": "SCALAR", "target_writer": "SYSTEM"})
        _post(client, f"/api/dashboard-v2/mapping-releases/{release['id']}/rules", {"logical_field_key": semantic["semantic_key"], "target_key": "authority_signature", "transform_type": "SCALAR", "target_writer": "AUTHORITY_ONLY"})
        assert client.post(f"/api/dashboard-v2/mapping-releases/{release['id']}/RELEASED", headers=OWNER).status_code == 409
        assert client.post(f"/api/dashboard-v2/mapping-releases/{release['id']}/REVIEW", headers=OWNER).status_code == 200
        assert client.post(f"/api/dashboard-v2/mapping-releases/{release['id']}/APPROVED", headers=OWNER).status_code == 200

        preview = client.post(f"/api/dashboard-v2/mapping-releases/{release['id']}/preview", json={"resolved_values": {semantic["semantic_key"]: "V2-CASE-001"}}, headers=OWNER)
        assert preview.status_code == 200, preview.text
        artifact_id = preview.json()["artifact"]["id"]
        ids["artifact"] = artifact_id
        for qa_type in ("STRUCTURAL_MAPPING", "SYNTHETIC_FILL", "READ_BACK", "WRITER_OWNERSHIP"):
            qa = client.post(f"/api/form-automation/artifacts/{artifact_id}/qa", json={"qa_type": qa_type, "result": "PASS", "checks_json": {"synthetic": True}}, headers=OWNER)
            assert qa.status_code == 200, qa.text
        released = client.post(f"/api/dashboard-v2/mapping-releases/{release['id']}/RELEASED", headers=OWNER)
        assert released.status_code == 200, released.text
        readiness = _post(client, f"/api/dashboard-v2/profiles/{profile['id']}/readiness/evaluate")
        assert readiness["state"] == "AUTOMATED_USE_READY", readiness
        automation = client.get(f"/api/dashboard-v2/resolve-automation?external_body_id={body['id']}&jurisdiction_id={jurisdiction['id']}&service_type_id={service['id']}&lifecycle_phase_id={phase['id']}", headers=OWNER)
        assert automation.status_code == 200, automation.text
        assert automation.json()["mapping_release"]["id"] == release["id"]
        changed = client.post(f"/api/master-content/{item_id}/versions", data={"expected_current_version": "1", "change_reason": "Synthetic V2 source update"}, files={"file": ("v2-source-v2.txt", b"synthetic governed form v2", "text/plain")}, headers=OWNER)
        assert changed.status_code == 200, changed.text
        revalidated = _post(client, f"/api/dashboard-v2/profiles/{profile['id']}/readiness/evaluate")
        assert revalidated["state"] == "NEEDS_REVALIDATION"
        assert client.get(f"/api/dashboard-v2/resolve-automation?external_body_id={body['id']}&jurisdiction_id={jurisdiction['id']}&service_type_id={service['id']}&lifecycle_phase_id={phase['id']}", headers=OWNER).status_code == 409
    finally:
        with SessionLocal() as db:
            for model, key in ((FormMappingReleaseQAGate, "release"), (FormQARun, None), (FormValidationResult, None), (GeneratedArtifact, "artifact"), (FormInstance, "profile"), (FormMappingRule, "release"), (AutomationReadinessAssessment, "profile"), (FormMappingRelease, "release"), (FormAutomationProfile, "profile"), (RequirementPolicyLineage, "policy_lineage"), (TechnicalRuleLineage, "technical_lineage"), (MasterContentApplicability, "applicability")):
                if model is GeneratedArtifact and ids.get("artifact"):
                    db.execute(delete(model).where(model.id == ids["artifact"]))
                elif model is FormInstance and ids.get("profile"):
                    db.execute(delete(model).where(model.profile_id == ids["profile"]))
                elif model is AutomationReadinessAssessment and ids.get("profile"):
                    db.execute(delete(model).where(model.profile_id == ids["profile"]))
                elif model is FormMappingRelease and ids.get("release"):
                    db.execute(delete(model).where(model.id == ids["release"]))
                elif key and ids.get(key):
                    column = getattr(model, "mapping_release_id", None) or getattr(model, "profile_id", None) or getattr(model, "id")
                    db.execute(delete(model).where(column == ids[key]))
                elif model is FormQARun and ids.get("artifact"):
                    db.execute(delete(model).where(model.generated_artifact_id == ids["artifact"]))
                elif model is FormValidationResult and ids.get("artifact"):
                    db.execute(delete(model).where(model.generated_artifact_id == ids["artifact"]))
            if ids.get("technical_lineage"): db.execute(delete(TechnicalRuleLineage).where(TechnicalRuleLineage.id == ids["technical_lineage"]))
            if ids.get("rule"): db.execute(delete(TechnicalRule).where(TechnicalRule.id == ids["rule"]))
            if ids.get("ruleset"): db.execute(delete(TechnicalRuleSetVersion).where(TechnicalRuleSetVersion.id == ids["ruleset"]))
            if ids.get("policy_lineage"): db.execute(delete(RequirementPolicyLineage).where(RequirementPolicyLineage.id == ids["policy_lineage"]))
            if ids.get("policy"): db.execute(delete(RequirementPolicyVersion).where(RequirementPolicyVersion.id == ids["policy"]))
            if ids.get("semantic"): db.execute(delete(SemanticKeyDefinition).where(SemanticKeyDefinition.id == ids["semantic"]))
            if ids.get("item"):
                db.execute(delete(MasterContentSourceSection).where(MasterContentSourceSection.master_content_item_id == ids["item"]))
            db.commit()
        if ids.get("item"):
            client.post(f"/api/master-content/{ids['item']}/archive", headers=OWNER)
