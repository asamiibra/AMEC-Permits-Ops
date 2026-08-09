"""Focused E5/E6 contract and safety coverage over synthetic data only."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.app.db import SessionLocal
from backend.app.main import app
from backend.app.models import *
from backend.app.seed.cli import seed
from backend.app.services.week45 import stable_hash


@pytest.fixture(autouse=True)
def reset_after_test():
    yield
    seed()


def _context():
    with SessionLocal() as db:
        project = db.scalar(select(Project).order_by(Project.project_number))
        review = db.scalar(select(EngineeringReview).where(EngineeringReview.project_id == project.id))
        source = RegulationSource(source_code="SYN-E5-FOCUSED-TEST", title="Synthetic controlled test source", jurisdiction="SYNTHETIC", authority_name="Synthetic", source_type="CONTROLLED_TEST", publication_state="APPROVED_FOR_TEST")
        db.add(source)
        db.flush()
        approved = RegulationVersion(regulation_source_id=source.id, edition="SYNTHETIC-TEST-1", version="1.0", source_uri_or_reference="synthetic://approved-test/e5", content_status="APPROVED_FOR_TEST", content_hash=stable_hash("approved"))
        unverified = RegulationVersion(regulation_source_id=source.id, edition="UNVERIFIED-1", version="0.0", source_uri_or_reference="synthetic://unverified/e5", content_status="UNVERIFIED_DO_NOT_USE_FOR_AUTHORITY", content_hash=stable_hash("unverified"))
        db.add_all([approved, unverified])
        db.commit()
        return project.id, review.id, approved.id, unverified.id


def _ok(response, checks, code=200):
    checks.append(response.status_code == code)
    assert response.status_code == code, response.text
    return response.json()


def test_e5_engineering_advisory_contract_has_depth(client: TestClient):
    project_id, review_id, approved_id, unverified_id = _context()
    checks = []
    engineer = {"actor": "engineer", "actor_role": "RESPONSIBLE_ENGINEER"}
    admin = {"actor": "admin", "actor_role": "SYSTEM_ADMIN"}

    reviews = _ok(client.get(f"/api/projects/{project_id}/engineering-reviews"), checks)
    checks += [len(reviews) >= 1, reviews[0]["project_id"] == project_id]
    scope = _ok(client.post(f"/api/engineering-reviews/{review_id}/scope", json={**engineer, "scope_code": "SYN-E5-FOCUSED-SCOPE", "discipline": "ARCHITECTURAL", "supported_drawing_types": ["PDF"], "selected_regulation_version_ids": [approved_id], "excluded_topics": ["CERTIFICATION", "STAMPING", "DWF"]}), checks)
    checks += [scope["synthetic_only"] is True, scope["stage2_disposition"] == "UNDECIDED_STAGE2", scope["authorized_engineer_role"] == "AUTHORIZED_ENGINEER", "CERTIFICATION" in scope["excluded_topics"]]
    applicability = _ok(client.post(f"/api/engineering-reviews/{review_id}/regulation-applicability/review", json={**engineer, "regulation_version_id": approved_id, "applicability_status": "APPROVED_APPLICABLE", "evidence_reference": "synthetic://applicability"}), checks)
    checks += [applicability["applicability_status"] == "APPROVED_APPLICABLE", applicability["approved_by_user_id"] in {None, "engineer"}, applicability["basis_evidence"]["evidence_reference"].startswith("synthetic://")]
    regulations = _ok(client.get(f"/api/engineering-reviews/{review_id}/applicable-regulations"), checks)
    checks += [len(regulations["regulations"]) == 1, regulations["applicability"][0]["review_scope_id"] == scope["id"]]
    run = _ok(client.post(f"/api/engineering-reviews/{review_id}/runs", json=engineer), checks)
    checks += [run["status"] == "READY_FOR_ANALYSIS", bool(run["pinned_drawing_hash"]), bool(run["pinned_revision_label"]), run["review_scope_id"] == scope["id"], run["regulation_applicability_snapshot"]["trusted"] is True, run["evidence_recipe"]["open_web"] is False]
    result = _ok(client.post(f"/api/engineering-review-runs/{run['id']}/analyze", json={**engineer, "proposed_text": "Candidate issue with cited evidence"}), checks)
    comment = result["comments"][0]
    checks += [result["run"]["status"] == "PROPOSED_COMMENTS_READY", comment["source_type"] == "PROPOSED_BY_AI", comment["engineer_disposition"] == "NOT_DISPOSED", comment["stable_comment_number"].startswith("ENG-"), comment["drawing_document_version_id"] == run["drawing_document_version_id"], comment["regulation_version_id"] == approved_id, comment["regulation_evidence_reference"].startswith("synthetic://"), comment["evidence_snapshot"]["drawing_hash"] == run["pinned_drawing_hash"], comment["uncertainty_state"] == "SUPPORTED_EVIDENCE"]
    checks.append(client.post(f"/api/engineering-comments/{comment['id']}/engineer-disposition", json={**admin, "action": "ACCEPT_COMMENT"}).status_code == 403)
    modified = _ok(client.post(f"/api/engineering-comments/{comment['id']}/engineer-disposition", json={**engineer, "action": "MODIFY_AND_ACCEPT", "modified_text": "Human-modified comment"}), checks)
    checks += [modified["status"] == "ENGINEER_MODIFIED", modified["engineer_disposition"] == "MODIFY_AND_ACCEPT", modified["engineer_notes"] is None]
    compliance = _ok(client.post(f"/api/engineering-review-runs/{run['id']}/render-compliance-sheet", json={"actor": "renderer"}), checks)
    checks += [compliance["artifact"]["artifact_type"] == "COMPLIANCE_SHEET", compliance["artifact"]["template_version_id"], compliance["artifact"]["content_hash"], compliance["artifact"]["synthetic_only"] is True, compliance["status_label"].startswith("ENGINEERING REVIEW")]
    sheet = _ok(client.post(f"/api/engineering-review-runs/{run['id']}/render-comment-sheet", json={"actor": "renderer"}), checks)
    checks += [sheet["artifact"]["artifact_type"] == "COMMENT_SHEET", len(sheet["accepted_comments"]) == 1, sheet["artifact"]["source_revision_ids"], sheet["artifact"]["render_input_hash"]]
    block = _ok(client.get(f"/api/engineering-reviews/{review_id}/block-time"), checks)
    matching_block = next(item for item in block["items"] if item["comment_number"] == comment["stable_comment_number"])
    checks += [block["sla_claim"] is False, matching_block["duration_semantics"] == "OBSERVED_DURATION_ONLY", matching_block["comment_number"] == comment["stable_comment_number"]]
    no_ai_approval = client.get("/openapi.json").json()["paths"]
    checks += ["/api/engineering/approve-by-ai" not in no_ai_approval, any(path.endswith("/engineering-reviews") for path in no_ai_approval)]
    denied_applicability = client.post(f"/api/engineering-reviews/{review_id}/regulation-applicability/review", json={**engineer, "regulation_version_id": unverified_id, "applicability_status": "APPROVED_APPLICABLE"})
    checks.append(denied_applicability.status_code == 409)

    second = _ok(client.post(f"/api/projects/{project_id}/engineering-reviews", json={"discipline": "STRUCTURAL"}), checks)
    bad_scope = _ok(client.post(f"/api/engineering-reviews/{second['id']}/scope", json={"scope_code": "SYN-E5-BAD-SCOPE", "selected_regulation_version_ids": [unverified_id], "discipline": "STRUCTURAL"}), checks)
    checks += [bad_scope["selected_regulation_version_ids"] == [unverified_id]]
    bad_run = client.post(f"/api/engineering-reviews/{second['id']}/runs", json={"actor": "engineer"})
    checks.append(bad_run.status_code == 409)
    abstain_run = _ok(client.post(f"/api/engineering-reviews/{review_id}/runs", json=engineer), checks)
    abstain = _ok(client.post(f"/api/engineering-review-runs/{abstain_run['id']}/analyze", json={**engineer, "evidence_sufficient": False}), checks)
    checks += [abstain["comments"] == [], abstain["run"]["status"] == "PROPOSED_COMMENTS_READY"]
    new_drawing = _ok(client.post(f"/api/engineering-reviews/{review_id}/new-drawing-version", json={"actor": "engineer", "content": "synthetic corrected drawing V2", "revision_label": "V2"}), checks)
    checks += [new_drawing["drawing_version"]["revision_label"] == "V2", new_drawing["drawing_version"]["version_number"] >= 2, new_drawing["new_run_required"] is True, new_drawing["old_review_state"] in {"HISTORICAL_STALE", "HISTORICAL"}]
    stale_detail = _ok(client.get(f"/api/engineering-review-runs/{run['id']}"), checks)
    stale_comment = next(item for item in stale_detail["comments"] if item["stable_comment_number"] == comment["stable_comment_number"])
    checks += [stale_detail["run"]["status"] == "STALE", stale_comment["engineer_disposition"] == "MODIFY_AND_ACCEPT", stale_comment["closure_state"] == "OPEN"]
    rereview = _ok(client.post(f"/api/engineering-reviews/{review_id}/re-review", json=engineer), checks)
    checks += [rereview["status"] == "READY_FOR_ANALYSIS", rereview["drawing_document_version_id"] == new_drawing["drawing_version"]["id"], rereview["pinned_drawing_hash"] == new_drawing["drawing_version"]["sha256"]]
    rerun = _ok(client.post(f"/api/engineering-review-runs/{rereview['id']}/analyze", json=engineer), checks)
    checks += [rerun["comments"][0]["drawing_document_version_id"] == rereview["drawing_document_version_id"], rerun["comments"][0]["comment_number"] == 1, rerun["comments"][0]["source_type"] == "PROPOSED_BY_AI"]
    checks += [len(checks) >= 55, sum(bool(value) for value in checks) == len(checks)]
    assert sum(bool(value) for value in checks) == len(checks), [(index, value) for index, value in enumerate(checks) if not value]


def test_e6_finance_handover_contract_has_depth(client: TestClient):
    with SessionLocal() as db:
        project = db.scalar(select(Project).order_by(Project.project_number))
        contract = db.scalar(select(Contract).order_by(Contract.contract_reference))
    checks = []
    finance = {"actor": "finance", "actor_role": "FINANCE_ACCOUNTANT"}
    unauthorized = {"actor": "admin", "actor_role": "SYSTEM_ADMIN"}
    ai = client.post(f"/api/contracts/{contract.id}/invoice-requirement/decision", json={"actor": "ai", "actor_role": "SYSTEM_ADMIN", "decision": "REQUIRED", "decision_source": "AI_INFERRED_AS_AUTHORITY"})
    checks.append(ai.status_code == 403)
    not_required = _ok(client.post(f"/api/contracts/{contract.id}/invoice-requirement/decision", json={**finance, "decision": "NOT_REQUIRED", "reason": "Synthetic case B"}), checks)
    checks += [not_required["decision"] == "NOT_REQUIRED", not_required["decision_source"] == "HUMAN_DECISION", not_required["decided_by"] == "finance", not_required["evidence"]["synthetic_only"] is True]
    blocked_invoice = client.post(f"/api/contracts/{contract.id}/invoices", json={"actor": "finance"})
    checks.append(blocked_invoice.status_code == 409)
    required = _ok(client.post(f"/api/contracts/{contract.id}/invoice-requirement/decision", json={**finance, "decision": "REQUIRED", "reason": "Synthetic milestone requires invoice review"}), checks)
    requirement = _ok(client.get(f"/api/contracts/{contract.id}/invoice-requirement"), checks)
    checks += [requirement["decision"]["id"] == required["id"], requirement["authority"].startswith("HUMAN_DECISION"), requirement["milestone"]["id"] == required["milestone_id"]]
    created = _ok(client.post(f"/api/contracts/{contract.id}/invoices", json={"actor": "finance", "invoice_reference": "SYN-E6-FOCUSED-INV"}), checks)
    invoice, revision = created["invoice"], created["revision"]
    checks += [invoice["status"] == "DRAFT", invoice["requirement_decision_id"] == required["id"], revision["controlling_contract_revision_id"] == required["contract_revision_id"], revision["controlling_milestone_id"] == required["milestone_id"], revision["source_snapshot"]["synthetic_only"] is True]
    rendered = _ok(client.post(f"/api/invoice-revisions/{revision['id']}/render", json={"actor": "finance"}), checks)
    checks += [rendered["revision"]["status"] == "READY_FOR_FINANCE_REVIEW", rendered["revision"]["template_version_id"], rendered["revision"]["rendered_artifact_id"] == rendered["artifact"]["id"], rendered["artifact"]["artifact_type"] == "INVOICE", rendered["artifact"]["synthetic_only"] is True, rendered["artifact"]["content_hash"]]
    submitted = _ok(client.post(f"/api/invoice-revisions/{revision['id']}/submit-finance-review", json={"actor": "finance"}), checks)
    checks += [submitted["status"] == "FINANCE_REVIEW"]
    denied = client.post(f"/api/invoice-revisions/{revision['id']}/finance-decision", json={**unauthorized, "decision": "APPROVE_FOR_ISSUE"})
    checks.append(denied.status_code == 403)
    approved = _ok(client.post(f"/api/invoice-revisions/{revision['id']}/finance-decision", json={**finance, "decision": "APPROVE_FOR_ISSUE"}), checks)
    checks += [approved["revision"]["status"] == "APPROVED_FOR_ISSUE", approved["external_issue"] is False]
    before_issue = client.get(f"/api/invoices/{invoice['id']}").json()
    checks += [before_issue["invoice"]["status"] == "APPROVED_FOR_ISSUE", before_issue["evidence"] == []]
    handoff = _ok(client.post(f"/api/invoices/{invoice['id']}/accounting-handoff", json={"actor": "finance"}), checks)
    checks += [handoff["assigned_role"] == "GENERIC_FINANCE_HANDOFF", handoff["status"] == "PENDING", handoff["evidence"]["external_accounting_write"] is False]
    issued = _ok(client.post(f"/api/invoices/{invoice['id']}/issue-evidence", json={"actor": "finance", "evidence_reference": "synthetic://issued"}), checks)
    checks += [issued["invoice"]["status"] == "ISSUED_EVIDENCE_RECORDED", issued["external_issue"] is False, issued["evidence"]["source"] == "SYNTHETIC_EXTERNAL_EVENT"]
    payment = _ok(client.post(f"/api/invoices/{invoice['id']}/payment-evidence", json={"actor": "finance", "evidence_reference": "synthetic://paid"}), checks)
    checks += [payment["invoice"]["status"] == "PAID_EVIDENCE_RECORDED", payment["payment_processing"] is False]
    follow = _ok(client.get(f"/api/invoices/{invoice['id']}/follow-up"), checks)
    checks += [follow["invoice_required"] is True, follow["payment_follow_up_state"] == "PAYMENT_EVIDENCE_RECORDED", follow["late_claim"] is False, "DUE_DATE_UNKNOWN" in follow["payment_due_state"], follow["finance_owner"] == "GENERIC_FINANCE_HANDOFF"]
    draft = _ok(client.post(f"/api/invoices/{invoice['id']}/communication-draft", json={"actor": "finance", "communication_type": "PAYMENT_FOLLOW_UP"}), checks)
    checks += [draft["policy_state"] == "HUMAN_SEND", "HUMAN_SEND" in draft["body"], draft["status"] == "HUMAN_REVIEW"]
    handoff_detail = _ok(client.get(f"/api/invoices/{invoice['id']}"), checks)
    checks += [len(handoff_detail["handoffs"]) == 1, len(handoff_detail["evidence"]) == 2, handoff_detail["lineage"]]
    blocked = _ok(client.post(f"/api/projects/{project.id}/handovers", json={"actor": "owner", "require_deliverables": True}), checks)
    checks += [blocked["evaluation"]["state"] == "BLOCKED", blocked["handover"]["approval_state"] == "HANDOVER_DRAFT_READY"]
    checks.append(client.post(f"/api/project-handovers/{blocked['handover']['id']}/render", json={"actor": "owner"}).status_code == 409)
    ready = _ok(client.post(f"/api/projects/{project.id}/handovers", json={"actor": "owner", "selected_deliverables": ["synthetic://deliverable"]}), checks)
    checks += [ready["evaluation"]["state"] == "READY", ready["handover"]["readiness_state"] == "READY", ready["handover"]["approval_state"] == "HANDOVER_DRAFT_READY"]
    form = _ok(client.post(f"/api/project-handovers/{ready['handover']['id']}/render", json={"actor": "owner"}), checks)
    checks += [form["artifact"]["artifact_type"] == "HANDOVER_FORM", form["handover"]["rendered_artifact_id"] == form["artifact"]["id"], form["external_email"] is False]
    denied_release = client.post(f"/api/project-handovers/{ready['handover']['id']}/approval", json={**unauthorized})
    checks.append(denied_release.status_code == 403)
    approved_handover = _ok(client.post(f"/api/project-handovers/{ready['handover']['id']}/approval", json={"actor": "owner", "actor_role": "PROJECT_OWNER"}), checks)
    checks += [approved_handover["handover"]["approval_state"] == "HANDOVER_APPROVED_FOR_RELEASE", approved_handover["project_closed"] is False]
    released = _ok(client.post(f"/api/project-handovers/{ready['handover']['id']}/release-evidence", json={"actor": "owner"}), checks)
    checks += [released["handover"]["status"] == "HANDOVER_RELEASED", released["handover"]["release_evidence_status"] == "HANDOVER_RELEASE_EVIDENCE_RECORDED", released["project_closed"] is False, released["project_status"]["status"] != "PROJECT_CLOSED"]
    handover_draft = _ok(client.post(f"/api/project-handovers/{ready['handover']['id']}/communication-draft", json={"actor": "owner"}), checks)
    checks += [handover_draft["policy_state"] == "HUMAN_SEND", handover_draft["status"] == "HUMAN_REVIEW", "HUMAN_SEND" in handover_draft["body"]]
    paths = client.get("/openapi.json").json()["paths"]
    checks += ["/api/send-email" not in paths, "/api/post-ledger" not in paths, "/api/pay" not in paths, "/api/projects/{project_id}/handover-readiness" in paths]
    checks += [len(checks) >= 40, sum(bool(value) for value in checks) == len(checks)]
    assert sum(bool(value) for value in checks) == len(checks), [index for index, value in enumerate(checks) if not value]
