from datetime import datetime, timezone
from uuid import uuid4

from backend.app.db import SessionLocal
from backend.app.models import ConsultancyOffice, Document, DocumentApprovalState, DocumentType, DocumentVersion, ExternalBody, Jurisdiction, Party, ServiceType


def _headers(role="SYSTEM_ADMIN", actor="source18-owner"):
    return {"X-Dev-Role": role, "X-Dev-Actor": actor}


def test_source18_non_project_subject_and_project_required_gate_are_persisted(client):
    suffix = uuid4().hex[:10].upper()
    with SessionLocal() as db:
        office = db.query(ConsultancyOffice).first()
        engineer = Party(party_type="INDIVIDUAL", name_en=f"Synthetic Engineer {suffix}", name_ar=None, status="CURRENT")
        body = ExternalBody(code=f"S18-BODY-{suffix}", name_en="Synthetic Current Authority", body_type="AUTHORITY", status="ACTIVE", verification_state="VERIFIED", created_by="source18-owner")
        jurisdiction = Jurisdiction(code=f"S18-JUR-{suffix}", country_code="QA", name_en="Synthetic Jurisdiction", level="LOCALITY", status="ACTIVE")
        service = ServiceType(code=f"S18-SVC-{suffix}", name_en="Synthetic Regulatory Service", status="ACTIVE")
        document = Document(project_id=None, document_type=DocumentType.OTHER, logical_name=f"synthetic-original-{suffix}.pdf", language="EN", source_system="SYNTHETIC")
        db.add_all([engineer, body, jurisdiction, service, document])
        db.flush()
        original_1 = DocumentVersion(document_id=document.id, version_number=1, source_filename="synthetic-original-1.pdf", source_path_or_reference="synthetic://original/1", sha256="1" * 64, mime_type="application/pdf", file_size=10, language="EN", approval_state=DocumentApprovalState.APPROVED, source_system="SYNTHETIC", synthetic_content=b"original-1")
        original_2 = DocumentVersion(document_id=document.id, version_number=2, source_filename="synthetic-original-2.pdf", source_path_or_reference="synthetic://original/2", sha256="2" * 64, mime_type="application/pdf", file_size=10, language="EN", approval_state=DocumentApprovalState.APPROVED, source_system="SYNTHETIC", synthetic_content=b"original-2")
        db.add_all([original_1, original_2])
        db.commit()
        ids = {"office": office.id, "engineer": engineer.id, "body": body.id, "jurisdiction": jurisdiction.id, "service": service.id, "original_1": original_1.id, "original_2": original_2.id}

    non_project = client.post(
        "/api/authority-cases",
        headers=_headers(),
        json={
            "external_body_id": ids["body"], "jurisdiction_id": ids["jurisdiction"], "service_type_id": ids["service"],
            "subject_type": "OFFICE_REGISTRATION", "subject_id": ids["office"],
            "transaction_type": "OFFICE_REGISTRATION_CHANGE", "processing_mode": "COUNTER_PROCESS",
            "idempotency_key": f"s18-office-{suffix}",
        },
    )
    assert non_project.status_code == 200, non_project.text
    case = non_project.json()["case"]
    assert case["project_required"] is False
    assert case["processing_mode"] == "COMMITTEE_PANEL"
    assert case["g5_blocking_currentness_gap"] is True
    assert case["live_action_eligibility"] == "BLOCKED_UNKNOWN"

    project_required = client.post(
        "/api/authority-cases",
        headers=_headers(),
        json={
            "external_body_id": ids["body"], "jurisdiction_id": ids["jurisdiction"], "service_type_id": ids["service"],
            "subject_type": "ENGINEER", "subject_id": ids["engineer"], "transaction_type": "MAINTENANCE_PERMIT",
            "idempotency_key": f"s18-project-required-{suffix}",
        },
    )
    assert project_required.status_code == 409
    assert project_required.json()["detail"]["code"] == "CANONICAL_PROJECT_REQUIRED_FOR_AUTHORITY_CASE"

    civil_defense_required = client.post(
        "/api/authority-cases",
        headers=_headers(),
        json={
            "external_body_id": ids["body"], "jurisdiction_id": ids["jurisdiction"], "service_type_id": ids["service"],
            "subject_type": "ENGINEER", "subject_id": ids["engineer"], "transaction_type": "CIVIL_DEFENSE",
            "idempotency_key": f"s18-civil-defense-project-required-{suffix}",
        },
    )
    assert civil_defense_required.status_code == 409
    assert civil_defense_required.json()["detail"]["code"] == "CANONICAL_PROJECT_REQUIRED_FOR_AUTHORITY_CASE"

    workspace = client.get(f"/api/authority-cases/{case['id']}", headers=_headers())
    assert workspace.status_code == 200
    assert workspace.json()["currentness"]["live_action_eligibility"] == "BLOCKED_UNKNOWN"

    packet = client.post(
        f"/api/authority-cases/{case['id']}/committee-packets",
        headers=_headers(),
        json={"field_values": {"applicant": "Synthetic", "authority_field": "N/A"}, "required_fields": ["applicant", "authority_field"], "authority_only_fields": ["authority_field"]},
    )
    assert packet.status_code == 200, packet.text
    assert packet.json()["revision_number"] == 1
    release = client.post(f"/api/authority-cases/{case['id']}/committee-packets/{packet.json()['id']}/owner-release", headers=_headers())
    assert release.status_code == 409
    currentness = client.post(
        f"/api/authority-cases/{case['id']}/currentness", headers=_headers(),
        json={"current_authority_policy_verified": True, "current_official_form_verified": True, "official_form_version_id": ids["original_1"], "official_form_publisher": "Synthetic Authority", "official_form_number": "FORM-S18", "official_form_revision": "2026-01", "official_form_retrieved_at": "2026-09-10T09:00:00+00:00", "evidence": {"authority_policy_source": "synthetic://authority/policy-current", "official_form_source": "synthetic://authority/form-current"}},
    )
    assert currentness.status_code == 200, currentness.text
    assert currentness.json()["currentness"]["live_action_eligibility"] == "ALLOWED"
    released = client.post(f"/api/authority-cases/{case['id']}/committee-packets/{packet.json()['id']}/owner-release", headers=_headers())
    assert released.status_code == 200, released.text
    signed_return = client.post(f"/api/authority-cases/{case['id']}/committee-packets/{packet.json()['id']}/signed-return", headers=_headers(), json={"signed_return_document_version_id": ids["original_2"]})
    assert signed_return.status_code == 200, signed_return.text

    accepted = client.post(
        f"/api/authority-cases/{case['id']}/regulatory-state",
        headers=_headers(),
        json={"state_type": "CURRENT_CONSULTING_OFFICE_REGISTRATION_VERSION", "status": "ACCEPTED", "source_reference": "synthetic://authority/registration-v1", "state": {"registration": "v1"}, "synthetic_only": True},
    )
    assert accepted.status_code == 200, accepted.text
    returned = client.post(
        f"/api/authority-cases/{case['id']}/regulatory-state",
        headers=_headers(),
        json={"state_type": "CURRENT_CONSULTING_OFFICE_REGISTRATION_VERSION", "status": "RETURNED", "reason": "Synthetic return", "state": {"registration": "v2"}, "synthetic_only": True},
    )
    assert returned.status_code == 200, returned.text
    state_rows = client.get(f"/api/authority-cases/{case['id']}", headers=_headers()).json()["regulatory_state_versions"]
    assert [row["is_current"] for row in state_rows] == [True, False]

    custody_1 = client.post(
        f"/api/authority-cases/{case['id']}/physical-original-custody", headers=_headers(),
        json={"document_version_id": ids["original_1"], "event_type": "RECEIVED_ORIGINAL", "custodian": "Synthetic AMEC custody", "event_at": datetime.now(timezone.utc).isoformat(), "evidence_reference": "synthetic://custody/1"},
    )
    assert custody_1.status_code == 200, custody_1.text
    custody_2 = client.post(
        f"/api/authority-cases/{case['id']}/physical-original-custody", headers=_headers(),
        json={"document_version_id": ids["original_2"], "event_type": "RECEIVED_ORIGINAL", "custodian": "Synthetic AMEC custody", "event_at": datetime.now(timezone.utc).isoformat(), "evidence_reference": "synthetic://custody/2"},
    )
    assert custody_2.status_code == 409
