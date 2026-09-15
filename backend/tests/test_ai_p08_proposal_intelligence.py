from __future__ import annotations

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from backend.app.api.dependencies import AuthenticatedPrincipal
from backend.app.config.settings import Settings
from backend.app.models import (
    Base,
    ConsultancyOffice,
    Document,
    DocumentApprovalState,
    DocumentType,
    DocumentVersion,
    MasterContentItem,
    Opportunity,
    ProposalAcceptedRevision,
    ProposalIntelligenceReviewBinding,
    ProposalRevision,
    Role,
    User,
    WorkflowTask,
)
from backend.app.services.proposal_intelligence import (
    P08_POLICY_VERSION, ProposalDeterministicProvider, execute_proposal_intelligence,
    proposal_reviews, submit_proposal_review,
)
from backend.app.services.intelligence_foundation import dependency_current, invalidate_dependency
from backend.app.models import ContextDependency, AIWorkProduct
from backend.app.ai.skill_registry import PROPOSAL_SKILLS
from backend.app.ai.policy import authorize_ai_request


def test_proposal_skill_pack_is_exact_and_strict():
    expected = [
        "proposal.tender-intake-analysis",
        "proposal.requirement-evidence-analysis",
        "proposal.section-draft",
        "proposal.commercial-consistency-review",
        "proposal.lpo-variance-analysis",
        "proposal.handoff-preflight",
    ]
    assert [item.manifest.skill_id for item in PROPOSAL_SKILLS] == expected
    assert all(item.manifest.version == "1.0.0" for item in PROPOSAL_SKILLS)
    assert all(item.manifest.owning_module == "BD_PROPOSAL" for item in PROPOSAL_SKILLS)
    assert all(item.manifest.purpose.startswith("PROPOSAL_") for item in PROPOSAL_SKILLS)
    assert all(item.manifest.allowed_scope_types == ["PROPOSAL", "PROPOSAL_REVISION"] for item in PROPOSAL_SKILLS)
    assert all(getattr(item.manifest, field) == "NONE" for item in PROPOSAL_SKILLS for field in ("canonical_write_authority", "protected_action_authority", "canonical_or_protected_authority"))
    assert all(item.manifest.allowed_tools == [] for item in PROPOSAL_SKILLS)
    assert all(item.output.provider_schema.get("additionalProperties") is False for item in PROPOSAL_SKILLS)


def test_final_six_proposal_skills_execute_through_shared_runtime(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'p08-six.db'}")
    Base.metadata.create_all(engine)
    operations = [
        ("tender-intake-analysis", "proposal.tender-intake-analysis"),
        ("requirement-evidence-analysis", "proposal.requirement-evidence-analysis"),
        ("section-draft", "proposal.section-draft"),
        ("commercial-consistency-review", "proposal.commercial-consistency-review"),
        ("lpo-variance-analysis", "proposal.lpo-variance-analysis"),
        ("handoff-preflight", "proposal.handoff-preflight"),
    ]
    with Session(engine) as db:
        office = ConsultancyOffice(id="six-office", office_code="SIX", name_en="SIX", name_ar="SIX")
        user = User(id="six-user", email="six@example.test", display_name="Six", role=Role.SYSTEM_ADMIN, office_id=office.id, active=True)
        proposal = Opportunity(id="six-proposal", office_id=office.id, opportunity_reference="SIX-001", title="Synthetic Proposal", status="ACCEPTED", source_type="TEST", fixture_classification="SYNTHETIC_OWNER_TEST")
        revision = ProposalAcceptedRevision(id="six-revision", proposal_id=proposal.id, revision_number=1, snapshot={"title": proposal.title}, validation_snapshot={}, content_hash="a" * 64, accepted_by=user.id, status="ACCEPTED")
        db.add_all([office, user, proposal, revision]); _seed_synthetic_proposal_master_content(db); db.commit()
        principal = AuthenticatedPrincipal(auth_mode="TEST", role=Role.SYSTEM_ADMIN, user_id=user.id, office_id=office.id)
        for index, (operation, skill_id) in enumerate(operations):
            result = execute_proposal_intelligence(db, proposal_id=proposal.id, operation=operation, principal=principal, idempotency_key=f"six-exec-{index}", correlation_id=f"six-corr-{index}", settings=_settings(), provider=ProposalDeterministicProvider())
            assert result["skill_id"] == skill_id
            assert result["canonical_state_mutated"] is False
            assert result["protected_action_count"] == 0
    engine.dispose()


def test_preaccepted_intelligence_does_not_create_working_revision(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'p08-no-revision-side-effect.db'}")
    Base.metadata.create_all(engine)
    operations = ["intake-analysis", "requirement-evidence-analysis", "section-draft", "commercial-consistency-review"]
    with Session(engine) as db:
        office = ConsultancyOffice(id="pre-office", office_code="PRE", name_en="PRE", name_ar="PRE")
        user = User(id="pre-user", email="pre@example.test", display_name="Pre", role=Role.PROCESS_CHAMPION, office_id=office.id, active=True)
        proposal = Opportunity(id="pre-proposal", office_id=office.id, opportunity_reference="PRE-001", title="Synthetic intake", status="IN_REVIEW", source_type="TEST", fixture_classification="SYNTHETIC_OWNER_TEST", proposal_fields_json={"scope": "Synthetic"})
        db.add_all([office, user, proposal]); _seed_synthetic_proposal_master_content(db); db.commit()
        principal = AuthenticatedPrincipal(auth_mode="TEST", role=Role.PROCESS_CHAMPION, user_id=user.id, office_id=office.id)
        assert db.scalar(select(ProposalRevision).where(ProposalRevision.proposal_id == proposal.id)) is None
        for index, operation in enumerate(operations):
            result = execute_proposal_intelligence(db, proposal_id=proposal.id, operation=operation, principal=principal, idempotency_key=f"pre-no-revision-{index}", correlation_id=f"pre-no-revision-corr-{index}", settings=_settings(), provider=ProposalDeterministicProvider())
            assert result["canonical_state_mutated"] is False
        assert db.scalar(select(ProposalRevision).where(ProposalRevision.proposal_id == proposal.id)) is None
    engine.dispose()


def test_proposal_authorization_is_office_bound_and_not_project_membership_bound(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'p08-proposal-authorization.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        office_a = ConsultancyOffice(id="auth-office-a", office_code="AUTH-A", name_en="A", name_ar="A")
        office_b = ConsultancyOffice(id="auth-office-b", office_code="AUTH-B", name_en="B", name_ar="B")
        bd = User(id="auth-bd", email="auth-bd@example.test", display_name="BD", role=Role.PROCESS_CHAMPION, office_id=office_a.id, active=True)
        inactive = User(id="auth-inactive", email="auth-inactive@example.test", display_name="Inactive", role=Role.PROCESS_CHAMPION, office_id=office_a.id, active=False)
        proposal = Opportunity(id="auth-proposal", office_id=office_a.id, opportunity_reference="AUTH-001", title="Pre-project proposal", status="IN_REVIEW", source_type="TEST", fixture_classification="SYNTHETIC_OWNER_TEST")
        db.add_all([office_a, office_b, bd, inactive, proposal]); db.commit()

        authorized, target, _ = authorize_ai_request(
            db, AuthenticatedPrincipal(auth_mode="TEST", role=Role.PROCESS_CHAMPION, user_id=bd.id, office_id=office_a.id),
            purpose_value="PROPOSAL_TENDER_INTAKE_ANALYSIS", execution_mode_value="INTERACTIVE",
            target_entity_type_value="PROPOSAL", target_entity_id=proposal.id,
            synthetic_only=True, real_data_allowed=False,
        )
        assert authorized.scope_decision == "AUTHORIZED"
        assert target.target_entity_id == proposal.id

        with pytest.raises(HTTPException) as wrong_office:
            authorize_ai_request(
                db, AuthenticatedPrincipal(auth_mode="TEST", role=Role.PROCESS_CHAMPION, user_id=bd.id, office_id=office_b.id),
                purpose_value="PROPOSAL_TENDER_INTAKE_ANALYSIS", execution_mode_value="INTERACTIVE",
                target_entity_type_value="PROPOSAL", target_entity_id=proposal.id,
                synthetic_only=True, real_data_allowed=False,
            )
        assert wrong_office.value.detail == {"code": "PROPOSAL_SCOPE_NOT_PROVABLE"}

        with pytest.raises(HTTPException) as inactive_denied:
            authorize_ai_request(
                db, AuthenticatedPrincipal(auth_mode="TEST", role=Role.PROCESS_CHAMPION, user_id=inactive.id, office_id=office_a.id),
                purpose_value="PROPOSAL_TENDER_INTAKE_ANALYSIS", execution_mode_value="INTERACTIVE",
                target_entity_type_value="PROPOSAL", target_entity_id=proposal.id,
                synthetic_only=True, real_data_allowed=False,
            )
        assert inactive_denied.value.detail == {"code": "PROPOSAL_SCOPE_NOT_PROVABLE"}
    engine.dispose()


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


def _seed_synthetic_proposal_master_content(db: Session) -> None:
    """Provide the governed synthetic source required by Owner-test skills."""
    document = Document(
        id="p08-proposal-master-document",
        document_type=DocumentType.OTHER,
        logical_name="Synthetic Proposal Master Content",
        language="EN",
        source_system="SYNTHETIC_OWNER_TEST",
    )
    version = DocumentVersion(
        id="p08-proposal-master-version",
        document_id=document.id,
        version_number=1,
        source_filename="synthetic-proposal-master.txt",
        source_path_or_reference="synthetic-db://master/BD-PROP-001",
        sha256="b" * 64,
        mime_type="text/plain",
        file_size=32,
        language="EN",
        approval_state=DocumentApprovalState.REVIEWED,
        source_system="SYNTHETIC_OWNER_TEST",
        metadata_json={"master_status": "CURRENT", "synthetic_non_business_fixture": True, "synthetic_owner_test_only": True},
        synthetic_content=b"Synthetic Proposal master content",
    )
    document.current_version_id = version.id
    item = MasterContentItem(
        id="p08-proposal-master-item",
        ref="BD-PROP-001",
        content_type="FORM",
        title="Synthetic Proposal Master Content",
        description="Owner-test-only proposal template fixture",
        used_in=["BD"],
        source_type_code="SYNTHETIC_OWNER_TEST",
        status="ACTIVE",
        needs_review=False,
        document_id=document.id,
        current_document_version_id=version.id,
        created_by="p08-test",
    )
    db.add_all([document, version, item])


def test_proposal_analysis_is_module_owned_and_revision_selective(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'p08.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        office = ConsultancyOffice(id="p08-office", office_code="P08", name_en="P08", name_ar="P08")
        user = User(id="p08-user", email="p08@example.test", display_name="P08", role=Role.SYSTEM_ADMIN, office_id=office.id, active=True)
        proposal = Opportunity(id="p08-proposal", office_id=office.id, opportunity_reference="P08-001", title="Synthetic Proposal", status="ACCEPTED", source_type="TEST", fixture_classification="SYNTHETIC_OWNER_TEST")
        revision = ProposalAcceptedRevision(id="p08-revision-a", proposal_id=proposal.id, revision_number=1, snapshot={"title": proposal.title}, validation_snapshot={}, content_hash="a" * 64, accepted_by=user.id, status="ACCEPTED")
        db.add_all([office, user, proposal, revision]); db.commit()
        principal = AuthenticatedPrincipal(auth_mode="TEST", role=Role.SYSTEM_ADMIN, user_id=user.id, office_id=office.id)
        result = execute_proposal_intelligence(db, proposal_id=proposal.id, operation="intake-analysis", principal=principal, idempotency_key="p08-exec-1", correlation_id="p08-corr-1", settings=_settings(), provider=ProposalDeterministicProvider())
        assert result["output_class"] == "ANALYSIS"
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
    engine.dispose()


def test_proposal_review_duplicate_and_conflicting_decision_are_fail_closed(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'p08-review.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        office = ConsultancyOffice(id="p08-office", office_code="P08", name_en="P08", name_ar="P08")
        user = User(id="p08-user", email="p08@example.test", display_name="P08", role=Role.SYSTEM_ADMIN, office_id=office.id, active=True)
        proposal = Opportunity(id="p08-proposal", office_id=office.id, opportunity_reference="P08-001", title="Synthetic Proposal", status="ACCEPTED", source_type="TEST", fixture_classification="SYNTHETIC_OWNER_TEST")
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
