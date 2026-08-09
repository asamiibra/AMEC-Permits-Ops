"""Reproducible synthetic E5 engineering and E6 commercial-closeout paths."""

import json
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.app.db import SessionLocal
from backend.app.main import app
from backend.app.models import *
from backend.app.seed.cli import seed
from backend.app.services.week45 import stable_hash


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "artifacts" / "expansion"


def main():
    seed()
    checks_e5, checks_e6 = [], []
    with SessionLocal() as db:
        project = db.scalar(select(Project).order_by(Project.project_number))
        review = db.scalar(select(EngineeringReview).where(EngineeringReview.project_id == project.id))
        source = RegulationSource(source_code="SYN-E5-GOLDEN-TEST", title="Synthetic controlled engineering source", jurisdiction="SYNTHETIC", authority_name="Synthetic Authority Placeholder", source_type="CONTROLLED_TEST", publication_state="APPROVED_FOR_TEST")
        db.add(source)
        db.flush()
        regulation = RegulationVersion(regulation_source_id=source.id, edition="SYNTHETIC-TEST-1", version="1.0", source_uri_or_reference="synthetic://approved-test/e5-regulation", content_status="APPROVED_FOR_TEST", content_hash=stable_hash("e5-golden-regulation"))
        db.add(regulation)
        db.commit()
        project_id, review_id, regulation_id = project.id, review.id, regulation.id

    def call(client, checks, method, path, payload=None, code=200):
        response = getattr(client, method)(path, json=payload) if payload is not None else getattr(client, method)(path)
        checks.append(response.status_code == code)
        if response.status_code != code:
            raise RuntimeError(f"{method} {path}: {response.status_code} {response.text}")
        return response.json()

    with TestClient(app) as client:
        engineer = {"actor": "synthetic-engineer", "actor_role": "RESPONSIBLE_ENGINEER"}
        scope = call(client, checks_e5, "post", f"/api/engineering-reviews/{review_id}/scope", {**engineer, "scope_code": "SYN-E5-GOLDEN-SCOPE", "discipline": "ARCHITECTURAL", "selected_regulation_version_ids": [regulation_id], "supported_drawing_types": ["PDF"]})
        applicability = call(client, checks_e5, "post", f"/api/engineering-reviews/{review_id}/regulation-applicability/review", {**engineer, "regulation_version_id": regulation_id, "applicability_status": "APPROVED_APPLICABLE"})
        run1 = call(client, checks_e5, "post", f"/api/engineering-reviews/{review_id}/runs", engineer)
        analysis1 = call(client, checks_e5, "post", f"/api/engineering-review-runs/{run1['id']}/analyze", engineer)
        comment = analysis1["comments"][0]
        accepted = call(client, checks_e5, "post", f"/api/engineering-comments/{comment['id']}/engineer-disposition", {**engineer, "action": "ACCEPT_COMMENT"})
        compliance = call(client, checks_e5, "post", f"/api/engineering-review-runs/{run1['id']}/render-compliance-sheet", {"actor": "synthetic-renderer"})
        comment_sheet = call(client, checks_e5, "post", f"/api/engineering-review-runs/{run1['id']}/render-comment-sheet", {"actor": "synthetic-renderer"})
        drawing2 = call(client, checks_e5, "post", f"/api/engineering-reviews/{review_id}/new-drawing-version", {"actor": "synthetic-engineer", "content": "synthetic corrected drawing V2", "revision_label": "V2"})
        run2 = call(client, checks_e5, "post", f"/api/engineering-reviews/{review_id}/re-review", engineer)
        analysis2 = call(client, checks_e5, "post", f"/api/engineering-review-runs/{run2['id']}/analyze", engineer)
        checks_e5 += [scope["stage2_disposition"] == "UNDECIDED_STAGE2", applicability["applicability_status"] == "APPROVED_APPLICABLE", run1["pinned_drawing_hash"] is not None, run1["regulation_applicability_snapshot"]["trusted"] is True, analysis1["comments"][0]["source_type"] == "PROPOSED_BY_AI", accepted["engineer_disposition"] == "ACCEPT_COMMENT", compliance["status_label"].startswith("ENGINEERING REVIEW"), comment_sheet["accepted_comments"], drawing2["old_review_state"] == "HISTORICAL_STALE", run2["drawing_document_version_id"] == drawing2["drawing_version"]["id"], analysis2["comments"][0]["comment_number"] == 1, client.get(f"/api/engineering-reviews/{review_id}/block-time").json()["sla_claim"] is False]

        with SessionLocal() as db:
            contract = db.scalar(select(Contract).order_by(Contract.contract_reference))
        finance = {"actor": "synthetic-finance", "actor_role": "FINANCE_ACCOUNTANT"}
        decision = call(client, checks_e6, "post", f"/api/contracts/{contract.id}/invoice-requirement/decision", {**finance, "decision": "REQUIRED", "reason": "Synthetic milestone test"})
        invoice_result = call(client, checks_e6, "post", f"/api/contracts/{contract.id}/invoices", {"actor": "synthetic-finance"})
        invoice, invoice_revision = invoice_result["invoice"], invoice_result["revision"]
        invoice_render = call(client, checks_e6, "post", f"/api/invoice-revisions/{invoice_revision['id']}/render", {"actor": "synthetic-finance"})
        call(client, checks_e6, "post", f"/api/invoice-revisions/{invoice_revision['id']}/submit-finance-review", {"actor": "synthetic-finance"})
        finance_approval = call(client, checks_e6, "post", f"/api/invoice-revisions/{invoice_revision['id']}/finance-decision", {**finance, "decision": "APPROVE_FOR_ISSUE"})
        handoff = call(client, checks_e6, "post", f"/api/invoices/{invoice['id']}/accounting-handoff", {"actor": "synthetic-finance"})
        issue = call(client, checks_e6, "post", f"/api/invoices/{invoice['id']}/issue-evidence", {"actor": "synthetic-finance", "evidence_reference": "synthetic://invoice-issued"})
        follow = call(client, checks_e6, "get", f"/api/invoices/{invoice['id']}/follow-up")
        invoice_draft = call(client, checks_e6, "post", f"/api/invoices/{invoice['id']}/communication-draft", {"actor": "synthetic-finance", "communication_type": "INVOICE_FOLLOW_UP"})
        handover_result = call(client, checks_e6, "post", f"/api/projects/{project_id}/handovers", {"actor": "synthetic-owner", "selected_deliverables": ["synthetic://deliverable"]})
        handover = handover_result["handover"]
        handover_form = call(client, checks_e6, "post", f"/api/project-handovers/{handover['id']}/render", {"actor": "synthetic-owner"})
        handover_approval = call(client, checks_e6, "post", f"/api/project-handovers/{handover['id']}/approval", {"actor": "synthetic-owner", "actor_role": "PROJECT_OWNER"})
        release = call(client, checks_e6, "post", f"/api/project-handovers/{handover['id']}/release-evidence", {"actor": "synthetic-owner", "evidence_reference": "synthetic://handover-released"})
        handover_draft = call(client, checks_e6, "post", f"/api/project-handovers/{handover['id']}/communication-draft", {"actor": "synthetic-owner"})
        checks_e6 += [decision["decision_source"] == "HUMAN_DECISION", invoice["requirement_decision_id"] == decision["id"], invoice_render["revision"]["rendered_artifact_id"] == invoice_render["artifact"]["id"], finance_approval["revision"]["status"] == "APPROVED_FOR_ISSUE", handoff["assigned_role"] == "GENERIC_FINANCE_HANDOFF", issue["invoice"]["status"] == "ISSUED_EVIDENCE_RECORDED", follow["late_claim"] is False, invoice_draft["policy_state"] == "HUMAN_SEND", handover_result["evaluation"]["state"] == "READY", handover_form["artifact"]["artifact_type"] == "HANDOVER_FORM", handover_approval["handover"]["approval_state"] == "HANDOVER_APPROVED_FOR_RELEASE", release["handover"]["status"] == "HANDOVER_RELEASED", release["project_closed"] is False, handover_draft["policy_state"] == "HUMAN_SEND"]

    e5 = {"result": "PASS" if all(checks_e5) else "FAIL", "assertion_count": len(checks_e5), "scenario": "Drawing V1 → controlled applicable regulation → advisory comments → Authorized Engineer → sheets → Drawing V2 → stale/re-review", "labels": ["E5_ENGINEERING_REVIEW_ASSISTANT_READY", "ENGINEERING_ADVISORY_GOLDEN_PATH_PASS"], "execution_authority": "PROTOTYPE_DEV_ONLY", "evidence_class": "SYNTHETIC_IMPLEMENTATION_EVIDENCE", "synthetic_only": True, "real_external_actions": False}
    e6 = {"result": "PASS" if all(checks_e6) else "FAIL", "assertion_count": len(checks_e6), "scenario": "Contract milestone → human invoice decision → draft/render → finance handoff → issue evidence → follow-up → bounded handover → human release", "labels": ["E6_FINANCE_INVOICE_HANDOVER_READY", "COMMERCIAL_CLOSEOUT_GOLDEN_PATH_PASS"], "execution_authority": "PROTOTYPE_DEV_ONLY", "evidence_class": "SYNTHETIC_IMPLEMENTATION_EVIDENCE", "synthetic_only": True, "real_external_actions": False}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "e5-engineering-advisory-golden-path.json").write_text(json.dumps(e5, indent=2) + "\n")
    (OUT / "e6-commercial-closeout-golden-path.json").write_text(json.dumps(e6, indent=2) + "\n")
    if e5["result"] != "PASS" or e6["result"] != "PASS":
        raise SystemExit(1)
    # Golden Path execution is evidence-only; leave the shared synthetic seed clean.
    seed()
    print(json.dumps({"e5": e5, "e6": e6}))


if __name__ == "__main__":
    main()
