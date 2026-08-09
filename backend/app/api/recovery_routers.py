"""Synthetic E2–E4 recovery runtime over the shared PermitOps substrate."""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..audit.service import audit
from ..db import get_db
from ..expansion.execution import PROTOTYPE_POLICY, policy_snapshot, require_human_role
from ..expansion.runtime import approve_communication_for_human_send, create_communication_draft, invoke_capability, mark_source_stale, render_artifact, select_template
from ..expansion.unified import CANONICAL_ASSISTANTS, CAPABILITY_MAP, accept_handoff, build_context_packet, build_my_work, create_handoff
from ..models import *
from ..services.week45 import stable_hash

router = APIRouter(prefix="/api")


def cid(request: Request) -> str:
    return getattr(request.state, "correlation_id", "recovery-api")


def row(item):
    if item is None:
        return None
    return jsonable_encoder({column.name: getattr(item, column.name) for column in item.__table__.columns})


def require(db: Session, model, item_id: str, detail: str):
    item = db.get(model, item_id)
    if not item:
        raise HTTPException(404, detail)
    return item


def actor(payload: dict, default: str = "synthetic-operator") -> tuple[str, str]:
    return str(payload.get("actor", default)), str(payload.get("actor_role", "ADMIN_PROJECT_COORDINATOR"))


def first_project(db: Session) -> Project:
    project = db.scalar(select(Project).order_by(Project.project_number))
    if not project:
        raise HTTPException(409, "SYNTHETIC_PROJECT_REQUIRED")
    return project


def first_application(db: Session, project_id: str) -> PermitApplication:
    app = db.scalar(select(PermitApplication).where(PermitApplication.project_id == project_id).order_by(PermitApplication.external_request_number))
    if not app:
        raise HTTPException(409, "SYNTHETIC_APPLICATION_REQUIRED")
    return app


def ensure_task(db: Session, *, project_id: str, task_type: str, title: str, owner_role: str, correlation_id: str, context_id: str):
    application = first_application(db, project_id)
    finding = db.scalar(select(Finding).where(Finding.project_id == project_id).order_by(Finding.captured_at))
    if not finding:
        return None
    task = WorkflowTask(project_id=project_id, application_id=application.id, finding_id=finding.id, task_type=task_type, title=title,
                        description=f"Synthetic recovery task for {context_id}; canonical context remains shared.", owner_role=owner_role,
                        owner_user_id=None, status="OPEN", priority="MEDIUM", correlation_id=correlation_id)
    db.add(task)
    db.flush()
    audit(db, correlation_id=correlation_id, event_type="WORKFLOW_TASK_CREATED", entity_type="WorkflowTask", entity_id=task.id,
          after={"task_type": task_type, "owner_role": owner_role, "context_id": context_id}, metadata={"synthetic": True})
    return task


@router.get("/execution-policy")
def execution_policy():
    return policy_snapshot()


@router.get("/templates")
def templates(db: Session = Depends(get_db)):
    return [{**row(item), "versions": [row(version) for version in db.scalars(select(TemplateVersion).where(TemplateVersion.template_definition_id == item.id).order_by(TemplateVersion.version)).all()]}
            for item in db.scalars(select(TemplateDefinition).order_by(TemplateDefinition.template_code)).all()]


@router.get("/templates/{template_id}")
def template_detail(template_id: str, db: Session = Depends(get_db)):
    item = require(db, TemplateDefinition, template_id, "TEMPLATE_NOT_FOUND")
    return {**row(item), "versions": [row(version) for version in db.scalars(select(TemplateVersion).where(TemplateVersion.template_definition_id == item.id).order_by(TemplateVersion.version)).all()]}


@router.get("/templates/{template_id}/versions")
def template_versions(template_id: str, db: Session = Depends(get_db)):
    require(db, TemplateDefinition, template_id, "TEMPLATE_NOT_FOUND")
    return [row(item) for item in db.scalars(select(TemplateVersion).where(TemplateVersion.template_definition_id == template_id).order_by(TemplateVersion.version)).all()]


@router.post("/templates/{template_id}/versions")
def create_template_version(template_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    definition = require(db, TemplateDefinition, template_id, "TEMPLATE_NOT_FOUND")
    actor_id, actor_role = actor(payload, "synthetic-template-maintainer")
    require_human_role(actor_role, {"SYSTEM_ADMIN", "PORTAL_MAINTAINER", "REQUIREMENT_STEWARD", "ADMIN_PROJECT_COORDINATOR"})
    status = payload.get("status", "SYNTHETIC_STANDIN")
    if status == "APPROVED_FOR_PRODUCTION":
        raise HTTPException(403, "PRODUCTION_TEMPLATE_APPROVAL_REQUIRED")
    version = TemplateVersion(template_definition_id=definition.id, version=str(payload["version"]), status=status,
                              content_hash=payload.get("content_hash") or stable_hash({"template_id": template_id, "version": payload["version"], "content": payload.get("content", "")} ),
                              source_document_version_id=payload.get("source_document_version_id"), supersedes_id=payload.get("supersedes_id"))
    db.add(version)
    db.flush()
    audit(db, correlation_id=cid(request), event_type="TEMPLATE_VERSION_CREATED", entity_type="TemplateVersion", entity_id=version.id,
          actor_id=actor_id, after={"template_id": template_id, "version": version.version, "status": version.status, "synthetic_only": True})
    db.commit()
    return row(version)


@router.post("/templates/{template_id}/versions/{version_id}/validate")
def validate_template_version(template_id: str, version_id: str, db: Session = Depends(get_db)):
    version = require(db, TemplateVersion, version_id, "TEMPLATE_VERSION_NOT_FOUND")
    if version.template_definition_id != template_id:
        raise HTTPException(409, "TEMPLATE_VERSION_DEFINITION_MISMATCH")
    definition = require(db, TemplateDefinition, template_id, "TEMPLATE_NOT_FOUND")
    return {"valid": bool(version.content_hash and version.version and definition.artifact_type), "validation_status": "PASS", "synthetic_only": True, "template": row(definition), "version": row(version)}


@router.post("/templates/{template_id}/versions/{version_id}/supersede")
def supersede_template_version(template_id: str, version_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    version = require(db, TemplateVersion, version_id, "TEMPLATE_VERSION_NOT_FOUND")
    if version.template_definition_id != template_id:
        raise HTTPException(409, "TEMPLATE_VERSION_DEFINITION_MISMATCH")
    actor_id, actor_role = actor(payload, "synthetic-template-maintainer")
    require_human_role(actor_role, {"SYSTEM_ADMIN", "PORTAL_MAINTAINER", "REQUIREMENT_STEWARD", "ADMIN_PROJECT_COORDINATOR"})
    version.status = "SUPERSEDED"
    audit(db, correlation_id=cid(request), event_type="TEMPLATE_VERSION_SUPERSEDED", entity_type="TemplateVersion", entity_id=version.id,
          actor_id=actor_id, after={"status": version.status, "synthetic_only": True})
    db.commit()
    return row(version)


@router.post("/render")
def render(payload: dict, request: Request, db: Session = Depends(get_db)):
    actor_id, _ = actor(payload, "synthetic-renderer")
    artifact = render_artifact(db, artifact_type=payload["artifact_type"], context_type=payload["context_type"], context_id=payload["context_id"],
                               payload=payload.get("verified_fields", payload.get("payload", {})), source_revision_ids=payload.get("source_revision_ids", []),
                               template_version_id=payload.get("template_version_id"), actor=actor_id, correlation_id=cid(request),
                               project_id=payload.get("project_id"), language=payload.get("language", "EN"))
    db.commit()
    return row(artifact)


@router.post("/render-requests")
def render_request(payload: dict, request: Request, db: Session = Depends(get_db)):
    return render(payload, request, db)


@router.get("/rendered-artifacts/{artifact_id}")
def rendered_artifact(artifact_id: str, db: Session = Depends(get_db)):
    return row(require(db, RenderedArtifact, artifact_id, "RENDERED_ARTIFACT_NOT_FOUND"))


@router.get("/rendered-artifacts/{artifact_id}/lineage")
def rendered_artifact_lineage(artifact_id: str, db: Session = Depends(get_db)):
    artifact = require(db, RenderedArtifact, artifact_id, "RENDERED_ARTIFACT_NOT_FOUND")
    return {"artifact": row(artifact), "lineage": [row(item) for item in db.scalars(select(LineageEdge).where(LineageEdge.downstream_type == "RenderedArtifact", LineageEdge.downstream_id == artifact.id)).all()]}


@router.post("/communication-drafts")
def communication_draft(payload: dict, request: Request, db: Session = Depends(get_db)):
    actor_id, _ = actor(payload, "synthetic-operator")
    draft = create_communication_draft(db, communication_type=payload["communication_type"], context_type=payload["context_type"], context_id=payload["context_id"],
                                       subject=payload["subject"], body=payload.get("body", ""), actor=actor_id, correlation_id=cid(request),
                                       recipient_contact_id=payload.get("recipient_contact_id"), template_version_id=payload.get("template_version_id"))
    db.commit()
    return row(draft)


@router.get("/communication-drafts")
def communication_drafts(db: Session = Depends(get_db)):
    return [row(item) for item in db.scalars(select(CommunicationDraft).order_by(CommunicationDraft.created_at.desc())).all()]


@router.get("/communication-drafts/{draft_id}")
def get_communication_draft(draft_id: str, db: Session = Depends(get_db)):
    draft = require(db, CommunicationDraft, draft_id, "COMMUNICATION_DRAFT_NOT_FOUND")
    return {"draft": row(draft), "delivery": [row(item) for item in db.scalars(select(CommunicationDelivery).where(CommunicationDelivery.communication_draft_id == draft.id)).all()],
            "approvals": [row(item) for item in db.scalars(select(CommunicationApproval).where(CommunicationApproval.communication_draft_id == draft.id)).all()]}


@router.get("/communication-drafts/{draft_id}/lineage")
def communication_lineage(draft_id: str, db: Session = Depends(get_db)):
    draft = require(db, CommunicationDraft, draft_id, "COMMUNICATION_DRAFT_NOT_FOUND")
    return {"draft": row(draft), "lineage": [row(item) for item in db.scalars(select(LineageEdge).where(LineageEdge.downstream_type == "CommunicationDraft", LineageEdge.downstream_id == draft.id)).all()]}


@router.post("/communication-drafts/{draft_id}/submit-review")
def submit_communication_review(draft_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    draft = require(db, CommunicationDraft, draft_id, "COMMUNICATION_DRAFT_NOT_FOUND")
    if draft.status not in {"DRAFT", "HUMAN_REVIEW"}:
        raise HTTPException(409, "COMMUNICATION_NOT_REVIEWABLE")
    draft.status = "HUMAN_REVIEW"
    audit(db, correlation_id=cid(request), event_type="COMMUNICATION_SUBMITTED_FOR_HUMAN_REVIEW", entity_type="CommunicationDraft", entity_id=draft.id, actor_id=payload.get("actor", "synthetic-operator"), after={"status": draft.status})
    db.commit()
    return row(draft)


@router.post("/communication-drafts/{draft_id}/approve-for-human-send")
def approve_communication(draft_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    draft = require(db, CommunicationDraft, draft_id, "COMMUNICATION_DRAFT_NOT_FOUND")
    actor_id, actor_role = actor(payload, "synthetic-communication-approver")
    approve_communication_for_human_send(db, draft, actor=actor_id, actor_role=actor_role, correlation_id=cid(request))
    db.commit()
    return row(draft)


@router.post("/invalidation/source")
def invalidate_source(payload: dict, request: Request, db: Session = Depends(get_db)):
    result = mark_source_stale(db, source_revision_id=str(payload["source_revision_id"]), reason=payload.get("reason", "Source revision changed"),
                               actor=payload.get("actor", "synthetic-operator"), correlation_id=cid(request))
    db.commit()
    return {**result, "status": "INVALIDATION_RECORDED", "synthetic_only": True}


@router.get("/assistant-capabilities")
def assistant_capabilities(db: Session = Depends(get_db)):
    return [row(item) for item in db.scalars(select(AssistantCapabilityDefinition).order_by(AssistantCapabilityDefinition.assistant_id, AssistantCapabilityDefinition.capability_id)).all()]


@router.get("/assistant-capabilities/{capability_id}")
def assistant_capability(capability_id: str, db: Session = Depends(get_db)):
    return row(require(db, AssistantCapabilityDefinition, capability_id, "CAPABILITY_NOT_FOUND"))


@router.post("/assistant-capabilities/{capability_id}/invoke")
def capability_invoke(capability_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    capability = db.scalar(select(AssistantCapabilityDefinition).where(AssistantCapabilityDefinition.capability_id == capability_id))
    if not capability:
        raise HTTPException(404, "CAPABILITY_NOT_FOUND")
    actor_id, actor_role = actor(payload, "synthetic-operator")
    result = invoke_capability(db, assistant_id=capability.assistant_id, capability_id=capability.capability_id, context_id=payload["context_id"],
                               caller=actor_id, caller_role=actor_role, correlation_id=cid(request), source_revision_ids=payload.get("source_revision_ids", []))
    db.commit()
    return result


@router.get("/assistant-capability-map")
def assistant_capability_map():
    return {"assistant_ids": list(CANONICAL_ASSISTANTS), "capabilities": CAPABILITY_MAP, "synthetic_only": True}


@router.get("/my-work")
def my_work(request: Request, assistant_id: str | None = None, role: str | None = None, db: Session = Depends(get_db)):
    result = build_my_work(db, assistant_id=assistant_id, role=role)
    audit(db, correlation_id=cid(request), event_type="ROLE_FILTER_APPLIED", entity_type="WorkflowTask", entity_id="WORK_QUEUE",
          actor_id=role or "DEMO_AS_OPERATOR", after={"assistant_id": assistant_id, "role": role, "item_count": len(result["items"])}, metadata={"synthetic_only": True, "self_escalation": False})
    db.commit()
    return result


@router.get("/my-work/next-actions")
def my_work_next_actions(request: Request, assistant_id: str | None = None, db: Session = Depends(get_db)):
    return {"items": build_my_work(db, assistant_id=assistant_id)["items"], "deterministic": True, "synthetic_only": True}


@router.get("/assistant-lenses/{assistant_id}/work")
def assistant_lens(assistant_id: str, request: Request, db: Session = Depends(get_db)):
    result = build_my_work(db, assistant_id=assistant_id)
    audit(db, correlation_id=cid(request), event_type="ROLE_FILTER_APPLIED", entity_type="WorkflowTask", entity_id="WORK_QUEUE",
          actor_id="DEMO_AS_OPERATOR", after={"assistant_id": assistant_id, "item_count": len(result["items"])}, metadata={"synthetic_only": True})
    db.commit()
    return result


@router.get("/assistant-context-packets/{task_id}")
def assistant_context_packet(task_id: str, assistant_id: str, request: Request, db: Session = Depends(get_db)):
    task = require(db, WorkflowTask, task_id, "WORKFLOW_TASK_NOT_FOUND")
    packet = build_context_packet(db, assistant_id=assistant_id, task=task)
    audit(db, correlation_id=cid(request), event_type="ASSISTANT_CONTEXT_ASSEMBLED", entity_type="WorkflowTask", entity_id=task.id,
          actor_id="DEMO_AS_OPERATOR", after={"assistant_id": assistant_id, "context_type": task.context_type, "context_id": task.context_id}, metadata={"synthetic_only": True})
    db.commit()
    return packet


@router.get("/role-context")
def role_context(mode: str = "SYNTHETIC", requested_role: str | None = None):
    synthetic = mode.upper() in {"SYNTHETIC", "DEV", "TEST"}
    if requested_role and not synthetic:
        raise HTTPException(403, "PRODUCTION_ROLE_SWITCH_REQUIRES_AUTHENTICATED_IDENTITY")
    return {"mode": "SYNTHETIC_DEMO" if synthetic else "PRODUCTION_LIKE", "demo_as": synthetic, "self_role_switch_allowed": synthetic, "human_rbac_required": not synthetic}


@router.post("/assistant-handoffs")
def handoff_create(payload: dict, request: Request, db: Session = Depends(get_db)):
    handoff = create_handoff(db, from_assistant_id=payload["from_assistant_id"], to_assistant_id=payload["to_assistant_id"],
                             context_type=payload["context_type"], context_id=payload["context_id"], reason=payload.get("reason", "Shared context handoff"),
                             actor=payload.get("actor", "synthetic-operator"), correlation_id=cid(request), project_id=payload.get("project_id"),
                             opportunity_id=payload.get("opportunity_id"), source_revision_ids=payload.get("source_revision_ids", []))
    db.commit()
    return row(handoff)


@router.get("/assistant-handoffs")
def handoffs(db: Session = Depends(get_db)):
    return [row(item) for item in db.scalars(select(AssistantHandoff).order_by(AssistantHandoff.created_at.desc())).all()]


@router.post("/assistant-handoffs/{handoff_id}/accept")
def handoff_accept(handoff_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    handoff = require(db, AssistantHandoff, handoff_id, "HANDOFF_NOT_FOUND")
    accept_handoff(db, handoff, actor=payload.get("actor", "synthetic-operator"), correlation_id=cid(request))
    db.commit()
    return row(handoff)


@router.get("/issues/unified")
def unified_issues(db: Session = Depends(get_db)):
    return build_my_work(db)["issues"]


@router.get("/communications")
def unified_communications(db: Session = Depends(get_db)):
    return build_my_work(db)["communications"]


@router.get("/opportunities")
def opportunities(db: Session = Depends(get_db)):
    return [row(item) for item in db.scalars(select(Opportunity).order_by(Opportunity.opportunity_reference)).all()]


@router.post("/opportunities")
def create_opportunity(payload: dict, request: Request, db: Session = Depends(get_db)):
    office = db.scalar(select(ConsultancyOffice).order_by(ConsultancyOffice.office_code))
    if not office:
        raise HTTPException(409, "OFFICE_REQUIRED")
    client = db.get(ClientAccount, payload.get("client_account_id")) if payload.get("client_account_id") else None
    if not client:
        client = ClientAccount(client_reference=payload.get("client_reference", f"SYN-CLIENT-{db.scalar(select(func.count(ClientAccount.id))) + 1:04d}"),
                               legal_name=payload.get("client_name", "Synthetic Client"), display_name=payload.get("client_name", "Synthetic Client"), client_type="COMPANY", data_classification="SYNTHETIC")
        db.add(client)
        db.flush()
    opportunity = Opportunity(office_id=office.id, client_account_id=client.id, opportunity_reference=payload.get("opportunity_reference", f"AMEC-SYN-OPP-{db.scalar(select(func.count(Opportunity.id))) + 1:04d}"),
                              title=payload.get("title", "Synthetic RFQ opportunity"), status="RECEIVED", source_type=payload.get("source_type", "RFQ_EMAIL"), current_owner_user_id=payload.get("owner_user_id"), stage2_capability_scope="UNDECIDED_STAGE2")
    db.add(opportunity)
    db.flush()
    audit(db, correlation_id=cid(request), event_type="OPPORTUNITY_CREATED", entity_type="Opportunity", entity_id=opportunity.id, actor_id=payload.get("actor", "synthetic-bd"), after=row(opportunity), metadata={"synthetic": True})
    db.commit()
    return row(opportunity)


@router.get("/opportunities/{opportunity_id}")
def opportunity_detail(opportunity_id: str, db: Session = Depends(get_db)):
    opportunity = require(db, Opportunity, opportunity_id, "OPPORTUNITY_NOT_FOUND")
    client = db.get(ClientAccount, opportunity.client_account_id) if opportunity.client_account_id else None
    return {"opportunity": row(opportunity), "client": row(client),
            "rfqs": [row(item) for item in db.scalars(select(RFQ).where(RFQ.opportunity_id == opportunity.id)).all()],
            "tenders": [row(item) for item in db.scalars(select(TenderDocument).where(TenderDocument.opportunity_id == opportunity.id)).all()],
            "quotations": [row(item) for item in db.scalars(select(Quotation).where(Quotation.opportunity_id == opportunity.id)).all()],
            "responses": [row(item) for item in db.scalars(select(ClientResponse).where(ClientResponse.opportunity_id == opportunity.id)).all()]}


@router.post("/opportunities/{opportunity_id}/sources")
def add_opportunity_source(opportunity_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    opportunity = require(db, Opportunity, opportunity_id, "OPPORTUNITY_NOT_FOUND")
    version = db.get(DocumentVersion, payload.get("document_version_id")) if payload.get("document_version_id") else db.scalar(select(DocumentVersion).order_by(DocumentVersion.ingested_at))
    if not version:
        raise HTTPException(422, "DOCUMENT_VERSION_REQUIRED")
    source_type = payload.get("source_type", "RFQ_EMAIL")
    if source_type == "TENDER_DOCUMENT":
        item = TenderDocument(opportunity_id=opportunity.id, document_version_id=version.id, document_role=payload.get("document_role", "TENDER"), status="RECEIVED")
    else:
        item = RFQ(opportunity_id=opportunity.id, source_document_version_id=version.id, sender_reference=payload.get("sender_reference", "SYNTHETIC"), source_reference=payload.get("source_reference", version.id), language=payload.get("language", "EN"), status="RECEIVED")
    db.add(item)
    opportunity.status = "RECEIVED"
    db.flush()
    audit(db, correlation_id=cid(request), event_type="RFQ_SOURCE_REGISTERED", entity_type=type(item).__name__, entity_id=item.id, actor_id=payload.get("actor", "synthetic-bd"), after={"document_version_id": version.id, "source_type": source_type})
    db.commit()
    return row(item)


@router.post("/opportunities/{opportunity_id}/intake/review")
def review_intake(opportunity_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    opportunity = require(db, Opportunity, opportunity_id, "OPPORTUNITY_NOT_FOUND")
    allowed = {"RECEIVED": {"IN_REVIEW"}, "IN_REVIEW": {"INFORMATION_REQUIRED", "READY_FOR_QUOTATION"}, "INFORMATION_REQUIRED": {"IN_REVIEW"}}
    target = payload.get("status", "IN_REVIEW")
    if target not in allowed.get(opportunity.status, set()):
        raise HTTPException(409, {"code": "INVALID_OPPORTUNITY_TRANSITION", "from": opportunity.status, "to": target})
    before = opportunity.status
    opportunity.status = target
    audit(db, correlation_id=cid(request), event_type="BD_SOURCE_REVIEWED", entity_type="Opportunity", entity_id=opportunity.id, actor_id=payload.get("actor", "synthetic-bd"), before={"status": before}, after={"status": target})
    db.commit()
    return row(opportunity)


def current_quotation(db: Session, opportunity: Opportunity) -> tuple[Quotation, QuotationRevision]:
    quotation = db.scalar(select(Quotation).where(Quotation.opportunity_id == opportunity.id).order_by(Quotation.created_at.desc()))
    if not quotation:
        raise HTTPException(409, "QUOTATION_NOT_STARTED")
    revision = db.get(QuotationRevision, quotation.current_revision_id) if quotation.current_revision_id else db.scalar(
        select(QuotationRevision).where(QuotationRevision.quotation_id == quotation.id).order_by(QuotationRevision.revision_number.desc()))
    if not revision:
        raise HTTPException(409, "QUOTATION_REVISION_REQUIRED")
    return quotation, revision


def approved_for(db: Session, entity_type: str, entity_id: str, approval_type: str):
    return db.scalar(select(Approval).where(Approval.entity_type == entity_type, Approval.entity_id == entity_id,
                                          Approval.approval_type == approval_type, Approval.status.in_(("APPROVED", "APPROVED_FOR_RELEASE", "APPROVED_FOR_HUMAN_SEND"))).order_by(Approval.decided_at.desc()))


@router.get("/opportunities/{opportunity_id}/quotation")
def opportunity_quotation(opportunity_id: str, db: Session = Depends(get_db)):
    opportunity = require(db, Opportunity, opportunity_id, "OPPORTUNITY_NOT_FOUND")
    quotation = db.scalar(select(Quotation).where(Quotation.opportunity_id == opportunity.id).order_by(Quotation.created_at.desc()))
    if not quotation:
        raise HTTPException(404, "QUOTATION_NOT_FOUND")
    revisions = db.scalars(select(QuotationRevision).where(QuotationRevision.quotation_id == quotation.id).order_by(QuotationRevision.revision_number)).all()
    return {"quotation": row(quotation), "revisions": [{**row(revision), "observations": [row(item) for item in db.scalars(select(QuotationFieldObservation).where(QuotationFieldObservation.quotation_revision_id == revision.id)).all()],
                                                           "approvals": [row(item) for item in db.scalars(select(QuotationApproval).where(QuotationApproval.quotation_revision_id == revision.id)).all()]} for revision in revisions]}


@router.post("/opportunities/{opportunity_id}/quotation/revisions")
def create_quotation_revision(opportunity_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    opportunity = require(db, Opportunity, opportunity_id, "OPPORTUNITY_NOT_FOUND")
    if opportunity.status not in {"READY_FOR_QUOTATION", "IN_REVIEW", "QUOTATION_IN_PROGRESS", "COMMERCIAL_REVIEW"}:
        raise HTTPException(409, "OPPORTUNITY_NOT_READY_FOR_QUOTATION")
    quotation = db.scalar(select(Quotation).where(Quotation.opportunity_id == opportunity.id).order_by(Quotation.created_at.desc()))
    if not quotation:
        client_id = opportunity.client_account_id
        quotation = Quotation(opportunity_id=opportunity.id, client_account_id=client_id,
                              quotation_reference=payload.get("quotation_reference", f"SYN-QTN-{db.scalar(select(func.count(Quotation.id))) + 1:04d}"), status="DRAFT")
        db.add(quotation)
        db.flush()
    previous = db.scalar(select(QuotationRevision).where(QuotationRevision.quotation_id == quotation.id).order_by(QuotationRevision.revision_number.desc()))
    revision = QuotationRevision(quotation_id=quotation.id, revision_number=(previous.revision_number + 1 if previous else 1),
                                 source_snapshot=payload.get("source_snapshot", {"synthetic": True, "source": "governed_opportunity"}),
                                 content_hash=stable_hash(payload.get("source_snapshot", {})), semantic_hash=stable_hash(payload.get("field_values", {})),
                                 supersedes_revision_id=previous.id if previous else None, status="DRAFT", created_by=payload.get("actor", "synthetic-bd"))
    db.add(revision)
    db.flush()
    quotation.current_revision_id = revision.id
    quotation.status = "DRAFT"
    opportunity.status = "QUOTATION_IN_PROGRESS"
    for code, value in payload.get("field_values", {}).items():
        db.add(QuotationFieldObservation(quotation_revision_id=revision.id, field_code=str(code), candidate_value=str(value), state="CANDIDATE", authority_mode="HUMAN_APPROVED"))
        if str(code) in {"PRICE", "PAYMENT_CONDITION", "INCLUSION", "EXCLUSION", "DURATION"}:
            db.add(CommercialTerm(quotation_revision_id=revision.id, term_type=str(code), value_text=str(value), status="PROPOSED"))
    db.add(LineageEdge(project_id=first_project(db).id, upstream_type="Opportunity", upstream_id=opportunity.id, upstream_version_or_hash=stable_hash(row(opportunity)),
                       downstream_type="QuotationRevision", downstream_id=revision.id, downstream_version_or_hash=revision.content_hash, dependency_kind="QUOTATION_REVISION_FROM_OPPORTUNITY", correlation_id=cid(request)))
    audit(db, correlation_id=cid(request), event_type="QUOTATION_REVISION_CREATED", entity_type="QuotationRevision", entity_id=revision.id, actor_id=payload.get("actor", "synthetic-bd"), after=row(revision), metadata={"synthetic": True})
    db.commit()
    return row(revision)


@router.post("/quotation-revisions/{revision_id}/extract-or-propose")
def extract_quotation_fields(revision_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    revision = require(db, QuotationRevision, revision_id, "QUOTATION_REVISION_NOT_FOUND")
    existing = {item.field_code: item for item in db.scalars(select(QuotationFieldObservation).where(QuotationFieldObservation.quotation_revision_id == revision.id)).all()}
    defaults = {"SCOPE": "Synthetic advisory and permit coordination scope", "PRICE": "SYNTHETIC-TO-BE-VERIFIED", "CURRENCY": "QAR", "PAYMENT_TERMS": "SYNTHETIC-TO-BE-VERIFIED", "VALIDITY": "SYNTHETIC-TO-BE-VERIFIED"}
    fields = {**defaults, **payload.get("fields", {})}
    for code, value in fields.items():
        item = existing.get(code)
        if not item:
            item = QuotationFieldObservation(quotation_revision_id=revision.id, field_code=code)
            db.add(item)
        item.candidate_value = str(value) if value is not None else None
        item.proposed_offer_value = None
        item.state = "CANDIDATE"
        item.authority_mode = "HUMAN_APPROVED"
    revision.status = "EXTRACTED_CANDIDATES"
    audit(db, correlation_id=cid(request), event_type="QUOTATION_FIELDS_EXTRACTED", entity_type="QuotationRevision", entity_id=revision.id, actor_id=payload.get("actor", "synthetic-bd"), after={"field_count": len(fields), "state": "CANDIDATE"})
    db.commit()
    return {"revision": row(revision), "observations": [row(item) for item in db.scalars(select(QuotationFieldObservation).where(QuotationFieldObservation.quotation_revision_id == revision.id)).all()]}


@router.post("/quotation-revisions/{revision_id}/verify-field")
def verify_quotation_field(revision_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    revision = require(db, QuotationRevision, revision_id, "QUOTATION_REVISION_NOT_FOUND")
    actor_id, actor_role = actor(payload, "synthetic-data-verifier")
    require_human_role(actor_role, {"DATA_VERIFIER", "BD_USER", "ADMIN_PROJECT_COORDINATOR", "COMMERCIAL_APPROVER"})
    field_code = payload.get("field_code")
    item = db.scalar(select(QuotationFieldObservation).where(QuotationFieldObservation.quotation_revision_id == revision.id, QuotationFieldObservation.field_code == field_code))
    if not item:
        raise HTTPException(404, "QUOTATION_FIELD_NOT_FOUND")
    item.verified_value = str(payload.get("verified_value", item.candidate_value)) if payload.get("verified_value", item.candidate_value) is not None else None
    item.state = "VERIFIED"
    item.authority_mode = "HUMAN_VERIFIED"
    audit(db, correlation_id=cid(request), event_type="QUOTATION_FIELD_VERIFIED", entity_type="QuotationFieldObservation", entity_id=item.id, actor_id=actor_id, after={"field_code": field_code, "state": item.state})
    db.commit()
    return row(item)


@router.post("/quotation-revisions/{revision_id}/submit-commercial-review")
def submit_commercial_review(revision_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    revision = require(db, QuotationRevision, revision_id, "QUOTATION_REVISION_NOT_FOUND")
    observations = db.scalars(select(QuotationFieldObservation).where(QuotationFieldObservation.quotation_revision_id == revision.id)).all()
    if not observations or any(item.state not in {"VERIFIED", "APPROVED"} for item in observations if item.material):
        raise HTTPException(409, "MATERIAL_QUOTATION_FIELDS_REQUIRE_VERIFICATION")
    revision.status = "IN_COMMERCIAL_REVIEW"
    quotation = db.get(Quotation, revision.quotation_id)
    opportunity = db.get(Opportunity, quotation.opportunity_id)
    opportunity.status = "COMMERCIAL_REVIEW"
    audit(db, correlation_id=cid(request), event_type="QUOTATION_SUBMITTED_FOR_COMMERCIAL_REVIEW", entity_type="QuotationRevision", entity_id=revision.id, actor_id=payload.get("actor", "synthetic-bd"), after={"status": revision.status})
    db.commit()
    return row(revision)


@router.post("/quotation-revisions/{revision_id}/commercial-approval")
def commercial_approval(revision_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    revision = require(db, QuotationRevision, revision_id, "QUOTATION_REVISION_NOT_FOUND")
    actor_id, actor_role = actor(payload, "synthetic-commercial-approver")
    require_human_role(actor_role, {"COMMERCIAL_APPROVER", "OWNER_SPONSOR", "PROCESS_CHAMPION"})
    if revision.status != "IN_COMMERCIAL_REVIEW":
        raise HTTPException(409, "QUOTATION_NOT_IN_COMMERCIAL_REVIEW")
    observations = db.scalars(select(QuotationFieldObservation).where(QuotationFieldObservation.quotation_revision_id == revision.id)).all()
    overrides = payload.get("approved_offer_values", {})
    for item in observations:
        item.approved_offer_value = str(overrides.get(item.field_code, item.verified_value)) if overrides.get(item.field_code, item.verified_value) is not None else None
        item.state = "APPROVED"
        item.authority_mode = "HUMAN_APPROVED"
    approval = Approval(approval_type="COMMERCIAL_QUOTATION_RELEASE", entity_type="QuotationRevision", entity_id=revision.id, status="APPROVED_FOR_RELEASE", decided_by=actor_id, decided_at=datetime.now(timezone.utc), role_at_decision=actor_role, reason=payload.get("reason", "Synthetic human commercial approval"), evidence_refs=payload.get("evidence_refs", []))
    db.add(approval)
    db.flush()
    db.add(QuotationApproval(quotation_revision_id=revision.id, approval_id=approval.id))
    revision.status = "APPROVED_FOR_RELEASE"
    db.commit()
    return {"revision": row(revision), "approval": row(approval)}


@router.post("/quotation-revisions/{revision_id}/return-for-change")
def return_quotation_for_change(revision_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    revision = require(db, QuotationRevision, revision_id, "QUOTATION_REVISION_NOT_FOUND")
    revision.status = "RETURNED_FOR_CHANGE"
    audit(db, correlation_id=cid(request), event_type="QUOTATION_RETURNED_FOR_CHANGE", entity_type="QuotationRevision", entity_id=revision.id, actor_id=payload.get("actor", "synthetic-commercial-approver"), after={"status": revision.status, "reason": payload.get("reason", "")})
    db.commit()
    return row(revision)


@router.post("/quotation-revisions/{revision_id}/render")
def render_quotation_revision(revision_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    revision = require(db, QuotationRevision, revision_id, "QUOTATION_REVISION_NOT_FOUND")
    if revision.status not in {"APPROVED_FOR_RELEASE", "RENDERED", "RELEASED"}:
        raise HTTPException(409, "QUOTATION_NOT_READY_TO_RENDER")
    values = {item.field_code: item.approved_offer_value for item in db.scalars(select(QuotationFieldObservation).where(QuotationFieldObservation.quotation_revision_id == revision.id)).all()}
    quotation = db.get(Quotation, revision.quotation_id)
    artifact = render_artifact(db, artifact_type="QUOTATION", context_type="QUOTATION_REVISION", context_id=revision.id, payload=values, source_revision_ids=[revision.id], template_version_id=payload.get("template_version_id"), actor=payload.get("actor", "synthetic-renderer"), correlation_id=cid(request), project_id=first_project(db).id)
    revision.rendered_artifact_id = artifact.id
    revision.template_version_id = artifact.template_version_id
    revision.render_input_hash = artifact.render_input_hash
    revision.content_hash = artifact.content_hash
    revision.status = "RENDERED"
    db.commit()
    return {"revision": row(revision), "artifact": row(artifact)}


@router.post("/quotation-revisions/{revision_id}/release")
def release_quotation(revision_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    revision = require(db, QuotationRevision, revision_id, "QUOTATION_REVISION_NOT_FOUND")
    if revision.status == "RELEASED":
        raise HTTPException(409, "RELEASED_QUOTATION_IS_IMMUTABLE")
    approval = approved_for(db, "QuotationRevision", revision.id, "COMMERCIAL_QUOTATION_RELEASE")
    artifact = db.get(RenderedArtifact, revision.rendered_artifact_id) if revision.rendered_artifact_id else None
    if revision.status != "RENDERED" or not approval or not artifact or artifact.status != "RENDERED":
        raise HTTPException(409, "QUOTATION_RELEASE_PREREQUISITES_MISSING")
    quotation = db.get(Quotation, revision.quotation_id)
    opportunity = db.get(Opportunity, quotation.opportunity_id)
    release = db.scalar(select(QuotationRelease).where(QuotationRelease.quotation_revision_id == revision.id))
    if not release:
        release = QuotationRelease(quotation_revision_id=revision.id, rendered_artifact_id=artifact.id, approval_id=approval.id, released_by=payload.get("actor", "synthetic-bd"), release_channel_intent="HUMAN_SEND")
        db.add(release)
    revision.status = "RELEASED"
    quotation.status = "RELEASED_TO_CLIENT"
    opportunity.status = "CLIENT_RESPONSE_PENDING"
    draft = create_communication_draft(db, communication_type="QUOTATION_RELEASE", context_type="QUOTATION_REVISION", context_id=revision.id, subject=f"Quotation {quotation.quotation_reference} — synthetic release draft", body="Quotation release is prepared for human review and manual send.", actor=payload.get("actor", "synthetic-bd"), correlation_id=cid(request))
    db.commit()
    return {"release": row(release), "draft": row(draft), "status": opportunity.status}


@router.post("/opportunities/{opportunity_id}/client-response")
def record_client_response(opportunity_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    opportunity = require(db, Opportunity, opportunity_id, "OPPORTUNITY_NOT_FOUND")
    quotation, revision = current_quotation(db, opportunity)
    if revision.status != "RELEASED":
        raise HTTPException(409, "RELEASED_QUOTATION_REQUIRED")
    response_type = payload.get("response_type", "PENDING")
    if response_type not in {"ACCEPTED", "REJECTED", "REQUESTED_CHANGE", "NO_RESPONSE", "EXPIRED", "OTHER_REVIEW_REQUIRED", "CLARIFICATION_REQUESTED", "PENDING"}:
        raise HTTPException(422, "INVALID_CLIENT_RESPONSE")
    evidence = EvidenceArtifact(evidence_type="CLIENT_RESPONSE", source_reference=payload.get("evidence_reference", "synthetic://client-response"), content_hash=stable_hash(payload), synthetic_only=True, label="SYNTHETIC / NOT CLIENT APPROVED")
    db.add(evidence)
    db.flush()
    response = ClientResponse(opportunity_id=opportunity.id, quotation_revision_id=revision.id, response_type=response_type, evidence_artifact_id=evidence.id, recorded_by=payload.get("actor", "synthetic-bd"), notes=payload.get("notes"))
    db.add(response)
    db.flush()
    opportunity.status = {"ACCEPTED": "ACCEPTED", "REJECTED": "REJECTED", "REQUESTED_CHANGE": "INFORMATION_REQUIRED", "CLARIFICATION_REQUESTED": "INFORMATION_REQUIRED", "NO_RESPONSE": "CLIENT_RESPONSE_PENDING", "EXPIRED": "EXPIRED", "OTHER_REVIEW_REQUIRED": "INFORMATION_REQUIRED", "PENDING": "CLIENT_RESPONSE_PENDING"}[response_type]
    audit(db, correlation_id=cid(request), event_type="CLIENT_RESPONSE_RECORDED", entity_type="ClientResponse", entity_id=response.id, actor_id=response.recorded_by, after={"response_type": response_type, "opportunity_status": opportunity.status}, metadata={"synthetic": True})
    db.commit()
    return row(response)


@router.get("/opportunities/{opportunity_id}/contract-transition-readiness")
def contract_transition_readiness(opportunity_id: str, db: Session = Depends(get_db)):
    opportunity = require(db, Opportunity, opportunity_id, "OPPORTUNITY_NOT_FOUND")
    quotation = db.scalar(select(Quotation).where(Quotation.opportunity_id == opportunity.id).order_by(Quotation.created_at.desc()))
    blockers = []
    revision = db.get(QuotationRevision, quotation.current_revision_id) if quotation and quotation.current_revision_id else None
    if not revision or revision.status != "RELEASED": blockers.append("RELEASED_QUOTATION_REQUIRED")
    if revision and not approved_for(db, "QuotationRevision", revision.id, "COMMERCIAL_QUOTATION_RELEASE"): blockers.append("COMMERCIAL_APPROVAL_REQUIRED")
    if revision and not revision.rendered_artifact_id: blockers.append("RENDERED_QUOTATION_REQUIRED")
    response = db.scalar(select(ClientResponse).where(ClientResponse.opportunity_id == opportunity.id, ClientResponse.quotation_revision_id == revision.id).order_by(ClientResponse.recorded_at.desc())) if revision else None
    if not response or response.response_type != "ACCEPTED": blockers.append("CLIENT_ACCEPTANCE_REQUIRED")
    blockers.extend(item.control_code for item in db.scalars(select(SystemBlock).where(SystemBlock.context_type == "OPPORTUNITY", SystemBlock.context_id == opportunity.id, SystemBlock.blocking == True)).all())
    return {"opportunity_id": opportunity.id, "state": "READY_FOR_CONTRACT" if not blockers else "BLOCKED", "blockers": sorted(set(blockers)), "quotation_revision_id": revision.id if revision else None}


@router.post("/opportunities/{opportunity_id}/contracts")
def create_contract(opportunity_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    opportunity = require(db, Opportunity, opportunity_id, "OPPORTUNITY_NOT_FOUND")
    readiness = contract_transition_readiness(opportunity_id, db)
    if readiness["state"] != "READY_FOR_CONTRACT":
        raise HTTPException(409, {"code": "CONTRACT_TRANSITION_BLOCKED", "blockers": readiness["blockers"]})
    quotation, quotation_revision = current_quotation(db, opportunity)
    contract = Contract(client_account_id=opportunity.client_account_id, quotation_id=quotation.id, contract_reference=payload.get("contract_reference", f"SYN-CTR-{db.scalar(select(func.count(Contract.id))) + 1:04d}"), status="DRAFT")
    db.add(contract)
    db.flush()
    terms_snapshot = {item.term_type: {"source": item.value_text, "approved": None} for item in db.scalars(select(CommercialTerm).where(CommercialTerm.quotation_revision_id == quotation_revision.id)).all()}
    revision = ContractRevision(contract_id=contract.id, revision_number=1, controlling_quotation_revision_id=quotation_revision.id, status="DRAFT", commercial_terms_snapshot=terms_snapshot, content_hash=stable_hash({"quotation_revision_id": quotation_revision.id, "terms": terms_snapshot}))
    db.add(revision)
    db.flush()
    contract.current_revision_id = revision.id
    db.add(ContractMilestone(contract_id=contract.id, contract_revision_id=revision.id, milestone_reference="SYN-M1", title="Synthetic permit package milestone", payment_condition="Tracking only", amount_value="SYNTHETIC", status="PLANNED"))
    opportunity.status = "CONTRACT_IN_PROGRESS"
    db.add(LineageEdge(project_id=first_project(db).id, upstream_type="QuotationRevision", upstream_id=quotation_revision.id, upstream_version_or_hash=quotation_revision.content_hash, downstream_type="ContractRevision", downstream_id=revision.id, downstream_version_or_hash="DRAFT", dependency_kind="CONTRACT_FROM_ACCEPTED_QUOTATION", correlation_id=cid(request)))
    audit(db, correlation_id=cid(request), event_type="CONTRACT_CREATED", entity_type="Contract", entity_id=contract.id, actor_id=payload.get("actor", "synthetic-admin"), after={"contract_revision_id": revision.id, "status": contract.status})
    db.commit()
    return {"contract": row(contract), "revision": row(revision)}


@router.get("/contracts/{contract_id}")
def contract_detail(contract_id: str, db: Session = Depends(get_db)):
    contract = require(db, Contract, contract_id, "CONTRACT_NOT_FOUND")
    revision = db.get(ContractRevision, contract.current_revision_id) if contract.current_revision_id else None
    return {"contract": row(contract), "revision": row(revision), "milestones": [row(item) for item in db.scalars(select(ContractMilestone).where(ContractMilestone.contract_id == contract.id)).all()], "approvals": [row(item) for item in db.scalars(select(ContractApproval).join(ContractRevision).where(ContractRevision.contract_id == contract.id)).all()], "execution_evidence": [row(item) for item in db.scalars(select(ContractExecutionEvidence).join(ContractRevision).where(ContractRevision.contract_id == contract.id)).all()]}


@router.post("/contracts/{contract_id}/revisions")
def create_contract_revision(contract_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    contract = require(db, Contract, contract_id, "CONTRACT_NOT_FOUND")
    previous = db.scalar(select(ContractRevision).where(ContractRevision.contract_id == contract.id).order_by(ContractRevision.revision_number.desc()))
    quotation_revision = db.get(QuotationRevision, payload.get("controlling_quotation_revision_id")) if payload.get("controlling_quotation_revision_id") else db.get(ContractRevision, contract.current_revision_id).controlling_quotation_revision_id
    controlling_id = quotation_revision.id if isinstance(quotation_revision, QuotationRevision) else quotation_revision
    terms_snapshot = {item.term_type: {"source": item.value_text, "approved": None} for item in db.scalars(select(CommercialTerm).where(CommercialTerm.quotation_revision_id == controlling_id)).all()}
    revision = ContractRevision(contract_id=contract.id, revision_number=previous.revision_number + 1, controlling_quotation_revision_id=controlling_id, supersedes_revision_id=previous.id, status="DRAFT", commercial_terms_snapshot=terms_snapshot, content_hash=stable_hash({"quotation_revision_id": controlling_id, "terms": terms_snapshot}))
    db.add(revision)
    db.flush()
    contract.current_revision_id = revision.id
    contract.status = "DRAFT"
    audit(db, correlation_id=cid(request), event_type="CONTRACT_REVISION_CREATED", entity_type="ContractRevision", entity_id=revision.id, actor_id=payload.get("actor", "synthetic-admin"), after=row(revision))
    db.commit()
    return row(revision)


@router.post("/contract-revisions/{revision_id}/render")
def render_contract_revision(revision_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    revision = require(db, ContractRevision, revision_id, "CONTRACT_REVISION_NOT_FOUND")
    if revision.status in {"APPROVED", "EXECUTED_EVIDENCE_RECORDED"}:
        raise HTTPException(409, "APPROVED_CONTRACT_REVISION_IS_IMMUTABLE")
    artifact = render_artifact(db, artifact_type="CONTRACT", context_type="CONTRACT_REVISION", context_id=revision.id, payload=payload.get("fields", {"contract_reference": db.get(Contract, revision.contract_id).contract_reference}), source_revision_ids=[revision.controlling_quotation_revision_id, revision.id], template_version_id=payload.get("template_version_id"), actor=payload.get("actor", "synthetic-renderer"), correlation_id=cid(request), project_id=first_project(db).id)
    revision.status = "RENDERED"
    revision.rendered_artifact_id = artifact.id
    revision.template_version_id = artifact.template_version_id
    revision.render_input_hash = artifact.render_input_hash
    revision.content_hash = artifact.content_hash
    db.commit()
    return {"revision": row(revision), "artifact": row(artifact)}


@router.post("/contract-revisions/{revision_id}/submit-review")
def submit_contract_review(revision_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    revision = require(db, ContractRevision, revision_id, "CONTRACT_REVISION_NOT_FOUND")
    revision.status = "IN_REVIEW"
    audit(db, correlation_id=cid(request), event_type="CONTRACT_SUBMITTED_FOR_REVIEW", entity_type="ContractRevision", entity_id=revision.id, actor_id=payload.get("actor", "synthetic-admin"), after={"status": revision.status})
    db.commit()
    return row(revision)


@router.post("/contract-revisions/{revision_id}/approval")
def approve_contract_revision(revision_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    revision = require(db, ContractRevision, revision_id, "CONTRACT_REVISION_NOT_FOUND")
    actor_id, actor_role = actor(payload, "synthetic-contract-approver")
    require_human_role(actor_role, {"CONTRACT_APPROVER", "OWNER_SPONSOR", "PROCESS_CHAMPION"})
    if revision.status not in {"IN_REVIEW", "RENDERED"}:
        raise HTTPException(409, "CONTRACT_NOT_REVIEWABLE")
    approval = Approval(approval_type="CONTRACT_APPROVAL", entity_type="ContractRevision", entity_id=revision.id, status="APPROVED", decided_by=actor_id, decided_at=datetime.now(timezone.utc), role_at_decision=actor_role, reason="Synthetic human contract approval", evidence_refs=payload.get("evidence_refs", []))
    db.add(approval)
    db.flush()
    db.add(ContractApproval(contract_revision_id=revision.id, approval_id=approval.id))
    revision.status = "APPROVED"
    db.get(Contract, revision.contract_id).status = "APPROVED"
    db.commit()
    return {"revision": row(revision), "approval": row(approval)}


@router.post("/contract-revisions/{revision_id}/execution-evidence")
def record_contract_execution_evidence(revision_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    revision = require(db, ContractRevision, revision_id, "CONTRACT_REVISION_NOT_FOUND")
    if not approved_for(db, "ContractRevision", revision.id, "CONTRACT_APPROVAL"):
        raise HTTPException(409, "CONTRACT_APPROVAL_REQUIRED")
    actor_id, actor_role = actor(payload, "synthetic-contract-approver")
    require_human_role(actor_role, {"CONTRACT_APPROVER", "OWNER_SPONSOR", "PROCESS_CHAMPION"})
    evidence = EvidenceArtifact(evidence_type="CONTRACT_EXECUTION", source_reference=payload.get("evidence_reference", "synthetic://contract-execution"), content_hash=stable_hash(payload), synthetic_only=True, label="SYNTHETIC / NOT EXECUTED IN PRODUCTION")
    db.add(evidence)
    db.flush()
    record = ContractExecutionEvidence(contract_revision_id=revision.id, evidence_artifact_id=evidence.id, execution_status="EXECUTED_EVIDENCE_RECORDED", recorded_by=actor_id, notes=payload.get("notes"))
    db.add(record)
    db.flush()
    contract = db.get(Contract, revision.contract_id)
    contract.status = "EXECUTED_EVIDENCE_RECORDED"
    audit(db, correlation_id=cid(request), event_type="CONTRACT_EXECUTION_EVIDENCE_RECORDED", entity_type="ContractExecutionEvidence", entity_id=record.id, actor_id=actor_id, after={"status": record.execution_status, "external_execution": False})
    db.commit()
    return row(record)


@router.get("/contracts/{contract_id}/checklist")
def contract_checklist(contract_id: str, db: Session = Depends(get_db)):
    require(db, Contract, contract_id, "CONTRACT_NOT_FOUND")
    return [row(item) for item in db.scalars(select(ChecklistItem).where(ChecklistItem.context_type == "CONTRACT", ChecklistItem.context_id == contract_id).order_by(ChecklistItem.requirement_code)).all()]


@router.post("/contracts/{contract_id}/checklist/evaluate")
def evaluate_contract_checklist(contract_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    contract = require(db, Contract, contract_id, "CONTRACT_NOT_FOUND")
    items = db.scalars(select(ChecklistItem).where(ChecklistItem.context_type == "CONTRACT", ChecklistItem.context_id == contract.id)).all()
    if not items:
        item = ChecklistItem(context_type="CONTRACT", context_id=contract.id, requirement_code="SYN.CONTRACT.SUPPORTING_DOCUMENT", title="Synthetic contract supporting document", required_condition="Required before project handover", required_document_type="OTHER", owner_role="ADMIN_PROJECT_COORDINATOR", blocking=True)
        db.add(item)
        db.flush()
        items = [item]
    supplied = payload.get("document_version_id")
    for item in items:
        if supplied:
            item.current_document_version_id = supplied
            validity = db.scalar(select(DocumentValidity).where(DocumentValidity.document_version_id == supplied))
            if not validity:
                validity = DocumentValidity(document_version_id=supplied, validity_status="VALID", rule_version="SYNTHETIC-1")
                db.add(validity)
            item.validity_status = validity.validity_status
            item.status = "PASS" if item.applicability != "NOT_APPLICABLE" and validity.validity_status == "VALID" else "OPEN"
        else:
            item.status = "OPEN"
            item.validity_status = "MISSING"
    blocking = [item for item in items if item.blocking and item.status != "PASS" and item.applicability != "NOT_APPLICABLE"]
    for old in db.scalars(select(SystemBlock).where(SystemBlock.context_type == "CONTRACT", SystemBlock.context_id == contract.id, SystemBlock.control_code == "CHECKLIST_MISSING")).all():
        old.blocking = False
        old.resolved_at = datetime.now(timezone.utc)
    if blocking:
        block = SystemBlock(context_type="CONTRACT", context_id=contract.id, control_code="CHECKLIST_MISSING", blocking=True, reason="Required contract checklist evidence is missing or invalid.", evidence=[], owner_role="ADMIN_PROJECT_COORDINATOR", required_action="Provide and validate the required document.", resolution_condition="All blocking checklist items are PASS")
        db.add(block)
        ensure_task(db, project_id=first_project(db).id, task_type="MISSING_CONTRACT_DOCUMENT", title="Resolve contract checklist blocker", owner_role="ADMIN_PROJECT_COORDINATOR", correlation_id=cid(request), context_id=contract.id)
    audit(db, correlation_id=cid(request), event_type="CONTRACT_CHECKLIST_EVALUATED", entity_type="Contract", entity_id=contract.id, actor_id=payload.get("actor", "synthetic-admin"), after={"blocking_items": len(blocking)})
    db.commit()
    return {"items": [row(item) for item in items], "state": "BLOCKED" if blocking else "PASS", "blocking_item_ids": [item.id for item in blocking]}


@router.post("/checklist-items/{item_id}/document-request")
def request_checklist_document(item_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    item = require(db, ChecklistItem, item_id, "CHECKLIST_ITEM_NOT_FOUND")
    contract = db.get(Contract, item.context_id) if item.context_type == "CONTRACT" else None
    client_id = contract.client_account_id if contract else payload.get("client_account_id")
    if not client_id:
        raise HTTPException(422, "CLIENT_ACCOUNT_REQUIRED")
    contact = db.scalar(select(ClientContact).where(ClientContact.client_account_id == client_id).order_by(ClientContact.created_at))
    request_record = DocumentRequest(checklist_item_id=item.id, client_account_id=client_id, requested_from_contact_id=contact.id if contact else None, status="OPEN")
    db.add(request_record)
    db.flush()
    draft = create_communication_draft(db, communication_type="MISSING_DOCUMENT", context_type="DOCUMENT_REQUEST", context_id=request_record.id, subject=payload.get("subject", "Synthetic supporting document request"), body=payload.get("body", "Please provide the required document for human review."), actor=payload.get("actor", "synthetic-admin"), correlation_id=cid(request), recipient_contact_id=contact.id if contact else None)
    request_record.communication_draft_id = draft.id
    ensure_task(db, project_id=first_project(db).id, task_type="DOCUMENT_REQUEST_FOLLOWUP", title="Follow up on requested document", owner_role=item.owner_role, correlation_id=cid(request), context_id=request_record.id)
    db.commit()
    return {"request": row(request_record), "draft": row(draft)}


@router.get("/opportunities/{opportunity_id}/system-blocks")
def opportunity_system_blocks(opportunity_id: str, db: Session = Depends(get_db)):
    require(db, Opportunity, opportunity_id, "OPPORTUNITY_NOT_FOUND")
    return [row(item) for item in db.scalars(select(SystemBlock).where(SystemBlock.context_type == "OPPORTUNITY", SystemBlock.context_id == opportunity_id).order_by(SystemBlock.created_at.desc())).all()]


@router.post("/opportunities/{opportunity_id}/admin-comments")
def create_admin_comment(opportunity_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    opportunity = require(db, Opportunity, opportunity_id, "OPPORTUNITY_NOT_FOUND")
    project = first_project(db)
    comment = AdminDocumentComment(project_id=payload.get("project_id", project.id), comment_number=str(payload.get("comment_number", "ADMIN-001")), source_document_version_id=payload.get("source_document_version_id"), reviewed_artifact_id=payload.get("reviewed_artifact_id"), text=payload["text"], severity=payload.get("severity", "MEDIUM"), blocking=bool(payload.get("blocking", False)), owner_role=payload.get("owner_role", "ADMIN_PROJECT_COORDINATOR"))
    db.add(comment)
    db.flush()
    if comment.blocking:
        db.add(SystemBlock(context_type="OPPORTUNITY", context_id=opportunity.id, control_code="ADMIN_COMMENT_BLOCKING", blocking=True, reason=comment.text, evidence=[], owner_role=comment.owner_role, required_action="Resolve the administrative comment.", resolution_condition="Comment status is RESOLVED with evidence"))
    audit(db, correlation_id=cid(request), event_type="ADMIN_COMMENT_CREATED", entity_type="AdminDocumentComment", entity_id=comment.id, actor_id=payload.get("actor", "synthetic-admin"), after={"blocking": comment.blocking, "status": comment.status, "source_type": comment.source_type})
    db.commit()
    return row(comment)


@router.post("/admin-comments/{comment_id}/update")
def update_admin_comment(comment_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    comment = require(db, AdminDocumentComment, comment_id, "ADMIN_COMMENT_NOT_FOUND")
    comment.status = payload.get("status", comment.status)
    comment.resolution_evidence = payload.get("resolution_evidence", comment.resolution_evidence)
    if comment.status == "RESOLVED" and comment.resolution_evidence:
        for block in db.scalars(select(SystemBlock).where(SystemBlock.control_code == "ADMIN_COMMENT_BLOCKING", SystemBlock.blocking == True)).all():
            if block.reason == comment.text:
                block.blocking = False
                block.resolved_at = datetime.now(timezone.utc)
    audit(db, correlation_id=cid(request), event_type="ADMIN_COMMENT_UPDATED", entity_type="AdminDocumentComment", entity_id=comment.id, actor_id=payload.get("actor", "synthetic-admin"), after={"status": comment.status, "resolution_evidence": comment.resolution_evidence})
    db.commit()
    return row(comment)


@router.post("/opportunities/{opportunity_id}/reference/assign")
def assign_reference(opportunity_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    opportunity = require(db, Opportunity, opportunity_id, "OPPORTUNITY_NOT_FOUND")
    contract = db.scalar(select(Contract).join(Quotation, Contract.quotation_id == Quotation.id).where(Quotation.opportunity_id == opportunity.id).order_by(Contract.created_at.desc()))
    revision = db.get(ContractRevision, contract.current_revision_id) if contract and contract.current_revision_id else None
    if not revision or not db.scalar(select(ContractExecutionEvidence).where(ContractExecutionEvidence.contract_revision_id == revision.id, ContractExecutionEvidence.execution_status == "EXECUTED_EVIDENCE_RECORDED")):
        raise HTTPException(409, "CONTRACT_EXECUTION_EVIDENCE_REQUIRED")
    if db.scalar(select(SystemBlock).where(SystemBlock.context_type == "OPPORTUNITY", SystemBlock.context_id == opportunity.id, SystemBlock.blocking == True)):
        raise HTTPException(409, "OPPORTUNITY_SYSTEM_BLOCKED")
    quotation = db.get(Quotation, contract.quotation_id)
    reference = db.scalar(select(ReferenceNumber).where(ReferenceNumber.opportunity_id == opportunity.id))
    if not reference:
        reference = ReferenceNumber(reference_value=payload.get("reference_value", f"AMEC-SYN-2026-{db.scalar(select(func.count(ReferenceNumber.id))) + 1:04d}"), reference_type="PROJECT_REFERENCE", opportunity_id=opportunity.id, quotation_id=quotation.id, contract_id=contract.id, status="ACTIVATED")
        db.add(reference)
        db.flush()
    else:
        reference.quotation_id = reference.quotation_id or quotation.id
        reference.contract_id = reference.contract_id or contract.id
        reference.status = "ACTIVATED"
    draft = create_communication_draft(db, communication_type="REFERENCE_NUMBER", context_type="REFERENCE_NUMBER", context_id=reference.id, subject=f"Reference {reference.reference_value} — synthetic draft", body="Reference number is prepared for human review; no external communication was sent.", actor=payload.get("actor", "synthetic-admin"), correlation_id=cid(request))
    opportunity.status = "REFERENCE_ASSIGNED"
    audit(db, correlation_id=cid(request), event_type="REFERENCE_NUMBER_ASSIGNED", entity_type="ReferenceNumber", entity_id=reference.id, actor_id=payload.get("actor", "synthetic-admin"), after={"reference_value": reference.reference_value, "status": reference.status})
    db.commit()
    return {"reference": row(reference), "draft": row(draft)}


@router.get("/opportunities/{opportunity_id}/reference")
def opportunity_reference(opportunity_id: str, db: Session = Depends(get_db)):
    require(db, Opportunity, opportunity_id, "OPPORTUNITY_NOT_FOUND")
    reference = db.scalar(select(ReferenceNumber).where(ReferenceNumber.opportunity_id == opportunity_id))
    if not reference: raise HTTPException(404, "REFERENCE_NOT_FOUND")
    return row(reference)


@router.post("/opportunities/{opportunity_id}/project-bootstrap")
def bootstrap_project(opportunity_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    opportunity = require(db, Opportunity, opportunity_id, "OPPORTUNITY_NOT_FOUND")
    reference = db.scalar(select(ReferenceNumber).where(ReferenceNumber.opportunity_id == opportunity.id))
    if not reference: raise HTTPException(409, "REFERENCE_NUMBER_REQUIRED")
    project = db.get(Project, payload.get("project_id")) if payload.get("project_id") else first_project(db)
    record = db.scalar(select(ProjectAdministrationRecord).where(ProjectAdministrationRecord.project_id == project.id))
    if record and record.reference_number_id != reference.id:
        raise HTTPException(409, "PROJECT_IDENTITY_RECONCILIATION_REQUIRED")
    reference.project_id = project.id
    reference.status = "ACTIVATED"
    reference.activated_at = reference.activated_at or datetime.now(timezone.utc)
    if not record:
        record = ProjectAdministrationRecord(project_id=project.id, reference_number_id=reference.id, client_account_id=opportunity.client_account_id, payment_status="NOT_CONFIGURED", payment_followup_state="TRACK_ONLY", project_status="ACTIVE", engineer_email_projection=project.assigned_engineer, synology_linkage_reference=f"synthetic://synology/{project.project_number}", excel_linkage_reference=f"synthetic://excel/{project.project_number}")
        db.add(record)
    links = {link.system_type.value if hasattr(link.system_type, "value") else str(link.system_type): link for link in db.scalars(select(ExternalSystemLink).where(ExternalSystemLink.project_id == project.id)).all()}
    if "SYNOLOGY" not in links: db.add(ExternalSystemLink(project_id=project.id, system_type=SystemType.SYNOLOGY, external_reference=f"synthetic://synology/{project.project_number}", display_reference=project.project_number, metadata_json={"synthetic": True}))
    if "EXCEL" not in links: db.add(ExternalSystemLink(project_id=project.id, system_type=SystemType.EXCEL, external_reference=f"synthetic://excel/{project.project_number}", display_reference=project.project_number, metadata_json={"synthetic": True}))
    projection = db.scalar(select(ProjectStatusProjection).where(ProjectStatusProjection.project_id == project.id))
    if not projection:
        client = db.get(ClientAccount, opportunity.client_account_id) if opportunity.client_account_id else None
        projection = ProjectStatusProjection(project_id=project.id, reference_number=reference.reference_value, name=project.project_name, client=client.display_name if client else "SYNTHETIC", payment=record.payment_status, status=record.project_status, engineer_email=record.engineer_email_projection)
        db.add(projection)
    opportunity.status = "PROJECT_BOOTSTRAPPED"
    audit(db, correlation_id=cid(request), event_type="PROJECT_BOOTSTRAP_RECORDED", entity_type="ProjectAdministrationRecord", entity_id=record.id, actor_id=payload.get("actor", "synthetic-admin"), after={"project_id": project.id, "external_writes": False}, metadata={"adapters": ["SYNTHETIC_LOCAL_SYNOLOGY", "SYNTHETIC_LOCAL_EXCEL"]})
    db.commit()
    return {"project": row(project), "administration": row(record), "projection": row(projection), "external_writes": False}


@router.get("/opportunities/{opportunity_id}/project-bootstrap-status")
def project_bootstrap_status(opportunity_id: str, db: Session = Depends(get_db)):
    opportunity = require(db, Opportunity, opportunity_id, "OPPORTUNITY_NOT_FOUND")
    reference = db.scalar(select(ReferenceNumber).where(ReferenceNumber.opportunity_id == opportunity.id))
    project = first_project(db)
    record = db.scalar(select(ProjectAdministrationRecord).where(ProjectAdministrationRecord.project_id == project.id))
    projection = db.scalar(select(ProjectStatusProjection).where(ProjectStatusProjection.project_id == project.id))
    return {"opportunity_status": opportunity.status, "reference": row(reference), "administration": row(record), "projection": row(projection), "ready": bool(reference and record and projection)}


@router.get("/projects/{project_id}/administration-status")
def project_administration_status(project_id: str, db: Session = Depends(get_db)):
    require(db, Project, project_id, "PROJECT_NOT_FOUND")
    record = db.scalar(select(ProjectAdministrationRecord).where(ProjectAdministrationRecord.project_id == project_id))
    return {"administration": row(record), "links": [row(item) for item in db.scalars(select(ExternalSystemLink).where(ExternalSystemLink.project_id == project_id)).all()]}


@router.get("/projects/{project_id}/project-status-projection")
def project_status_projection(project_id: str, db: Session = Depends(get_db)):
    require(db, Project, project_id, "PROJECT_NOT_FOUND")
    return row(db.scalar(select(ProjectStatusProjection).where(ProjectStatusProjection.project_id == project_id)))


@router.post("/projects/{project_id}/handoff-to-permit")
def handoff_to_permit(project_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    project = require(db, Project, project_id, "PROJECT_NOT_FOUND")
    record = db.scalar(select(ProjectAdministrationRecord).where(ProjectAdministrationRecord.project_id == project.id))
    reference = db.scalar(select(ReferenceNumber).where(ReferenceNumber.project_id == project.id))
    if not record or not reference or db.scalar(select(SystemBlock).where(SystemBlock.context_type == "PROJECT", SystemBlock.context_id == project.id, SystemBlock.blocking == True)):
        raise HTTPException(409, "PROJECT_HANDOVER_BLOCKED")
    handover = db.scalar(select(ProjectHandover).where(ProjectHandover.project_id == project.id))
    if not handover: handover = ProjectHandover(project_id=project.id)
    handover.status = "READY_FOR_PERMIT"
    handover.readiness_state = "READY_FOR_PERMIT"
    artifact = render_artifact(db, artifact_type="HANDOVER", context_type="PROJECT_HANDOVER", context_id=handover.id, payload={"project_number": project.project_number, "reference": reference.reference_value, "status": "READY_FOR_PERMIT"}, source_revision_ids=[], template_version_id=payload.get("template_version_id"), actor=payload.get("actor", "synthetic-admin"), correlation_id=cid(request), project_id=project.id)
    handover.rendered_artifact_id = artifact.id
    db.add(handover)
    application = first_application(db, project.id)
    audit(db, correlation_id=cid(request), event_type="PROJECT_HANDOVER_READY_FOR_PERMIT", entity_type="ProjectHandover", entity_id=handover.id, actor_id=payload.get("actor", "synthetic-admin"), after={"readiness_state": handover.readiness_state, "permit_application_id": application.id})
    db.commit()
    return {"handover": row(handover), "permit_application": row(application), "external_submission": False}
