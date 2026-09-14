"""Owner-governed provisioning and immutable lifecycle for Source 13 signers."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import delete, select

from backend.app.db import SessionLocal
from backend.app.models import (
    ConsultancyOffice, Document, DocumentApprovalState, DocumentType, DocumentVersion,
    FinancialAccountMaster, GovernedSignatoryAuthority, Role, User,
)


def _headers(role: str) -> dict[str, str]:
    return {"X-Dev-Role": role}


def _fixture():
    with SessionLocal() as db:
        target = db.scalar(select(User).where(User.email == "engineer@amec.synthetic"))
        owner = db.scalar(select(User).where(User.email == "owner@amec.synthetic"))
        admin = db.scalar(select(User).where(User.email == "admin@amec.synthetic"))
        office = db.get(ConsultancyOffice, target.office_id)
        legal_entity = f"GOVERNED-ENTITY-{uuid4().hex[:8]}"
        account = FinancialAccountMaster(office_id=office.id, legal_entity_ref=legal_entity, account_name="Governed authority account", status="ACTIVE", created_by=owner.id)
        document = Document(id=str(uuid4()), project_id=None, document_type=DocumentType.OTHER, logical_name="Owner signatory authority", language="EN", source_system="SOURCE13")
        version = DocumentVersion(id=str(uuid4()), document_id=document.id, version_number=1, source_filename="owner-authority.pdf", source_path_or_reference="source13://owner-authority", sha256="b" * 64, mime_type="application/pdf", file_size=12, language="EN", approval_state=DocumentApprovalState.APPROVED, source_system="SOURCE13", metadata_json={"governed": True})
        db.add_all([account, document, version]); db.commit()
        return {"target": target.id, "owner": owner.id, "admin": admin.id, "office": office.id, "entity": legal_entity, "evidence": version.id, "account": account.id, "document": document.id}


def _payload(fixture, suffix: str = "A"):
    return {
        "user_id": fixture["target"], "office_id": fixture["office"], "legal_entity_ref": fixture["entity"],
        "capacity": "GENERAL_MANAGER", "authority_type": "GOVERNED", "effective_from": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
        "owner_authorization_reference": f"OWNER-AUTH-{suffix}", "authority_evidence_document_version_id": fixture["evidence"],
    }


def test_owner_governed_signatory_lifecycle_and_forgery_rejection(client):
    fixture = _fixture()
    created = client.post("/api/admin/signatory-authorities", headers=_headers("OWNER_SPONSOR"), json=_payload(fixture))
    assert created.status_code == 200, created.text
    authority = created.json()
    assert authority["status"] == "PENDING_APPROVAL" and authority["created_by"] == fixture["owner"]
    assert authority["approved_by"] is None and authority["approved_at"] is None

    forged = client.post("/api/admin/signatory-authorities", headers=_headers("OWNER_SPONSOR"), json={**_payload(fixture, "FORGED"), "created_by": "caller", "approved_by": "caller", "approved_at": "2020-01-01T00:00:00Z", "status": "ACTIVE"})
    assert forged.status_code == 422 and forged.json()["detail"]["code"] == "SIGNATORY_PROTECTED_FIELDS_SERVER_OWNED"
    assert client.post("/api/admin/signatory-authorities", headers=_headers("PROCESS_CHAMPION"), json=_payload(fixture, "NONOWNER")).status_code == 403
    assert client.post(f"/api/admin/signatory-authorities/{authority['id']}/approve", headers=_headers("OWNER_SPONSOR"), json={}).json()["detail"]["code"] == "SIGNATORY_SELF_APPROVAL_DENIED"

    approved = client.post(f"/api/admin/signatory-authorities/{authority['id']}/approve", headers=_headers("SYSTEM_ADMIN"), json={})
    assert approved.status_code == 200 and approved.json()["status"] == "ACTIVE" and approved.json()["approved_by"] == fixture["admin"]
    assert client.post(f"/api/admin/signatory-authorities/{authority['id']}/revoke", headers=_headers("PROCESS_CHAMPION"), json={}).status_code == 403
    revoked = client.post(f"/api/admin/signatory-authorities/{authority['id']}/revoke", headers=_headers("SYSTEM_ADMIN"), json={})
    assert revoked.status_code == 200 and revoked.json()["status"] == "REVOKED" and revoked.json()["revoked_by"] == fixture["admin"]

    second = client.post("/api/admin/signatory-authorities", headers=_headers("OWNER_SPONSOR"), json=_payload(fixture, "SECOND"))
    assert second.status_code == 200
    second_approved = client.post(f"/api/admin/signatory-authorities/{second.json()['id']}/approve", headers=_headers("SYSTEM_ADMIN"), json={})
    assert second_approved.status_code == 200
    replacement = client.post("/api/admin/signatory-authorities", headers=_headers("OWNER_SPONSOR"), json=_payload(fixture, "REPLACEMENT"))
    assert replacement.status_code == 200
    replacement_approved = client.post(f"/api/admin/signatory-authorities/{replacement.json()['id']}/approve", headers=_headers("SYSTEM_ADMIN"), json={})
    assert replacement_approved.status_code == 200
    superseded = client.post(f"/api/admin/signatory-authorities/{second.json()['id']}/supersede", headers=_headers("SYSTEM_ADMIN"), json={"replacement_authority_id": replacement.json()["id"]})
    assert superseded.status_code == 200 and superseded.json()["superseded"]["status"] == "SUPERSEDED"
    history = client.get("/api/admin/signatory-authorities", headers=_headers("OWNER_SPONSOR"))
    assert history.status_code == 200
    statuses = {item["status"] for item in history.json()["items"] if item["id"] in {authority["id"], second.json()["id"], replacement.json()["id"]}}
    assert {"REVOKED", "SUPERSEDED", "ACTIVE"}.issubset(statuses)

    with SessionLocal() as db:
        db.execute(delete(GovernedSignatoryAuthority).where(GovernedSignatoryAuthority.id.in_([authority["id"], second.json()["id"], replacement.json()["id"]])))
        db.execute(delete(DocumentVersion).where(DocumentVersion.id == fixture["evidence"]))
        db.execute(delete(Document).where(Document.id == fixture["document"]))
        db.execute(delete(FinancialAccountMaster).where(FinancialAccountMaster.id == fixture["account"]))
        db.commit()
