from __future__ import annotations

import hashlib
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from backend.app.ai.context import build_context_manifest
from backend.app.ai.contracts import (
    AI_ARCHITECTURE,
    AIContextItem,
    AIContextManifest,
    AIContextScope,
    AIExecutionMode,
    AIPurpose,
    AITargetEntityType,
)
from backend.app.ai.policy import authorize_ai_request
from backend.app.api.dependencies import AuthenticatedPrincipal
from backend.app.db import SessionLocal
from backend.app.models import (
    AuthorityCase,
    DocumentVersion,
    EngineeringProjectMember,
    Project,
    Role,
)
from backend.app.services.governed_retrieval import (
    GovernedRetrievalEnvelope,
    GovernedRetrievalResult,
    RetrievalCitation,
    RetrievalQuery,
)


def _settings(**overrides):
    return SimpleNamespace(
        synthetic_only=overrides.get("synthetic_only", True),
        real_data_allowed=overrides.get("real_data_allowed", False),
    )


def _principal(
    role: Role,
    *,
    user_id: str | None = None,
) -> AuthenticatedPrincipal:
    return AuthenticatedPrincipal(
        auth_mode="ENTRA" if user_id else "DEV_HEADER",
        role=role,
        user_id=user_id,
        office_id="synthetic-office",
        tenant_id="tenant-not-for-provider",
        object_id="object-not-for-provider",
    )


def _result(
    *,
    project_id: str,
    content: str = "Synthetic engineering evidence",
    version_id: str = "version-1",
    source_hash: str = "a" * 64,
    relationship_context: dict | None = None,
    domain: str = "TRANSACTIONAL_EVIDENCE",
) -> GovernedRetrievalResult:
    envelope = GovernedRetrievalEnvelope(
        canonical_domain=domain,
        canonical_entity_type="DocumentVersion",
        canonical_entity_id=version_id,
        transactional_entity_id=project_id,
        document_id="document-1",
        document_version_id=version_id,
        source_currentness_state="CURRENT",
        verification_state="VERIFIED",
        authority_source_class="PROJECT_EVIDENCE",
        sensitivity_class="NONE",
        relationship_context={"project_id": project_id, **(relationship_context or {})},
        content=content,
        citation=RetrievalCitation(
            canonical_domain=domain,
            canonical_entity_type="DocumentVersion",
            canonical_entity_id=version_id,
            document_id="document-1",
            document_version_id=version_id,
            locator_type="DOCUMENT_VERSION",
            locator=f"DocumentVersion:{version_id}",
            source_hash=source_hash,
        ),
    )
    return GovernedRetrievalResult(envelope=envelope, score_reason="synthetic")


def _project(db) -> Project:
    return db.scalar(select(Project).order_by(Project.id))


def _manifest(
    monkeypatch,
    db,
    principal,
    project_id,
    result=None,
    **kwargs,
):
    monkeypatch.setattr(
        "backend.app.ai.context.governed_retrieve",
        lambda db, query, access: (result or _result(project_id=project_id),),
    )
    return build_context_manifest(
        db,
        principal,
        purpose=kwargs.pop("purpose", "ENGINEERING_TECHNICAL_DRAFT"),
        execution_mode=kwargs.pop("execution_mode", "INTERACTIVE"),
        target_entity_type=kwargs.pop("target_entity_type", "PROJECT"),
        target_entity_id=kwargs.pop("target_entity_id", project_id),
        query=kwargs.pop("query", RetrievalQuery(query="engineering", limit=1)),
        settings=kwargs.pop("settings", _settings()),
    )


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def test_d0_contract_is_exact_and_has_no_auto_or_fallback():
    assert AI_ARCHITECTURE.architecture_version == "AI-D0-D1-ARCHITECTURE-1.0"
    assert AI_ARCHITECTURE.execution_modes == (
        AIExecutionMode.INTERACTIVE,
        AIExecutionMode.BACKGROUND,
    )
    assert AI_ARCHITECTURE.auto_mode_allowed is False
    assert AI_ARCHITECTURE.hidden_interactive_background_fallback is False
    assert AI_ARCHITECTURE.provider == "AZURE_OPENAI_FOUNDRY"
    assert AI_ARCHITECTURE.model == "gpt-5.1"
    assert AI_ARCHITECTURE.model_version == "2025-11-13"
    assert AI_ARCHITECTURE.deployment_type == "Standard"
    assert AI_ARCHITECTURE.resource_region == "uaenorth"
    assert AI_ARCHITECTURE.processing_boundary == "UAE_NORTH_REGIONAL"
    assert AI_ARCHITECTURE.model_router_allowed is False
    assert AI_ARCHITECTURE.fallback_models == ()
    assert AI_ARCHITECTURE.provider_managed_memory_allowed is False
    assert AI_ARCHITECTURE.provider_managed_threads_allowed is False
    assert AI_ARCHITECTURE.real_content_allowed is False
    assert AI_ARCHITECTURE.external_invocation_enabled is False
    assert AI_ARCHITECTURE.canonical_write_authority == "ZERO"
    assert AI_ARCHITECTURE.protected_action_authority == "ZERO"


def test_full_principal_and_exact_membership_are_required(monkeypatch, db):
    project = _project(db)
    engineer = db.scalar(select(Project).where(Project.id == project.id))
    assert engineer is not None

    principal = _principal(Role.RESPONSIBLE_ENGINEER, user_id="engineer-user-id")
    with pytest.raises(HTTPException) as missing:
        authorize_ai_request(
            db,
            principal,
            purpose_value="ENGINEERING_TECHNICAL_DRAFT",
            execution_mode_value="INTERACTIVE",
            target_entity_type_value="PROJECT",
            target_entity_id=project.id,
            synthetic_only=True,
            real_data_allowed=False,
        )
    assert missing.value.detail == {"code": "PROJECT_SCOPE_NOT_PROVABLE"}

    member = EngineeringProjectMember(
        project_id=project.id,
        actor_id=principal.user_id,
        capability="ENGINEERING_EDIT",
        status="ACTIVE",
        added_by="synthetic-owner",
    )
    db.add(member)
    db.flush()
    authorization, target, _ = authorize_ai_request(
        db,
        principal,
        purpose_value="ENGINEERING_TECHNICAL_DRAFT",
        execution_mode_value="BACKGROUND",
        target_entity_type_value="PROJECT",
        target_entity_id=project.id,
        synthetic_only=True,
        real_data_allowed=False,
    )
    assert authorization.principal_user_id == principal.user_id
    assert target.project_id == project.id


def test_role_value_actor_and_inactive_membership_do_not_authorize(db):
    project = _project(db)
    principal = _principal(Role.RESPONSIBLE_ENGINEER, user_id=Role.RESPONSIBLE_ENGINEER.value)
    db.add(
        EngineeringProjectMember(
            project_id=project.id,
            actor_id=principal.user_id,
            capability="ENGINEERING_EDIT",
            status="INACTIVE",
            added_by="synthetic-owner",
        )
    )
    db.flush()
    with pytest.raises(HTTPException) as denied:
        authorize_ai_request(
            db,
            principal,
            purpose_value="ENGINEERING_TECHNICAL_DRAFT",
            execution_mode_value="INTERACTIVE",
            target_entity_type_value="PROJECT",
            target_entity_id=project.id,
            synthetic_only=True,
            real_data_allowed=False,
        )
    assert denied.value.detail == {"code": "PROJECT_SCOPE_NOT_PROVABLE"}


def test_owner_requires_explicit_exact_target_and_synthetic_gate(db):
    project = _project(db)
    principal = _principal(Role.OWNER_SPONSOR)
    with pytest.raises(HTTPException) as unsupported:
        authorize_ai_request(
            db,
            principal,
            purpose_value="UNKNOWN",
            execution_mode_value="INTERACTIVE",
            target_entity_type_value="PROJECT",
            target_entity_id=project.id,
            synthetic_only=True,
            real_data_allowed=False,
        )
    assert unsupported.value.detail == {"code": "AI_PURPOSE_NOT_SUPPORTED"}

    with pytest.raises(HTTPException) as real:
        authorize_ai_request(
            db,
            principal,
            purpose_value="ENGINEERING_TECHNICAL_DRAFT",
            execution_mode_value="INTERACTIVE",
            target_entity_type_value="PROJECT",
            target_entity_id=project.id,
            synthetic_only=False,
            real_data_allowed=False,
        )
    assert real.value.detail == {"code": "AI_REAL_CONTENT_NOT_AUTHORIZED"}


def test_authority_case_is_resolved_server_side_and_mismatch_denied(db):
    project = _project(db)
    case = AuthorityCase(
        case_reference="AI-D1-SYNTHETIC-CASE",
        external_body_id="missing-external-body",
        service_type_id="missing-service",
        jurisdiction_id="missing-jurisdiction",
        subject_type="PROJECT",
        subject_id=project.id,
        created_by="synthetic",
    )
    db.add(case)
    db.flush()
    authorization, target, _ = authorize_ai_request(
        db,
        _principal(Role.SYSTEM_ADMIN),
        purpose_value="ENGINEERING_TECHNICAL_DRAFT",
        execution_mode_value="INTERACTIVE",
        target_entity_type_value="AUTHORITY_CASE",
        target_entity_id=case.id,
        synthetic_only=True,
        real_data_allowed=False,
    )
    assert authorization.resolved_project_id == project.id
    assert target.project_id == project.id


def test_manifest_uses_governed_retrieval_and_preserves_safe_provenance(monkeypatch, db):
    project = _project(db)
    result = _result(
        project_id=project.id,
        relationship_context={
            "verified_assertion_ids": ["assertion-1"],
            "unsafe_email": "person@example.invalid",
            "unsafe_actor": "actor-from-source",
        },
    )
    manifest = _manifest(monkeypatch, db, _principal(Role.OWNER_SPONSOR), project.id, result)
    item = manifest.items[0]
    assert item.content_trust_class == "UNTRUSTED_EVIDENCE_TEXT"
    assert item.document_version_id == "version-1"
    assert item.verification_state == "VERIFIED"
    assert item.source_currentness_state == "CURRENT"
    assert item.citation.source_hash == "a" * 64
    assert item.relationship_context == {
        "project_id": project.id,
        "verified_assertion_ids": ("assertion-1",),
    }
    serialized = manifest.model_dump_json()
    for secret_or_pii in (
        "bearer",
        "client_secret",
        "database_url",
        "smb",
        "person@example.invalid",
        "object-not-for-provider",
        "tenant-not-for-provider",
    ):
        assert secret_or_pii not in serialized


def test_manifest_fingerprint_is_deterministic_and_state_sensitive(monkeypatch, db):
    project = _project(db)
    principal = _principal(Role.OWNER_SPONSOR)
    first = _manifest(monkeypatch, db, principal, project.id)
    second = _manifest(monkeypatch, db, principal, project.id)
    assert first.manifest_fingerprint == second.manifest_fingerprint

    changed_content = _manifest(
        monkeypatch,
        db,
        principal,
        project.id,
        result=_result(project_id=project.id, content="Changed synthetic evidence"),
    )
    assert first.manifest_fingerprint != changed_content.manifest_fingerprint

    changed_source = _manifest(
        monkeypatch,
        db,
        principal,
        project.id,
        result=_result(project_id=project.id, source_hash="b" * 64),
    )
    assert first.manifest_fingerprint != changed_source.manifest_fingerprint

    background = _manifest(
        monkeypatch,
        db,
        principal,
        project.id,
        execution_mode="BACKGROUND",
    )
    assert first.manifest_fingerprint != background.manifest_fingerprint


@pytest.mark.parametrize(
    ("field", "value", "code"),
    [
        ("superseded", True, "AI_CONTEXT_SUPERSEDED_DENIED"),
        ("sensitivity_class", "HIGH", "AI_CONTEXT_SENSITIVITY_DENIED"),
        ("source_currentness_state", "HISTORICAL", "AI_CONTEXT_HISTORICAL_DENIED"),
    ],
)
def test_manifest_rejects_unsafe_currentness_or_sensitivity(
    monkeypatch, db, field, value, code
):
    project = _project(db)
    result = _result(project_id=project.id)
    result = result.model_copy(
        update={"envelope": result.envelope.model_copy(update={field: value})}
    )
    with pytest.raises(HTTPException) as denied:
        _manifest(monkeypatch, db, _principal(Role.OWNER_SPONSOR), project.id, result)
    assert denied.value.detail == {"code": code}


def test_manifest_preserves_conflict_as_typed_failure(monkeypatch, db):
    project = _project(db)
    result = _result(
        project_id=project.id,
        relationship_context={"conflict_state": "CONFLICTING"},
    )
    with pytest.raises(HTTPException) as conflict:
        _manifest(monkeypatch, db, _principal(Role.OWNER_SPONSOR), project.id, result)
    assert conflict.value.detail == {"code": "AI_CONTEXT_CONFLICT"}


def test_manifest_budget_rejects_without_silent_truncation(monkeypatch, db):
    project = _project(db)
    too_large = _result(project_id=project.id, content="x" * (16 * 1024 + 1))
    with pytest.raises(HTTPException) as item_error:
        _manifest(monkeypatch, db, _principal(Role.OWNER_SPONSOR), project.id, too_large)
    assert item_error.value.detail == {"code": "AI_CONTEXT_BUDGET_EXCEEDED"}

    monkeypatch.setattr(
        "backend.app.ai.context.governed_retrieve",
        lambda db, query, access: tuple(
            _result(project_id=project.id, version_id=f"v-{index}")
            for index in range(21)
        ),
    )
    with pytest.raises(HTTPException) as count_error:
        build_context_manifest(
            db,
            _principal(Role.OWNER_SPONSOR),
            purpose="ENGINEERING_TECHNICAL_DRAFT",
            execution_mode="INTERACTIVE",
            target_entity_type="PROJECT",
            target_entity_id=project.id,
            query=RetrievalQuery(limit=20),
            settings=_settings(),
        )
    assert count_error.value.detail == {"code": "AI_CONTEXT_BUDGET_EXCEEDED"}

    monkeypatch.setattr(
        "backend.app.ai.context.governed_retrieve",
        lambda db, query, access: tuple(
            _result(project_id=project.id, version_id=f"budget-{index}", content="y" * (16 * 1024))
            for index in range(7)
        ),
    )
    with pytest.raises(HTTPException) as total_error:
        build_context_manifest(
            db,
            _principal(Role.OWNER_SPONSOR),
            purpose="ENGINEERING_TECHNICAL_DRAFT",
            execution_mode="INTERACTIVE",
            target_entity_type="PROJECT",
            target_entity_id=project.id,
            query=RetrievalQuery(limit=20),
            settings=_settings(),
        )
    assert total_error.value.detail == {"code": "AI_CONTEXT_BUDGET_EXCEEDED"}

    with pytest.raises(HTTPException) as requested_count_error:
        build_context_manifest(
            db,
            _principal(Role.OWNER_SPONSOR),
            purpose="ENGINEERING_TECHNICAL_DRAFT",
            execution_mode="INTERACTIVE",
            target_entity_type="PROJECT",
            target_entity_id=project.id,
            query=RetrievalQuery(limit=21),
            settings=_settings(),
        )
    assert requested_count_error.value.detail == {"code": "AI_CONTEXT_BUDGET_EXCEEDED"}


def test_retrieval_project_is_server_bound_and_client_fields_are_not_authority(monkeypatch, db):
    project = _project(db)
    captured = {}

    def fake_retrieve(db, query, access):
        captured["query"] = query
        captured["access"] = access
        return ()

    monkeypatch.setattr("backend.app.ai.context.governed_retrieve", fake_retrieve)
    build_context_manifest(
        db,
        _principal(Role.OWNER_SPONSOR),
        purpose="ENGINEERING_TECHNICAL_DRAFT",
        execution_mode="INTERACTIVE",
        target_entity_type="PROJECT",
        target_entity_id=project.id,
        query=RetrievalQuery(project_id=project.id, limit=1),
        settings=_settings(),
    )
    assert captured["query"].project_id == project.id
    assert captured["access"].purpose == "READ"
    assert captured["access"].project_ids == (project.id,)

    with pytest.raises(HTTPException) as mismatch:
        build_context_manifest(
            db,
            _principal(Role.OWNER_SPONSOR),
            purpose="ENGINEERING_TECHNICAL_DRAFT",
            execution_mode="INTERACTIVE",
            target_entity_type="PROJECT",
            target_entity_id=project.id,
            query=RetrievalQuery(project_id="client-claimed-other-project", limit=1),
            settings=_settings(),
        )
    assert mismatch.value.detail == {"code": "AI_CONTEXT_SCOPE_MISMATCH"}


def test_api_route_requires_full_principal_and_supports_background(client, monkeypatch):
    with SessionLocal() as db:
        project = _project(db)
        project_id = project.id

    monkeypatch.setattr(
        "backend.app.ai.context.governed_retrieve",
        lambda db, query, access: (_result(project_id=project_id),),
    )

    response = client.post(
        "/api/ai/context/manifest",
        headers={"X-Dev-Role": "OWNER_SPONSOR"},
        json={
            "purpose": "ENGINEERING_TECHNICAL_DRAFT",
            "execution_mode": "BACKGROUND",
            "target_entity_type": "PROJECT",
            "target_entity_id": project_id,
            "retrieval": {"limit": 1},
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["execution_mode"] == "BACKGROUND"
    assert body["external_model_invocation_count"] == 0
    assert body["canonical_write_count"] == 0
    assert body["real_content_egress_count"] == 0

    rejected = client.post(
        "/api/ai/context/manifest",
        headers={"X-Dev-Role": "OWNER_SPONSOR"},
        json={
            "purpose": "ENGINEERING_TECHNICAL_DRAFT",
            "execution_mode": "INTERACTIVE",
            "target_entity_type": "PROJECT",
            "target_entity_id": project_id,
            "user_id": "client-authority",
        },
    )
    assert rejected.status_code == 422


@pytest.mark.parametrize("field", ["role", "project_ids", "actor", "entra_oid"])
def test_api_rejects_client_authority_fields(client, field):
    with SessionLocal() as db:
        project_id = _project(db).id
    response = client.post(
        "/api/ai/context/manifest",
        headers={"X-Dev-Role": "OWNER_SPONSOR"},
        json={
            "purpose": "ENGINEERING_TECHNICAL_DRAFT",
            "execution_mode": "INTERACTIVE",
            "target_entity_type": "PROJECT",
            "target_entity_id": project_id,
            field: ["client-project"] if field == "project_ids" else "client-authority",
        },
    )
    assert response.status_code == 422
