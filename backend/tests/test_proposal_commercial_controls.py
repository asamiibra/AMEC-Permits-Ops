"""SQL-facing API contract tests for the Proposal commercial boundary."""

from concurrent.futures import ThreadPoolExecutor

from sqlalchemy import select
import pytest

from backend.app.db import SessionLocal
from backend.app.models import (
    MasterContentItem,
    MasterContentModuleBinding,
    Opportunity,
    ProposalAcceptanceVerification,
    ProposalCommercialRelease,
    ProposalContractHandoff,
    ProposalDistributionEvent,
    ProposalLpoReconciliation,
    ProposalScopeConfirmation,
    ProposalServiceEligibility,
    ProposalTechnicalAssessment,
)

from .test_bd_proposal_owner_session import _headers


@pytest.fixture(autouse=True)
def isolate_proposal_content_resolver():
    with SessionLocal() as db:
        bindings = db.scalars(
            select(MasterContentModuleBinding).where(
                MasterContentModuleBinding.module == "BD",
                MasterContentModuleBinding.usage_type.in_(("PROPOSAL_TEMPLATE", "PROPOSAL_CHECKLIST")),
            )
        ).all()
        item_ids = {binding.master_content_id for binding in bindings}
        items = {item.id: item for item in db.scalars(select(MasterContentItem).where(MasterContentItem.id.in_(item_ids))).all()}
        original_items = {
            item_id: {
                "status": items[item_id].status,
                "needs_review": items[item_id].needs_review,
            }
            for item_id in item_ids
        }
        original_bindings = {binding.id: binding.active for binding in bindings}
        for item in items.values():
            item.status = "ARCHIVED"
        for binding in bindings:
            binding.active = False
        db.commit()
    yield
    with SessionLocal() as db:
        for item in db.scalars(select(MasterContentItem).where(MasterContentItem.ref.in_(("SYN-QUAL-PROPOSAL-TEMPLATE-V1", "SYN-QUAL-PROPOSAL-CHECKLIST-V1")))).all():
            item.status = "ARCHIVED"
        for item_id, state in original_items.items():
            item = db.get(MasterContentItem, item_id)
            if item:
                item.status = state["status"]
                item.needs_review = state["needs_review"]
        for binding_id, active in original_bindings.items():
            binding = db.get(MasterContentModuleBinding, binding_id)
            if binding:
                binding.active = active
        db.commit()


def _ensure_qualified_proposal_templates(client):
    for ref, title, usage in (("SYN-QUAL-PROPOSAL-TEMPLATE-V1", "Synthetic Qualified Proposal Template", "PROPOSAL_TEMPLATE"), ("SYN-QUAL-PROPOSAL-CHECKLIST-V1", "Synthetic Qualified Proposal Checklist", "PROPOSAL_CHECKLIST")):
        rows = client.get("/api/master-content", params={"q": ref, "include_archived": "true"}, headers=_headers("SYSTEM_ADMIN")).json()
        item = next((row for row in rows if row["ref"] == ref), None)
        if item and item.get("status") == "ARCHIVED":
            with SessionLocal() as db:
                db.get(MasterContentItem, item["id"]).status = "ACTIVE"
                db.commit()
        if not item:
            created = client.post("/api/master-content", data={"content_type": "FORM", "ref": ref, "title": title, "description": title, "used_in": '["BD"]'}, files={"file": (f"{ref}.txt", b"synthetic qualified proposal content", "text/plain")}, headers=_headers("SYSTEM_ADMIN"))
            assert created.status_code == 200, created.text
            item = created.json()
        governed = client.patch(f"/api/master-content/{item['id']}/governance", json={"content_ownership_class": "AMEC_OWNED", "artifact_kind": "AMEC_FORM" if usage == "PROPOSAL_TEMPLATE" else "CHECKLIST", "language_profile": "EN"}, headers=_headers("SYSTEM_ADMIN"))
        assert governed.status_code == 200, governed.text
        provenance = client.post(f"/api/master-content/{item['id']}/provenance", json={"obtained_from": "Synthetic qualification fixture"}, headers=_headers("SYSTEM_ADMIN"))
        assert provenance.status_code == 200, provenance.text
        bound = client.put(f"/api/master-content/{item['id']}/module-bindings", json=[{"module": "BD", "usage_type": usage}], headers=_headers("SYSTEM_ADMIN"))
        assert bound.status_code == 200, bound.text


def _create_ready_proposal(client) -> str:
    _ensure_qualified_proposal_templates(client)
    created = client.post("/api/bd/proposals", headers=_headers("COMMERCIAL_APPROVER"), json={"proposal_description": "Synthetic controlled tender", "project_reference": "SYN-CTR-001", "client_name": "Synthetic Tender Client"})
    assert created.status_code == 200, created.text
    proposal_id = created.json()["id"]
    for source_type in ("TENDER_DOCUMENT", "TENDER_EMAIL", "TENDER_PHOTO", "CLIENT_DATA"):
        uploaded = client.post(f"/api/bd/proposals/{proposal_id}/sources", headers=_headers("COMMERCIAL_APPROVER"), data={"source_type": source_type, "source_revision": "S1"}, files={"file": (f"{source_type}.txt", f"synthetic {source_type}".encode(), "text/plain")})
        assert uploaded.status_code == 200, uploaded.text
    patched = client.patch(f"/api/bd/proposals/{proposal_id}", headers=_headers("COMMERCIAL_APPROVER"), json={"fields": {"scope_of_work": "Synthetic engineering and permitting scope", "client_scope_of_work": "Synthetic client tender scope", "process_of_work": "Review, prepare, verify, hand off", "price": "QAR 10000", "currency": "QAR", "duration": "30 days", "inclusions": ["Design"], "exclusions": ["Authority fees"]}})
    assert patched.status_code == 200, patched.text
    assert client.post(f"/api/bd/proposals/{proposal_id}/proceed", headers=_headers("COMMERCIAL_APPROVER")).status_code == 200
    assert client.post(f"/api/proposals-main/proposals/{proposal_id}/engineering-ready", headers=_headers("RESPONSIBLE_ENGINEER")).status_code == 200
    return proposal_id


def test_proposal_commercial_controls_require_order_and_preserve_lineage(client):
    proposal_id = _create_ready_proposal(client)
    release_before_scope = client.post(f"/api/bd/proposals/{proposal_id}/commercial-release", headers=_headers("COMMERCIAL_APPROVER"), json={})
    assert release_before_scope.status_code == 409
    assert release_before_scope.json()["detail"]["code"] == "ACCEPTED_REVISION_REQUIRED"

    assessment = client.post(f"/api/bd/proposals/{proposal_id}/technical-assessments", headers=_headers("RESPONSIBLE_ENGINEER"), json={"status": "PASS", "findings": [{"code": "SITE-READY", "disposition": "PASS"}], "assumptions": [{"code": "A-1", "text": "Synthetic site evidence"}], "source_lineage": {"fixture": "SYNTHETIC_ONLY"}})
    assert assessment.status_code == 200, assessment.text
    assessment_id = assessment.json()["control"]["id"]
    scope = client.post(f"/api/bd/proposals/{proposal_id}/scope-confirmations", headers=_headers("COMMERCIAL_APPROVER"), json={"scope_statement": "Synthetic confirmed scope", "service_offering_codes": ["PERMITTING"], "technical_assessment_ids": [assessment_id]})
    assert scope.status_code == 200, scope.text
    eligibility = client.post(f"/api/bd/proposals/{proposal_id}/service-eligibility", headers=_headers("COMMERCIAL_APPROVER"), json={"service_offering_code": "PERMITTING", "result": "ELIGIBLE", "capability_reference": "SYN-CAPABILITY-V1", "policy_reference": "SYN-POLICY-V1"})
    assert eligibility.status_code == 200, eligibility.text

    accepted = client.post(f"/api/bd/proposals/{proposal_id}/accept", headers=_headers("COMMERCIAL_APPROVER"))
    assert accepted.status_code == 200, accepted.text
    revision_id = accepted.json()["current_revision"]["id"]
    release = client.post(f"/api/bd/proposals/{proposal_id}/commercial-release", headers=_headers("COMMERCIAL_APPROVER"), json={"idempotency_key": "syn-release-1"})
    assert release.status_code == 200, release.text
    assert client.post(f"/api/bd/proposals/{proposal_id}/commercial-release", headers=_headers("COMMERCIAL_APPROVER"), json={"idempotency_key": "syn-release-1"}).json()["result"] == "IDEMPOTENT"
    distributed = client.post(f"/api/bd/proposals/{proposal_id}/distribution", headers=_headers("COMMERCIAL_APPROVER"), json={"channel": "CLIENT_PORTAL", "evidence_reference": "synthetic://distribution/1", "idempotency_key": "syn-distribution-1"})
    assert distributed.status_code == 200, distributed.text
    response = client.post(f"/api/bd/proposals/{proposal_id}/client-responses", headers=_headers("COMMERCIAL_APPROVER"), json={"response_type": "ACCEPTED", "evidence_reference": "synthetic://client-acceptance/1", "idempotency_key": "syn-response-1"})
    assert response.status_code == 200, response.text
    response_id = response.json()["response"]["id"]
    verified = client.post(f"/api/bd/proposals/{proposal_id}/acceptance-verification", headers=_headers("COMMERCIAL_APPROVER"), json={"client_response_id": response_id, "evidence_reference": "synthetic://client-acceptance/1"})
    assert verified.status_code == 200, verified.text
    verified_replay = client.post(f"/api/bd/proposals/{proposal_id}/acceptance-verification", headers=_headers("COMMERCIAL_APPROVER"), json={"client_response_id": response_id, "evidence_reference": "synthetic://client-acceptance/1"})
    assert verified_replay.status_code == 200
    assert verified_replay.json()["result"] == "IDEMPOTENT"
    lpo_payload = {"applies": True, "client_artifact_reference": "synthetic://lpo/1", "fields_compared": ["amount", "currency", "scope"], "variances": [], "idempotency_key": "syn-lpo-1"}
    lpo = client.post(f"/api/bd/proposals/{proposal_id}/lpo-reconciliation", headers=_headers("COMMERCIAL_APPROVER"), json=lpo_payload)
    assert lpo.status_code == 200, lpo.text
    lpo_replay = client.post(f"/api/bd/proposals/{proposal_id}/lpo-reconciliation", headers=_headers("COMMERCIAL_APPROVER"), json=lpo_payload)
    assert lpo_replay.status_code == 200
    assert lpo_replay.json()["result"] == "IDEMPOTENT"
    preview = client.get(f"/api/bd/proposals/{proposal_id}/handoff/contract", headers=_headers("SYSTEM_ADMIN"))
    assert preview.status_code == 200, preview.text
    assert preview.json()["eligible"] is True
    assert preview.json()["accepted_revision_id"] == revision_id
    handoff = client.post(f"/api/bd/proposals/{proposal_id}/handoff/contract-eligibility", headers=_headers("COMMERCIAL_APPROVER"))
    assert handoff.status_code == 200, handoff.text
    handoff_replay = client.post(f"/api/bd/proposals/{proposal_id}/handoff/contract-eligibility", headers=_headers("COMMERCIAL_APPROVER"))
    assert handoff_replay.status_code == 200
    assert handoff_replay.json()["result"] == "IDEMPOTENT"

    with SessionLocal() as db:
        assert db.scalar(select(ProposalTechnicalAssessment).where(ProposalTechnicalAssessment.proposal_id == proposal_id, ProposalTechnicalAssessment.status == "PASS"))
        assert db.scalar(select(ProposalScopeConfirmation).where(ProposalScopeConfirmation.proposal_id == proposal_id, ProposalScopeConfirmation.status == "CURRENT"))
        assert db.scalar(select(ProposalServiceEligibility).where(ProposalServiceEligibility.proposal_id == proposal_id, ProposalServiceEligibility.result == "ELIGIBLE"))
        assert db.scalar(select(ProposalCommercialRelease).where(ProposalCommercialRelease.proposal_id == proposal_id, ProposalCommercialRelease.accepted_revision_id == revision_id))
        assert db.scalar(select(ProposalDistributionEvent).where(ProposalDistributionEvent.proposal_id == proposal_id, ProposalDistributionEvent.accepted_revision_id == revision_id))
        assert db.scalar(select(ProposalAcceptanceVerification).where(ProposalAcceptanceVerification.proposal_id == proposal_id, ProposalAcceptanceVerification.accepted_revision_id == revision_id))
        assert db.scalar(select(ProposalLpoReconciliation).where(ProposalLpoReconciliation.proposal_id == proposal_id, ProposalLpoReconciliation.result == "PASS"))
        assert db.query(ProposalAcceptanceVerification).filter(ProposalAcceptanceVerification.proposal_id == proposal_id).count() == 1
        assert db.query(ProposalLpoReconciliation).filter(ProposalLpoReconciliation.proposal_id == proposal_id).count() == 1
        assert db.query(ProposalContractHandoff).filter(ProposalContractHandoff.proposal_id == proposal_id).count() == 1


def test_proposal_create_idempotency_returns_the_same_context(client):
    payload = {"proposal_description": "Synthetic idempotent Proposal", "project_reference": "SYN-IDEM-001", "client_name": "Synthetic Idempotency Client", "idempotency_key": "synthetic-proposal-create-1"}
    first = client.post("/api/bd/proposals", headers=_headers("COMMERCIAL_APPROVER"), json=payload)
    second = client.post("/api/bd/proposals", headers=_headers("COMMERCIAL_APPROVER"), json=payload)
    assert first.status_code == second.status_code == 200
    assert first.json()["result"] == "CREATED"
    assert second.json()["result"] == "IDEMPOTENT"
    assert first.json()["id"] == second.json()["id"]
    with SessionLocal() as db:
        assert db.query(Opportunity).filter(Opportunity.idempotency_key == payload["idempotency_key"]).count() == 1


def test_proposal_control_replays_are_concurrency_stable(client):
    """Committed duplicate requests remain one logical transition under concurrency."""
    _ensure_qualified_proposal_templates(client)
    create_payload = {
        "proposal_description": "Synthetic concurrent replay Proposal",
        "project_reference": "SYN-CONCURRENT-001",
        "client_name": "Synthetic Concurrent Client",
        "idempotency_key": "synthetic-concurrent-create-1",
    }
    created = client.post("/api/bd/proposals", headers=_headers("COMMERCIAL_APPROVER"), json=create_payload)
    assert created.status_code == 200
    proposal_id = created.json()["id"]
    assert client.post("/api/bd/proposals", headers=_headers("COMMERCIAL_APPROVER"), json=create_payload).json()["result"] == "IDEMPOTENT"

    def replay(path, payload=None, role="COMMERCIAL_APPROVER"):
        return client.post(
            f"/api/bd/proposals/{proposal_id}/{path}",
            headers=_headers(role),
            json=payload or {},
        )

    for source_type in ("TENDER_DOCUMENT", "TENDER_EMAIL", "TENDER_PHOTO", "CLIENT_DATA"):
        uploaded = client.post(
            f"/api/bd/proposals/{proposal_id}/sources",
            headers=_headers("COMMERCIAL_APPROVER"),
            data={"source_type": source_type, "source_revision": "S1"},
            files={"file": (f"{source_type}.txt", f"synthetic {source_type}".encode(), "text/plain")},
        )
        assert uploaded.status_code == 200
    assert client.patch(
        f"/api/bd/proposals/{proposal_id}",
        headers=_headers("COMMERCIAL_APPROVER"),
        json={"fields": {"scope_of_work": "Synthetic concurrent scope", "client_scope_of_work": "Synthetic concurrent client scope", "process_of_work": "Review, prepare, verify, hand off", "price": "QAR 10000", "currency": "QAR", "duration": "30 days", "inclusions": ["Design"], "exclusions": ["Authority fees"]}},
    ).status_code == 200
    assert client.post(f"/api/bd/proposals/{proposal_id}/proceed", headers=_headers("COMMERCIAL_APPROVER")).status_code == 200
    assert client.post(f"/api/proposals-main/proposals/{proposal_id}/engineering-ready", headers=_headers("RESPONSIBLE_ENGINEER")).status_code == 200
    assessment = replay("technical-assessments", {"status": "PASS", "findings": [{"code": "SITE-READY"}]}, "RESPONSIBLE_ENGINEER")
    assert assessment.status_code == 200
    assessment_id = assessment.json()["control"]["id"]
    assert replay("scope-confirmations", {"scope_statement": "Synthetic concurrent confirmed scope", "service_offering_codes": ["PERMITTING"], "technical_assessment_ids": [assessment_id]}).status_code == 200
    assert replay("service-eligibility", {"service_offering_code": "PERMITTING", "result": "ELIGIBLE"}).status_code == 200
    accepted = client.post(f"/api/bd/proposals/{proposal_id}/accept", headers=_headers("COMMERCIAL_APPROVER"))
    assert accepted.status_code == 200, accepted.text
    revision_id = accepted.json()["current_revision"]["id"]
    release_payload = {"idempotency_key": "synthetic-concurrent-release-1"}
    assert replay("commercial-release", release_payload).status_code == 200
    distribution_payload = {"channel": "CLIENT_PORTAL", "evidence_reference": "synthetic://concurrent/distribution", "idempotency_key": "synthetic-concurrent-distribution-1"}
    assert replay("distribution", distribution_payload).status_code == 200
    response_payload = {"response_type": "ACCEPTED", "evidence_reference": "synthetic://concurrent/acceptance", "idempotency_key": "synthetic-concurrent-response-1"}
    response = replay("client-responses", response_payload)
    assert response.status_code == 200
    response_id = response.json()["response"]["id"]
    verification_payload = {"client_response_id": response_id, "evidence_reference": "synthetic://concurrent/acceptance"}
    assert replay("acceptance-verification", verification_payload).status_code == 200
    lpo_payload = {"applies": True, "client_artifact_reference": "synthetic://concurrent/lpo", "fields_compared": ["amount", "currency", "scope"], "variances": [], "idempotency_key": "synthetic-concurrent-lpo-1"}
    assert replay("lpo-reconciliation", lpo_payload).status_code == 200
    assert replay("handoff/contract-eligibility").status_code == 200

    replays = [
        ("", create_payload),
        ("commercial-release", release_payload),
        ("client-responses", response_payload),
        ("acceptance-verification", verification_payload),
        ("lpo-reconciliation", lpo_payload),
        ("handoff/contract-eligibility", {}),
    ]
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = []
        for path, payload in replays:
            if not path:
                results.append(pool.submit(client.post, "/api/bd/proposals", headers=_headers("COMMERCIAL_APPROVER"), json=payload))
            else:
                results.append(pool.submit(replay, path, payload))
        responses = [future.result() for future in results]
    assert all(response.status_code == 200 for response in responses), [response.text for response in responses]
    assert all(response.json().get("result") == "IDEMPOTENT" for response in responses), [response.json() for response in responses]
    with SessionLocal() as db:
        assert db.query(Opportunity).filter(Opportunity.idempotency_key == create_payload["idempotency_key"]).count() == 1
        assert db.query(ProposalCommercialRelease).filter(ProposalCommercialRelease.proposal_id == proposal_id, ProposalCommercialRelease.accepted_revision_id == revision_id).count() == 1
        assert db.query(ProposalAcceptanceVerification).filter(ProposalAcceptanceVerification.proposal_id == proposal_id).count() == 1
        assert db.query(ProposalLpoReconciliation).filter(ProposalLpoReconciliation.proposal_id == proposal_id).count() == 1
        assert db.query(ProposalContractHandoff).filter(ProposalContractHandoff.proposal_id == proposal_id).count() == 1


def test_proposal_commercial_controls_fail_closed_on_mismatch_and_stale_revision(client):
    proposal_id = _create_ready_proposal(client)
    assessment = client.post(f"/api/bd/proposals/{proposal_id}/technical-assessments", headers=_headers("RESPONSIBLE_ENGINEER"), json={"status": "PASS", "findings": [{"code": "SITE-READY"}]})
    assessment_id = assessment.json()["control"]["id"]
    assert client.post(f"/api/bd/proposals/{proposal_id}/scope-confirmations", headers=_headers("COMMERCIAL_APPROVER"), json={"scope_statement": "Synthetic confirmed scope", "service_offering_codes": ["PERMITTING"], "technical_assessment_ids": [assessment_id]}).status_code == 200
    assert client.post(f"/api/bd/proposals/{proposal_id}/service-eligibility", headers=_headers("COMMERCIAL_APPROVER"), json={"service_offering_code": "PERMITTING", "result": "ELIGIBLE"}).status_code == 200
    accepted = client.post(f"/api/bd/proposals/{proposal_id}/accept", headers=_headers("COMMERCIAL_APPROVER"))
    revision_id = accepted.json()["current_revision"]["id"]
    assert client.post(f"/api/bd/proposals/{proposal_id}/commercial-release", headers=_headers("COMMERCIAL_APPROVER"), json={}).status_code == 200
    distribution = client.post(f"/api/bd/proposals/{proposal_id}/distribution", headers=_headers("COMMERCIAL_APPROVER"), json={"evidence_reference": "synthetic://distribution/1"})
    assert distribution.status_code == 200
    response = client.post(f"/api/bd/proposals/{proposal_id}/client-responses", headers=_headers("COMMERCIAL_APPROVER"), json={"response_type": "ACCEPTED", "evidence_reference": "synthetic://acceptance/1"})
    response_id = response.json()["response"]["id"]
    assert client.post(f"/api/bd/proposals/{proposal_id}/acceptance-verification", headers=_headers("COMMERCIAL_APPROVER"), json={"client_response_id": response_id}).status_code == 200
    mismatch = client.post(f"/api/bd/proposals/{proposal_id}/lpo-reconciliation", headers=_headers("COMMERCIAL_APPROVER"), json={"applies": True, "client_artifact_reference": "synthetic://lpo/mismatch", "variances": [{"field": "amount", "proposal": "10000", "lpo": "11000"}]})
    assert mismatch.status_code == 200
    assert mismatch.json()["control"]["result"] == "MISMATCH"
    blocked = client.get(f"/api/bd/proposals/{proposal_id}/handoff/contract", headers=_headers("SYSTEM_ADMIN"))
    assert blocked.status_code == 200
    assert blocked.json()["eligible"] is False
    assert "LPO_RECONCILIATION_REQUIRED" in blocked.json()["blockers"]
    stale_release = client.post(f"/api/bd/proposals/{proposal_id}/commercial-release", headers=_headers("COMMERCIAL_APPROVER"), json={"accepted_revision_id": "stale-revision"})
    assert stale_release.status_code == 409
    assert stale_release.json()["detail"]["code"] == "STALE_REVISION_RELEASE_FORBIDDEN"
    with SessionLocal() as db:
        assert db.query(ProposalCommercialRelease).filter(ProposalCommercialRelease.proposal_id == proposal_id, ProposalCommercialRelease.accepted_revision_id == revision_id).count() == 1
        assert db.query(ProposalContractHandoff).filter(ProposalContractHandoff.proposal_id == proposal_id).count() == 0
