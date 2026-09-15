"""Purpose-specific AI authorization policy.

AI purpose authorization is intentionally separate from the legacy governed
retrieval purpose matrix.  Passing this policy is required before the AI seam
may reuse governed retrieval with its bounded READ purpose.
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..api.dependencies import AuthenticatedPrincipal
from ..models import AuthorityCase, EngineeringProjectMember, MasterContentItem, Opportunity, Project, Role, User
from ..services.backend_realignment import CAPABILITY_MATRIX, persona_for_role
from .contracts import (
    AIExecutionMode,
    AIPurpose,
    AITargetEntityType,
    POLICY_VERSION,
)


REQUIRED_CAPABILITY = "ENGINEERING_PROJECT_READ"
OWNER_ROLES = frozenset({Role.OWNER_SPONSOR, Role.SYSTEM_ADMIN})


@dataclass(frozen=True)
class AIPurposePolicy:
    purpose_id: AIPurpose
    policy_version: str
    allowed_roles: frozenset[Role]
    required_capabilities: tuple[str, ...]
    allowed_target_entity_types: frozenset[AITargetEntityType]
    allowed_execution_modes: frozenset[AIExecutionMode]
    allow_master_content: bool
    allow_transactional_evidence: bool
    allow_definitions: bool
    allowed_sensitivity_classes: frozenset[str]
    allow_historical: bool
    allow_superseded: bool
    real_content_allowed: bool
    protected_action_authority: str
    canonical_write_authority: str


ENGINEERING_TECHNICAL_DRAFT_POLICY = AIPurposePolicy(
    purpose_id=AIPurpose.ENGINEERING_TECHNICAL_DRAFT,
    policy_version=POLICY_VERSION,
    allowed_roles=frozenset(
        {Role.OWNER_SPONSOR, Role.SYSTEM_ADMIN, Role.RESPONSIBLE_ENGINEER}
    ),
    required_capabilities=(REQUIRED_CAPABILITY,),
    allowed_target_entity_types=frozenset(
        {AITargetEntityType.PROJECT, AITargetEntityType.AUTHORITY_CASE}
    ),
    allowed_execution_modes=frozenset(
        {AIExecutionMode.INTERACTIVE, AIExecutionMode.BACKGROUND}
    ),
    allow_master_content=True,
    allow_transactional_evidence=True,
    allow_definitions=True,
    allowed_sensitivity_classes=frozenset({"NONE"}),
    allow_historical=False,
    allow_superseded=False,
    real_content_allowed=False,
    protected_action_authority="ZERO",
    canonical_write_authority="ZERO",
)

PROPOSAL_INTELLIGENCE_POLICY = AIPurposePolicy(
    purpose_id=AIPurpose.PROPOSAL_INTELLIGENCE,
    policy_version="PROPOSAL_INTELLIGENCE-1.0",
    allowed_roles=frozenset({Role.OWNER_SPONSOR, Role.SYSTEM_ADMIN, Role.PROCESS_CHAMPION, Role.RESPONSIBLE_ENGINEER}),
    required_capabilities=("BD_PROPOSAL_READ",),
    allowed_target_entity_types=frozenset({AITargetEntityType.PROPOSAL}),
    allowed_execution_modes=frozenset({AIExecutionMode.INTERACTIVE, AIExecutionMode.BACKGROUND}),
    allow_master_content=True,
    allow_transactional_evidence=True,
    allow_definitions=True,
    allowed_sensitivity_classes=frozenset({"NONE", "SYNTHETIC"}),
    allow_historical=False,
    allow_superseded=False,
    real_content_allowed=False,
    protected_action_authority="ZERO",
    canonical_write_authority="ZERO",
)


def _proposal_skill_policy(purpose: AIPurpose) -> AIPurposePolicy:
    """Return the shared fail-closed policy for one precise Proposal skill."""

    return AIPurposePolicy(
        purpose_id=purpose,
        policy_version="PROPOSAL_INTELLIGENCE_V1-1.0",
        allowed_roles=frozenset({Role.OWNER_SPONSOR, Role.SYSTEM_ADMIN, Role.PROCESS_CHAMPION, Role.RESPONSIBLE_ENGINEER}),
        required_capabilities=("BD_PROPOSAL_READ",),
        allowed_target_entity_types=frozenset({AITargetEntityType.PROPOSAL}),
        allowed_execution_modes=frozenset({AIExecutionMode.INTERACTIVE}),
        allow_master_content=True,
        allow_transactional_evidence=True,
        allow_definitions=True,
        allowed_sensitivity_classes=frozenset({"NONE", "SYNTHETIC"}),
        allow_historical=False,
        allow_superseded=False,
        real_content_allowed=False,
        protected_action_authority="ZERO",
        canonical_write_authority="ZERO",
    )


PROPOSAL_V1_POLICIES = {
    purpose: _proposal_skill_policy(purpose)
    for purpose in (
        AIPurpose.PROPOSAL_TENDER_INTAKE_ANALYSIS,
        AIPurpose.PROPOSAL_REQUIREMENT_EVIDENCE_ANALYSIS,
        AIPurpose.PROPOSAL_SECTION_DRAFT,
        AIPurpose.PROPOSAL_COMMERCIAL_CONSISTENCY_REVIEW,
        AIPurpose.PROPOSAL_LPO_VARIANCE_ANALYSIS,
        AIPurpose.PROPOSAL_HANDOFF_PREFLIGHT,
    )
}

MASTER_CONTENT_INTELLIGENCE_POLICY = AIPurposePolicy(
    purpose_id=AIPurpose.MASTER_CONTENT_INTELLIGENCE,
    policy_version="MASTER_CONTENT_INTELLIGENCE-1.0",
    allowed_roles=frozenset({Role.OWNER_SPONSOR, Role.SYSTEM_ADMIN}),
    required_capabilities=("READ_ALL",),
    allowed_target_entity_types=frozenset({AITargetEntityType.MASTER_CONTENT_ITEM}),
    allowed_execution_modes=frozenset({AIExecutionMode.INTERACTIVE}),
    allow_master_content=True,
    allow_transactional_evidence=False,
    allow_definitions=True,
    allowed_sensitivity_classes=frozenset({"NONE", "SYNTHETIC"}),
    allow_historical=False,
    allow_superseded=False,
    real_content_allowed=False,
    protected_action_authority="ZERO",
    canonical_write_authority="ZERO",
)


AI_PURPOSE_POLICIES = {
    AIPurpose.ENGINEERING_TECHNICAL_DRAFT: ENGINEERING_TECHNICAL_DRAFT_POLICY,
    AIPurpose.PROPOSAL_INTELLIGENCE: PROPOSAL_INTELLIGENCE_POLICY,
    **PROPOSAL_V1_POLICIES,
    AIPurpose.MASTER_CONTENT_INTELLIGENCE: MASTER_CONTENT_INTELLIGENCE_POLICY,
}


@dataclass(frozen=True)
class ResolvedAITarget:
    target_entity_type: AITargetEntityType
    target_entity_id: str
    project_id: str | None


@dataclass(frozen=True)
class AIAuthorizationContext:
    principal_user_id: str | None
    principal_role: Role
    principal_office_id: str | None
    auth_mode: str
    requested_purpose: AIPurpose
    execution_mode: AIExecutionMode
    target_entity_type: AITargetEntityType
    target_entity_id: str
    resolved_project_id: str | None
    required_capabilities: tuple[str, ...]
    scope_decision: str
    decision_code: str


def ai_error(status_code: int, code: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"code": code})


def parse_purpose(value: str) -> AIPurpose:
    try:
        return AIPurpose(value)
    except (TypeError, ValueError) as exc:
        raise ai_error(403, "AI_PURPOSE_NOT_SUPPORTED") from exc


def parse_execution_mode(value: str) -> AIExecutionMode:
    try:
        return AIExecutionMode(value)
    except (TypeError, ValueError) as exc:
        raise ai_error(403, "AI_EXECUTION_MODE_NOT_SUPPORTED") from exc


def policy_for(purpose: AIPurpose) -> AIPurposePolicy:
    policy = AI_PURPOSE_POLICIES.get(purpose)
    if policy is None:
        raise ai_error(403, "AI_PURPOSE_NOT_SUPPORTED")
    return policy


def _has_capability(role: Role, capability: str) -> bool:
    return capability in CAPABILITY_MATRIX.get(persona_for_role(role), set())


def resolve_target(
    db: Session,
    target_entity_type: AITargetEntityType,
    target_entity_id: str,
) -> ResolvedAITarget:
    if target_entity_type is AITargetEntityType.PROJECT:
        project = db.get(Project, target_entity_id)
        if project is None:
            raise ai_error(404, "AI_CONTEXT_TARGET_NOT_FOUND")
        return ResolvedAITarget(target_entity_type, target_entity_id, project.id)

    if target_entity_type is AITargetEntityType.PROPOSAL:
        proposal = db.get(Opportunity, target_entity_id)
        if proposal is None:
            raise ai_error(404, "AI_CONTEXT_TARGET_NOT_FOUND")
        if not proposal.project_id:
            # Proposal intelligence can be prepared for provisional intake,
            # but it must not be presented as a project-scoped operation.
            return ResolvedAITarget(target_entity_type, target_entity_id, proposal.id)
        return ResolvedAITarget(target_entity_type, target_entity_id, proposal.project_id)

    if target_entity_type is AITargetEntityType.MASTER_CONTENT_ITEM:
        item = db.get(MasterContentItem, target_entity_id)
        if item is None:
            raise ai_error(404, "AI_CONTEXT_TARGET_NOT_FOUND")
        return ResolvedAITarget(target_entity_type, target_entity_id, None)

    case = db.get(AuthorityCase, target_entity_id)
    if case is None:
        raise ai_error(404, "AI_CONTEXT_TARGET_NOT_FOUND")
    if case.subject_type != "PROJECT" or not case.subject_id:
        raise ai_error(403, "AI_CONTEXT_SCOPE_MISMATCH")
    project = db.get(Project, case.subject_id)
    if project is None:
        raise ai_error(403, "AI_CONTEXT_SCOPE_MISMATCH")
    return ResolvedAITarget(target_entity_type, target_entity_id, project.id)


def authorize_ai_request(
    db: Session,
    principal: AuthenticatedPrincipal,
    *,
    purpose_value: str,
    execution_mode_value: str,
    target_entity_type_value: str,
    target_entity_id: str,
    synthetic_only: bool,
    real_data_allowed: bool,
    require_environment_synthetic: bool = True,
) -> tuple[AIAuthorizationContext, ResolvedAITarget, AIPurposePolicy]:
    purpose = parse_purpose(purpose_value)
    execution_mode = parse_execution_mode(execution_mode_value)
    try:
        target_entity_type = AITargetEntityType(target_entity_type_value)
    except (TypeError, ValueError) as exc:
        raise ai_error(403, "AI_CONTEXT_SCOPE_MISMATCH") from exc

    policy = policy_for(purpose)
    if execution_mode not in policy.allowed_execution_modes:
        raise ai_error(403, "AI_EXECUTION_MODE_NOT_SUPPORTED")
    if target_entity_type not in policy.allowed_target_entity_types:
        raise ai_error(403, "AI_CONTEXT_SCOPE_MISMATCH")
    if principal.role not in policy.allowed_roles:
        raise ai_error(403, "AI_PURPOSE_NOT_AUTHORIZED")
    if not all(_has_capability(principal.role, capability) for capability in policy.required_capabilities):
        raise ai_error(403, "AI_PURPOSE_NOT_AUTHORIZED")
    if require_environment_synthetic and (not synthetic_only or real_data_allowed):
        raise ai_error(403, "AI_REAL_CONTENT_NOT_AUTHORIZED")

    target = resolve_target(db, target_entity_type, target_entity_id)
    if target_entity_type is AITargetEntityType.PROPOSAL:
        proposal = db.get(Opportunity, target_entity_id)
        user = db.get(User, principal.user_id) if principal.user_id else None
        if user is None or not user.active or user.role != principal.role:
            raise ai_error(403, "PROPOSAL_SCOPE_NOT_PROVABLE")
        if principal.role not in OWNER_ROLES and user.office_id != proposal.office_id:
            raise ai_error(403, "PROPOSAL_SCOPE_NOT_PROVABLE")
        if principal.office_id and principal.role not in OWNER_ROLES and principal.office_id != proposal.office_id:
            raise ai_error(403, "PROPOSAL_SCOPE_NOT_PROVABLE")
    elif principal.role not in OWNER_ROLES:
        if not principal.user_id:
            raise ai_error(403, "PROJECT_SCOPE_NOT_PROVABLE")
        member = db.scalar(
            select(EngineeringProjectMember).where(
                EngineeringProjectMember.project_id == target.project_id,
                EngineeringProjectMember.actor_id == principal.user_id,
                EngineeringProjectMember.status == "ACTIVE",
            )
        )
        if member is None:
            raise ai_error(403, "PROJECT_SCOPE_NOT_PROVABLE")

    authorization = AIAuthorizationContext(
        principal_user_id=principal.user_id,
        principal_role=principal.role,
        principal_office_id=principal.office_id,
        auth_mode=principal.auth_mode,
        requested_purpose=purpose,
        execution_mode=execution_mode,
        target_entity_type=target_entity_type,
        target_entity_id=target_entity_id,
        resolved_project_id=target.project_id,
        required_capabilities=policy.required_capabilities,
        scope_decision="AUTHORIZED",
        decision_code="AI_CONTEXT_AUTHORIZED",
    )
    return authorization, target, policy
