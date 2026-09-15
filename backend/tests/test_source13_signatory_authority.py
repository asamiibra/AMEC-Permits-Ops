"""Source 13 governed signatory authority negative-path proof."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from backend.app.api import billing_invoice_routers
from backend.app.api.billing_invoice_routers import _signer_evidence
from backend.app.db import SessionLocal
from backend.app.models import (
    Document, DocumentApprovalState, DocumentType, DocumentVersion, FinancialAccountMaster,
    GovernedSignatoryAuthority, Invoice, InvoiceRevision, Project, Role, User,
)


def _code(exc: HTTPException) -> str:
    return exc.detail["code"]


def test_source13_resolves_governed_signer_and_rejects_caller_assertions(monkeypatch):
    monkeypatch.setattr(billing_invoice_routers, "get_settings", lambda: SimpleNamespace(synthetic_only=False))
    with SessionLocal() as db:
        project = db.scalar(select(Project).order_by(Project.project_number))
        signer_user = User(id=str(uuid4()), email=f"signer-{uuid4()}@amec.example", display_name="Governed GM", role=Role.OWNER_SPONSOR, office_id=project.office_id)
        invoice_id, revision_id, account_id = str(uuid4()), str(uuid4()), str(uuid4())
        invoice = Invoice(id=invoice_id, contract_id=str(uuid4()), project_id=project.id, client_account_id=str(uuid4()), invoice_reference=f"DRAFT-{uuid4()}")
        revision = InvoiceRevision(id=revision_id, invoice_id=invoice_id, revision_number=1, controlling_contract_revision_id=str(uuid4()), currency="QAR", contract_project_context_snapshot={"legal_entity_ref": "AMEC-LEGAL"})
        account = FinancialAccountMaster(id=account_id, office_id=project.office_id, legal_entity_ref="AMEC-LEGAL", account_name="AMEC QAR", status="ACTIVE", created_by=signer_user.id)
        authority = GovernedSignatoryAuthority(
            id=str(uuid4()), user_id=signer_user.id, office_id=project.office_id, legal_entity_ref="AMEC-LEGAL",
            capacity="GENERAL_MANAGER", authority_type="GENERAL_MANAGER", effective_from=datetime.now(timezone.utc) - timedelta(days=1),
            effective_to=datetime.now(timezone.utc) + timedelta(days=1), status="ACTIVE", owner_authorization_reference="OWNER-AUTH-13",
            authority_evidence_reference="source13://authority/gm", created_by=signer_user.id, approved_by=signer_user.id,
            approved_at=datetime.now(timezone.utc),
        )
        signed_document = Document(id=str(uuid4()), project_id=project.id, document_type=DocumentType.OTHER, logical_name="Signed invoice", language="EN", source_system="SOURCE13")
        signed_version = DocumentVersion(id=str(uuid4()), document_id=signed_document.id, version_number=1, source_filename="signed-invoice.pdf", source_path_or_reference="source13://signed-invoice", sha256="a" * 64, mime_type="application/pdf", file_size=10, language="EN", approval_state=DocumentApprovalState.APPROVED, source_system="SOURCE13", metadata_json={"invoice_id": invoice_id})
        db.add_all([signer_user, invoice, revision, account, authority, signed_document, signed_version])
        db.commit()
        valid_payload = {"signer_authority_id": authority.id, "signer_identity": signer_user.id, "signer_capacity": "GENERAL_MANAGER", "signed_invoice_evidence_document_version_id": signed_version.id}
        resolved = _signer_evidence(db, valid_payload, invoice=invoice, revision=revision, project=project, account_master=account, issue_at=datetime.now(timezone.utc))
        assert resolved["authority_id"] == authority.id
        assert resolved["identity"] == signer_user.id

        with pytest.raises(HTTPException) as missing:
            _signer_evidence(db, {**valid_payload, "signer_authority_id": "invented"}, invoice=invoice, revision=revision, project=project, account_master=account, issue_at=datetime.now(timezone.utc))
        assert _code(missing.value) == "SIGNER_AUTHORITY_RECORD_REQUIRED"
        with pytest.raises(HTTPException) as invented:
            _signer_evidence(db, {**valid_payload, "signer_identity": "invented"}, invoice=invoice, revision=revision, project=project, account_master=account, issue_at=datetime.now(timezone.utc))
        assert _code(invented.value) == "SIGNER_IDENTITY_MISMATCH"

        cases = [
            ("REVOKED", {"status": "REVOKED"}, "SIGNER_AUTHORITY_NOT_ACTIVE_AT_ISSUE"),
            ("EXPIRED", {"effective_to": datetime.now(timezone.utc) - timedelta(days=1)}, "SIGNER_AUTHORITY_NOT_ACTIVE_AT_ISSUE"),
            ("FUTURE", {"effective_from": datetime.now(timezone.utc) + timedelta(days=1), "effective_to": datetime.now(timezone.utc) + timedelta(days=2)}, "SIGNER_AUTHORITY_NOT_ACTIVE_AT_ISSUE"),
            ("WRONG_ENTITY", {"legal_entity_ref": "OTHER-LEGAL"}, "SIGNER_LEGAL_ENTITY_MISMATCH"),
            ("MISSING_AUTHORITY_EVIDENCE", {"authority_evidence_reference": None}, "SIGNER_AUTHORITY_EVIDENCE_REQUIRED"),
            ("WRONG_CAPACITY", {"capacity": "OWNER"}, "SIGNER_CAPACITY_NOT_AUTHORIZED"),
        ]
        for _label, changes, expected in cases:
            db.rollback()
            authority = db.get(GovernedSignatoryAuthority, authority.id)
            for key, value in changes.items():
                setattr(authority, key, value)
            db.flush()
            with pytest.raises(HTTPException) as blocked:
                _signer_evidence(db, valid_payload, invoice=invoice, revision=revision, project=project, account_master=account, issue_at=datetime.now(timezone.utc))
            assert _code(blocked.value) == expected
        db.rollback()
        authority = db.get(GovernedSignatoryAuthority, authority.id)
        with pytest.raises(HTTPException) as no_signed:
            _signer_evidence(db, {**valid_payload, "signed_invoice_evidence_document_version_id": None}, invoice=invoice, revision=revision, project=project, account_master=account, issue_at=datetime.now(timezone.utc))
        assert _code(no_signed.value) == "SIGNED_INVOICE_EVIDENCE_REQUIRED"
        db.rollback()
        db.delete(signed_version); db.delete(signed_document); db.delete(authority); db.delete(account); db.delete(revision); db.delete(invoice); db.delete(signer_user); db.commit()
