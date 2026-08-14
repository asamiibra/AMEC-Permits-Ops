"""Post-implementation Handover bridge certification on authoritative PostgreSQL."""

from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from sqlalchemy import delete, select

from backend.app.db import SessionLocal, engine
from backend.app.models import (
    Contract,
    ContractAdministrativeClosure,
    ContractRevision,
    DistributionRequirement,
    Document,
    DocumentVersion,
    FinancialSettlementContext,
    FinancialSettlementRecord,
    HandoverAcceptance,
    HandoverDistribution,
    HandoverPackage,
    HandoverPackageItem,
    HandoverPackageRevision,
    HandoverParticipant,
    HandoverPolicyVersion,
    HandoverPunchItem,
    HandoverReadiness,
    HandoverReceipt,
    HandoverReleaseAuthorization,
    Invoice,
    Project,
    ProjectArchiveRecord,
    ProjectCloseoutAssessment,
    ProjectCloseoutPolicyVersion,
    RegulatoryCloseoutAssessment,
    ServiceEngagement,
    ServiceScopeClosure,
    User,
)


pytestmark = pytest.mark.skipif(engine.dialect.name != "postgresql", reason="Authoritative bridge suite requires PostgreSQL")


def _post(client, path, payload=None, role="SYSTEM_ADMIN"):
    response = client.post(path, headers={"X-Dev-Role": role}, json=payload or {})
    return response


@pytest.fixture
def bridge_case():
    suffix = uuid4().hex[:10]
    with SessionLocal() as db:
        source_contract = db.scalar(select(Contract).order_by(Contract.created_at))
        source_project = db.get(Project, source_contract.project_id)
        source_contract_revision = db.scalar(select(ContractRevision).where(ContractRevision.contract_id == source_contract.id))
        source_document = db.scalar(select(DocumentVersion).join(Document, Document.id == DocumentVersion.document_id).where(Document.project_id == source_project.id))
        project = Project(
            project_number=f"BRIDGE-{suffix}",
            project_name="Handover closure bridge synthetic project",
            office_id=source_project.office_id,
            workstream="BRIDGE",
            status="ACTIVE",
            municipality="Doha",
            permit_type="Building Permit",
            assigned_engineer="Bridge Engineer",
        )
        db.add(project)
        db.flush()
        contract = Contract(client_account_id=source_contract.client_account_id, quotation_id=source_contract.quotation_id, contract_reference=f"BRIDGE-{suffix}-CONTRACT", status="ACTIVE", project_id=project.id, contract_name="Handover closure bridge synthetic contract")
        db.add(contract)
        db.flush()
        contract_revision = ContractRevision(contract_id=contract.id, revision_number=1, controlling_quotation_revision_id=source_contract_revision.controlling_quotation_revision_id, status="ACCEPTED", contract_name="Handover closure bridge synthetic contract")
        db.add(contract_revision)
        db.commit()
        context = {"suffix": suffix, "project_id": project.id, "contract_id": contract.id, "contract_revision_id": contract_revision.id, "document_version_id": source_document.id}
    yield context
    with SessionLocal() as db:
        package_ids = [x.id for x in db.scalars(select(HandoverPackage).where(HandoverPackage.project_id == context["project_id"])).all()]
        revision_ids = [x.id for x in db.scalars(select(HandoverPackageRevision).where(HandoverPackageRevision.handover_package_id.in_(package_ids))).all()] if package_ids else []
        distribution_ids = [x.id for x in db.scalars(select(HandoverDistribution).where(HandoverDistribution.handover_package_revision_id.in_(revision_ids))).all()] if revision_ids else []
        db.execute(delete(HandoverReceipt).where(HandoverReceipt.distribution_id.in_(distribution_ids)))
        db.execute(delete(HandoverDistribution).where(HandoverDistribution.handover_package_revision_id.in_(revision_ids)))
        db.execute(delete(HandoverPunchItem).where(HandoverPunchItem.handover_package_revision_id.in_(revision_ids)))
        db.execute(delete(HandoverParticipant).where(HandoverParticipant.handover_package_revision_id.in_(revision_ids)))
        db.execute(delete(HandoverPackageItem).where(HandoverPackageItem.handover_package_revision_id.in_(revision_ids)))
        db.execute(delete(ServiceScopeClosure).where(ServiceScopeClosure.project_id == context["project_id"]))
        db.execute(delete(HandoverReleaseAuthorization).where(HandoverReleaseAuthorization.handover_package_revision_id.in_(revision_ids)))
        db.execute(delete(HandoverReadiness).where(HandoverReadiness.handover_package_revision_id.in_(revision_ids)))
        db.execute(delete(HandoverAcceptance).where(HandoverAcceptance.handover_package_revision_id.in_(revision_ids)))
        db.execute(delete(DistributionRequirement).where(DistributionRequirement.handover_package_revision_id.in_(revision_ids)))
        db.query(HandoverPackage).filter(HandoverPackage.id.in_(package_ids)).update({HandoverPackage.current_revision_id: None}, synchronize_session=False)
        db.execute(delete(HandoverPackageRevision).where(HandoverPackageRevision.handover_package_id.in_(package_ids)))
        db.execute(delete(HandoverPackage).where(HandoverPackage.project_id == context["project_id"]))
        db.execute(delete(ContractAdministrativeClosure).where(ContractAdministrativeClosure.project_id == context["project_id"]))
        db.execute(delete(RegulatoryCloseoutAssessment).where(RegulatoryCloseoutAssessment.project_id == context["project_id"]))
        db.execute(delete(FinancialSettlementRecord).where(FinancialSettlementRecord.project_id == context["project_id"]))
        db.execute(delete(FinancialSettlementContext).where(FinancialSettlementContext.project_id == context["project_id"]))
        db.execute(delete(ProjectArchiveRecord).where(ProjectArchiveRecord.project_id == context["project_id"]))
        db.execute(delete(ProjectCloseoutAssessment).where(ProjectCloseoutAssessment.project_id == context["project_id"]))
        db.execute(delete(ProjectCloseoutPolicyVersion).where(ProjectCloseoutPolicyVersion.policy_code.like(f"BRIDGE-{context['suffix']}-%")))
        db.execute(delete(Invoice).where(Invoice.project_id == context["project_id"]))
        db.execute(delete(HandoverPolicyVersion).where(HandoverPolicyVersion.policy_code.like(f"BRIDGE-{context['suffix']}-%")))
        db.execute(delete(ServiceEngagement).where(ServiceEngagement.project_id == context["project_id"]))
        db.execute(delete(ContractRevision).where(ContractRevision.id == context["contract_revision_id"]))
        db.execute(delete(Contract).where(Contract.id == context["contract_id"]))
        db.execute(delete(Project).where(Project.id == context["project_id"]))
        db.commit()


def _package(client, case, service_ref, *, required=("PDF",), available=("PDF",), policy_id=None):
    service = _post(client, "/api/handover/service-engagements", {"project_id": case["project_id"], "contract_id": case["contract_id"], "contract_revision_id": case["contract_revision_id"], "service_ref": service_ref, "service_offering_code": service_ref.split("-")[0], "description": f"Synthetic {service_ref}"})
    assert service.status_code == 200, service.text
    service_id = service.json()["service_engagement"]["id"]
    package = _post(client, "/api/handover/packages", {"project_id": case["project_id"], "service_engagement_id": service_id, "contract_id": case["contract_id"], "package_ref": f"{service_ref}-PKG", "contract_revision_id": case["contract_revision_id"], "policy_version_id": policy_id})
    assert package.status_code == 200, package.text
    package_id = package.json()["package"]["id"]
    item = _post(client, f"/api/handover/{package_id}/items", {"item_type": "DOCUMENT", "label": f"{service_ref} PDF", "required_renditions": list(required), "available_renditions": list(available), "source_type": "DOCUMENT_VERSION", "document_version_id": case["document_version_id"]})
    assert item.status_code == 200, item.text
    requirement = _post(client, f"/api/handover/{package_id}/distribution-requirements", {"recipient_role": "CUSTOMER", "medium": "DIGITAL_PORTAL", "copy_count": 1, "acknowledgement_required": True})
    assert requirement.status_code == 200, requirement.text
    return {"service_id": service_id, "package_id": package_id, "requirement_id": requirement.json()["requirement"]["id"]}


def _release(client, package):
    assert _post(client, f"/api/handover/{package['package_id']}/lock").status_code == 200
    assert _post(client, f"/api/handover/{package['package_id']}/release").status_code == 200


def _deliver_and_receive(client, package, key):
    distribution = _post(client, f"/api/handover/{package['package_id']}/distributions", {"distribution_requirement_id": package["requirement_id"], "recipient_role": "CUSTOMER", "medium": "DIGITAL_PORTAL", "copy_count": 1, "idempotency_key": f"{key}-distribution"})
    assert distribution.status_code == 200, distribution.text
    distribution_id = distribution.json()["distribution"]["id"]
    receipt = _post(client, f"/api/handover/distributions/{distribution_id}/receipt", {"received_by_ref": "BRIDGE-CUSTOMER", "idempotency_key": f"{key}-receipt"})
    assert receipt.status_code == 200, receipt.text
    return distribution_id


def test_bridge_lifecycle_service_scope_and_independent_axes(client, bridge_case):
    suffix = bridge_case["suffix"]
    policy = _post(client, "/api/handover/policies", {"policy_code": f"BRIDGE-{suffix}-ACCEPTANCE", "version": "1", "acceptance_rules_json": {"accepted_with_remarks": True}})
    assert policy.status_code == 200, policy.text
    policy_id = policy.json()["policy"]["id"]
    design = _package(client, bridge_case, f"DESIGN-BRIDGE-{suffix}", policy_id=policy_id)
    supervision = _package(client, bridge_case, f"SUPERVISION-BRIDGE-{suffix}")
    participant = _post(client, f"/api/handover/{design['package_id']}/participants", {"participant_ref": "CUSTOMER-01", "participant_role": "CUSTOMER", "required_signer": True})
    assert participant.status_code == 200
    punch = _post(client, f"/api/handover/{design['package_id']}/punch", {"category": "REMARK", "remark": "Provide final indexed PDF", "blocking": True})
    assert punch.status_code == 200
    _release(client, design)
    _deliver_and_receive(client, design, f"{suffix}-design")
    blocked_acceptance = _post(client, f"/api/handover/{design['package_id']}/acceptance", {"acceptance_status": "ACCEPTED", "evidence_reference": "BRIDGE-EXTERNAL-ACCEPTANCE", "idempotency_key": f"{suffix}-accept-blocked"})
    assert blocked_acceptance.status_code == 409
    resolved = _post(client, f"/api/handover/punch/{punch.json()['punch']['id']}/resolve", {"resolution": "Indexed PDF evidence attached", "evidence_document_version_id": bridge_case["document_version_id"]})
    assert resolved.status_code == 200
    accepted = _post(client, f"/api/handover/{design['package_id']}/acceptance", {"acceptance_status": "ACCEPTED", "evidence_reference": "BRIDGE-EXTERNAL-ACCEPTANCE", "idempotency_key": f"{suffix}-accept"})
    assert accepted.status_code == 200
    closed = _post(client, f"/api/handover/{design['package_id']}/service-close")
    assert closed.status_code == 200
    workspace = client.get(f"/api/handover/{design['package_id']}").json()
    assert workspace["axes"]["service_scope"] == "ACTIVE"
    assert workspace["axes"]["handover"] == "ACCEPTED"
    assert workspace["axes"]["contract_admin"] == "OPEN"
    assert workspace["axes"]["financial"] == "NEEDS_REVIEW"
    assert workspace["axes"]["archive"] == "NOT_ARCHIVED"
    assert supervision["service_id"] in [row["id"] for row in closed.json()["other_active_services"]]


def test_bridge_hp_revision_rendition_and_immutability(client, bridge_case):
    suffix = bridge_case["suffix"]
    incomplete = _package(client, bridge_case, f"INCOMPLETE-BRIDGE-{suffix}", required=("PDF", "DWG"), available=("PDF",))
    assert client.get(f"/api/handover/{incomplete['package_id']}").json()["readiness"]["state"] == "NOT_READY"
    assert _post(client, f"/api/handover/{incomplete['package_id']}/lock").status_code == 409
    ready = _package(client, bridge_case, f"REVISION-BRIDGE-{suffix}")
    _release(client, ready)
    late_item = _post(client, f"/api/handover/{ready['package_id']}/items", {"item_type": "DOCUMENT", "label": "Late mutation", "source_type": "DOCUMENT_VERSION", "document_version_id": bridge_case["document_version_id"]})
    assert late_item.status_code == 409
    hp2 = _post(client, f"/api/handover/{ready['package_id']}/revisions", {"project_id": bridge_case["project_id"], "service_engagement_id": ready["service_id"], "contract_id": bridge_case["contract_id"], "package_ref": f"REVISION-BRIDGE-{suffix}-HP2", "contract_revision_id": bridge_case["contract_revision_id"]})
    assert hp2.status_code == 200, hp2.text
    assert hp2.json()["revision"]["revision_number"] == 2
    assert hp2.json()["revision"]["status"] == "DRAFT"


def test_bridge_rbac_and_accepted_with_remarks_policy(client, bridge_case):
    package = _package(client, bridge_case, f"RBAC-BRIDGE-{bridge_case['suffix']}")
    assert _post(client, f"/api/handover/{package['package_id']}/lock", role="RESPONSIBLE_ENGINEER").status_code == 403
    assert _post(client, f"/api/handover/{package['package_id']}/lock").status_code == 200
    assert _post(client, f"/api/handover/{package['package_id']}/release", role="RESPONSIBLE_ENGINEER").status_code == 403
    disabled = _package(client, bridge_case, f"REMARKS-DISABLED-{bridge_case['suffix']}")
    _release(client, disabled)
    _deliver_and_receive(client, disabled, f"{bridge_case['suffix']}-remarks-disabled")
    assert _post(client, f"/api/handover/{disabled['package_id']}/acceptance", {"acceptance_status": "ACCEPTED_WITH_REMARKS", "evidence_reference": "BRIDGE-REMARKS-DISABLED", "idempotency_key": f"{bridge_case['suffix']}-remarks-disabled-accept"}).status_code == 409
    policy = _post(client, "/api/handover/policies", {"policy_code": f"BRIDGE-{bridge_case['suffix']}-REMARKS", "version": "1", "acceptance_rules_json": {"accepted_with_remarks": True}})
    assert policy.status_code == 200, policy.text
    enabled = _package(client, bridge_case, f"REMARKS-ENABLED-{bridge_case['suffix']}", policy_id=policy.json()["policy"]["id"])
    _release(client, enabled)
    _deliver_and_receive(client, enabled, f"{bridge_case['suffix']}-remarks-enabled")
    assert _post(client, f"/api/handover/{enabled['package_id']}/acceptance", {"acceptance_status": "ACCEPTED_WITH_REMARKS", "evidence_reference": "BRIDGE-REMARKS-ENABLED", "idempotency_key": f"{bridge_case['suffix']}-remarks-enabled-accept"}).status_code == 200


def test_bridge_regulatory_financial_and_archive_boundaries(client, bridge_case):
    package = _package(client, bridge_case, f"ARCHIVE-BRIDGE-{bridge_case['suffix']}")
    _release(client, package)
    _deliver_and_receive(client, package, bridge_case["suffix"])
    assert _post(client, f"/api/handover/{package['package_id']}/acceptance", {"acceptance_status": "ACCEPTED", "evidence_reference": "BRIDGE-ACCEPTED", "idempotency_key": f"{bridge_case['suffix']}-archive-accept"}).status_code == 200
    assert _post(client, f"/api/handover/{package['package_id']}/service-close").status_code == 200
    admin = _post(client, f"/api/handover/{package['package_id']}/contract-admin-close")
    assert admin.status_code == 200, admin.text
    regulatory = _post(client, f"/api/handover/projects/{bridge_case['project_id']}/regulatory-assessment", {"state": "CLOSED", "authority_case_ids": [], "basis": "Synthetic derived assessment"})
    assert regulatory.status_code == 200, regulatory.text
    with SessionLocal() as db:
        invoice = Invoice(contract_id=bridge_case["contract_id"], project_id=bridge_case["project_id"], invoice_reference=f"BRIDGE-{bridge_case['suffix']}-PAID", status="PAID")
        db.add(invoice)
        db.commit()
    context = client.get(f"/api/handover/projects/{bridge_case['project_id']}/financial-settlement")
    assert context.status_code == 200
    assert context.json()["context"]["readiness_state"] == "READY_FOR_SETTLEMENT"
    settlement = _post(client, f"/api/handover/projects/{bridge_case['project_id']}/financial-settlement", {"basis": "Synthetic paid invoice reconciliation"})
    assert settlement.status_code == 200, settlement.text
    assert settlement.json()["billing_mutated"] is False
    policy = _post(client, f"/api/handover/projects/{bridge_case['project_id']}/closeout-policy", {"policy_code": f"BRIDGE-{bridge_case['suffix']}-ARCHIVE", "version": "1", "required_axes": ["service_scope", "handover", "contract_admin", "financial", "regulatory"]})
    assert policy.status_code == 200, policy.text
    archive = _post(client, f"/api/handover/projects/{bridge_case['project_id']}/archive", {"reason": "Synthetic bridge archive proof"})
    assert archive.status_code == 200, archive.text
    assert archive.json()["non_destructive"] is True
    assert archive.json()["property_preserved"] is True
    assert archive.json()["authority_cases_unchanged"] is True


def test_bridge_concurrent_idempotency_and_terminal_events(client, bridge_case):
    package = _package(client, bridge_case, f"CONCURRENCY-BRIDGE-{bridge_case['suffix']}")
    _release(client, package)
    def distribution(_):
        return _post(client, f"/api/handover/{package['package_id']}/distributions", {"distribution_requirement_id": package["requirement_id"], "recipient_role": "CUSTOMER", "medium": "DIGITAL_PORTAL", "copy_count": 1, "idempotency_key": f"{bridge_case['suffix']}-same-distribution"})
    with ThreadPoolExecutor(max_workers=8) as executor:
        distributions = list(executor.map(distribution, range(8)))
    assert all(response.status_code == 200 for response in distributions)
    assert sum(not response.json()["idempotent"] for response in distributions) == 1
    distribution_id = distributions[0].json()["distribution"]["id"]
    def receipt(_):
        return _post(client, f"/api/handover/distributions/{distribution_id}/receipt", {"received_by_ref": "BRIDGE-CUSTOMER", "idempotency_key": f"{bridge_case['suffix']}-same-receipt"})
    with ThreadPoolExecutor(max_workers=8) as executor:
        receipts = list(executor.map(receipt, range(8)))
    assert all(response.status_code == 200 for response in receipts)
    assert sum(not response.json()["idempotent"] for response in receipts) == 1
    def acceptance(_):
        return _post(client, f"/api/handover/{package['package_id']}/acceptance", {"acceptance_status": "ACCEPTED", "evidence_reference": "BRIDGE-CONCURRENT-ACCEPTANCE", "idempotency_key": f"{bridge_case['suffix']}-same-acceptance"})
    with ThreadPoolExecutor(max_workers=8) as executor:
        acceptances = list(executor.map(acceptance, range(8)))
    assert sum(response.status_code == 200 for response in acceptances) == 1
    assert all(response.status_code in {200, 409} for response in acceptances)
    def close(_):
        return _post(client, f"/api/handover/{package['package_id']}/service-close")
    with ThreadPoolExecutor(max_workers=8) as executor:
        closures = list(executor.map(close, range(8)))
    assert all(response.status_code == 200 for response in closures)
    with SessionLocal() as db:
        assert db.scalar(select(HandoverDistribution).where(HandoverDistribution.idempotency_key == f"{bridge_case['suffix']}-same-distribution"))
        assert len(db.scalars(select(HandoverReceipt).where(HandoverReceipt.idempotency_key == f"{bridge_case['suffix']}-same-receipt")).all()) == 1
        assert len(db.scalars(select(HandoverAcceptance).where(HandoverAcceptance.idempotency_key == f"{bridge_case['suffix']}-same-acceptance")).all()) == 1
        assert len(db.scalars(select(ServiceScopeClosure).where(ServiceScopeClosure.service_engagement_id == package["service_id"])).all()) == 1


def test_bridge_concurrent_revision_allocation_and_lock(client, bridge_case):
    package = _package(client, bridge_case, f"REV-CONCURRENCY-BRIDGE-{bridge_case['suffix']}")
    def lock(_):
        return _post(client, f"/api/handover/{package['package_id']}/lock")
    with ThreadPoolExecutor(max_workers=8) as executor:
        locks = list(executor.map(lock, range(8)))
    assert sum(response.status_code == 200 for response in locks) == 1
    assert all(response.status_code in {200, 409} for response in locks)
    def revision(_):
        return _post(client, f"/api/handover/{package['package_id']}/revisions", {"project_id": bridge_case["project_id"], "service_engagement_id": package["service_id"], "contract_id": bridge_case["contract_id"], "package_ref": f"REV-CONCURRENCY-BRIDGE-{bridge_case['suffix']}-HP2", "contract_revision_id": bridge_case["contract_revision_id"]})
    with ThreadPoolExecutor(max_workers=8) as executor:
        revisions = list(executor.map(revision, range(8)))
    assert sum(response.status_code == 200 for response in revisions) == 1
    assert all(response.status_code in {200, 409} for response in revisions)
    with SessionLocal() as db:
        rows = db.scalars(select(HandoverPackageRevision).where(HandoverPackageRevision.handover_package_id == package["package_id"]).order_by(HandoverPackageRevision.revision_number)).all()
        assert [row.revision_number for row in rows] == [1, 2]


def test_bridge_roles_and_global_role_invariant(client, bridge_case):
    package = _package(client, bridge_case, f"ROLE-BRIDGE-{bridge_case['suffix']}")
    before = None
    with SessionLocal() as db:
        before = {user.role.value for user in db.scalars(select(User)).all()}
    assert before.issuperset({"SYSTEM_ADMIN", "OWNER_SPONSOR", "PROCESS_CHAMPION", "RESPONSIBLE_ENGINEER"})
    assert _post(client, f"/api/handover/{package['package_id']}/lock", role="PROCESS_CHAMPION").status_code == 403
    assert _post(client, f"/api/handover/{package['package_id']}/lock", role="RESPONSIBLE_ENGINEER").status_code == 403
