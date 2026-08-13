"""Synthetic vertical-slice contracts for the shared domain foundations."""

from uuid import uuid4

from sqlalchemy import delete

from backend.app.db import SessionLocal
from backend.app.models import (
    AuthorityCase,
    AuthorityCaseIdentifier,
    AuthorityCaseWorkPeriod,
    AuthorityOutcome,
    ExternalBody,
    ExternalBodyUnit,
    ExternalInteractionProfile,
    FormAutomationProfile,
    FormInstance,
    FormMappingRelease,
    FormMappingRule,
    FormQARun,
    FormSignatureRequirement,
    FormValidationResult,
    GeneratedArtifact,
    Jurisdiction,
    RegulatoryJourney,
    RegulatoryLifecyclePhase,
    RegulatoryRelation,
    RequirementApplicabilityDecision,
    RequirementDefinition,
    RequirementDecision,
    RequirementEvidenceConstraint,
    RequirementEvidenceEvaluation,
    RequirementEvaluation,
    RequirementGroup,
    RequirementPolicyItem,
    RequirementPolicyLineage,
    RequirementPolicyVersion,
    SemanticKeyDefinition,
    SemanticValueAssertion,
    ServiceType,
    ServiceTypeVersion,
    SignaturePacket,
    TechnicalRule,
    TechnicalRuleEvaluation,
    TechnicalRuleLineage,
    TechnicalRuleSetVersion,
)


OWNER = {"X-Dev-Role": "SYSTEM_ADMIN"}
BD = {"X-Dev-Role": "PROCESS_CHAMPION"}


def _post(client, path, payload, headers=OWNER):
    response = client.post(path, json=payload, headers=headers)
    assert response.status_code in {200, 201}, f"{path}: {response.status_code} {response.text}"
    return response.json()


def _form_source(client):
    ref = f"SYN-FOUNDATION-FORM-{uuid4().hex[:8]}"
    response = client.post(
        "/api/master-content",
        data={"content_type": "FORM", "ref": ref, "title": "Synthetic Foundation Form", "description": "Synthetic foundation source", "used_in": '["BD"]'},
        files={"file": (f"{ref}.txt", b"synthetic foundation form", "text/plain")},
        headers=OWNER,
    )
    assert response.status_code == 200, response.text
    item = response.json()
    return item["id"], item["current_version_id"]


def _cleanup_foundations():
    models = [
        SignaturePacket, FormSignatureRequirement, FormQARun, FormValidationResult, GeneratedArtifact, FormInstance,
        FormMappingRule, FormMappingRelease, SemanticValueAssertion, SemanticKeyDefinition, FormAutomationProfile,
        TechnicalRuleEvaluation, TechnicalRuleLineage, TechnicalRule, TechnicalRuleSetVersion,
        RequirementDecision, RequirementEvidenceEvaluation, RequirementEvaluation, RequirementApplicabilityDecision,
        RequirementPolicyLineage, RequirementEvidenceConstraint, RequirementPolicyItem, RequirementGroup, RequirementPolicyVersion, RequirementDefinition,
        AuthorityOutcome, ExternalInteractionProfile, AuthorityCaseWorkPeriod, AuthorityCaseIdentifier, AuthorityCase,
        RegulatoryRelation, RegulatoryJourney, RegulatoryLifecyclePhase, ServiceTypeVersion, ServiceType, ExternalBodyUnit, ExternalBody, Jurisdiction,
    ]
    with SessionLocal() as db:
        for model in models:
            db.execute(delete(model))
        db.commit()


def test_shared_foundations_vertical_slice_and_safety_contracts(client):
    suffix = uuid4().hex[:8]
    item_id, version_id = _form_source(client)

    # Foundation A: catalogue, explicit journey/case, late identifier, work period, outcome, and relation.
    jurisdiction = _post(client, "/api/regulatory/jurisdictions", {"code": f"SYN-J-{suffix}", "country_code": "ZZ", "name_en": "Synthetic Locality", "level": "LOCALITY"})
    body = _post(client, "/api/regulatory/external-bodies", {"code": f"SYN-B-{suffix}", "name_en": "Synthetic Authority", "body_type": "AUTHORITY", "jurisdiction_id": jurisdiction["id"], "verification_state": "SYNTHETIC_UNVERIFIED"})
    service = _post(client, "/api/regulatory/service-types", {"code": f"SYN-S-{suffix}", "name_en": "Synthetic Permit Service", "description": "Synthetic foundation fixture"})
    _post(client, f"/api/regulatory/service-types/{service['id']}/versions", {"version": "1", "status": "ACTIVE", "effective_from": "2026-01-01", "provenance_json": {"synthetic": True}})
    phase = _post(client, "/api/regulatory/lifecycle-phases", {"code": f"SYN-APPLICATION-{suffix}", "name_en": "Synthetic Application", "sort_order": 20})
    journey = _post(client, "/api/regulatory/journeys", {"journey_code": f"SYN-JOURNEY-{suffix}", "service_type_id": service["id"], "jurisdiction_id": jurisdiction["id"], "external_body_id": body["id"]})
    case = _post(client, "/api/regulatory/cases", {"case_reference": f"SYN-CASE-{suffix}", "regulatory_journey_id": journey["id"], "external_body_id": body["id"], "service_type_id": service["id"], "jurisdiction_id": jurisdiction["id"], "subject_type": "PROJECT", "subject_id": "synthetic-project-a"})
    identifier = _post(client, f"/api/regulatory/cases/{case['id']}/identifiers", {"identifier_type": "OFFICIAL_APPLICATION", "value": f"SYN-OFFICIAL-{suffix}"})
    assert identifier["authority_case_id"] == case["id"]
    period = _post(client, f"/api/regulatory/cases/{case['id']}/work-periods", {"period_type": "REGULATORY_REVIEW", "starts_at": "2026-02-01T00:00:00+00:00"})
    assert period["authority_case_id"] == case["id"]
    outcome = _post(client, f"/api/regulatory/cases/{case['id']}/outcomes", {"outcome_type": "APPROVAL", "issued_at": "2026-03-01T00:00:00+00:00", "decision_payload": {"synthetic": True}})
    assert outcome["authority_case_id"] == case["id"]
    relation = _post(client, "/api/regulatory/relations", {"source_type": "ServiceType", "source_id": service["id"], "relation_type": "REQUIRES_APPROVAL_FROM", "target_type": "ExternalBody", "target_id": body["id"]})
    assert relation["target_id"] == body["id"]
    assert client.post("/api/regulatory/external-bodies", json={"code": f"SYN-DENIED-{suffix}", "name_en": "Denied"}, headers=BD).status_code == 403

    # Foundation B: three-valued applicability, grouped items, evidence constraints,
    # exact source lineage, deterministic policy resolver, and fail-closed evidence.
    requirement_form = _post(client, "/api/requirements/definitions", {"code": f"SYN-FORM-{suffix}", "name_en": "Synthetic Form", "kind": "FORM"})
    requirement_unknown = _post(client, "/api/requirements/definitions", {"code": f"SYN-UNKNOWN-{suffix}", "name_en": "Synthetic Unknown", "kind": "APPROVAL"})
    policy = _post(client, "/api/requirements/policies", {"service_type_id": service["id"], "jurisdiction_id": jurisdiction["id"], "external_body_id": body["id"], "version": "P1", "purpose": "AUTHORITY_SUBMISSION"})
    group = _post(client, f"/api/requirements/policies/{policy['id']}/groups", {"code": "ANY_FORM_OR_APPROVAL", "group_type": "ANY_OF"})
    item = _post(client, f"/api/requirements/policies/{policy['id']}/items", {"requirement_definition_id": requirement_form["id"], "phase_id": phase["id"], "group_id": group["id"], "applicability_expression": {"field": "service_type_id", "equals": service["id"]}})
    unknown_item = _post(client, f"/api/requirements/policies/{policy['id']}/items", {"requirement_definition_id": requirement_unknown["id"], "phase_id": phase["id"], "applicability_expression": {"always": "APPLICABILITY_UNKNOWN"}})
    _post(client, f"/api/requirements/policy-items/{item['id']}/evidence-constraint", {"allowed_formats": ["PDF"], "freshness_days": 30})
    _post(client, f"/api/requirements/policies/{policy['id']}/lineage", {"master_content_item_id": item_id, "document_version_id": version_id, "relation_type": "SOURCE_OF_POLICY"})
    activated = _post(client, f"/api/requirements/policies/{policy['id']}/activate", {})
    assert activated["status"] == "ACTIVE"
    resolved_policy = client.get(f"/api/requirements/resolve?service_type_id={service['id']}&jurisdiction_id={jurisdiction['id']}&external_body_id={body['id']}", headers=OWNER)
    assert resolved_policy.status_code == 200
    evaluation = _post(client, "/api/requirements/evaluate", {"policy_version_id": policy["id"], "context": {"context_type": "AuthorityCase", "context_id": case["id"], "service_type_id": service["id"]}, "evidence": [{"document_version_id": version_id, "context_type": "AuthorityCase", "context_id": case["id"], "verified": True, "format": "PDF"}]})
    statuses = {row["requirement_definition_id"]: row for row in evaluation["items"]}
    assert statuses[item["requirement_definition_id"]]["status"] == "SATISFIED"
    assert statuses[unknown_item["requirement_definition_id"]]["applicability"] == "APPLICABILITY_UNKNOWN"
    wrong_context = _post(client, "/api/requirements/evaluate", {"policy_version_id": policy["id"], "context": {"context_type": "AuthorityCase", "context_id": "synthetic-case-b", "service_type_id": service["id"]}, "evidence": [{"document_version_id": version_id, "context_type": "AuthorityCase", "context_id": case["id"], "verified": True, "format": "PDF"}]})
    assert next(row for row in wrong_context["items"] if row["requirement_definition_id"] == item["requirement_definition_id"])["status"] == "MISSING"
    assert client.post(f"/api/requirements/policies/{policy['id']}/activate", headers=BD).status_code == 403

    # Foundation C: approved active rule set, source lineage, resolver, deterministic
    # evaluation, explicit units, and unknown result for incompatible units.
    rule_set = _post(client, "/api/technical-rules/sets", {"code": f"SYN-RULESET-{suffix}", "name": "Synthetic Rule Set", "version": "T1", "discipline": "STRUCTURAL", "service_type_id": service["id"], "jurisdiction_id": jurisdiction["id"]})
    rule = _post(client, f"/api/technical-rules/sets/{rule_set['id']}/rules", {"code": "SYN-X-THRESHOLD", "name": "Synthetic threshold", "rule_type": "THRESHOLD", "expression_json": {"input_key": "x", "operator": ">", "threshold": 10, "unit": "m"}})
    _post(client, f"/api/technical-rules/{rule['id']}/lineage", {"master_content_item_id": item_id, "document_version_id": version_id})
    activated_rule_set = _post(client, f"/api/technical-rules/sets/{rule_set['id']}/activate", {"approved_by": "synthetic-professional"})
    assert activated_rule_set["status"] == "ACTIVE"
    assert client.get(f"/api/technical-rules/resolve?code={rule_set['code']}", headers=OWNER).status_code == 200
    technical_pass = _post(client, f"/api/technical-rules/{rule['id']}/evaluate", {"context_type": "AuthorityCase", "context_id": case["id"], "inputs": {"x": {"value": 12000, "unit": "mm"}}})
    assert technical_pass["evaluation"]["result"] == "PASS"
    technical_unknown = _post(client, f"/api/technical-rules/{rule['id']}/evaluate", {"context_type": "AuthorityCase", "context_id": case["id"], "inputs": {"x": {"value": 12, "unit": "kg"}}})
    assert technical_unknown["evaluation"]["result"] == "UNKNOWN"
    assert client.post("/api/technical-rules/sets", json={"code": f"SYN-DENIED-RULE-{suffix}", "name": "Denied", "version": "1"}, headers=BD).status_code == 403

    # Foundation D: semantic assertions, profile/source pin, draft mapping only,
    # deterministic synthetic renderer, read-back validation, writer ownership,
    # and repeating-grid overflow protection.
    profile = _post(client, "/api/form-automation/profiles", {"master_content_item_id": item_id, "source_document_version_id": version_id, "renderer_type": "SYNTHETIC_JSON"})
    semantic_key = _post(client, "/api/form-automation/semantic-keys", {"semantic_key": f"synthetic.case.reference.{suffix}", "value_type": "STRING", "consequential": True})
    assertion = _post(client, "/api/form-automation/assertions", {"semantic_key_id": semantic_key["id"], "context_type": "AuthorityCase", "context_id": case["id"], "value_json": f"CASE-{suffix}", "value_type": "STRING", "source_type": "AuthorityCaseIdentifier", "source_id": identifier["id"], "source_version": "1", "verification_status": "VERIFIED"})
    assert assertion["verification_status"] == "VERIFIED"
    release = _post(client, f"/api/form-automation/profiles/{profile['id']}/mapping-releases", {"version": "DRAFT-1"})
    _post(client, f"/api/form-automation/mapping-releases/{release['id']}/rules", {"logical_field_key": semantic_key["semantic_key"], "target_key": "case_reference", "transform_type": "SCALAR", "target_writer": "SYSTEM"})
    _post(client, f"/api/form-automation/mapping-releases/{release['id']}/rules", {"logical_field_key": semantic_key["semantic_key"], "target_key": "authority_reference", "transform_type": "SCALAR", "target_writer": "AUTHORITY_ONLY"})
    instance = _post(client, "/api/form-automation/instances", {"profile_id": profile["id"], "mapping_release_id": release["id"], "context_type": "AuthorityCase", "context_id": case["id"], "semantic_keys": [semantic_key["semantic_key"]]})
    rendered = _post(client, f"/api/form-automation/instances/{instance['id']}/render", {})
    assert rendered["artifact"]["generated_payload"]["fields"]["case_reference"] == f"CASE-{suffix}"
    assert rendered["artifact"]["generated_payload"]["skipped_writer_targets"][0]["writer"] == "AUTHORITY_ONLY"
    assert client.post(f"/api/form-automation/artifacts/{rendered['artifact']['id']}/validate", headers=OWNER).status_code == 200
    assert client.post(f"/api/form-automation/artifacts/{rendered['artifact']['id']}/qa", json={"result": "PASS", "checks_json": {"rtl": "SEAM_VERIFIED"}}, headers=OWNER).status_code == 200
    overflow_release = _post(client, f"/api/form-automation/profiles/{profile['id']}/mapping-releases", {"version": "DRAFT-OVERFLOW"})
    _post(client, f"/api/form-automation/mapping-releases/{overflow_release['id']}/rules", {"logical_field_key": "rows", "target_key": "rows", "transform_type": "REPEATING_GRID", "target_writer": "SYSTEM", "capacity": 1})
    overflow_instance = _post(client, "/api/form-automation/instances", {"profile_id": profile["id"], "mapping_release_id": overflow_release["id"], "context_type": "AuthorityCase", "context_id": case["id"], "resolved_values": {"rows": [{"n": 1}, {"n": 2}]}})
    assert client.post(f"/api/form-automation/instances/{overflow_instance['id']}/render", headers=OWNER).status_code == 409
    assert client.post(f"/api/form-automation/mapping-releases/{release['id']}/release", headers=OWNER).status_code == 409
    assert client.get("/api/shared-domain/future-seam", headers=OWNER).status_code == 200

    _cleanup_foundations()
