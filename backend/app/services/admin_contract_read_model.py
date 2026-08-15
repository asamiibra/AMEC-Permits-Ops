"""Owner-facing Contract reconciliation read model extensions."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import ClientAccount, ClientContact, Contract, ContractAdminEvidence, ContractClientInputRequirement, ContractDeliverableCommitment, ContractPaymentTerm, ContractRevision, ContractTemplateSnapshot, DocumentVersion, Opportunity, ProposalAcceptedRevision, ProposalContactContext
from .contract_workspace import contract_billing_context
from .owner_decisions import runtime_decision_value


def _document(db: Session, version_id: str | None) -> dict[str, Any] | None:
    if not version_id:
        return None
    version = db.get(DocumentVersion, version_id)
    if not version:
        return {"id": version_id, "status": "MISSING"}
    approval = version.approval_state.value if hasattr(version.approval_state, "value") else version.approval_state
    return {"id": version.id, "document_id": version.document_id, "version_number": version.version_number, "filename": version.source_filename, "source_reference": version.source_path_or_reference, "sha256": version.sha256, "approval_state": approval, "read_back_verified": bool((version.metadata_json or {}).get("read_back_verified")), "synthetic_only": bool((version.metadata_json or {}).get("synthetic_only")), "download": None}


def _client_fields(db: Session, contract: Contract, revision: ContractRevision | None) -> dict[str, Any]:
    client = db.get(ClientAccount, contract.client_account_id) if contract.client_account_id else None
    contact = db.scalars(select(ClientContact).where(ClientContact.client_account_id == contract.client_account_id, ClientContact.status == "ACTIVE").order_by(ClientContact.name)).first() if contract.client_account_id else None
    proposal = db.get(Opportunity, contract.proposal_id) if contract.proposal_id else None
    proposal_contact = db.scalar(select(ProposalContactContext).where(ProposalContactContext.proposal_id == contract.proposal_id)) if contract.proposal_id else None
    accepted = db.get(ProposalAcceptedRevision, contract.accepted_proposal_revision_id) if contract.accepted_proposal_revision_id else None
    override = dict((revision.admin_input_snapshot or {}).get("client_fields") or {}) if revision else {}
    canonical = {
        "client_name": client.display_name if client else (proposal_contact.display_name if proposal_contact else None),
        "client_company": client.legal_name if client else None,
        "cr_number": client.commercial_registration_number if client else None,
        "mobile": contact.phone if contact else (proposal_contact.mobile if proposal_contact else None),
        "pin_number": None,
        "client_email": contact.email if contact else (proposal_contact.email if proposal_contact else None),
    }
    labels = {"client_name": "Client master", "client_company": "Client master", "cr_number": "Client master", "mobile": "Client contact", "client_email": "Client contact", "pin_number": "Owner definition required"}
    fields: dict[str, Any] = {}
    for key, canonical_value in canonical.items():
        diverged = key in override
        value = override.get(key) if diverged else canonical_value
        fields[key] = {"value": value, "display_value": value or ("Not configured" if key == "pin_number" else "Needs confirmation"), "source": "CONTRACT_REVISION" if diverged else ("OWNER_DEFINITION_REQUIRED" if key == "pin_number" else "CLIENT_MASTER"), "source_label": "Contract revision" if diverged else labels[key], "read_only": key == "pin_number" and not diverged, "diverged": diverged, "snapshot": bool(revision and (revision.status in {"FINALIZED", "APPROVED"})), "last_changed": revision.created_at.isoformat() if diverged and revision and revision.created_at else None}
    return {"fields": fields, "canonical_client_id": client.id if client else None, "accepted_revision_id": accepted.id if accepted else None, "proposal_id": proposal.id if proposal else None, "pin_semantic_status": "OWNER_DEFINITION_REQUIRED"}


def owner_contract_extensions(db: Session, contract: Contract) -> dict[str, Any]:
    revision = db.get(ContractRevision, contract.current_revision_id) if contract.current_revision_id else None
    terms = db.scalars(select(ContractPaymentTerm).where(ContractPaymentTerm.contract_revision_id == revision.id).order_by(ContractPaymentTerm.sequence)).all() if revision else []
    deliverables = db.scalars(select(ContractDeliverableCommitment).where(ContractDeliverableCommitment.contract_revision_id == revision.id).order_by(ContractDeliverableCommitment.sequence)).all() if revision else []
    client_inputs = db.scalars(select(ContractClientInputRequirement).where(ContractClientInputRequirement.contract_revision_id == revision.id).order_by(ContractClientInputRequirement.sequence)).all() if revision else []
    contacts = db.scalars(select(ClientContact).where(ClientContact.client_account_id == contract.client_account_id, ClientContact.status == "ACTIVE").order_by(ClientContact.name)).all() if contract.client_account_id else []
    evidence = db.scalars(select(ContractAdminEvidence).where(ContractAdminEvidence.contract_id == contract.id).order_by(ContractAdminEvidence.recorded_at.desc())).all()
    client_fields = _client_fields(db, contract, revision)
    current_by_role: dict[str, Any] = {}
    for item in evidence:
        if item.source_role in {"LPO", "CLIENT_DOCUMENT"} and item.source_role not in current_by_role:
            current_by_role[item.source_role] = item
    template = db.scalar(select(ContractTemplateSnapshot).where(ContractTemplateSnapshot.contract_id == contract.id).order_by(ContractTemplateSnapshot.captured_at.desc()))
    proposal = db.get(Opportunity, contract.proposal_id) if contract.proposal_id else None
    accepted = db.get(ProposalAcceptedRevision, contract.accepted_proposal_revision_id) if contract.accepted_proposal_revision_id else None
    lpo_policy = str(runtime_decision_value(db, "CONTRACT_LPO_REQUIREDNESS_POLICY", "OWNER_DEFINITION_REQUIRED"))
    def panel_document(role: str) -> dict[str, Any]:
        item = current_by_role.get(role)
        document = _document(db, item.document_version_id) if item else None
        if document:
            document["download"] = f"/api/admin/contracts/{contract.id}/documents/{document['id']}/download"
        return {"status": item.status if item else "NEEDED", "document": document, "count": sum(1 for row in evidence if row.source_role == role), "history": [{"id": row.id, "status": row.status, "recorded_at": row.recorded_at.isoformat(), "document": _document(db, row.document_version_id)} for row in evidence if row.source_role == role]}
    lpo = panel_document("LPO")
    client_document = panel_document("CLIENT_DOCUMENT")
    source_panel = [
        {"key": "contract", "label": "Contract", "detail": f"Current Contract Revision {revision.revision_number}" if revision else "Current Contract Revision pending", "source": "ContractRevision", "open": None},
        {"key": "document_list", "label": "Document List", "detail": f"{len(client_inputs)} structured client input(s)", "source": "ContractClientInputRequirement", "open": f"/admin/contracts/{contract.id}#documents-needed"},
        {"key": "proposal", "label": "Accepted Proposal", "detail": f"{proposal.opportunity_reference} · Revision {accepted.revision_number}" if proposal and accepted else "Accepted Proposal pending", "source": "AcceptedProposalRevision", "open": f"/opportunities/{proposal.id}" if proposal else None},
        {"key": "lpo", "label": "LPO", "detail": lpo["document"]["filename"] if lpo["document"] else "Needed / not received", "source": "DocumentVersion", "open": lpo["document"]["download"] if lpo["document"] else None},
        {"key": "client_document", "label": "Client Document", "detail": client_document["document"]["filename"] if client_document["document"] else "Needed / not received", "source": "DocumentVersion", "open": client_document["document"]["download"] if client_document["document"] else None},
        {"key": "contract_template", "label": "Contract Template", "detail": f"Dashboard · v{template.version}" if template else "Dashboard template unresolved", "source": "Dashboard", "open": f"/api/master-content/{template.master_content_id}/download" if template else None},
    ]
    return {
        "contract": {"payment_condition_text": contract.payment_condition_text, "contracted_scope_text": contract.contracted_scope_text, "valuation_amount": str(contract.valuation_amount) if contract.valuation_amount is not None else None, "valuation_currency": contract.valuation_currency, "valuation_basis": contract.valuation_basis, "valuation_status": contract.valuation_status, "project_opportunity_ref": contract.project_opportunity_ref, "project_description": ((accepted.snapshot or {}).get("project_description") if accepted else None) or ((accepted.snapshot or {}).get("fields", {}).get("project_description") if accepted else None) or ((accepted.snapshot or {}).get("fields", {}).get("scope_of_work") if accepted else None)},
        "client_fields": client_fields["fields"],
        "field_lineage": client_fields,
        "client_contacts": [{"id": item.id, "name": item.name, "email": item.email, "phone": item.phone, "role_title": item.role_title} for item in contacts],
        "payment_terms": [{"id": item.id, "sequence": item.sequence, "label": item.label, "term_text": item.term_text, "basis_type": item.basis_type, "percentage": str(item.percentage) if item.percentage is not None else None, "fixed_amount": str(item.fixed_amount) if item.fixed_amount is not None else None, "currency": item.currency, "trigger_type": item.trigger_type, "trigger_description": item.trigger_description, "due_days": item.due_days, "source_clause": item.source_clause, "source_document": _document(db, item.source_document_version_id), "status": item.status, "human_verified_by": item.human_verified_by, "human_verified_at": item.human_verified_at.isoformat() if item.human_verified_at else None} for item in terms],
        "deliverables": [{"id": item.id, "sequence": item.sequence, "commitment_ref": item.commitment_ref, "name": item.name, "description": item.description, "due_trigger_description": item.due_trigger_description, "status": item.status, "source_document": _document(db, item.source_document_version_id), "human_verified_by": item.human_verified_by} for item in deliverables],
        "client_inputs": [{"id": item.id, "sequence": item.sequence, "input_code": item.input_code, "title": item.title, "description": item.description, "required": item.required, "status": item.status, "source_type": item.source_type, "source_document": _document(db, item.source_document_version_id), "human_verified_by": item.human_verified_by} for item in client_inputs],
        "evidence_detail": [{"id": item.id, "type": item.evidence_type, "source_role": item.source_role, "source_reference": item.source_reference, "document": _document(db, item.document_version_id), "hash": item.content_hash, "status": item.status, "recorded_by": item.recorded_by} for item in evidence],
        "client_document": client_document,
        "lpo": {**lpo, "requiredness": lpo_policy},
        "documents_needed": [{"id": item.id, "title": item.title, "description": item.description, "required": item.required, "status": item.status, "source_type": item.source_type, "evidence": _document(db, item.source_document_version_id)} for item in client_inputs],
        "deliverable_commitments": [{"id": item.id, "name": item.name, "description": item.description, "status": item.status, "due_trigger_description": item.due_trigger_description, "source_document": _document(db, item.source_document_version_id)} for item in deliverables],
        "source_panel": source_panel,
        "billing_readiness": contract_billing_context(db, contract),
        "boundary": {"proposal_accept": "IMMUTABLE_ACCEPTED_PROPOSAL_REVISION", "contract_authority": "OWNER_CONTRACT_AUTHORITY_ONLY", "project_activation": "EXPLICIT_HUMAN_OWNER_ACTION"},
    }
