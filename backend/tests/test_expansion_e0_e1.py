from pathlib import Path

import yaml
from sqlalchemy import func, select

from backend.app.expansion.fixture import EXPANDED_FIXTURE_MANIFEST_HASH, EXPANDED_FIXTURE_VERSION, expanded_fixture_metadata
from backend.app.expansion.governance import ASSISTANT_IDS, OWNER_IDS, validate_governance
from backend.app.models import *


def test_e0_registries_are_separate_and_exact():
    governance = validate_governance()
    assert governance["a12b_count"] == 40
    assert [item["id"] for item in governance["owner_requirements"]] == OWNER_IDS
    assert governance["a15_count"] == 18
    assert [item["id"] for item in governance["clarifications"]] == [f"A15-{i:02d}" for i in range(1, 19)]
    assert len({item["id"] for item in governance["owner_requirements"]}) == 40
    assert len({item["id"] for item in governance["clarifications"]}) == 18
    a12 = yaml.safe_load(Path("config/recording_fidelity_requirements_v2_5.yaml").read_text())
    assert len(a12["requirements"]) == 20
    assert not any(item.get("id", "").startswith("OWN-NEW-") for item in a12["requirements"])


def test_e0_safe_defaults_and_assistant_boundary():
    governance = validate_governance()
    clarifications = {item["id"]: item for item in governance["clarifications"]}
    assert clarifications["A15-05"]["safe_default"] == "No automatic approval routing. Generic human Finance Handoff only."
    assert clarifications["A15-06"]["safe_default"] == "Human decision or configured deterministic rule. No AI inference."
    assert clarifications["A15-08"]["safe_default"].endswith("Do not create a fifth autonomous assistant.")
    assert clarifications["A15-09"]["safe_default"].startswith("Per-system capability policy only.")
    assert clarifications["A15-11"]["safe_default"].startswith("All external message classes remain HUMAN_SEND")
    assert clarifications["A15-12"]["safe_default"] == "TRACK / DRAFT / HANDOFF only. No accounting write/post."
    assert clarifications["A15-15"]["safe_default"].startswith("No authoritative engineering claim")
    assert clarifications["A15-16"]["safe_default"].startswith("No NFPA compliance claim")
    assert clarifications["A15-17"]["safe_default"].startswith("Permit core mandatory.")
    assert clarifications["A15-18"]["safe_default"].startswith("All four are discovery lenses.")
    assert ASSISTANT_IDS == ["BD_ASSISTANT", "ADMIN_ASSISTANT", "ENGINEERING_REVIEW_ASSISTANT", "PROJECT_PERMIT_COORDINATION_ASSISTANT"]
    assert "JUNIOR_ENGINEER_AI" not in ASSISTANT_IDS
    assert all(item["current_disposition"] == "UNDECIDED_STAGE2" for item in governance["owner_requirements"])


def test_e1_shared_domain_rows_and_primitives(client):
    summary = client.get("/api/expansion/domain-summary").json()
    # ProposalOps now keeps a deterministic active pre-contract Proposal next
    # to the contracted owner-demo chain so both lifecycle paths are visible.
    assert summary["counts"]["opportunities"] >= 2
    assert summary["counts"]["rfqs"] == 1
    assert summary["counts"]["quotation_revisions"] == 1
    assert summary["counts"]["contract_revisions"] == 1
    assert summary["counts"]["checklist_items"] == 1
    assert summary["counts"]["document_requests"] == 1
    assert summary["counts"]["reference_numbers"] == 1
    assert summary["counts"]["communication_drafts"] == 1
    assert summary["counts"]["invoices"] == 1
    assert summary["counts"]["accounting_handoffs"] == 1
    assert summary["counts"]["project_handovers"] == 1
    assert summary["counts"]["engineering_reviews"] == 1
    assert summary["counts"]["engineering_review_runs"] == 1
    assert summary["counts"]["regulation_versions"] == 1
    assert summary["counts"]["engineering_comments"] == 1
    assert summary["counts"]["drawing_review_cycles"] == 1
    assert summary["counts"]["template_versions"] == 1
    assert summary["counts"]["rendered_artifacts"] == 1
    assert summary["counts"]["assistant_capability_definitions"] >= 30
    assert "DocumentVersion" in summary["shared_primitives"]
    assert "Approval" in summary["shared_primitives"]
    assert "LineageEdge" in summary["shared_primitives"]
    assert summary["external_actions"] == {"email": False, "accounting_write": False, "government_write": False, "machine_final_submit": False}


def test_e1_foreign_key_semantics_and_safe_states():
    from backend.app.db import SessionLocal
    with SessionLocal() as db:
        opportunity = db.scalar(select(Opportunity))
        rfq = db.scalar(select(RFQ))
        quotation_revision = db.scalar(select(QuotationRevision))
        contract_revision = db.scalar(select(ContractRevision))
        request = db.scalar(select(DocumentRequest))
        delivery = db.scalar(select(CommunicationDelivery))
        handoff = db.scalar(select(AccountingHandoff))
        handover = db.scalar(select(ProjectHandover))
        review_run = db.scalar(select(EngineeringReviewRun))
        comment = db.scalar(select(EngineeringComment))
        regulation = db.scalar(select(RegulationVersion))
        template = db.scalar(select(TemplateVersion))
        artifact = db.scalar(select(RenderedArtifact))
        capability = db.scalar(select(AssistantCapabilityDefinition))
        assert rfq.opportunity_id == opportunity.id
        assert rfq.source_document_version_id
        assert quotation_revision.status == "DRAFT"
        assert contract_revision.controlling_quotation_revision_id == quotation_revision.id
        assert request.checklist_item_id
        assert delivery.delivery_status == "NOT_SENT"
        assert handoff.assigned_role == "GENERIC_FINANCE_HANDOFF"
        assert handoff.status == "TRACK_ONLY"
        assert handover.status == "NOT_READY"
        assert handover.approval_id is None
        assert review_run.drawing_document_version_id
        assert comment.engineering_review_run_id == review_run.id
        assert comment.drawing_document_version_id == review_run.drawing_document_version_id
        assert regulation.content_status == "SYNTHETIC_PLACEHOLDER"
        assert template.status == "SYNTHETIC_STANDIN"
        assert artifact.status == "DRAFT"
        assert capability.assistant_id in ASSISTANT_IDS
        assert capability.stage2_disposition == "UNDECIDED_STAGE2"


def test_e1_fixture_successor_and_branding(client):
    fixture = client.get("/api/expansion/fixture").json()
    assert fixture["fixture_version"] == EXPANDED_FIXTURE_VERSION
    assert fixture["fixture_manifest_hash"] == EXPANDED_FIXTURE_MANIFEST_HASH
    assert fixture["predecessor"]["version"] == "1.1.1"
    assert fixture["synthetic_only"] is True
    assert len(fixture["manifest"]["source_families"]) == 8
    assert set(fixture["manifest"]["scenarios"]) == {"EXPANSION_A_HAPPY_UPSTREAM_HANDOFF", "EXPANSION_B_MISSING_EXPIRED_DOCUMENT", "EXPANSION_C_ENGINEERING_REVIEW_FOUNDATION"}
    assert len(fixture["resources"]) >= 30
    office = client.get("/api/office").json()
    assert office["name_en"] == "AMEC Engineering"
    requirements = client.get("/api/expansion/requirements").json()
    clarifications = client.get("/api/expansion/clarifications").json()
    capabilities = client.get("/api/expansion/capabilities").json()
    assert requirements["count"] == 40
    assert clarifications["count"] == 18
    assert capabilities["assistant_ids"] == ASSISTANT_IDS
    assert capabilities["stage2_approval"] == "NOT_PRESENT"
