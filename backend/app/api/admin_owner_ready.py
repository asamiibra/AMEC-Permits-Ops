"""Owner-facing Administration projections and bounded configuration commands."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from ..adapters.excel.adapter import MockExcelAdapter
from ..adapters.municipality.adapter import MockMunicipalityAdapter
from ..adapters.synology.adapter import MockSynologyAdapter
from ..audit.service import audit
from ..api.dependencies import current_user_role
from ..config.settings import get_settings, repo_root
from ..db import get_db
from ..models import (
    AuditEvent, AttachmentCategoryConfig, ConfigurationArtifact, ConfigurationBundle,
    Contract, ContractRevision, ExternalSystemLink, FieldDefinition, Finding,
    FormTemplate, FormTemplateVersion, MunicipalityConfig, NotificationEvent,
    Opportunity, Project, ProjectNumberReservation, ProposalIntakeArtifact,
    Quotation, RequirementConfig, Role, ScenarioConfig, SynologyProjectBootstrap,
    TargetRenderingRule, TemplateDefinition, TemplateVersion, User, WorkflowTask,
)
from ..services.proposals_sor import ACTION_CONFIG, SEMANTIC_FOLDER_CONFIG

router = APIRouter(prefix="/api/admin", tags=["owner-administration"])
settings = get_settings()


def owner_admin(role: Role = Depends(current_user_role)) -> Role:
    if role not in {Role.SYSTEM_ADMIN, Role.OWNER_SPONSOR}:
        raise HTTPException(status_code=403, detail={"code": "ADMINISTRATION_ACCESS_DENIED", "message": "Global Administration is available to Owner only."})
    return role


def _enum(value: Any) -> str | None:
    return value.value if hasattr(value, "value") else value


def _status(value: str | None) -> str:
    return value.replace("_", " ").title() if value else "Needs AMEC Input"


def _user_role(role: Role | str) -> str:
    value = _enum(role) or ""
    if value in {"SYSTEM_ADMIN", "OWNER_SPONSOR"}:
        return "Owner"
    if value in {"PROCESS_CHAMPION", "COMMERCIAL_APPROVER", "BD_USER"}:
        return "Business Development"
    return "Engineering"


def _capability_rows() -> list[dict[str, str]]:
    rows = [
        ("Proposal intake", "View / edit / act", "View / edit / act", "View / edit"),
        ("Proposal technical preparation", "View / act", "View", "View / edit / act"),
        ("Contract management", "View / edit / act", "View / edit / act", "View"),
        ("Contract → Permit handoff", "View / act", "View / act", "View"),
        ("Permit technical work", "View", "View", "View / edit / act"),
        ("Final human submission", "Human boundary", "Human boundary", "Human boundary"),
        ("Administration", "View / edit / act", "Denied", "Denied"),
        ("Audit visibility", "View", "View limited", "View limited"),
    ]
    return [{"capability": a, "owner": b, "business_development": c, "engineering": d} for a, b, c, d in rows]


def _readable(value: Any, fallback: str = "Needs AMEC Input") -> str:
    if value is None or value == "":
        return fallback
    text = str(value)
    for source, target in {
        "ConfigurationArtifact": "Configuration",
        "ProjectArtifactRecord": "Project record",
        "FieldMatrixCoverage": "Field matrix coverage",
        "RequirementMatrixCoverage": "Requirement matrix coverage",
        "ProposalIntakeArtifact": "Proposal intake",
        "AuditEvent": "Audit event",
        "WorkflowTask": "Work item",
    }.items():
        text = text.replace(source, target)
    return text.replace("_", " ").replace("QUOTATION", "PROPOSAL").replace("Quotation", "Proposal").replace("quotation", "proposal").replace("commercial approver", "business development").title()


def _safe_connection(name: str, purpose: str, result: dict[str, Any], mode: str, affected: str, last_tested: str | None = None) -> dict[str, Any]:
    healthy = bool(result.get("healthy", result.get("status") in {"OK", "HEALTHY", "CONNECTED"}))
    return {
        "name": name,
        "purpose": purpose,
        "status": "Simulator Ready" if healthy else "Simulator Check Failed",
        "production_status": "Production Not Connected",
        "environment": mode,
        "configured": True,
        "last_tested": last_tested,
        "affected_workflow": affected,
        "details": {"adapter": result.get("adapter") or result.get("system") or "Synthetic adapter"},
    }


def _connection_test_state(db: Session | None) -> dict[str, Any]:
    if db is None:
        return {}
    item = db.scalar(select(ConfigurationArtifact).where(ConfigurationArtifact.stable_id == "ADMIN_CONNECTION_HEALTH:AMEC"))
    return item.semantic_payload_json if item and isinstance(item.semantic_payload_json, dict) else {}


def _connections(db: Session | None = None) -> list[dict[str, Any]]:
    root = Path(settings.mock_systems_root)
    tested = _connection_test_state(db)
    synology = MockSynologyAdapter(str(root / "synology")).health_check()
    excel = MockExcelAdapter(str(root / "excel/permit_tracker.xlsx")).health_check()
    municipality = MockMunicipalityAdapter({}).health_check()
    return [
        _safe_connection("Synology / document SOR", "Canonical project source and Proposal/Contract evidence", synology, "Synthetic connector", "Source intake and project evidence", tested.get("Synology / document SOR")),
        _safe_connection("Excel project register", "Human-owned project/status representation", excel, "Test Mode", "Project status projection", tested.get("Excel project register")),
        _safe_connection("Tender / email source", "Human-provided Proposal intake evidence", {"healthy": True, "adapter": "Manual source intake"}, "Test Mode", "Proposal intake", tested.get("Tender / email source")),
        _safe_connection("Municipality / Portal", "Downstream Permit reads and assisted preparation", municipality, "Simulator", "Permit workflow; final submission remains human-controlled", tested.get("Municipality / Portal")),
    ]


def _scenario(db: Session) -> ScenarioConfig | None:
    return db.scalar(select(ScenarioConfig).order_by(ScenarioConfig.scenario_code))


def _templates(db: Session) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for item in db.scalars(select(TemplateDefinition).order_by(TemplateDefinition.template_code)).all():
        versions = db.scalars(select(TemplateVersion).where(TemplateVersion.template_definition_id == item.id).order_by(TemplateVersion.version)).all()
        result.append({"id": item.id, "name": _readable(item.name), "code": item.template_code, "purpose": _readable(item.artifact_type), "owner_role": _readable(item.owner_role), "status": "Synthetic stand-in" if "SYNTHETIC" in item.status else _readable(item.status), "versions": [{"version": v.version, "status": "Synthetic stand-in" if "SYNTHETIC" in v.status else _readable(v.status), "updated_at": v.effective_from.isoformat() if v.effective_from else None} for v in versions]})
    for item in db.scalars(select(FormTemplate).order_by(FormTemplate.template_code)).all():
        versions = db.scalars(select(FormTemplateVersion).where(FormTemplateVersion.template_id == item.id).order_by(FormTemplateVersion.version)).all()
        result.append({"id": item.id, "name": _readable(item.name), "code": item.template_code, "purpose": "Municipality form", "owner_role": "Permit Workflow", "status": "Synthetic stand-in" if "SYNTHETIC" in item.status else _readable(item.status), "versions": [{"version": v.version, "status": "Synthetic stand-in" if "SYNTHETIC" in v.status else _readable(v.status), "updated_at": None} for v in versions]})
    return result


def _notification_settings(db: Session) -> dict[str, Any]:
    item = db.scalar(select(ConfigurationArtifact).where(ConfigurationArtifact.stable_id == "ADMIN_RUNTIME_SETTINGS:AMEC"))
    payload = item.semantic_payload_json if item else {}
    return {"follow_up_hours": payload.get("follow_up_hours") if isinstance(payload, dict) else None, "status": "Configured" if item else "Needs Setup", "source": item.stable_id if item else None, "synthetic": True}


@router.get("/summary")
def admin_summary(db: Session = Depends(get_db), _role: Role = Depends(owner_admin)):
    return {
        "title": "Administration",
        "subtitle": "Configure how ProposalOps works for AMEC.",
        "environment": "Synthetic prototype · test data and simulated connections",
        "categories": [
            {"key": "people-access", "label": "People & Access", "route": "/admin/people-access", "status": "Configured"},
            {"key": "data-connections", "label": "Data & Connections", "route": "/admin/data-connections", "status": "Simulator Ready · Production Not Connected"},
            {"key": "project-folder-setup", "label": "Project & Folder Setup", "route": "/admin/project-folder-setup", "status": "Configured for demo"},
            {"key": "proposal-setup", "label": "Proposal Setup", "route": "/admin/proposal-setup", "status": "Configured for demo"},
            {"key": "contract-setup", "label": "Contract Setup", "route": "/admin/contract-setup", "status": "Configured for demo"},
            {"key": "forms", "label": "Forms", "route": "/admin/forms", "status": "Canonical library"},
            {"key": "permit-setup", "label": "Permit Workflow Setup", "route": "/admin/permit-setup", "status": "Configured for demo"},
            {"key": "templates", "label": "Templates & Documents", "route": "/admin/templates", "status": "Synthetic stand-ins"},
            {"key": "notifications", "label": "Notifications & Follow-up", "route": "/admin/notifications", "status": _notification_settings(db)["status"]},
            {"key": "security", "label": "Data, Security & Retention", "route": "/admin/security", "status": "Configured for demo"},
            {"key": "integration-health", "label": "Integration Health", "route": "/admin/integration-health", "status": "Simulator Ready"},
            {"key": "audit", "label": "Audit History", "route": "/admin/audit", "status": "Available"},
            {"key": "advanced-diagnostics", "label": "Advanced Diagnostics", "route": "/admin/advanced-diagnostics", "status": "Secondary"},
        ],
        "go_live": {"route": "/admin/go-live-readiness", "label": "View Inputs & Go-Live", "status": "Separate helper"},
    }


@router.get("/users")
def admin_users(db: Session = Depends(get_db), _role: Role = Depends(owner_admin)):
    users = db.scalars(select(User).order_by(User.display_name)).all()
    return {"users": [{"id": u.id, "name": u.display_name, "email": u.email, "role": _user_role(u.role), "status": "Active" if u.active else "Inactive", "office": u.office.name_en if u.office else "Needs AMEC Input"} for u in users], "production_user_management": "Needs AMEC production setup", "permissions": _capability_rows(), "inputs_route": "/admin/go-live-readiness"}


@router.get("/permissions")
def admin_permissions(_role: Role = Depends(owner_admin)):
    return {"roles": ["Owner", "Business Development", "Engineering"], "rows": _capability_rows(), "protected_boundaries": ["Professional Engineering authority", "Human final Municipality submission", "Commercial release rules", "Credential handling"]}


@router.get("/connections")
def admin_connections(db: Session = Depends(get_db), _role: Role = Depends(owner_admin)):
    return {"connections": _connections(db), "secrets": "Masked and server-side; no credentials are returned.", "status_definition": "Simulator status reflects the synthetic adapter only; production connection state is shown separately."}


@router.post("/connections/test")
def test_admin_connection(payload: dict[str, str], request: Request, db: Session = Depends(get_db), role: Role = Depends(owner_admin)):
    name = payload.get("name", "")
    match = next((item for item in _connections(db) if item["name"] == name), None)
    if not match:
        raise HTTPException(404, "CONNECTION_NOT_FOUND")
    tested_at = datetime.now(timezone.utc).isoformat()
    item = db.scalar(select(ConfigurationArtifact).where(ConfigurationArtifact.stable_id == "ADMIN_CONNECTION_HEALTH:AMEC"))
    before = dict(item.semantic_payload_json or {}) if item and isinstance(item.semantic_payload_json, dict) else {}
    after = {**before, name: tested_at}
    if item:
        item.semantic_payload_json = after
        item.version = f"ADMIN_CONNECTION_HEALTH:{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        item.checksum = __import__("hashlib").sha256(str(after).encode()).hexdigest()
    else:
        item = ConfigurationArtifact(stable_id="ADMIN_CONNECTION_HEALTH:AMEC", artifact_type="ADMIN_CONNECTION_HEALTH", version="ADMIN_CONNECTION_HEALTH:1.0", checksum=__import__("hashlib").sha256(str(after).encode()).hexdigest(), effective_from=datetime.now(timezone.utc), status="ACTIVE", source_basis="Owner Administration synthetic connection tests", semantic_payload_json=after)
        db.add(item)
    db.flush()
    audit(db, correlation_id=getattr(request.state, "correlation_id", "missing-correlation-id"), event_type="ADMIN_CONNECTION_TESTED", entity_type="ConfigurationArtifact", entity_id=item.id, actor_id=role.value, before=before, after=after, metadata={"connection": name, "synthetic": True})
    db.commit()
    return {"name": name, "status": match["status"], "production_status": match["production_status"], "tested_at": tested_at, "message": "Synthetic connection test completed and recorded."}


@router.get("/project-setup")
def admin_project_setup(db: Session = Depends(get_db), _role: Role = Depends(owner_admin)):
    scenario = _scenario(db)
    project = db.scalar(select(Project).order_by(Project.project_number))
    bootstrap = db.scalar(select(SynologyProjectBootstrap).where(SynologyProjectBootstrap.project_id == project.id)) if project else None
    reservations = db.scalars(select(ProjectNumberReservation).order_by(ProjectNumberReservation.reserved_at.desc()).limit(10)).all()
    return {"reference_behavior": {"proposal_before_project": "A provisional Proposal reference can exist before a Project", "project_reference": "A canonical Project Reference is assigned before downstream work", "lineage": "Proposal → Contract → Permit → canonical Project folder", "status": "Configured for demo"}, "scenario": {"project_type": scenario.permit_type if scenario else "Needs AMEC Input", "municipality": scenario.municipality if scenario else "Needs AMEC Input", "status": _status(_enum(scenario.status) if scenario else None)}, "folder_structure": [{"category": value.get("label", key.replace("_", " ").title()), "mapping": value.get("folder", "Needs AMEC Input"), "status": "Configured for demo", "reconciliation": "Semantic mapping verified against canonical project template"} for key, value in SEMANTIC_FOLDER_CONFIG.items()], "root_mapping": bootstrap.root_path if bootstrap else "Needs AMEC Input", "folder_template_version": "SYN-AMEC-PROJECT-FOLDERS-1.0" if bootstrap else "Needs AMEC Input", "excel_mapping": {"status": "Simulator Ready", "project_reference": project.project_number if project else None}, "recent_reservations": [{"reference": r.proposed_number, "status": _status(_enum(r.status))} for r in reservations]}


@router.get("/proposal-setup")
def admin_proposal_setup(db: Session = Depends(get_db), _role: Role = Depends(owner_admin)):
    # The local seeded database may predate newer Opportunity ORM columns. Read
    # only the stable columns needed for this owner projection so schema drift
    # does not turn a business-facing screen into a false broken route.
    proposal = db.execute(text("SELECT status FROM opportunities ORDER BY opportunity_reference LIMIT 1")).mappings().first()
    fields = ["Client", "Proposal Description", "Price", "SOW", "Period", "Exclusions", "Payment Condition", "Process of Work"]
    source_labels = {"CLIENT_LIST": "Client List", "PROPOSAL_FORM": "Proposal Form", "NEW_PROPOSAL": "New Proposal", "TENDER_EMAIL": "Tender Email", "TENDER_DOCUMENT": "Tender Document", "TENDER_IMAGE": "Tender Image", "CLIENT_INFORMATION": "Client Information"}
    return {"required_fields": [{"label": field, "key": field.lower().replace(" ", "_"), "status": "Configured for demo" if field.lower().replace(" ", "_") in {"price", "sow", "period", "exclusions"} or field in {"Client", "Proposal Description"} else "Needs AMEC Input"} for field in fields], "source_types": [{"key": key, "label": source_labels.get(key, key.replace("_", " ").title()), "status": "Configured for demo", "purpose": "Proposal intake source" if key in {"TENDER_EMAIL", "TENDER_DOCUMENT", "TENDER_IMAGE", "CLIENT_INFORMATION"} else "Existing Proposal context or lifecycle action"} for key, value in ACTION_CONFIG.items() if key not in {"CONTRACT_FORM", "PERMIT_INITIATION"}], "lifecycle": {"current_demo_stage": _readable(proposal["status"] if proposal else None), "readiness": "Derived from source evidence, client context, description, and reference state"}, "handoffs": [{"from": "Business Development", "to": "Engineering", "when": "Verified source intake and Proposal context"}, {"from": "Engineering", "to": "Business Development", "when": "Technical preparation is ready"}], "reference_rule": "Use a provisional Proposal reference until a canonical Project Reference exists", "template_route": "/admin/templates"}


@router.get("/contract-setup")
def admin_contract_setup(db: Session = Depends(get_db), _role: Role = Depends(owner_admin)):
    contracts = db.scalars(select(Contract).order_by(Contract.contract_reference)).all()
    return {"contract_reference_rule": "Synthetic demo references are assigned by the seeded workflow; AMEC production numbering needs setup.", "required_fields": [{"label": "Contract Reference", "status": "Configured for demo" if contracts else "Needs AMEC Input"}, {"label": "Project Reference", "status": "Configured for demo" if contracts else "Needs AMEC Input"}, {"label": "Commercial terms", "status": "Configured for demo" if contracts else "Needs AMEC Input"}, {"label": "Milestones / dates", "status": "Configured for demo" if contracts else "Needs AMEC Input"}], "eligibility": "Proposal lifecycle, client context, and canonical Project identity are enforced by the backend", "permit_readiness": "An eligible Contract with a canonical Project starts or links the downstream Permit; an existing Permit is not required", "contracts": [{"reference": c.contract_reference, "status": _readable(c.status), "project_reference": db.get(Project, c.project_id).project_number if c.project_id and db.get(Project, c.project_id) else "Needs canonical Project"} for c in contracts], "template_route": "/admin/templates"}


@router.get("/permit-setup")
def admin_permit_setup(db: Session = Depends(get_db), _role: Role = Depends(owner_admin)):
    scenario = _scenario(db)
    municipality = db.scalar(select(MunicipalityConfig).where(MunicipalityConfig.scenario_id == scenario.id)) if scenario else None
    requirements = db.scalars(select(RequirementConfig).where(RequirementConfig.scenario_id == scenario.id).order_by(RequirementConfig.requirement_code)).all() if scenario else []
    attachments = db.scalars(select(AttachmentCategoryConfig).where(AttachmentCategoryConfig.scenario_id == scenario.id).order_by(AttachmentCategoryConfig.portal_order)).all() if scenario else []
    return {"permit_types": [{"name": scenario.permit_type, "municipality": scenario.municipality, "status": _status(_enum(scenario.status))}] if scenario else [], "requirements": [{"name": _readable(r.requirement_code), "description": r.description, "applicability": "Conditional" if r.applicability_expression_json else "Applies to this demo scenario", "required": r.blocking, "status": _status(_enum(r.status))} for r in requirements], "attachments": [{"label": a.label_en, "required_state": _readable(a.required_state), "formats": a.allowed_formats_json, "status": "Configured for demo"} for a in attachments], "municipality": {"mode": _readable(scenario.interaction_mode if scenario else None), "mfa": _readable(municipality.mfa_mode if municipality else None), "human_submission": True, "supported_reads": [_readable(x.get("operation")) for x in (municipality.operations_json if municipality else []) if x.get("operation", "").startswith("READ")], "supported_writes": [_readable(x.get("operation")) for x in (municipality.operations_json if municipality else []) if not x.get("operation", "").startswith("READ")]}}


@router.get("/templates")
def admin_templates(db: Session = Depends(get_db), _role: Role = Depends(owner_admin)):
    return {"templates": _templates(db), "production_templates": "Needs AMEC setup where synthetic stand-ins are shown."}


class FollowUpUpdate(BaseModel):
    follow_up_hours: int = Field(ge=1, le=720)


@router.get("/notifications")
def admin_notifications(db: Session = Depends(get_db), _role: Role = Depends(owner_admin)):
    recent_event_count = db.scalar(select(func.count()).select_from(NotificationEvent)) or 0
    return {"settings": _notification_settings(db), "audiences": [{"name": "Owner", "summary": "Administration and readiness changes", "status": "Configured for demo"}, {"name": "Business Development", "summary": "Proposal intake, commercial handoffs, and client follow-up", "status": "Configured for demo"}, {"name": "Engineering", "summary": "Technical preparation, findings, and Permit work", "status": "Configured for demo"}], "follow_up": {"status": "Synthetic test configuration", "rule": "Timing is persisted and audited; AMEC policy confirmation is required before production"}, "recent_event_count": recent_event_count, "notifications_route": "/notifications", "delivery_boundary": "No external email is sent; HUMAN_SEND remains the production boundary"}


@router.put("/notifications/follow-up")
def update_admin_follow_up(payload: FollowUpUpdate, request: Request, db: Session = Depends(get_db), role: Role = Depends(owner_admin)):
    item = db.scalar(select(ConfigurationArtifact).where(ConfigurationArtifact.stable_id == "ADMIN_RUNTIME_SETTINGS:AMEC"))
    before = dict(item.semantic_payload_json or {}) if item else {}
    if item:
        item.semantic_payload_json = {**before, "follow_up_hours": payload.follow_up_hours, "mode": "SYNTHETIC_TEST_CONFIGURATION"}
        item.version = f"ADMIN_RUNTIME_SETTINGS:{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        item.checksum = __import__("hashlib").sha256(str(item.semantic_payload_json).encode()).hexdigest()
    else:
        item = ConfigurationArtifact(stable_id="ADMIN_RUNTIME_SETTINGS:AMEC", artifact_type="ADMIN_RUNTIME_SETTINGS", version="ADMIN_RUNTIME_SETTINGS:1.0", checksum=__import__("hashlib").sha256(str(payload.follow_up_hours).encode()).hexdigest(), effective_from=datetime.now(timezone.utc), status="ACTIVE", source_basis="Owner Administration bounded synthetic setting", semantic_payload_json={"follow_up_hours": payload.follow_up_hours, "mode": "SYNTHETIC_TEST_CONFIGURATION"})
        db.add(item)
    db.flush()
    audit(db, correlation_id=getattr(request.state, "correlation_id", "missing-correlation-id"), event_type="ADMIN_CONFIGURATION_UPDATED", entity_type="ConfigurationArtifact", entity_id=item.id, actor_id=role.value, before=before, after=item.semantic_payload_json, metadata={"setting": "follow_up_hours", "synthetic": True})
    db.commit()
    return {"follow_up_hours": payload.follow_up_hours, "status": "Configured", "persisted": True}


@router.get("/security")
def admin_security(db: Session = Depends(get_db), _role: Role = Depends(owner_admin)):
    scenario = _scenario(db)
    municipality = db.scalar(select(MunicipalityConfig).where(MunicipalityConfig.scenario_id == scenario.id)) if scenario else None
    return {"environment": {"label": "Synthetic prototype", "status": "Test data only"}, "data_classification": {"label": "Production data", "status": "Needs AMEC Input"}, "mfa": {"label": "Owner and Municipality MFA", "status": "Configured for demo" if municipality else "Needs AMEC Input", "mode": _readable(municipality.mfa_mode if municipality else None)}, "role_based_access": {"label": "Owner-only Administration", "status": "Configured"}, "audit_retention": {"label": "Operational audit history", "status": "Available"}, "backup_recovery": {"label": "Production backup and recovery", "status": "Needs AMEC Input"}, "secrets": {"exposed": False, "display": "Masked server-side"}}


@router.get("/integration-health")
def admin_integration_health(db: Session = Depends(get_db), _role: Role = Depends(owner_admin)):
    return {"integrations": _connections(db), "checked_at": datetime.now(timezone.utc).isoformat(), "purpose": "Cross-system operational signal; connection setup remains on Data & Connections.", "diagnostic_route": "/admin/advanced-diagnostics"}


@router.get("/audit")
def admin_audit(entity_type: str | None = None, db: Session = Depends(get_db), _role: Role = Depends(owner_admin)):
    query = select(AuditEvent).order_by(AuditEvent.occurred_at.desc()).limit(100)
    if entity_type:
        query = query.where(AuditEvent.entity_type == entity_type)
    rows = db.scalars(query).all()
    return {"events": [{"id": e.id, "actor": "Owner configuration" if e.actor_id in {Role.SYSTEM_ADMIN.value, Role.OWNER_SPONSOR.value} else "Workflow service", "action": _readable(e.event_type), "record": _readable(e.entity_type), "reference": "Technical detail available", "when": e.occurred_at.isoformat(), "outcome": "Recorded", "detail_route": f"/admin/advanced-diagnostics?event={e.id}"} for e in rows], "filters": ["Proposal", "Contract", "Permit", "Configuration", "User / role", "Source / document"], "technical_detail_route": "/admin/advanced-diagnostics"}


@router.get("/advanced-diagnostics")
def admin_advanced(db: Session = Depends(get_db), _role: Role = Depends(owner_admin)):
    return {"secondary": True, "diagnostics": [{"name": "Attachment and grid diagnostics", "route": "/admin/advanced-diagnostics/attachments-grids", "status": "Available", "purpose": "Technical evidence only"}, {"name": "Control diagnostics", "route": "/admin/control-diagnostics", "status": "Available", "purpose": "Technical evidence only"}, {"name": "Detailed lineage", "route": "/admin/advanced-diagnostics/lineage", "status": "Available", "purpose": "Technical evidence only"}, {"name": "Adapter diagnostics", "route": "/admin/advanced-diagnostics/integration-health", "status": "Available", "purpose": "Technical evidence only"}], "counts": {"configuration_artifacts": db.scalar(select(func.count(ConfigurationArtifact.id))) or 0, "workflow_tasks": db.scalar(select(func.count(WorkflowTask.id))) or 0, "findings": db.scalar(select(func.count(Finding.id))) or 0}, "secrets": {"exposed": False, "note": "Technical diagnostics omit credentials and authorization material."}}
