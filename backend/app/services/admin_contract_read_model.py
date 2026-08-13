"""Owner-facing Contract reconciliation read model extensions."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import ClientContact, Contract, ContractAdminEvidence, ContractClientInputRequirement, ContractDeliverableCommitment, ContractPaymentTerm, ContractRevision, DocumentVersion
from .contract_workspace import contract_billing_context


def _document(db: Session, version_id: str | None) -> dict[str, Any] | None:
    if not version_id:
        return None
    version = db.get(DocumentVersion, version_id)
    if not version:
        return {"id": version_id, "status": "MISSING"}
    approval = version.approval_state.value if hasattr(version.approval_state, "value") else version.approval_state
    return {"id": version.id, "document_id": version.document_id, "version_number": version.version_number, "filename": version.source_filename, "source_reference": version.source_path_or_reference, "sha256": version.sha256, "approval_state": approval}


def owner_contract_extensions(db: Session, contract: Contract) -> dict[str, Any]:
    revision = db.get(ContractRevision, contract.current_revision_id) if contract.current_revision_id else None
    terms = db.scalars(select(ContractPaymentTerm).where(ContractPaymentTerm.contract_revision_id == revision.id).order_by(ContractPaymentTerm.sequence)).all() if revision else []
    deliverables = db.scalars(select(ContractDeliverableCommitment).where(ContractDeliverableCommitment.contract_revision_id == revision.id).order_by(ContractDeliverableCommitment.sequence)).all() if revision else []
    client_inputs = db.scalars(select(ContractClientInputRequirement).where(ContractClientInputRequirement.contract_revision_id == revision.id).order_by(ContractClientInputRequirement.sequence)).all() if revision else []
    contacts = db.scalars(select(ClientContact).where(ClientContact.client_account_id == contract.client_account_id, ClientContact.status == "ACTIVE").order_by(ClientContact.name)).all() if contract.client_account_id else []
    evidence = db.scalars(select(ContractAdminEvidence).where(ContractAdminEvidence.contract_id == contract.id).order_by(ContractAdminEvidence.recorded_at.desc())).all()
    return {
        "contract": {"payment_condition_text": contract.payment_condition_text, "contracted_scope_text": contract.contracted_scope_text, "valuation_amount": str(contract.valuation_amount) if contract.valuation_amount is not None else None, "valuation_currency": contract.valuation_currency, "valuation_basis": contract.valuation_basis, "valuation_status": contract.valuation_status, "project_opportunity_ref": contract.project_opportunity_ref},
        "client_contacts": [{"id": item.id, "name": item.name, "email": item.email, "phone": item.phone, "role_title": item.role_title} for item in contacts],
        "payment_terms": [{"id": item.id, "sequence": item.sequence, "label": item.label, "term_text": item.term_text, "basis_type": item.basis_type, "percentage": str(item.percentage) if item.percentage is not None else None, "fixed_amount": str(item.fixed_amount) if item.fixed_amount is not None else None, "currency": item.currency, "trigger_type": item.trigger_type, "trigger_description": item.trigger_description, "due_days": item.due_days, "source_clause": item.source_clause, "source_document": _document(db, item.source_document_version_id), "status": item.status, "human_verified_by": item.human_verified_by, "human_verified_at": item.human_verified_at.isoformat() if item.human_verified_at else None} for item in terms],
        "deliverables": [{"id": item.id, "sequence": item.sequence, "commitment_ref": item.commitment_ref, "name": item.name, "description": item.description, "due_trigger_description": item.due_trigger_description, "status": item.status, "source_document": _document(db, item.source_document_version_id), "human_verified_by": item.human_verified_by} for item in deliverables],
        "client_inputs": [{"id": item.id, "sequence": item.sequence, "input_code": item.input_code, "title": item.title, "description": item.description, "required": item.required, "status": item.status, "source_type": item.source_type, "source_document": _document(db, item.source_document_version_id), "human_verified_by": item.human_verified_by} for item in client_inputs],
        "evidence_detail": [{"id": item.id, "type": item.evidence_type, "source_role": item.source_role, "source_reference": item.source_reference, "document": _document(db, item.document_version_id), "hash": item.content_hash, "status": item.status, "recorded_by": item.recorded_by} for item in evidence],
        "billing_readiness": contract_billing_context(db, contract),
        "boundary": {"proposal_accept": "IMMUTABLE_ACCEPTED_PROPOSAL_REVISION", "contract_authority": "OWNER_CONTRACT_AUTHORITY_ONLY", "project_activation": "EXPLICIT_HUMAN_OWNER_ACTION"},
    }
