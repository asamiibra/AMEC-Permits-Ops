from uuid import uuid4

from sqlalchemy import select

from backend.app.db import SessionLocal
from backend.app.models import Contract, ContractRevision, Document, DocumentVersion, Project


def _seed_refs():
    with SessionLocal() as db:
        project = db.scalar(select(Project).order_by(Project.project_number))
        contract = db.scalar(select(Contract).where(Contract.project_id == project.id))
        revision = db.scalar(select(ContractRevision).where(ContractRevision.contract_id == contract.id))
        document = db.scalar(select(DocumentVersion).join(Document, Document.id == DocumentVersion.document_id).where(Document.project_id == project.id))
        assert project and contract and revision and document
        return project.id, contract.id, revision.id, document.id


def test_handover_release_distribution_receipt_acceptance_and_service_scope(client):
    project_id, contract_id, contract_revision_id, document_version_id = _seed_refs()
    suffix = uuid4().hex[:8]
    service = client.post(
        "/api/handover/service-engagements",
        json={
            "project_id": project_id,
            "contract_id": contract_id,
            "contract_revision_id": contract_revision_id,
            "service_ref": f"DESIGN-{suffix}",
            "service_offering_code": "DESIGN",
            "scope_category_code": "DETAILED_DESIGN",
            "description": "Synthetic Design service engagement",
        },
    )
    assert service.status_code == 200, service.text
    service_id = service.json()["service_engagement"]["id"]
    package = client.post(
        "/api/handover/packages",
        json={
            "project_id": project_id,
            "service_engagement_id": service_id,
            "contract_id": contract_id,
            "package_ref": f"HO-{suffix}",
            "contract_revision_id": contract_revision_id,
        },
    )
    assert package.status_code == 200, package.text
    package_id = package.json()["package"]["id"]
    item = client.post(
        f"/api/handover/{package_id}/items",
        json={
            "item_type": "DOCUMENT",
            "label": "Signed handover PDF",
            "required_renditions": ["PDF"],
            "available_renditions": ["PDF"],
            "source_type": "DOCUMENT_VERSION",
            "document_version_id": document_version_id,
        },
    )
    assert item.status_code == 200, item.text
    requirement = client.post(
        f"/api/handover/{package_id}/distribution-requirements",
        json={
            "recipient_role": "CUSTOMER",
            "medium": "PAPER_ORIGINAL",
            "copy_count": 1,
            "acknowledgement_required": True,
        },
    )
    assert requirement.status_code == 200, requirement.text
    requirement_id = requirement.json()["requirement"]["id"]
    locked = client.post(f"/api/handover/{package_id}/lock")
    assert locked.status_code == 200, locked.text
    assert client.post(f"/api/handover/{package_id}/items", json={"item_type": "DOCUMENT", "label": "Late item", "source_type": "DOCUMENT_VERSION"}).status_code == 409
    released = client.post(f"/api/handover/{package_id}/release")
    assert released.status_code == 200, released.text
    distribution = client.post(
        f"/api/handover/{package_id}/distributions",
        json={
            "distribution_requirement_id": requirement_id,
            "recipient_role": "CUSTOMER",
            "medium": "PAPER_ORIGINAL",
            "copy_count": 1,
            "delivery_reference": "SYN-PAPER-001",
            "idempotency_key": f"distribution-{suffix}",
        },
    )
    assert distribution.status_code == 200, distribution.text
    distribution_id = distribution.json()["distribution"]["id"]
    receipt = client.post(
        f"/api/handover/distributions/{distribution_id}/receipt",
        json={"received_by_ref": "CUSTOMER-RECEIVER", "idempotency_key": f"receipt-{suffix}"},
    )
    assert receipt.status_code == 200, receipt.text
    accepted = client.post(
        f"/api/handover/{package_id}/acceptance",
        json={
            "acceptance_status": "ACCEPTED",
            "evidence_reference": "SYN-CUSTOMER-ACCEPTANCE-001",
            "idempotency_key": f"acceptance-{suffix}",
        },
    )
    assert accepted.status_code == 200, accepted.text
    closed = client.post(f"/api/handover/{package_id}/service-close")
    assert closed.status_code == 200, closed.text
    assert closed.json()["other_active_services"] == []


def test_multi_service_contract_and_closeout_axes_remain_separate(client):
    project_id, contract_id, contract_revision_id, _ = _seed_refs()
    suffix = uuid4().hex[:8]
    first = client.post(
        "/api/handover/service-engagements",
        json={
            "project_id": project_id,
            "contract_id": contract_id,
            "contract_revision_id": contract_revision_id,
            "service_ref": f"SUPERVISION-{suffix}",
            "service_offering_code": "SUPERVISION",
            "description": "Synthetic active Supervision service engagement",
        },
    )
    assert first.status_code == 200, first.text
    service_id = first.json()["service_engagement"]["id"]
    package = client.post(
        "/api/handover/packages",
        json={
            "project_id": project_id,
            "service_engagement_id": service_id,
            "contract_id": contract_id,
            "package_ref": f"HO-SUP-{suffix}",
            "contract_revision_id": contract_revision_id,
        },
    )
    assert package.status_code == 200, package.text
    package_id = package.json()["package"]["id"]
    blocked = client.post(f"/api/handover/{package_id}/contract-admin-close")
    assert blocked.status_code == 409
    assessment = client.post(
        f"/api/handover/projects/{project_id}/regulatory-assessment",
        json={"state": "CLOSED", "authority_case_ids": [], "basis": "No applicable synthetic case in scoped service"},
    )
    assert assessment.status_code == 200, assessment.text
    financial = client.get(f"/api/handover/projects/{project_id}/financial-settlement")
    assert financial.status_code == 200, financial.text
    assert financial.json()["billing_mutated"] is False
    assert financial.json()["context"]["readiness_state"] == "NEEDS_REVIEW"
    assert service_id
