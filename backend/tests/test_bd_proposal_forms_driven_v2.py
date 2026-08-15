"""Executable commercial/scoping contract for BD Proposal Forms-driven v2."""

from sqlalchemy import delete, select, update

from backend.app.db import SessionLocal
from backend.app.models import (
    AuthorityCase,
    ClientAccount,
    Document,
    DocumentVersion,
    ExternalBody,
    Jurisdiction,
    AssistantHandoff,
    NotificationEvent,
    Party,
    ProposalAcceptedRevision,
    ProposalAssumption,
    ProposalContactContext,
    ProposalEngineeringContribution,
    ProposalExpectedInputPreview,
    ProposalExternalCostAssumption,
    ProposalRegulatoryScopeIntent,
    ProposalServiceScopeItem,
    ProposalSiteContext,
    ProposalSourceLink,
    ProposalOutputArtifact,
    ProposalSourceEvidence,
    ProposalIntakeArtifact,
    Opportunity,
    ProposalStakeholderIntent,
    ServiceType,
)


OWNER = {"X-Dev-Role": "OWNER_SPONSOR"}
BD = {"X-Dev-Role": "COMMERCIAL_APPROVER"}
ENGINEERING = {"X-Dev-Role": "RESPONSIBLE_ENGINEER"}


def _ensure_templates(client):
    for ref, title, usage in (("F-0003", "Synthetic BD v2 Proposal Template", "PROPOSAL_TEMPLATE"), ("F-0004", "Synthetic BD v2 Proposal Checklist", "PROPOSAL_CHECKLIST")):
        rows = client.get("/api/master-content", params={"q": ref}, headers=OWNER).json()
        item = next((row for row in rows if row["ref"] == ref), None)
        if not item:
            response = client.post("/api/master-content", data={"content_type": "FORM", "ref": ref, "title": title, "description": title, "used_in": '["BD"]'}, files={"file": (f"{ref}.txt", b"synthetic BD v2 content", "text/plain")}, headers=OWNER)
            assert response.status_code == 200, response.text
            item = response.json()
        bound = client.put(f"/api/master-content/{item['id']}/module-bindings", json=[{"module": "BD", "usage_type": usage}], headers=OWNER)
        assert bound.status_code == 200, bound.text


def _advance_to_engineering_handoff(client, proposal_id: str):
    proceeded = client.post(f"/api/bd/proposals/{proposal_id}/proceed", headers=BD)
    assert proceeded.status_code == 200, proceeded.text
    ready = client.post(f"/api/proposals-main/proposals/{proposal_id}/engineering-ready", headers={"X-Dev-Role": "RESPONSIBLE_ENGINEER"})
    assert ready.status_code == 200, ready.text


def _cleanup(proposal_id: str) -> None:
    with SessionLocal() as db:
        proposal = db.get(Opportunity, proposal_id)
        source_links = list(db.scalars(select(ProposalSourceLink).where(ProposalSourceLink.proposal_id == proposal_id)).all())
        document_ids = {row.document_id for row in source_links if row.document_id}
        db.execute(delete(ProposalExpectedInputPreview).where(ProposalExpectedInputPreview.proposal_id == proposal_id))
        db.execute(delete(ProposalEngineeringContribution).where(ProposalEngineeringContribution.proposal_id == proposal_id))
        db.execute(delete(ProposalExternalCostAssumption).where(ProposalExternalCostAssumption.proposal_id == proposal_id))
        db.execute(delete(ProposalAssumption).where(ProposalAssumption.proposal_id == proposal_id))
        db.execute(delete(ProposalRegulatoryScopeIntent).where(ProposalRegulatoryScopeIntent.proposal_id == proposal_id))
        db.execute(delete(ProposalServiceScopeItem).where(ProposalServiceScopeItem.proposal_id == proposal_id))
        db.execute(delete(ProposalStakeholderIntent).where(ProposalStakeholderIntent.proposal_id == proposal_id))
        db.execute(delete(ProposalSourceLink).where(ProposalSourceLink.proposal_id == proposal_id))
        db.execute(delete(ProposalSiteContext).where(ProposalSiteContext.proposal_id == proposal_id))
        db.execute(delete(ProposalContactContext).where(ProposalContactContext.proposal_id == proposal_id))
        db.execute(delete(ProposalOutputArtifact).where(ProposalOutputArtifact.proposal_id == proposal_id))
        db.execute(delete(ProposalAcceptedRevision).where(ProposalAcceptedRevision.proposal_id == proposal_id))
        db.execute(delete(ProposalSourceEvidence).where(ProposalSourceEvidence.proposal_id == proposal_id))
        db.execute(delete(ProposalIntakeArtifact).where(ProposalIntakeArtifact.opportunity_id == proposal_id))
        db.execute(delete(NotificationEvent).where(NotificationEvent.proposal_id == proposal_id))
        db.execute(delete(AssistantHandoff).where(AssistantHandoff.opportunity_id == proposal_id))
        db.execute(delete(Opportunity).where(Opportunity.id == proposal_id))
        for document_id in document_ids:
            db.execute(delete(DocumentVersion).where(DocumentVersion.document_id == document_id))
            db.execute(delete(Document).where(Document.id == document_id))
        db.commit()
    if proposal:
        from shutil import rmtree
        from backend.app.services.proposals_sor import intake_sor_root
        rmtree(intake_sor_root() / proposal.opportunity_reference, ignore_errors=True)


def test_bd_forms_v2_commercial_scoping_accept_snapshot_and_rbac(client):
    _ensure_templates(client)
    created = client.post("/api/bd/proposals", json={"proposal_description": "Synthetic Forms v2 Commercial Proposal", "project_reference": "OPP-FORMS-V2", "client_name": "Synthetic Commercial Client"}, headers=BD)
    assert created.status_code == 200, created.text
    proposal_id = created.json()["id"]
    created_catalog_ids: list[tuple[type, str]] = []
    party_id = None
    try:
        fields = {"project_description": "Synthetic site advisory", "client_scope_of_work": "Client requests design coordination", "scope_of_work": "AMEC provides design coordination and advisory", "price": "100000", "currency": "QAR", "duration": "3 months", "inclusions": "Coordination", "exclusions": "Authority fees"}
        patched = client.patch(f"/api/bd/proposals/{proposal_id}", json={"fields": fields}, headers=BD)
        assert patched.status_code == 200, patched.text

        uploaded = client.post(f"/api/bd/proposals/{proposal_id}/sources", data={"source_type": "TENDER_DOCUMENT"}, files={"file": ("synthetic-tender.txt", b"Synthetic tender evidence", "text/plain")}, headers=BD)
        assert uploaded.status_code == 200, uploaded.text
        assert uploaded.json()["proposal"]["forms_v2"]["source_links"][0]["document_version_id"]

        contact = client.put(f"/api/bd/proposals/{proposal_id}/contact", json={"display_name": "Synthetic Proposal Contact", "email": "contact@example.invalid", "mobile": "+97400000000"}, headers=BD)
        assert contact.status_code == 200, contact.text
        party = Party(party_type="COMPANY", name_en="Synthetic Commercial Client", status="CURRENT")
        with SessionLocal() as db:
            db.add(party)
            db.commit()
            party_id = party.id
        linked = client.put(f"/api/bd/proposals/{proposal_id}/client-party", json={"canonical_party_id": party_id}, headers=BD)
        assert linked.status_code == 200, linked.text

        scope = client.post(f"/api/bd/proposals/{proposal_id}/scope-items", json={"service_offering_code": "DESIGN_COORDINATION", "discipline_code": "ARCHITECTURE", "description": "Structured AMEC service scope", "included": True}, headers=BD)
        assert scope.status_code == 200, scope.text
        with SessionLocal() as db:
            jurisdiction = db.scalar(select(Jurisdiction))
            if not jurisdiction:
                jurisdiction = Jurisdiction(code="SYN-BD-FORMS-J", country_code="QA", name_en="Synthetic BD Jurisdiction", status="ACTIVE")
                db.add(jurisdiction)
                db.flush()
                created_catalog_ids.append((Jurisdiction, jurisdiction.id))
            body = db.scalar(select(ExternalBody))
            if not body:
                body = ExternalBody(code="SYN-BD-FORMS-BODY", name_en="Synthetic BD Body", status="ACTIVE", verification_state="VERIFIED")
                db.add(body)
                db.flush()
                created_catalog_ids.append((ExternalBody, body.id))
            service = db.scalar(select(ServiceType))
            if not service:
                service = ServiceType(code="SYN-BD-FORMS-SERVICE", name_en="Synthetic BD Service", status="ACTIVE")
                db.add(service)
                db.flush()
                created_catalog_ids.append((ServiceType, service.id))
            body_id, service_id, jurisdiction_id = body.id, service.id, jurisdiction.id
            db.commit()
        intent = client.post(f"/api/bd/proposals/{proposal_id}/regulatory-scope", json={"external_body_id": body_id, "service_type_id": service_id, "jurisdiction_id": jurisdiction_id, "status": "DRAFT", "source_type": "HUMAN_ENTERED", "rationale": "Synthetic commercial planning context"}, headers=BD)
        assert intent.status_code == 200, intent.text
        intent_id = intent.json()["forms_v2"]["regulatory_scope_intents"][0]["id"]
        confirmed = client.post(f"/api/bd/proposals/{proposal_id}/regulatory-scope/{intent_id}/confirm", headers=BD)
        assert confirmed.status_code == 200, confirmed.text
        assert confirmed.json()["forms_v2"]["regulatory_scope_intents"][0]["status"] == "HUMAN_CONFIRMED_FOR_PROPOSAL"

        assumption = client.post(f"/api/bd/proposals/{proposal_id}/assumptions", json={"category": "PROPERTY", "statement": "Site boundary remains subject to later canonical resolution", "materiality": "MATERIAL"}, headers=BD)
        assert assumption.status_code == 200, assumption.text
        assumption_id = assumption.json()["forms_v2"]["assumptions"][0]["id"]
        assert client.post(f"/api/bd/proposals/{proposal_id}/assumptions/{assumption_id}/acknowledge", headers=BD).status_code == 200

        preview = client.post(f"/api/bd/proposals/{proposal_id}/expected-client-inputs/preview", headers=BD)
        assert preview.status_code == 200, preview.text
        assert preview.json()["forms_v2"]["expected_client_inputs"]["status"] in {"NO_POLICY", "POLICY_AMBIGUOUS", "POLICY_RESOLVED", "APPLICABILITY_UNKNOWN"}

        readiness = client.get(f"/api/bd/proposals/{proposal_id}/readiness", headers=BD)
        assert readiness.status_code == 200, readiness.text
        assert readiness.json()["commercial_ready_not_regulatory_ready"] is True
        _advance_to_engineering_handoff(client, proposal_id)
        accepted = client.post(f"/api/bd/proposals/{proposal_id}/accept", headers=OWNER)
        assert accepted.status_code == 200, accepted.text
        snapshot = accepted.json()["current_revision"]
        assert snapshot["revision_number"] == 1
        with SessionLocal() as db:
            revision = db.scalar(select(ProposalAcceptedRevision).where(ProposalAcceptedRevision.proposal_id == proposal_id))
            assert revision.snapshot["forms_driven_v2"]["commercial_client"]["canonical_party_id"] == party_id
            assert revision.snapshot["forms_driven_v2"]["regulatory_scope_intents"][0]["status"] == "HUMAN_CONFIRMED_FOR_PROPOSAL"
            assert db.scalar(select(AuthorityCase)) is None

        assert client.patch(f"/api/bd/proposals/{proposal_id}", json={"fields": {"price": "200000"}}, headers=ENGINEERING).status_code == 403
        assert client.post(f"/api/bd/proposals/{proposal_id}/regulatory-scope/{intent_id}/confirm", headers=ENGINEERING).status_code == 403
        assert client.post(f"/api/bd/proposals/{proposal_id}/engineering-contributions", json={"discipline_code": "ARCHITECTURE", "content": "Engineering contribution only"}, headers=ENGINEERING).status_code == 200
    finally:
        _cleanup(proposal_id)
        with SessionLocal() as db:
            if party_id:
                db.execute(update(ClientAccount).where(ClientAccount.canonical_party_id == party_id).values(canonical_party_id=None))
            party = db.scalar(select(Party).where(Party.name_en == "Synthetic Commercial Client"))
            if party:
                db.delete(party)
            for model, row_id in reversed(created_catalog_ids):
                row = db.get(model, row_id)
                if row:
                    db.delete(row)
            db.commit()


def test_bd_forms_v2_unresolved_site_and_exact_contract_boundary(client):
    created = client.post("/api/bd/proposals", json={"proposal_description": "Synthetic unresolved site proposal", "client_name": "Synthetic Site Client"}, headers=BD)
    assert created.status_code == 200
    proposal_id = created.json()["id"]
    try:
        site = client.put(f"/api/bd/proposals/{proposal_id}/site-context", json={"status": "UNRESOLVED", "location_text": "Synthetic Lusail site", "plot_text": "PLOT-UNKNOWN", "area_value": 500, "area_unit": "m2", "area_kind": "LEGACY_UNSPECIFIED"}, headers=BD)
        assert site.status_code == 200, site.text
        site_payload = site.json()["forms_v2"]["site_context"]
        assert site_payload["status"] == "UNRESOLVED"
        assert site_payload["property"] is None
        assert site_payload["area_kind"] == "LEGACY_UNSPECIFIED"
        detail = client.get(f"/api/bd/proposals/{proposal_id}", headers=BD)
        assert detail.status_code == 200
        assert detail.json()["readiness_v2"]["commercial_ready_not_regulatory_ready"] is True
        assert client.post(f"/api/bd/proposals/{proposal_id}/handoff/contract", headers=BD).status_code in {403, 409}
    finally:
        _cleanup(proposal_id)
