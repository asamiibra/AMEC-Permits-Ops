"""Shared E2 runtime services used by synthetic E3/E4 workflows."""

from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit.service import audit
from ..models import Approval, AssistantCapabilityDefinition, CapabilityInvocationRecord, CommunicationApproval, CommunicationDelivery, CommunicationDraft, LineageEdge, RenderedArtifact, TemplateDefinition, TemplateVersion
from ..services.week45 import row, stable_hash
from .execution import PROTOTYPE_POLICY, require_human_role


ALLOWED_TEMPLATE_STATUSES = {"SYNTHETIC_STANDIN", "APPROVED_FOR_TEST", "APPROVED_FOR_PRODUCTION"}
DISABLED_TEMPLATE_STATUSES = {"SUPERSEDED", "DISABLED"}
COMMUNICATION_TYPES = {
    "RFQ_FOLLOWUP", "MISSING_DOCUMENT", "QUOTATION_RELEASE", "CLIENT_RESPONSE_FOLLOWUP",
    "REFERENCE_NUMBER", "CONTRACT", "INVOICE", "PAYMENT_FOLLOWUP", "APPROVAL_STATUS", "HANDOVER", "OTHER_CONFIGURED",
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def select_template(db: Session, template_version_id: str | None, artifact_type: str) -> TemplateVersion:
    version = db.get(TemplateVersion, template_version_id) if template_version_id else db.scalar(
        select(TemplateVersion).join(TemplateDefinition).where(
            TemplateDefinition.artifact_type == artifact_type,
            TemplateVersion.status.in_(ALLOWED_TEMPLATE_STATUSES),
        ).order_by(TemplateVersion.version.desc())
    )
    if not version:
        if template_version_id:
            raise HTTPException(404, "TEMPLATE_VERSION_NOT_FOUND")
        definition = TemplateDefinition(template_code=f"SYN-{artifact_type}-TEMPLATE", artifact_type=artifact_type,
                                         name=f"Synthetic {artifact_type.lower()} stand-in", language="EN",
                                         owner_role="ADMIN_PROJECT_COORDINATOR", status="SYNTHETIC_STANDIN")
        db.add(definition)
        db.flush()
        version = TemplateVersion(template_definition_id=definition.id, version="0.1", status="SYNTHETIC_STANDIN",
                                  content_hash=stable_hash({"template_code": definition.template_code, "version": "0.1"}))
        db.add(version)
        db.flush()
    definition = db.get(TemplateDefinition, version.template_definition_id)
    if definition and definition.artifact_type != artifact_type:
        raise HTTPException(409, "TEMPLATE_ARTIFACT_TYPE_MISMATCH")
    if version.status in DISABLED_TEMPLATE_STATUSES or version.status not in ALLOWED_TEMPLATE_STATUSES:
        raise HTTPException(409, "TEMPLATE_VERSION_NOT_ALLOWED")
    return version


def render_artifact(db: Session, *, artifact_type: str, context_type: str, context_id: str,
                    payload: dict[str, Any], source_revision_ids: list[str],
                    template_version_id: str | None, actor: str, correlation_id: str,
                    project_id: str | None = None, language: str = "EN") -> RenderedArtifact:
    PROTOTYPE_POLICY.assert_allowed("RENDER_SYNTHETIC_ARTIFACT", "TEST")
    template = select_template(db, template_version_id, artifact_type)
    render_contract = {
        "context_type": context_type,
        "context_id": context_id,
        "source_revision_ids": sorted(str(item) for item in source_revision_ids),
        "template_version_id": template.id,
        "template_content_hash": template.content_hash,
        "verified_or_canonical_fields": payload,
        "rendering_rules": {"renderer": "DETERMINISTIC_SYNTHETIC_TEXT", "artifact_type": artifact_type},
        "language": language,
    }
    input_hash = stable_hash(render_contract)
    content_hash = stable_hash({"render_input_hash": input_hash, "template_version_id": template.id, "payload": payload})
    artifact = RenderedArtifact(
        template_version_id=template.id, context_type=context_type, context_id=context_id,
        artifact_type=artifact_type, content_hash=content_hash,
        render_input_hash=input_hash, source_revision_ids=sorted(str(item) for item in source_revision_ids),
        rendered_values=payload, language=language, synthetic_only=True,
        storage_reference=f"synthetic://rendered/{artifact_type.lower()}/{content_hash}", status="RENDERED",
    )
    db.add(artifact)
    db.flush()
    audit(db, correlation_id=correlation_id, event_type="RENDER_COMPLETED", entity_type="RenderedArtifact", entity_id=artifact.id, actor_id=actor,
          after={"template_version_id": template.id, "render_input_hash": input_hash, "content_hash": content_hash, "status": "RENDERED"},
          metadata={"execution_authority": PROTOTYPE_POLICY.authority.value, "evidence_class": PROTOTYPE_POLICY.evidence_class.value})
    if project_id:
        db.add(LineageEdge(project_id=project_id, upstream_type=context_type, upstream_id=context_id, upstream_version_or_hash=input_hash,
                           downstream_type="RenderedArtifact", downstream_id=artifact.id, downstream_version_or_hash=content_hash,
                           dependency_kind="RENDERED_FROM_GOVERNED_INPUT", correlation_id=correlation_id))
    return artifact


def create_communication_draft(db: Session, *, communication_type: str, context_type: str, context_id: str,
                               subject: str, body: str, actor: str, correlation_id: str,
                               recipient_contact_id: str | None = None, template_version_id: str | None = None) -> CommunicationDraft:
    if communication_type not in COMMUNICATION_TYPES:
        raise HTTPException(422, "UNSUPPORTED_COMMUNICATION_TYPE")
    body_value = f"SYNTHETIC DRAFT — HUMAN_SEND — NOT CLIENT APPROVED.\n{body}"
    source_snapshot = {"context_type": context_type, "context_id": context_id, "subject": subject, "body_input": body, "synthetic_only": True}
    draft = CommunicationDraft(
        communication_type=communication_type, context_type=context_type, context_id=context_id,
        recipient_contact_id=recipient_contact_id, template_version_id=template_version_id,
        subject=subject, body=body_value, source_snapshot=source_snapshot,
        source_revision_ids=sorted(str(item) for item in source_snapshot.get("source_revision_ids", [])),
        body_hash=stable_hash(body_value),
        status="HUMAN_REVIEW", policy_state="HUMAN_SEND", created_by=actor,
    )
    db.add(draft)
    db.flush()
    db.add(CommunicationDelivery(communication_draft_id=draft.id, delivery_channel="EMAIL", delivery_status="NOT_SENT"))
    audit(db, correlation_id=correlation_id, event_type="COMMUNICATION_DRAFT_CREATED", entity_type="CommunicationDraft", entity_id=draft.id,
          actor_id=actor, after={"status": draft.status, "policy_state": draft.policy_state, "communication_type": communication_type},
          metadata={"external_send": False, "execution_authority": PROTOTYPE_POLICY.authority.value})
    return draft


def approve_communication_for_human_send(db: Session, draft: CommunicationDraft, *, actor: str, actor_role: str, correlation_id: str) -> CommunicationDraft:
    require_human_role(actor_role, {"COMMUNICATION_APPROVER", "ADMIN_PROJECT_COORDINATOR", "COMMERCIAL_APPROVER"})
    if draft.status not in {"HUMAN_REVIEW", "DRAFT"}:
        raise HTTPException(409, "COMMUNICATION_NOT_REVIEWABLE")
    approval = Approval(approval_type="COMMUNICATION_RELEASE", entity_type="CommunicationDraft", entity_id=draft.id,
                        status="APPROVED_FOR_HUMAN_SEND", decided_by=actor, decided_at=_now(), role_at_decision=actor_role,
                        reason="Synthetic prototype approval; human send remains required.", evidence_refs=[draft.body_hash] if draft.body_hash else [])
    db.add(approval)
    db.flush()
    db.add(CommunicationApproval(communication_draft_id=draft.id, approval_id=approval.id, approval_type="COMMUNICATION_RELEASE"))
    draft.status = "READY_FOR_HUMAN_SEND"
    draft.reviewed_by = actor
    draft.reviewed_at = _now()
    audit(db, correlation_id=correlation_id, event_type="COMMUNICATION_APPROVED_FOR_HUMAN_SEND", entity_type="CommunicationDraft", entity_id=draft.id,
          actor_id=actor, after={"status": draft.status, "approval_id": approval.id, "delivery": "NOT_SENT"})
    return draft


def mark_source_stale(db: Session, *, source_revision_id: str, reason: str, actor: str, correlation_id: str) -> dict[str, int]:
    rendered = db.scalars(select(RenderedArtifact)).all()
    drafts = db.scalars(select(CommunicationDraft)).all()
    artifact_count = 0
    draft_count = 0
    for artifact in rendered:
        if source_revision_id in (artifact.source_revision_ids or []):
            artifact.status = "STALE"
            artifact_count += 1
            audit(db, correlation_id=correlation_id, event_type="RENDER_ARTIFACT_STALE", entity_type="RenderedArtifact", entity_id=artifact.id,
                  actor_id=actor, after={"status": "STALE", "reason": reason, "source_revision_id": source_revision_id})
    for draft in drafts:
        if source_revision_id in (draft.source_revision_ids or []):
            draft.status = "STALE"
            draft.stale_reason = reason
            draft_count += 1
            audit(db, correlation_id=correlation_id, event_type="COMMUNICATION_DRAFT_STALE", entity_type="CommunicationDraft", entity_id=draft.id,
                  actor_id=actor, after={"status": "STALE", "reason": reason, "source_revision_id": source_revision_id})
    return {"rendered_artifacts_marked_stale": artifact_count, "communication_drafts_marked_stale": draft_count}


CANONICAL_ASSISTANTS = {"BD_ASSISTANT", "ADMIN_ASSISTANT", "ENGINEERING_REVIEW_ASSISTANT", "PROJECT_PERMIT_COORDINATION_ASSISTANT"}


def invoke_capability(db: Session, *, assistant_id: str, capability_id: str, context_id: str,
                      caller: str, caller_role: str, correlation_id: str,
                      source_revision_ids: list[str] | None = None) -> dict[str, Any]:
    if assistant_id not in CANONICAL_ASSISTANTS:
        raise HTTPException(403, "CANONICAL_ASSISTANT_SET_VIOLATION")
    capability = db.scalar(select(AssistantCapabilityDefinition).where(AssistantCapabilityDefinition.capability_id == capability_id,
                                                                         AssistantCapabilityDefinition.assistant_id == assistant_id))
    if not capability:
        raise HTTPException(404, "CAPABILITY_NOT_FOUND")
    if not capability.enabled or not capability.enabled_in_prototype or capability.capability_status != "ACTIVE":
        raise HTTPException(403, "CAPABILITY_DISABLED")
    if capability.stage2_disposition not in {"UNDECIDED_STAGE2", "IN", "IN_REDUCED_DEPTH"}:
        raise HTTPException(403, "CAPABILITY_NOT_AUTHORIZED_BY_STAGE2")
    if capability.execution_authority != PROTOTYPE_POLICY.authority.value:
        raise HTTPException(403, "EXECUTION_AUTHORITY_MISMATCH")
    source_ids = sorted(str(item) for item in (source_revision_ids or []))
    result = {"status": "INVOCATION_RECORDED", "assistant_id": assistant_id, "capability_id": capability_id,
              "context_id": context_id, "caller": caller, "caller_role": caller_role,
              "output_state": "CANDIDATE_OR_DRAFT", "external_action": False,
              "execution_authority": PROTOTYPE_POLICY.authority.value,
              "evidence_class": PROTOTYPE_POLICY.evidence_class.value,
              "policy_decision": "ALLOW_PROTOTYPE_ONLY", "result_type": "CANDIDATE_OR_DRAFT",
              "source_revision_ids": source_ids, "human_review_required": True,
              "deterministic_gate_result": "HUMAN_REVIEW_REQUIRED",
              "output_envelope": {"kind": "ASSISTANT_CAPABILITY_OUTPUT", "state": "CANDIDATE_OR_DRAFT", "synthetic_only": True}}
    db.add(CapabilityInvocationRecord(assistant_id=assistant_id, capability_id=capability_id, context_id=context_id,
                                      caller=caller, caller_role=caller_role, policy_decision="ALLOW_PROTOTYPE_ONLY",
                                      result_type="CANDIDATE_OR_DRAFT", output_envelope=result["output_envelope"],
                                      source_revision_ids=source_ids, evidence_refs=source_ids,
                                      human_review_required=True, deterministic_gate_result="HUMAN_REVIEW_REQUIRED"))
    audit(db, correlation_id=correlation_id, event_type="ASSISTANT_CAPABILITY_INVOKED", entity_type="AssistantCapabilityDefinition", entity_id=capability.id,
          actor_id=caller, after=result, metadata={"context_id": context_id, "caller_role": caller_role})
    return result
