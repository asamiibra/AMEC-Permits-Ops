"""Bounded, idempotent Proposal Owner-test corpus for a live PROD database."""

from __future__ import annotations

import hashlib

from sqlalchemy import select

from ..config.settings import get_settings
from ..db import SessionLocal
from ..models import (
    ClientAccount, ConsultancyOffice, Document, DocumentApprovalState,
    DocumentType, DocumentVersion, Opportunity, ProposalAcceptedRevision,
    ProposalLpoReconciliation, ProposalRevision, ProposalSourceEvidence,
    ProposalSourceLink, Role, User,
)
from ..services.intelligence_contracts import stable_hash

PREFIX = "OWNER-TEST-PROPOSAL"


def _document(db, *, proposal: Opportunity, key: str, filename: str, role: str, body: bytes) -> DocumentVersion:
    logical_name = f"{PREFIX}-{key}"
    document = db.scalar(select(Document).where(Document.logical_name == logical_name))
    if document is None:
        document = Document(project_id=proposal.project_id, document_type=DocumentType.OTHER, logical_name=logical_name, language="EN", source_system="SYNTHETIC_OWNER_TEST")
        db.add(document)
        db.flush()
    digest = hashlib.sha256(body).hexdigest()
    version = db.scalar(select(DocumentVersion).where(DocumentVersion.document_id == document.id, DocumentVersion.version_number == 1))
    if version is None:
        version = DocumentVersion(
            document_id=document.id, version_number=1, source_filename=filename,
            source_path_or_reference=f"synthetic-owner-test://{proposal.id}/{key}",
            sha256=digest, mime_type="text/plain", file_size=len(body), language="EN",
            approval_state=DocumentApprovalState.APPROVED, source_system="SYNTHETIC_OWNER_TEST",
            metadata_json={"synthetic_non_business_fixture": True, "synthetic_owner_test_only": True, "not_official_production_content": True, "proposal_id": proposal.id, "source_role": role},
            synthetic_content=body,
        )
        db.add(version)
        db.flush()
        document.current_version_id = version.id
    evidence = db.scalar(select(ProposalSourceEvidence).where(ProposalSourceEvidence.proposal_id == proposal.id, ProposalSourceEvidence.source_type == role, ProposalSourceEvidence.content_hash == digest))
    if evidence is None:
        evidence = ProposalSourceEvidence(proposal_id=proposal.id, source_type=role, source_filename=filename, source_reference=version.source_path_or_reference, content_hash=digest, content_type="text/plain", source_revision="OWNER-TEST-1", provenance={"synthetic_owner_test_only": True, "not_official_production_content": True}, status="CURRENT", verification_state="READ_BACK_VERIFIED", created_by="owner-test-seed")
        db.add(evidence)
        db.flush()
    link = db.scalar(select(ProposalSourceLink).where(ProposalSourceLink.proposal_id == proposal.id, ProposalSourceLink.document_version_id == version.id, ProposalSourceLink.source_role == role))
    if link is None:
        db.add(ProposalSourceLink(proposal_id=proposal.id, source_evidence_id=evidence.id, document_id=document.id, document_version_id=version.id, source_role=role, added_by="owner-test-seed", note="SYNTHETIC TEST only"))
    return version


def _proposal(db, *, office_id: str, client_id: str, key: str, status: str, fields: dict) -> Opportunity:
    reference = f"{PREFIX}-{key}"
    proposal = db.scalar(select(Opportunity).where(Opportunity.opportunity_reference == reference))
    if proposal is None:
        proposal = Opportunity(office_id=office_id, client_account_id=client_id, opportunity_reference=reference, provisional_reference=reference, title=f"SYNTHETIC TEST · {key.replace('-', ' ')}", status=status, source_type="SYNTHETIC_OWNER_TEST", proposal_fields_json=fields, reference_state="PROVISIONAL", fixture_classification="SYNTHETIC_OWNER_TEST", idempotency_key=f"owner-test-seed:{key}")
        db.add(proposal)
        db.flush()
    return proposal


def _accepted(db, proposal: Opportunity, actor_id: str) -> ProposalAcceptedRevision:
    accepted = db.scalar(select(ProposalAcceptedRevision).where(ProposalAcceptedRevision.proposal_id == proposal.id, ProposalAcceptedRevision.revision_number == 1))
    snapshot = {"proposal_id": proposal.id, "title": proposal.title, "fixture_classification": "SYNTHETIC_OWNER_TEST", "fields": proposal.proposal_fields_json or {}, "source_ids": []}
    if accepted is None:
        accepted = ProposalAcceptedRevision(proposal_id=proposal.id, revision_number=1, snapshot=snapshot, validation_snapshot={"owner_test_only": True}, definition_refs=[], content_hash=stable_hash(snapshot), accepted_by=actor_id)
        db.add(accepted)
        db.flush()
    return accepted


def seed_owner_test() -> dict[str, object]:
    settings = get_settings()
    if settings.app_env.upper() not in {"PROD", "PRODUCTION"}:
        raise RuntimeError("Owner-test corpus requires APP_ENV=PROD")
    if settings.synthetic_only or settings.real_data_allowed or not settings.owner_test_mode:
        raise RuntimeError("Owner-test corpus requires SYNTHETIC_ONLY=false, REAL_DATA_ALLOWED=false, OWNER_TEST_MODE=true")
    with SessionLocal() as db:
        office = db.scalar(select(ConsultancyOffice).where(ConsultancyOffice.status == "ACTIVE").order_by(ConsultancyOffice.office_code))
        if office is None:
            raise RuntimeError("An active production office is required before owner-test seeding")
        actor = db.scalar(select(User).where(User.active == True, User.role == Role.OWNER_SPONSOR, User.office_id == office.id).order_by(User.id))  # noqa: E712
        if actor is None:
            actor = db.scalar(select(User).where(User.active == True, User.office_id == office.id).order_by(User.id))  # noqa: E712
        if actor is None:
            raise RuntimeError("An active production owner/test user is required before owner-test seeding")
        client = db.scalar(select(ClientAccount).where(ClientAccount.client_reference == f"{PREFIX}-CLIENT"))
        if client is None:
            client = ClientAccount(client_reference=f"{PREFIX}-CLIENT", legal_name="SYNTHETIC TEST CLIENT ONLY", display_name="SYNTHETIC TEST CLIENT ONLY", client_type="COMPANY", data_classification="SYNTHETIC", status="ACTIVE")
            db.add(client)
            db.flush()
        definitions = [
            ("INTAKE", "IN_REVIEW", {"client_name": client.display_name, "client_scope_of_work": "Synthetic tender scope for Owner testing", "requested_timing": "Synthetic Q4 test window"}),
            ("COMMERCIAL", "COMMERCIAL_REVIEW", {"client_name": client.display_name, "scope_of_work": "Synthetic permitting and engineering scope", "price": 125000, "currency": "QAR", "duration": "12 weeks"}),
            ("ACCEPTED-LPO", "ACCEPTED", {"client_name": client.display_name, "scope_of_work": "Synthetic accepted proposal scope", "price": 98000, "currency": "QAR", "duration": "10 weeks"}),
            ("REVISION-CHANGE", "ACCEPTED", {"client_name": client.display_name, "scope_of_work": "Synthetic revision-change scope", "price": 75000, "currency": "QAR"}),
        ]
        fixtures: list[dict[str, object]] = []
        for key, status, fields in definitions:
            proposal = _proposal(db, office_id=office.id, client_id=client.id, key=key, status=status, fields=fields)
            tender = _document(db, proposal=proposal, key=f"{key}-TENDER", filename=f"{key.lower()}-tender.txt", role="TENDER_DOCUMENT", body=f"SYNTHETIC TEST tender for {key}. Never use as real business evidence.".encode())
            _document(db, proposal=proposal, key=f"{key}-CLIENT", filename=f"{key.lower()}-client.txt", role="CLIENT_DATA", body=f"SYNTHETIC TEST client correspondence for {key}.".encode())
            if key in {"ACCEPTED-LPO", "REVISION-CHANGE"}:
                accepted = _accepted(db, proposal, actor.id)
                lpo = _document(db, proposal=proposal, key=f"{key}-LPO", filename=f"{key.lower()}-lpo.txt", role="LPO_PO", body=b"SYNTHETIC TEST LPO amount QAR 100000; scope differs for mismatch testing.")
                existing_lpo = db.scalar(select(ProposalLpoReconciliation).where(ProposalLpoReconciliation.proposal_id == proposal.id, ProposalLpoReconciliation.accepted_revision_id == accepted.id))
                if existing_lpo is None:
                    db.add(ProposalLpoReconciliation(proposal_id=proposal.id, accepted_revision_id=accepted.id, client_document_version_id=lpo.id, client_artifact_reference="SYNTHETIC TEST LPO", applies=True, fields_compared=["scope", "price"], variances=[{"field": "price", "proposal_value": fields.get("price"), "lpo_value": 100000, "synthetic_owner_test": True}], result="MISMATCH", source_sha256=lpo.sha256, accepted_revision_hash=accepted.content_hash, compared_by=actor.id, idempotency_key=f"owner-test-lpo:{key}", audit_correlation_id=f"owner-test-seed:{key}"))
            if key == "REVISION-CHANGE" and db.scalar(select(ProposalRevision).where(ProposalRevision.proposal_id == proposal.id, ProposalRevision.status == "DRAFT")) is None:
                changed = {**fields, "change_request": "SYNTHETIC TEST change request"}
                db.add(ProposalRevision(proposal_id=proposal.id, revision_number=2, base_accepted_revision_id=accepted.id, status="DRAFT", change_summary={"synthetic_owner_test": True, "reason": "client change"}, snapshot=changed, content_hash=stable_hash(changed), created_by=actor.id))
            fixtures.append({"proposal_id": proposal.id, "reference": proposal.opportunity_reference, "fixture_classification": proposal.fixture_classification, "tender_document_version_id": tender.id})
        db.commit()
        return {"status": "APPLIED", "client_account_id": client.id, "fixtures": fixtures, "real_data_count": 0, "owner_test_only": True}


if __name__ == "__main__":
    print(seed_owner_test())
