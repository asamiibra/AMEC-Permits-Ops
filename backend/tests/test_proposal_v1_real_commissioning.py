from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.app.ai.errors import AIError
from backend.app.api.dependencies import AuthenticatedPrincipal
from backend.app.config.settings import Settings
from backend.app.models import AIExecutionLedger, Base, ConsultancyOffice, Opportunity, Role, User
from backend.app.services.proposal_intelligence import ProposalDeterministicProvider, execute_proposal_intelligence


def _settings(real: bool) -> Settings:
    return Settings(
        app_env="TEST", synthetic_only=True, real_data_allowed=False,
        ai_proposal_real_content_allowed=real,
        ai_feature_enabled=True, ai_external_inference_enabled=True,
        ai_d4_commissioning_id="proposal-real-commissioning",
        ai_azure_openai_endpoint="https://proposalops.openai.azure.com",
        ai_azure_openai_region="eastus", ai_azure_openai_deployment_type="DataZoneStandard",
        ai_max_context_items=8, ai_max_context_utf8_bytes=16384,
        ai_max_input_token_upper_bound=24000, ai_max_output_tokens=6000,
        ai_max_requests_per_user_per_minute=20, ai_max_requests_per_user_per_hour=100,
        ai_max_requests_per_project_per_hour=100, ai_max_requests_global_per_hour=100,
        ai_max_estimated_cost_usd_per_request=1, ai_max_estimated_cost_usd_per_day=10,
        ai_input_price_usd_per_1m_tokens=1, ai_output_price_usd_per_1m_tokens=1,
        ai_pricing_source_reference="proposal-real-commissioning-test",
    )


def test_proposal_real_content_requires_the_proposal_commissioning_switch(tmp_path: Path):
    engine = create_engine(f"sqlite:///{tmp_path / 'proposal-real-gate.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        office = ConsultancyOffice(id="real-office", office_code="REAL", name_en="REAL", name_ar="REAL")
        user = User(id="real-user", email="real@example.test", display_name="Real", role=Role.SYSTEM_ADMIN, office_id=office.id, active=True)
        proposal = Opportunity(id="real-proposal", office_id=office.id, opportunity_reference="REAL-001", title="Live proposal", status="IN_REVIEW", source_type="BD_WORKSPACE")
        db.add_all([office, user, proposal])
        db.commit()
        principal = AuthenticatedPrincipal(auth_mode="ENTRA", role=Role.SYSTEM_ADMIN, user_id=user.id, office_id=office.id)
        result = execute_proposal_intelligence(
            db, proposal_id=proposal.id, operation="intake-analysis", principal=principal,
            idempotency_key="proposal-real-enabled", correlation_id="proposal-real-enabled-corr",
            settings=_settings(True), provider=ProposalDeterministicProvider(),
        )
        assert result["status"] == "SUCCEEDED"
        ledger = db.get(AIExecutionLedger, result["execution_id"])
        assert ledger is not None and ledger.synthetic_only is False

        with pytest.raises(AIError, match="AI_REAL_CONTENT_NOT_AUTHORIZED"):
            execute_proposal_intelligence(
                db, proposal_id=proposal.id, operation="intake-analysis", principal=principal,
                idempotency_key="proposal-real-disabled", correlation_id="proposal-real-disabled-corr",
                settings=_settings(False), provider=ProposalDeterministicProvider(),
            )
    engine.dispose()
