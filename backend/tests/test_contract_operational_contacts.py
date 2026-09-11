"""CM-G16 purpose-specific operational contact controls."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from backend.app.db import SessionLocal
from backend.app.models import (
    AuditEvent,
    AuthorityCase,
    ClientAccount,
    ContactPoint,
    Contract,
    ContractAdminEvidence,
    ContractRevision,
    ConsultancyOffice,
    ClientContact,
    ExternalBody,
    Jurisdiction,
    LineageEdge,
    NotificationEvent,
    Opportunity,
    Party,
    PartyRoleAssignment,
    Project,
    Quotation,
    QuotationRevision,
    ServiceType,
    WorkflowTask,
)
from backend.app.services.contract_workspace import resolve_operational_contact


def _headers(actor="cm16-owner"):
    return {"X-Dev-Role": "OWNER_SPONSOR", "X-Dev-Actor": actor}


def test_cm16_exact_contact_routing_history_fallback_and_work(client):
    suffix = uuid4().hex[:10].upper()
    ids = {}
    with SessionLocal() as db:
        office = db.query(ConsultancyOffice).first()
        client_party = Party(party_type="COMPANY", name_en=f"Client Organization {suffix}", status="CURRENT")
        operational_party = Party(party_type="INDIVIDUAL", name_en=f"Operations Contact {suffix}", status="CURRENT")
        owner_party = Party(party_type="INDIVIDUAL", name_en=f"Legal Owner {suffix}", status="CURRENT")
        client_account = ClientAccount(client_reference=f"CM16-CLIENT-{suffix}", legal_name=client_party.name_en, display_name=client_party.name_en, client_type="COMPANY", canonical_party_id=client_party.id, data_classification="SYNTHETIC", status="ACTIVE")
        project = Project(project_number=f"CM16-PROJECT-{suffix}", project_name="CM-G16 Contact Routing", office_id=office.id, workstream="CONTRACT", status="ACTIVE", municipality="Synthetic Municipality", permit_type="Building")
        proposal = Opportunity(office_id=office.id, client_account_id=client_account.id, opportunity_reference=f"CM16-OPP-{suffix}", title="CM16 contact routing proposal", status="ACCEPTED", source_type="SYNTHETIC", project_id=project.id)
        quotation = Quotation(opportunity_id=proposal.id, quotation_reference=f"CM16-QTN-{suffix}", status="RELEASED_FOR_CONTRACT", client_account_id=client_account.id)
        quotation_revision = QuotationRevision(quotation_id=quotation.id, revision_number=1, source_snapshot={"synthetic": True}, content_hash="a" * 64, status="RELEASED", created_by="cm16-owner")
        contract = Contract(client_account_id=client_account.id, quotation_id=quotation.id, contract_reference=f"CM16-CTR-{suffix}", status="ACTIVE", project_id=project.id, proposal_id=proposal.id, project_opportunity_ref=project.project_number, contract_name="CM-G16 Contact Routing", amount_value="100", currency="QAR", duration="30 days")
        revision = ContractRevision(contract_id=contract.id, revision_number=1, controlling_quotation_revision_id=quotation_revision.id, content_hash="b" * 64, status="FINALIZED", accepted_proposal_revision_id=None)
        body = ExternalBody(code=f"CM16-BODY-{suffix}", name_en="Synthetic Authority", body_type="AUTHORITY", status="ACTIVE", verification_state="VERIFIED", created_by="cm16-owner")
        jurisdiction = Jurisdiction(code=f"CM16-JUR-{suffix}", country_code="QA", name_en="Synthetic Jurisdiction", level="LOCALITY", status="ACTIVE")
        service = ServiceType(code=f"CM16-SERVICE-{suffix}", name_en="Synthetic Service", status="ACTIVE")
        case = AuthorityCase(case_reference=f"CM16-CASE-{suffix}", external_body_id=body.id, service_type_id=service.id, jurisdiction_id=jurisdiction.id, status="DRAFT", project_required=True, created_by="cm16-owner")
        contact = ContactPoint(project_id=project.id, authority_case_id=case.id, party_id=operational_party.id, purpose="MISSING_DOCUMENT_REQUEST", channel="EMAIL", value="ops@example.test", verified=True, status="VERIFIED", maintained_by="cm16-owner")
        db.add_all([client_party, operational_party, owner_party])
        db.flush()
        client_account.canonical_party_id = client_party.id
        db.add_all([client_account, project, body, jurisdiction, service])
        db.flush()
        generic_client_contact = ClientContact(client_account_id=client_account.id, name="Generic client contact", email="generic@example.test", phone="+97411111111", role_title="General contact", status="ACTIVE")
        db.add(generic_client_contact)
        db.flush()
        proposal.client_account_id = client_account.id
        proposal.project_id = project.id
        db.add(proposal)
        db.flush()
        quotation.opportunity_id = proposal.id
        quotation.client_account_id = client_account.id
        db.add(quotation)
        db.flush()
        quotation_revision.quotation_id = quotation.id
        db.add(quotation_revision)
        db.flush()
        contract.client_account_id = client_account.id
        contract.quotation_id = quotation.id
        contract.project_id = project.id
        contract.proposal_id = proposal.id
        db.add(contract)
        db.flush()
        revision.contract_id = contract.id
        revision.controlling_quotation_revision_id = quotation_revision.id
        db.add(revision)
        db.flush()
        case.external_body_id = body.id
        case.service_type_id = service.id
        case.jurisdiction_id = jurisdiction.id
        db.add(case)
        db.flush()
        contact.project_id = project.id
        contact.authority_case_id = case.id
        contact.party_id = operational_party.id
        db.add(contact)
        db.flush()
        quotation.current_revision_id = quotation_revision.id
        contract.current_revision_id = revision.id
        db.add_all([
            PartyRoleAssignment(project_id=project.id, authority_case_id=case.id, party_id=client_party.id, role_code="COMMERCIAL_CLIENT", status="ACTIVE", assigned_by="cm16-owner"),
            PartyRoleAssignment(project_id=project.id, authority_case_id=case.id, party_id=owner_party.id, role_code="PROPERTY_OWNER", status="ACTIVE", assigned_by="cm16-owner"),
            PartyRoleAssignment(project_id=project.id, authority_case_id=case.id, party_id=operational_party.id, role_code="OPERATIONAL_CONTACT", status="ACTIVE", assigned_by="cm16-owner"),
            PartyRoleAssignment(project_id=project.id, authority_case_id=case.id, party_id=client_party.id, role_code="OPERATIONAL_CONTACT_ORGANIZATION", status="ACTIVE", assigned_by="cm16-owner"),
        ])
        db.commit()
        ids = {"party": [client_party.id, operational_party.id, owner_party.id], "client": client_account.id, "generic_contact": generic_client_contact.id, "project": project.id, "proposal": proposal.id, "quotation": quotation.id, "quotation_revision": quotation_revision.id, "contract": contract.id, "revision": revision.id, "case": case.id, "contact": contact.id, "body": body.id, "jurisdiction": jurisdiction.id, "service": service.id}

    try:
        initial = client.get(f"/api/admin/contracts/{ids['contract']}/operations", headers=_headers())
        assert initial.status_code == 200, initial.text
        assert initial.json()["operational_contact_routing"]["purposes"]["MISSING_DOCUMENT_REQUEST"]["status"] == "CONTACT_RESOLUTION_REQUIRED"
        assert initial.json()["operational_contact_routing"]["purposes"]["MISSING_DOCUMENT_REQUEST"]["generic_fallback_used"] is False

        bound = client.post(f"/api/admin/contracts/{ids['contract']}/operational-contact-routing", headers=_headers(), json={"purpose": "MISSING_DOCUMENT_REQUEST", "contact_point_id": ids["contact"], "organization_party_id": ids["party"][0], "practical_role": "Client document coordinator", "reason": "Bind exact operational contact"})
        assert bound.status_code == 200, bound.text
        assert bound.json()["routing"]["status"] == "RESOLVED"
        assert bound.json()["routing"]["operational_contact_party_id"] == ids["party"][1]
        assert bound.json()["routing"]["organization_party_id"] == ids["party"][0]
        assert bound.json()["routing"]["value_present"] is True

        with SessionLocal() as db:
            contract = db.get(Contract, ids["contract"])
            project = db.get(Project, ids["project"])
            resolved = resolve_operational_contact(db, project=project, contract=contract, purpose="MISSING_DOCUMENT_REQUEST")
            assert resolved["status"] == "RESOLVED"
            task = client.post(f"/api/admin/contracts/{ids['contract']}/missing-document-follow-up", headers=_headers(), json={"purpose": "MISSING_DOCUMENT_REQUEST", "missing_requirement": "Signed LPO", "next_action": "Review and send the approved human follow-up.", "reason": "Create controlled missing-document work"})
            assert task.status_code == 200, task.text
            assert task.json()["decision"] == "ROUTED"
            assert task.json()["task"]["next_action_code"] == "REVIEW_MISSING_DOCUMENT_CONTACT_FOLLOWUP"

        bad_purpose = client.post(f"/api/admin/contracts/{ids['contract']}/operational-contact-routing", headers=_headers(), json={"purpose": "GENERAL_PROJECT_FOLLOWUP", "contact_point_id": ids["contact"], "organization_party_id": ids["party"][0], "practical_role": "Client document coordinator", "reason": "Reject purpose mismatch"})
        assert bad_purpose.status_code == 409
        assert bad_purpose.json()["detail"]["code"] == "CONTACT_PURPOSE_MISMATCH"

        with SessionLocal() as db:
            old_contact = db.get(ContactPoint, ids["contact"])
            updated_contact = ContactPoint(project_id=old_contact.project_id, authority_case_id=old_contact.authority_case_id, party_id=old_contact.party_id, purpose=old_contact.purpose, channel="PHONE", value="+97400000000", verified=True, status="VERIFIED", maintained_by="cm16-owner")
            db.add(updated_contact)
            db.flush()
            ids["updated_contact"] = updated_contact.id
            db.commit()
        rebound = client.post(f"/api/admin/contracts/{ids['contract']}/operational-contact-routing", headers=_headers(), json={"purpose": "MISSING_DOCUMENT_REQUEST", "contact_point_id": ids["updated_contact"], "organization_party_id": ids["party"][0], "practical_role": "Client document coordinator", "reason": "Record current contact update"})
        assert rebound.status_code == 200, rebound.text
        with SessionLocal() as db:
            assert db.get(ContactPoint, ids["contact"]) is not None
            expired_on = datetime.now(timezone.utc).date() - timedelta(days=1)
            db.get(ContactPoint, ids["contact"]).effective_until = expired_on
            db.get(ContactPoint, ids["updated_contact"]).effective_until = expired_on
            db.commit()
            assert db.get(ContactPoint, ids["contact"]).effective_until == expired_on
            assert db.get(ContactPoint, ids["updated_contact"]).effective_until == expired_on
            resolved = resolve_operational_contact(db, project=db.get(Project, ids["project"]), contract=db.get(Contract, ids["contract"]), purpose="MISSING_DOCUMENT_REQUEST")
            assert resolved["status"] == "CONTACT_RESOLUTION_REQUIRED", resolved
            assert resolved["blocker_code"] == "PURPOSE_CONTACT_EXPIRED"
            assert resolved["generic_fallback_used"] is False

        missing_work = client.post(f"/api/admin/contracts/{ids['contract']}/missing-document-follow-up", headers=_headers(), json={"purpose": "AUTHORITY_FOLLOWUP", "missing_requirement": "Authority response", "next_action": "Assign a verified authority follow-up contact.", "reason": "Missing contact must remain actionable"})
        assert missing_work.status_code == 200, missing_work.text
        assert missing_work.json()["decision"] == "CONTACT_RESOLUTION_REQUIRED"
        assert missing_work.json()["task"]["status"] == "BLOCKED"
        assert missing_work.json()["task"]["next_action_code"] == "CONTACT_RESOLUTION_REQUIRED"
    finally:
        with SessionLocal() as db:
            contact_ids = [ids["contact"]] + ([ids["updated_contact"]] if ids.get("updated_contact") else [])
            task_ids = [item.id for item in db.query(WorkflowTask).filter(WorkflowTask.context_id == ids["contract"]).all()]
            if task_ids:
                db.query(NotificationEvent).filter(NotificationEvent.workflow_task_id.in_(task_ids)).delete(synchronize_session=False)
                db.query(WorkflowTask).filter(WorkflowTask.id.in_(task_ids)).delete(synchronize_session=False)
            db.query(NotificationEvent).filter(NotificationEvent.contract_id == ids["contract"]).delete(synchronize_session=False)
            db.query(ContractAdminEvidence).filter(ContractAdminEvidence.contract_id == ids["contract"]).delete(synchronize_session=False)
            db.query(AuditEvent).filter(AuditEvent.entity_id.in_([ids["contract"], ids["project"]])).delete(synchronize_session=False)
            db.query(LineageEdge).filter(LineageEdge.project_id == ids["project"]).delete(synchronize_session=False)
            db.query(PartyRoleAssignment).filter(PartyRoleAssignment.project_id == ids["project"]).delete(synchronize_session=False)
            db.query(ContactPoint).filter(ContactPoint.id.in_(contact_ids)).delete(synchronize_session=False)
            db.query(ClientContact).filter(ClientContact.id == ids["generic_contact"]).delete(synchronize_session=False)
            db.query(ContractRevision).filter(ContractRevision.id == ids["revision"]).delete(synchronize_session=False)
            db.query(Contract).filter(Contract.id == ids["contract"]).delete(synchronize_session=False)
            db.query(QuotationRevision).filter(QuotationRevision.id == ids["quotation_revision"]).delete(synchronize_session=False)
            db.query(Quotation).filter(Quotation.id == ids["quotation"]).delete(synchronize_session=False)
            db.query(Opportunity).filter(Opportunity.id == ids["proposal"]).delete(synchronize_session=False)
            db.query(AuthorityCase).filter(AuthorityCase.id == ids["case"]).delete(synchronize_session=False)
            db.query(ClientAccount).filter(ClientAccount.id == ids["client"]).delete(synchronize_session=False)
            db.query(Project).filter(Project.id == ids["project"]).delete(synchronize_session=False)
            db.query(Party).filter(Party.id.in_(ids["party"])).delete(synchronize_session=False)
            db.query(ExternalBody).filter(ExternalBody.id == ids["body"]).delete(synchronize_session=False)
            db.query(Jurisdiction).filter(Jurisdiction.id == ids["jurisdiction"]).delete(synchronize_session=False)
            db.query(ServiceType).filter(ServiceType.id == ids["service"]).delete(synchronize_session=False)
            db.commit()
