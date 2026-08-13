from datetime import datetime, timezone
from uuid import uuid4

from backend.app.db import SessionLocal
from backend.app.models import ConsultancyOffice, ExternalBody, Jurisdiction, Party, Project, RequirementDefinition, RequirementPolicyItem, RequirementPolicyVersion, ServiceType


def _headers(role="SYSTEM_ADMIN", actor="prebilling-owner"):
    return {"X-Dev-Role": role, "X-Dev-Actor": actor}


def test_case_parties_authorization_contact_snapshot_and_revalidation(client):
    suffix = uuid4().hex[:10].upper()
    with SessionLocal() as db:
        office = db.query(ConsultancyOffice).first()
        project = Project(project_number=f"PBC-{suffix}", project_name="Pre-billing context project", office_id=office.id, workstream="REGULATORY", status="ACTIVE", municipality="Synthetic Municipality", permit_type="Building", activated_at=datetime.now(timezone.utc), activated_by="prebilling-owner")
        body = ExternalBody(code=f"PBC-BODY-{suffix}", name_en="Synthetic Authority", body_type="AUTHORITY", status="ACTIVE", verification_state="VERIFIED", created_by="prebilling-owner")
        jurisdiction = Jurisdiction(code=f"PBC-JUR-{suffix}", country_code="QA", name_en="Synthetic Jurisdiction", level="LOCALITY", status="ACTIVE")
        service = ServiceType(code=f"PBC-SERVICE-{suffix}", name_en="Synthetic Service", status="ACTIVE")
        definition = RequirementDefinition(code=f"PBC-REQ-{suffix}", name_en="Synthetic requirement", kind="DOCUMENT", status="ACTIVE")
        owner = Party(party_type="INDIVIDUAL", name_en="Owner Person B", identifier_type="QID", identifier_value="B", status="CURRENT")
        applicant = Party(party_type="INDIVIDUAL", name_en="Applicant Person C", identifier_type="QID", identifier_value="C", status="CURRENT")
        agent = Party(party_type="COMPANY", name_en="Agent Office", status="CURRENT")
        commercial_client = Party(party_type="COMPANY", name_en="Commercial Client", status="CURRENT")
        db.add_all([project, body, jurisdiction, service, definition, owner, applicant, agent, commercial_client]); db.flush()
        policy = RequirementPolicyVersion(service_type_id=service.id, jurisdiction_id=jurisdiction.id, external_body_id=body.id, version="PBC-1", status="ACTIVE", purpose="AUTHORITY_SUBMISSION", approved_by="prebilling-owner", approved_at=datetime.now(timezone.utc))
        db.add(policy); db.flush(); db.add(RequirementPolicyItem(policy_version_id=policy.id, requirement_definition_id=definition.id, status="ACTIVE", order_index=1)); db.commit()
        project_id, body_id, jurisdiction_id, service_id, commercial_client_id = project.id, body.id, jurisdiction.id, service.id, commercial_client.id

    created = client.post("/api/authority-cases", headers=_headers(), json={"project_id": project_id, "external_body_id": body_id, "jurisdiction_id": jurisdiction_id, "service_type_id": service_id, "idempotency_key": f"pbc-case-{suffix}"})
    assert created.status_code == 200, created.text
    case_id = created.json()["case"]["id"]
    assert created.json()["journey"]["id"]
    assert client.post(f"/api/regulatory-context/cases/{case_id}/party-roles", headers=_headers(), json={"party_id": owner.id, "role_code": "PROPERTY_OWNER"}).status_code == 200
    assert client.post(f"/api/regulatory-context/cases/{case_id}/party-roles", headers=_headers(), json={"party_id": applicant.id, "role_code": "APPLICANT"}).status_code == 200
    assert client.post(f"/api/regulatory-context/cases/{case_id}/party-roles", headers=_headers(), json={"party_id": commercial_client_id, "role_code": "COMMERCIAL_CLIENT"}).status_code == 200
    authorization = client.post(f"/api/regulatory-context/cases/{case_id}/authorizations", headers=_headers(), json={"grantor_party_id": applicant.id, "grantee_party_id": agent.id, "authorization_type": "POWER_OF_ATTORNEY", "scope": "Prepare and coordinate this case", "status": "VALID"})
    assert authorization.status_code == 200 and authorization.json()["filename_only_authorization"] is False
    contact = client.post(f"/api/regulatory-context/cases/{case_id}/contacts", headers=_headers(), json={"party_id": agent.id, "purpose": "REGULATORY", "channel": "EMAIL", "value": "agent@example.test", "verified": True})
    assert contact.status_code == 200 and contact.json()["value_present"] is True
    general_contact = client.post(f"/api/regulatory-context/cases/{case_id}/contacts", headers=_headers(), json={"party_id": commercial_client_id, "purpose": "GENERAL", "channel": "MOBILE", "value": "+97400000000", "verified": True})
    assert general_contact.status_code == 200
    initialized = client.post(f"/api/authority-cases/{case_id}/requirements/initialize", headers=_headers(), json={})
    assert initialized.status_code == 200, initialized.text
    preparation = client.post(f"/api/authority-cases/{case_id}/preparations", headers=_headers(), json={})
    assert preparation.status_code == 200, preparation.text
    preparation_id = preparation.json()["id"]
    assert preparation.json()["case_party_snapshot_id"]
    context = client.get(f"/api/regulatory-context/cases/{case_id}", headers=_headers())
    assert context.status_code == 200
    roles = {item["role_code"]: item["party"]["name_en"] for item in context.json()["parties_representation"]["assignments"]}
    assert roles == {"APPLICANT": "Applicant Person C", "COMMERCIAL_CLIENT": "Commercial Client", "PROPERTY_OWNER": "Owner Person B"}
    assert {item["purpose"] for item in context.json()["parties_representation"]["contacts"]} == {"GENERAL", "REGULATORY"}
    assert context.json()["parties_representation"]["role_semantics"]["general_mobile_is_not_regulatory_contact"] is True
    replacement = Party(party_type="COMPANY", name_en="Replacement Consultant", status="CURRENT")
    with SessionLocal() as db:
        db.add(replacement); db.commit(); replacement_id = replacement.id
    changed = client.post(f"/api/regulatory-context/cases/{case_id}/party-roles", headers=_headers(), json={"party_id": replacement_id, "role_code": "CONSULTANT"})
    assert changed.status_code == 200
    with SessionLocal() as db:
        prep_row = db.get(__import__("backend.app.models", fromlist=["PreparationRevision"]).PreparationRevision, preparation_id)
        assert prep_row.status == "NEEDS_REVALIDATION"
