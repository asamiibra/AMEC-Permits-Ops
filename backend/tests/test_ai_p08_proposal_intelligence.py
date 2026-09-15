from __future__ import annotations

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from backend.app.api.dependencies import AuthenticatedPrincipal
from backend.app.config.settings import Settings
from backend.app.models import Base, ConsultancyOffice, Opportunity, ProposalAcceptedRevision, ProposalIntelligenceReviewBinding, Role, User, WorkflowTask
from backend.app.services.proposal_intelligence import (
    P08_POLICY_VERSION, ProposalDeterministicProvider, execute_proposal_intelligence,
    proposal_reviews, submit_proposal_review,
)
from backend.app.services.intelligence_foundation import dependency_current, invalidate_dependency
from backend.app.models import ContextDependency, AIWorkProduct
from backend.app.ai.skill_registry import PROPOSAL_SKILLS
from backend.app.services import backend_realignment
from backend.app.services.intelligence_contracts import IntelligenceContractError


def test_proposal_skill_pack_is_exact_and_strict():
    expected = [
        "proposal.intake-analysis",
        "proposal.scope-technical-analysis",
        "proposal.lpo-variance-analysis",
        "proposal.readiness-explanation",
    ]
    assert [item.manifest.skill_id for item in PROPOSAL_SKILLS] == expected
    assert all(item.manifest.version == "1.0.0" for item in PROPOSAL_SKILLS)
    assert all(item.manifest.owning_module == "proposal" for item in PROPOSAL_SKILLS)
    assert all(item.manifest.allowed_scope_types == ["PROPOSAL"] for item in PROPOSAL_SKILLS)
    assert all(getattr(item.manifest, field) == "NONE" for item in PROPOSAL_SKILLS for field in ("canonical_write_authority", "protected_action_authority", "canonical_or_protected_authority"))
    assert all(item.manifest.allowed_tools == [] for item in PROPOSAL_SKILLS)
    assert all(item.output.provider_schema.get("additionalProperties") is False for item in PROPOSAL_SKILLS)


def _settings() -> Settings:
    return Settings(
        app_env="TEST", synthetic_only=True, real_data_allowed=False,
        ai_feature_enabled=True, ai_external_inference_enabled=True,
        ai_d4_commissioning_id="p08-test", ai_azure_openai_endpoint="https://proposalops.openai.azure.com",
        ai_azure_openai_region="eastus", ai_azure_openai_deployment_type="DataZoneStandard",
        ai_max_context_items=8, ai_max_context_utf8_bytes=16384, ai_max_input_token_upper_bound=24000,
        ai_max_output_tokens=6000, ai_max_requests_per_user_per_minute=20, ai_max_requests_per_user_per_hour=100,
        ai_max_requests_per_project_per_hour=100, ai_max_requests_global_per_hour=100,
        ai_max_estimated_cost_usd_per_request=1, ai_max_estimated_cost_usd_per_day=10,
        ai_input_price_usd_per_1m_tokens=1, ai_output_price_usd_per_1m_tokens=1,
        ai_pricing_source_reference="p08-test-price",
    )


def test_proposal_analysis_is_module_owned_and_revision_selective(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'p08.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        office = ConsultancyOffice(id="p08-office", office_code="P08", name_en="P08", name_ar="P08")
        user = User(id="p08-user", email="p08@example.test", display_name="P08", role=Role.SYSTEM_ADMIN, office_id=office.id, active=True)
        proposal = Opportunity(id="p08-proposal", office_id=office.id, opportunity_reference="P08-001", title="Synthetic Proposal", status="ACCEPTED", source_type="TEST")
        revision = ProposalAcceptedRevision(id="p08-revision-a", proposal_id=proposal.id, revision_number=1, snapshot={"title": proposal.title}, validation_snapshot={}, content_hash="a" * 64, accepted_by=user.id, status="ACCEPTED")
        db.add_all([office, user, proposal, revision]); db.commit()
        principal = AuthenticatedPrincipal(auth_mode="TEST", role=Role.SYSTEM_ADMIN, user_id=user.id, office_id=office.id)
        result = execute_proposal_intelligence(db, proposal_id=proposal.id, operation="intake-analysis", principal=principal, idempotency_key="p08-exec-1", correlation_id="p08-corr-1", settings=_settings(), provider=ProposalDeterministicProvider())
        assert result["output_class"] == "ANALYSIS"
        assert result["citations"] and result["citations"][0]["source_id"] == proposal.id
        binding = db.scalar(select(ProposalIntelligenceReviewBinding))
        assert binding and db.scalar(select(WorkflowTask).where(WorkflowTask.id == binding.workflow_task_id))
        assert result["canonical_state_mutated"] is False
        assert len(db.scalars(select(AIWorkProduct)).all()) == 1
        assert len(db.scalars(select(ProposalAcceptedRevision)).all()) == 1
        accepted = db.get(ProposalAcceptedRevision, revision.id)
        accepted.status = "SUPERSEDED"
        replacement = ProposalAcceptedRevision(id="p08-revision-b", proposal_id=proposal.id, revision_number=2, snapshot={"title": proposal.title}, validation_snapshot={}, content_hash="b" * 64, accepted_by=user.id, status="ACCEPTED")
        db.add(replacement); db.flush()
        assert proposal_reviews(db, proposal.id)[0]["actionable"] is False
        assert db.scalar(select(AIWorkProduct)).state == "STALE"
        rerun = execute_proposal_intelligence(db, proposal_id=proposal.id, operation="intake-analysis", principal=principal, idempotency_key="p08-exec-1-rerun", correlation_id="p08-corr-1-rerun", settings=_settings(), provider=ProposalDeterministicProvider())
        assert rerun["execution_id"] != result["execution_id"]
        assert rerun["work_product_id"] != result["work_product_id"]
        assert rerun["context_snapshot_id"] != result["context_snapshot_id"]
        assert proposal_reviews(db, proposal.id)[-1]["actionable"] is True
        latest_citation = proposal_reviews(db, proposal.id)[-1]["citations"][0]
        assert latest_citation["source_id"] == proposal.id
        assert replacement.id in latest_citation["source_version_or_hash"]
    engine.dispose()


def test_proposal_review_duplicate_and_conflicting_decision_are_fail_closed(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'p08-review.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        office = ConsultancyOffice(id="p08-office", office_code="P08", name_en="P08", name_ar="P08")
        user = User(id="p08-user", email="p08@example.test", display_name="P08", role=Role.SYSTEM_ADMIN, office_id=office.id, active=True)
        proposal = Opportunity(id="p08-proposal", office_id=office.id, opportunity_reference="P08-001", title="Synthetic Proposal", status="ACCEPTED", source_type="TEST")
        revision = ProposalAcceptedRevision(id="p08-revision", proposal_id=proposal.id, revision_number=1, snapshot={"title": proposal.title}, validation_snapshot={}, content_hash="a" * 64, accepted_by=user.id, status="ACCEPTED")
        db.add_all([office, user, proposal, revision]); db.commit()
        principal = AuthenticatedPrincipal(auth_mode="TEST", role=Role.SYSTEM_ADMIN, user_id=user.id, office_id=office.id)
        result = execute_proposal_intelligence(db, proposal_id=proposal.id, operation="readiness-explanation", principal=principal, idempotency_key="p08-exec-2", correlation_id="p08-corr-2", settings=_settings(), provider=ProposalDeterministicProvider())
        binding = db.scalar(select(ProposalIntelligenceReviewBinding))
        first = submit_proposal_review(db, proposal_id=proposal.id, binding_id=binding.id, decision="ACCEPT", idempotency_key="p08-review-1", principal=principal, correlation_id="p08-corr-2", precondition_version=binding.precondition_version)
        assert first["protected_action_executed"] is False
        # A completed review is not actionable a second time; the immutable
        # shared decision remains the sole durable record.
        try:
            submit_proposal_review(db, proposal_id=proposal.id, binding_id=binding.id, decision="REJECT", idempotency_key="p08-review-2", principal=principal, correlation_id="p08-corr-2", precondition_version=binding.precondition_version)
        except Exception as exc:
            assert "PROPOSAL_REVIEW" in str(exc)
        else:
            raise AssertionError("completed Proposal review unexpectedly accepted a second decision")
    engine.dispose()


def test_owner_review_override_and_skill_specific_reviewer_routing(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'p08-owner-review-routing.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        office = ConsultancyOffice(id="p08-owner-office", office_code="P08O", name_en="P08 Owner", name_ar="P08 Owner")
        owner = User(id="p08-owner", email="owner@example.test", display_name="Owner", role=Role.OWNER_SPONSOR, office_id=office.id, active=True)
        bd = User(id="p08-bd", email="bd@example.test", display_name="BD", role=Role.PROCESS_CHAMPION, office_id=office.id, active=True)
        engineer = User(id="p08-engineer", email="engineer@example.test", display_name="Engineer", role=Role.RESPONSIBLE_ENGINEER, office_id=office.id, active=True)
        proposal = Opportunity(id="p08-owner-proposal", office_id=office.id, opportunity_reference="P08-OWNER-001", title="Synthetic Owner Proposal", status="ACCEPTED", source_type="TEST")
        revision = ProposalAcceptedRevision(id="p08-owner-revision", proposal_id=proposal.id, revision_number=1, snapshot={"title": proposal.title}, validation_snapshot={}, content_hash="c" * 64, accepted_by=owner.id, status="ACCEPTED")
        db.add_all([office, owner, bd, engineer, proposal, revision])
        db.commit()
        owner_principal = AuthenticatedPrincipal(auth_mode="TEST", role=Role.OWNER_SPONSOR, user_id=owner.id, office_id=office.id)
        bd_principal = AuthenticatedPrincipal(auth_mode="TEST", role=Role.PROCESS_CHAMPION, user_id=bd.id, office_id=office.id)
        engineer_principal = AuthenticatedPrincipal(auth_mode="TEST", role=Role.RESPONSIBLE_ENGINEER, user_id=engineer.id, office_id=office.id)

        intake = execute_proposal_intelligence(db, proposal_id=proposal.id, operation="intake-analysis", principal=owner_principal, idempotency_key="owner-intake", correlation_id="owner-intake-corr", settings=_settings(), provider=ProposalDeterministicProvider())
        intake_binding = db.scalar(select(ProposalIntelligenceReviewBinding).where(ProposalIntelligenceReviewBinding.work_product_id == intake["work_product_id"]))
        assert intake_binding.required_persona == "BUSINESS_DEVELOPMENT"
        owner_decision = submit_proposal_review(db, proposal_id=proposal.id, binding_id=intake_binding.id, decision="ACCEPT", idempotency_key="owner-intake-review", principal=owner_principal, correlation_id="owner-intake-review-corr", precondition_version=intake_binding.precondition_version)
        assert owner_decision["protected_action_executed"] is False

        bd_intake = execute_proposal_intelligence(db, proposal_id=proposal.id, operation="intake-analysis", principal=owner_principal, idempotency_key="bd-intake", correlation_id="bd-intake-corr", settings=_settings(), provider=ProposalDeterministicProvider())
        bd_binding = db.scalar(select(ProposalIntelligenceReviewBinding).where(ProposalIntelligenceReviewBinding.work_product_id == bd_intake["work_product_id"]))
        bd_decision = submit_proposal_review(db, proposal_id=proposal.id, binding_id=bd_binding.id, decision="DEFER", idempotency_key="bd-intake-review", principal=bd_principal, correlation_id="bd-intake-review-corr", precondition_version=bd_binding.precondition_version)
        assert bd_decision["decision"] == "DEFER"

        technical = execute_proposal_intelligence(db, proposal_id=proposal.id, operation="scope-technical-analysis", principal=owner_principal, idempotency_key="owner-technical", correlation_id="owner-technical-corr", settings=_settings(), provider=ProposalDeterministicProvider())
        technical_binding = db.scalar(select(ProposalIntelligenceReviewBinding).where(ProposalIntelligenceReviewBinding.work_product_id == technical["work_product_id"]))
        assert technical_binding.required_persona == "ENGINEERING"
        try:
            submit_proposal_review(db, proposal_id=proposal.id, binding_id=technical_binding.id, decision="ACCEPT", idempotency_key="bd-technical-review", principal=bd_principal, correlation_id="bd-technical-review-corr", precondition_version=technical_binding.precondition_version)
        except IntelligenceContractError as exc:
            assert str(exc) == "PROPOSAL_REVIEW_PERSONA_DENIED"
        else:
            raise AssertionError("BD incorrectly reviewed an Engineering-routed Proposal analysis")
        engineer_decision = submit_proposal_review(db, proposal_id=proposal.id, binding_id=technical_binding.id, decision="DEFER", idempotency_key="engineer-technical-review", principal=engineer_principal, correlation_id="engineer-technical-review-corr", precondition_version=technical_binding.precondition_version)
        assert engineer_decision["decision"] == "DEFER"

        readiness = execute_proposal_intelligence(db, proposal_id=proposal.id, operation="readiness-explanation", principal=owner_principal, idempotency_key="owner-readiness", correlation_id="owner-readiness-corr", settings=_settings(), provider=ProposalDeterministicProvider())
        readiness_binding = db.scalar(select(ProposalIntelligenceReviewBinding).where(ProposalIntelligenceReviewBinding.work_product_id == readiness["work_product_id"]))
        owner_capabilities = backend_realignment.CAPABILITY_MATRIX["OWNER"]
        monkeypatch.setitem(backend_realignment.CAPABILITY_MATRIX, "OWNER", owner_capabilities - {"BD_PROPOSAL_INTELLIGENCE_REVIEW"})
        try:
            submit_proposal_review(db, proposal_id=proposal.id, binding_id=readiness_binding.id, decision="ACCEPT", idempotency_key="owner-no-cap-review", principal=owner_principal, correlation_id="owner-no-cap-review-corr", precondition_version=readiness_binding.precondition_version)
        except Exception as exc:
            assert "CAPABILITY" in str(exc)
        else:
            raise AssertionError("Owner without review capability was accepted")
    engine.dispose()
