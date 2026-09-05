"""Dashboard-specific, persistent Master Content readiness projections."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, true
from sqlalchemy.orm import Session

from ..api.admin_owner_ready import _connections
from ..models import (
    AuditEvent,
    ContentCategory,
    DefinitionEntry,
    DashboardInputItem,
    MasterContentItem,
    MasterContentReferenceSequence,
    MasterContentGovernanceProfile,
    MasterContentQualityFlag,
)
from .master_content import ENGINEERING_DISCIPLINES, ENGINEERING_SOURCE_TYPES, resolve_master_content_purpose
from .forms_governance import source_blocker_rollup

CONTEXT_KEY = "DASHBOARD_MASTER_CONTENT"
GOVERNANCE_CONTEXT_KEY = "DASHBOARD_FORMS_GOVERNANCE"
# Keep the original response contract stable for existing consumers. Wave A
# governance inputs are opt-in through the dashboard UI query parameter.
LEGACY_INPUT_KEYS = {
    "DASHBOARD_CATEGORY_TAXONOMY",
    "DASHBOARD_CATEGORY_SEMANTICS",
    "DASHBOARD_REFERENCE_NUMBERING",
    "DASHBOARD_ENGINEERING_SOURCE_TYPES",
    "DASHBOARD_ENGINEERING_DISCIPLINES",
    "DASHBOARD_FORM_REFERENCE_POLICY",
    "DASHBOARD_REPORT_REFERENCE_POLICY",
    "DASHBOARD_ENGINEERING_REFERENCE_POLICY",
    "DASHBOARD_DEFINITION_REFERENCE_POLICY",
    "DASHBOARD_MODULE_USAGE_POLICY",
    "DASHBOARD_ENGINEERING_ACTIVATION_POLICY",
    "DASHBOARD_REPORT_SCOPE_POLICY",
    "DASHBOARD_MASTER_WRITE_PERMISSIONS",
    "DASHBOARD_OFFICIAL_PROPOSAL_TEMPLATE",
    "DASHBOARD_OFFICIAL_PROPOSAL_CHECKLIST",
    "DASHBOARD_OFFICIAL_CONTRACT_TEMPLATE",
    "DASHBOARD_FORMS_CONTENT_READINESS",
    "DASHBOARD_REPORTS_CONTENT_READINESS",
    "DASHBOARD_ENGINEERING_CONTENT_READINESS",
    "DASHBOARD_DEFINITIONS_CONTENT_READINESS",
    "DASHBOARD_SYNOLOGY_CONNECTION",
    "DASHBOARD_FILE_POLICY",
    "DASHBOARD_DEFINITION_ARABIC_ALIASES",
}
OPEN_STATUSES = {"NEEDS_CONFIRMATION", "PROPOSED_DEFAULT", "NEEDS_DECISION", "NEEDS_CONTENT", "IN_PROGRESS", "WAITING_ON_AMEC_IT"}
CONFIRMED_STATUSES = {"CONFIRMED", "COMPLETE", "NOT_APPLICABLE"}
FRIENDLY_STATUS = {
    "NEEDS_CONFIRMATION": "Needs confirmation",
    "PROPOSED_DEFAULT": "Using proposed default",
    "NEEDS_DECISION": "Needs decision",
    "NEEDS_CONTENT": "Needs content",
    "IN_PROGRESS": "In progress",
    "WAITING_ON_AMEC_IT": "Waiting on AMEC IT",
    "CONFIRMED": "Confirmed",
    "COMPLETE": "Complete",
    "OPTIONAL": "Optional",
    "NOT_APPLICABLE": "Not applicable",
}
GROUP_LABELS = {
    "BUSINESS_DECISION": "AMEC Business Decisions",
    "CONTENT_READINESS": "Master Content Readiness",
    "TECHNICAL_GO_LIVE": "Technical Go-Live",
    "OPTIONAL_FUTURE": "Optional / Future Decisions",
}

SPECS: list[dict[str, Any]] = [
    {"key": "DASHBOARD_CATEGORY_TAXONOMY", "group": "BUSINESS_DECISION", "title": "Production categories", "what": "Review and confirm the category taxonomy for Forms, Reports, Engineering Works, and Definitions.", "why": "Consistent categories keep the four libraries organized and make filtering and future suggestions reliable.", "status": "NEEDS_CONFIRMATION", "blocking": "BUSINESS", "route": "/dashboard#categories"},
    {"key": "DASHBOARD_CATEGORY_SEMANTICS", "group": "BUSINESS_DECISION", "title": "Category semantics", "what": "Confirm that Category is the Owner-managed business classification, separate from Engineering Source Type and Discipline.", "why": "Keeping classification, source provenance, and discipline distinct prevents ambiguous Engineering records.", "status": "NEEDS_CONFIRMATION", "blocking": "BUSINESS", "route": "/dashboard#engineering-works"},
    {"key": "DASHBOARD_REFERENCE_NUMBERING", "group": "BUSINESS_DECISION", "title": "Reference numbering", "what": "Confirm the proposed F / R / E / D numbering pattern for reusable master content.", "why": "Stable references make master content easy to identify, cite, and audit across modules.", "status": "NEEDS_CONFIRMATION", "blocking": "BUSINESS", "route": "/dashboard"},
    {"key": "DASHBOARD_ENGINEERING_SOURCE_TYPES", "group": "BUSINESS_DECISION", "title": "Engineering source types", "what": "Confirm the Engineering Source Type taxonomy: Regulation, QCS, Municipality Comment, Authority Guidance, Engineering Standard, Design Guide, Technical Reference, Other.", "why": "Source provenance is not the same thing as a business category or engineering discipline.", "status": "NEEDS_CONFIRMATION", "blocking": "BUSINESS", "route": "/dashboard#engineering-works"},
    {"key": "DASHBOARD_ENGINEERING_DISCIPLINES", "group": "BUSINESS_DECISION", "title": "Engineering disciplines", "what": "Confirm the discipline taxonomy: General, Design, Architecture, Structural, Civil, MEP, Fire & Life Safety, Permit, Other.", "why": "A separate discipline lets Engineering filter and review references without overloading Category.", "status": "NEEDS_CONFIRMATION", "blocking": "BUSINESS", "route": "/dashboard#engineering-works"},
    {"key": "DASHBOARD_FORM_REFERENCE_POLICY", "group": "BUSINESS_DECISION", "title": "Form references", "what": "Confirm the Form reference prefix and padding policy; existing references must not be renumbered.", "why": "Reference policy is a governance decision and a stable contract for downstream consumers.", "status": "NEEDS_CONFIRMATION", "blocking": "BUSINESS", "route": "/dashboard"},
    {"key": "DASHBOARD_REPORT_REFERENCE_POLICY", "group": "BUSINESS_DECISION", "title": "Report references", "what": "Confirm the Report reference prefix and padding policy; existing references must not be renumbered.", "why": "Stable report references protect citations and audit history.", "status": "NEEDS_CONFIRMATION", "blocking": "BUSINESS", "route": "/dashboard#reports"},
    {"key": "DASHBOARD_ENGINEERING_REFERENCE_POLICY", "group": "BUSINESS_DECISION", "title": "Engineering references", "what": "Confirm the Engineering Work reference prefix and padding policy; existing references must not be renumbered.", "why": "Engineering references must remain stable even when classification changes.", "status": "NEEDS_CONFIRMATION", "blocking": "BUSINESS", "route": "/dashboard#engineering-works"},
    {"key": "DASHBOARD_DEFINITION_REFERENCE_POLICY", "group": "BUSINESS_DECISION", "title": "Definition references", "what": "Confirm the Definition reference prefix and padding policy; existing references must not be renumbered.", "why": "Definitions are reused across workflows and need durable identifiers.", "status": "NEEDS_CONFIRMATION", "blocking": "BUSINESS", "route": "/dashboard#definitions"},
    {"key": "DASHBOARD_MODULE_USAGE_POLICY", "group": "BUSINESS_DECISION", "title": "Module usage policy", "what": "Confirm where each content type may be used across Proposal, Contract, Permit, Engineering, Reports, and Administration.", "why": "Explicit usage prevents a reusable item from appearing in the wrong workflow.", "status": "NEEDS_CONFIRMATION", "blocking": "BUSINESS", "route": "/dashboard"},
    {"key": "DASHBOARD_ENGINEERING_ACTIVATION_POLICY", "group": "BUSINESS_DECISION", "title": "Engineering activation policy", "what": "Choose whether Engineering Works are advisory references only or may support a controlled engineering workflow.", "why": "This is a professional-responsibility boundary and must be selected by AMEC rather than assumed by the product.", "status": "NEEDS_DECISION", "blocking": "BUSINESS", "route": "/dashboard#engineering-works"},
    {"key": "DASHBOARD_REPORT_SCOPE_POLICY", "group": "BUSINESS_DECISION", "title": "Reports scope", "what": "Confirm whether Reports are reusable master templates, project outputs, or both with separate scopes.", "why": "Separating master templates from project outputs protects reuse and project-specific records.", "status": "NEEDS_CONFIRMATION", "blocking": "BUSINESS", "route": "/dashboard#reports"},
    {"key": "DASHBOARD_MASTER_WRITE_PERMISSIONS", "group": "BUSINESS_DECISION", "title": "Master write permissions", "what": "Confirm Owner-only write access for master content, with Business Development and Engineering using read/use permissions.", "why": "A single accountable owner protects the canonical content library from ungoverned edits.", "status": "PROPOSED_DEFAULT", "blocking": "BUSINESS", "route": "/admin"},
    {"key": "DASHBOARD_OFFICIAL_PROPOSAL_TEMPLATE", "group": "CONTENT_READINESS", "title": "Official Proposal Template", "what": "Confirm the single active Proposal Template purpose binding used by BD Proposal validation and rendering.", "why": "A deterministic resolver prevents different proposal consumers from selecting different templates.", "status": "NEEDS_CONFIRMATION", "blocking": "CONTENT", "route": "/dashboard#forms"},
    {"key": "DASHBOARD_OFFICIAL_PROPOSAL_CHECKLIST", "group": "CONTENT_READINESS", "title": "Official Proposal Checklist", "what": "Confirm the single active Proposal Checklist purpose binding used by BD Proposal readiness.", "why": "A canonical checklist keeps Proposal validation and Owner review aligned.", "status": "NEEDS_CONFIRMATION", "blocking": "CONTENT", "route": "/dashboard#forms"},
    {"key": "DASHBOARD_OFFICIAL_CONTRACT_TEMPLATE", "group": "CONTENT_READINESS", "title": "Official Contract Template", "what": "Confirm the single active Contract Template purpose binding for Administration and Contract handoff.", "why": "Contract consumers need an explicit canonical source instead of a guessed Form.", "status": "NEEDS_CONFIRMATION", "blocking": "CONTENT", "route": "/dashboard#forms"},
    {"key": "DASHBOARD_FORMS_CONTENT_READINESS", "group": "CONTENT_READINESS", "title": "Forms readiness", "what": "Provide or confirm the production Forms, their versions, categories, and intended modules.", "why": "Forms are the reusable starting point for consistent proposal and contract work.", "status": "NEEDS_CONTENT", "blocking": "CONTENT", "type": "FORM", "route": "/dashboard#forms"},
    {"key": "DASHBOARD_REPORTS_CONTENT_READINESS", "group": "CONTENT_READINESS", "title": "Reports readiness", "what": "Provide or confirm the production Reports, their versions, categories, and intended modules.", "why": "Reports need an approved reusable baseline before teams can rely on them.", "status": "NEEDS_CONTENT", "blocking": "CONTENT", "type": "REPORT", "route": "/dashboard#reports"},
    {"key": "DASHBOARD_ENGINEERING_CONTENT_READINESS", "group": "CONTENT_READINESS", "title": "Engineering Works readiness", "what": "Provide or confirm the Engineering Works references and the professional review boundary.", "why": "Engineering references must be authoritative, current, and clearly separated from professional approval.", "status": "NEEDS_CONTENT", "blocking": "CONTENT", "type": "ENGINEERING_WORK", "route": "/dashboard#engineering-works"},
    {"key": "DASHBOARD_DEFINITIONS_CONTENT_READINESS", "group": "CONTENT_READINESS", "title": "Definitions readiness", "what": "Provide or confirm the canonical business terms, meanings, categories, and module usage.", "why": "Shared definitions keep Forms, Reports, Engineering Works, and workflows semantically aligned.", "status": "NEEDS_CONTENT", "blocking": "CONTENT", "type": "DEFINITION", "route": "/dashboard#definitions"},
    {"key": "DASHBOARD_SYNOLOGY_CONNECTION", "group": "TECHNICAL_GO_LIVE", "title": "Synology connection", "what": "Provide AMEC IT connection details and complete a real Synology health verification for the document source of record.", "why": "Production master-content files must be read from the AMEC-controlled source of record, not the synthetic connector.", "status": "WAITING_ON_AMEC_IT", "blocking": "EXTERNAL_TECHNICAL", "route": "/admin"},
    {"key": "DASHBOARD_FILE_POLICY", "group": "TECHNICAL_GO_LIVE", "title": "File policy", "what": "Confirm the production file policy for DOCX and PDF, including configurable size and version limits.", "why": "A clear file policy keeps uploads predictable and protects source-of-record storage.", "status": "PROPOSED_DEFAULT", "blocking": "TECHNICAL", "route": "/dashboard"},
    {"key": "DASHBOARD_DEFINITION_ARABIC_ALIASES", "group": "OPTIONAL_FUTURE", "title": "Arabic definition aliases", "what": "Decide later whether canonical English terms should have maintained Arabic aliases.", "why": "Aliases can improve bilingual discovery without creating a second definition authority.", "status": "OPTIONAL", "blocking": "OPTIONAL", "route": "/dashboard#definitions"},
    {"key": "MASTER_CONTENT_OWNERSHIP_POLICY", "group": "BUSINESS_DECISION", "title": "Content ownership policy", "what": "Confirm the governed ownership classes: AMEC owned, external official, external reference, and restricted reference sample.", "why": "Ownership determines which source actions AMEC may perform and whether a source can enter production use.", "status": "PROPOSED_DEFAULT", "blocking": "BUSINESS", "route": "/dashboard#forms"},
    {"key": "FORM_ARTIFACT_KIND_TAXONOMY", "group": "BUSINESS_DECISION", "title": "Form artifact kinds", "what": "Confirm the configurable Form artifact-kind vocabulary without changing the four Dashboard libraries.", "why": "Artifact kind is distinct from Category, Purpose, Used In, and Engineering Source Type.", "status": "PROPOSED_DEFAULT", "blocking": "BUSINESS", "route": "/dashboard#forms"},
    {"key": "FORM_SOURCE_CURRENTNESS_AUTHORITY", "group": "BUSINESS_DECISION", "title": "Source currentness authority", "what": "Confirm who may verify, revoke, or mark an external official source not current.", "why": "Upload provenance is not proof of current official status.", "status": "PROPOSED_DEFAULT", "blocking": "BUSINESS", "route": "/dashboard#forms"},
    {"key": "FORM_SOURCE_PROVENANCE_POLICY", "group": "BUSINESS_DECISION", "title": "Source provenance policy", "what": "Confirm the minimum evidence recorded for each exact source version.", "why": "Provenance and currentness must remain independently auditable.", "status": "PROPOSED_DEFAULT", "blocking": "BUSINESS", "route": "/dashboard#forms"},
    {"key": "EXTERNAL_FORM_CONTENT_EDIT_POLICY", "group": "BUSINESS_DECISION", "title": "External official source edits", "what": "Confirm that legal source content is replaced only by ingesting a new immutable official version.", "why": "AMEC metadata governance must not mutate external legal source content in place.", "status": "PROPOSED_DEFAULT", "blocking": "BUSINESS", "route": "/dashboard#forms"},
    {"key": "RESTRICTED_REFERENCE_SAMPLE_POLICY", "group": "BUSINESS_DECISION", "title": "Restricted reference samples", "what": "Confirm who may preview or download restricted samples and how they remain excluded from production resolution.", "why": "Sensitive/project-specific examples need backend-enforced access controls.", "status": "PROPOSED_DEFAULT", "blocking": "BUSINESS", "route": "/dashboard#forms"},
    {"key": "MASTER_CONTENT_QUALITY_FLAG_POLICY", "group": "BUSINESS_DECISION", "title": "Source-quality flags", "what": "Confirm the governed blocker catalog, severity, resolution, and evidence expectations.", "why": "Structured blockers make source readiness explainable and auditable.", "status": "PROPOSED_DEFAULT", "blocking": "BUSINESS", "route": "/dashboard#forms"},
    {"key": "MASTER_CONTENT_ACCEPTED_RISK_AUTHORITY", "group": "BUSINESS_DECISION", "title": "Accepted-risk authority", "what": "Confirm who may accept a source-quality risk and what evidence is required.", "why": "Accepted risk is not an automatic readiness promotion.", "status": "PROPOSED_DEFAULT", "blocking": "BUSINESS", "route": "/dashboard#forms"},
    {"key": "MASTER_CONTENT_MANUAL_READINESS_POLICY", "group": "BUSINESS_DECISION", "title": "Manual-use readiness policy", "what": "Confirm the Wave A gates for Reference Only, Blocked, Manual Use Ready, and Superseded.", "why": "The evaluator must not imply Form automation readiness.", "status": "PROPOSED_DEFAULT", "blocking": "BUSINESS", "route": "/dashboard#forms"},
    {"key": "MASTER_CONTENT_MATERIAL_CHANGE_POLICY", "group": "BUSINESS_DECISION", "title": "Governance material changes", "what": "Confirm which source-governance changes require downstream revalidation.", "why": "Material changes must propagate deterministically without duplicate work.", "status": "PROPOSED_DEFAULT", "blocking": "BUSINESS", "route": "/dashboard#forms"},
    {"key": "SOURCE_SECTION_GOVERNANCE_POLICY", "group": "BUSINESS_DECISION", "title": "Source section governance", "what": "Confirm who may pin and maintain exact source sections on immutable DocumentVersions.", "why": "Source sections are the future lineage seam and must never silently move between versions.", "status": "PROPOSED_DEFAULT", "blocking": "BUSINESS", "route": "/dashboard#forms"},
]


def ensure_dashboard_input_registry(db: Session) -> None:
    existing_rows = db.scalars(select(DashboardInputItem).where(DashboardInputItem.context_key.in_((CONTEXT_KEY, GOVERNANCE_CONTEXT_KEY)))).all()
    existing = {(item.context_key, item.input_key): item for item in existing_rows}
    for spec in SPECS:
        context_key = CONTEXT_KEY if spec["key"] in LEGACY_INPUT_KEYS else GOVERNANCE_CONTEXT_KEY
        # Move development versions of the Wave A items out of the legacy
        # context so the original persistent-count contract remains stable.
        item = existing.get((context_key, spec["key"]))
        if not item and context_key == GOVERNANCE_CONTEXT_KEY:
            item = existing.get((CONTEXT_KEY, spec["key"]))
            if item:
                item.context_key = GOVERNANCE_CONTEXT_KEY
        if not item:
            item = DashboardInputItem(context_key=context_key, input_key=spec["key"], group_name=spec["group"], title=spec["title"], why_needed=spec["why"], requested_input=spec["what"], status=spec["status"], blocking_level=spec["blocking"], owner_role="OWNER", linked_route=spec.get("route"), current_value_json={})
            db.add(item)
        else:
            item.group_name = spec["group"]
            item.title = spec["title"]
            item.why_needed = spec["why"]
            item.requested_input = spec["what"]
            item.linked_route = spec.get("route")
    db.flush()


def _content_state(db: Session, content_type: str) -> dict[str, Any]:
    if content_type == "DEFINITION":
        rows = list(db.scalars(select(DefinitionEntry).where(DefinitionEntry.status == "ACTIVE")).all())
        confirmed = sum(1 for row in rows if str(row.created_by).startswith("production") or str(row.created_by).startswith("amec-production"))
        return {"total": len(rows), "starter": len(rows) - confirmed, "confirmed_production": confirmed, "missing_usage": sum(1 for row in rows if not row.used_in), "source": "Master Content Definitions"}
    rows = [row for row in db.scalars(select(MasterContentItem).where(MasterContentItem.content_type == content_type, MasterContentItem.status == "ACTIVE")).all() if not (row.ref or "").startswith(("E2E", "B-F", "B-E", "AF-MSN", "DEPLOY-PROBE"))]
    confirmed = sum(1 for row in rows if str(row.created_by).startswith("production") or str(row.created_by).startswith("amec-production"))
    return {"total": len(rows), "starter": len(rows) - confirmed, "confirmed_production": confirmed, "missing_category": sum(1 for row in rows if not row.category_id), "missing_usage": sum(1 for row in rows if not row.used_in), "source": "Master Content Library"}


def _current_state(db: Session, spec: dict[str, Any]) -> dict[str, Any]:
    key = spec["key"]
    if key.startswith("ADMIN_"):
        return {"summary": "Safe default is available; explicit Owner confirmation remains required.", "safe_default": True, "owner_surface": "/admin/contract-setup"}
    if spec.get("type"):
        state = _content_state(db, spec["type"])
        state["summary"] = f"{state['total']} active starter/demo record(s); {state['confirmed_production']} confirmed production record(s)."
        return state
    if key == "DASHBOARD_CATEGORY_TAXONOMY":
        categories = list(db.scalars(select(ContentCategory).where(ContentCategory.active == true()).order_by(ContentCategory.sort_order, ContentCategory.label)).all())
        return {"categories": [{"label": c.label, "content_types": c.allowed_content_types} for c in categories], "summary": f"{len(categories)} starter configurable categories are available across the four libraries."}
    if key == "DASHBOARD_CATEGORY_SEMANTICS":
        return {"category": "Owner-managed business classification", "engineering_source_type": "Provenance taxonomy", "engineering_discipline": "Technical applicability taxonomy", "summary": "Category, Engineering Source Type, and Discipline are separate fields; Owner confirmation is still required."}
    if key == "DASHBOARD_REFERENCE_NUMBERING":
        # This is a proposed Owner policy, not a live allocation preview.
        # Keep the decision stable when earlier synthetic tests or existing
        # content have advanced the runtime sequence counters.
        patterns = ["F-0001", "R-0001", "E-0001", "D-0001"]
        return {"patterns": patterns, "summary": "Proposed references are F-0001, R-0001, E-0001, and D-0001."}
    if key == "DASHBOARD_ENGINEERING_SOURCE_TYPES":
        return {"values": list(ENGINEERING_SOURCE_TYPES), "summary": "Starter source types are explicit and separate from Category; Owner confirmation is still required."}
    if key == "DASHBOARD_ENGINEERING_DISCIPLINES":
        return {"values": list(ENGINEERING_DISCIPLINES), "summary": "Starter discipline values are explicit and separate from Category; Owner confirmation is still required."}
    if key.endswith("_REFERENCE_POLICY"):
        content_type = {"DASHBOARD_FORM_REFERENCE_POLICY": "FORM", "DASHBOARD_REPORT_REFERENCE_POLICY": "REPORT", "DASHBOARD_ENGINEERING_REFERENCE_POLICY": "ENGINEERING_WORK", "DASHBOARD_DEFINITION_REFERENCE_POLICY": "DEFINITION"}[key]
        sequence = db.scalar(select(MasterContentReferenceSequence).where(MasterContentReferenceSequence.content_type == content_type, MasterContentReferenceSequence.active == true()))
        return {"content_type": content_type, "prefix": sequence.prefix if sequence else None, "padding": sequence.padding if sequence else None, "renumber_existing": False, "summary": "Current policy is a proposed default; changing it does not renumber existing references."}
    if key == "DASHBOARD_MODULE_USAGE_POLICY":
        return {"policy": {"Forms": "Proposal, Contract, Permit, Engineering, Administration", "Reports": "Proposal, Contract, Permit, Engineering, Reports, Administration", "Engineering Works": "Engineering, Permit, Issues, Reports", "Definitions": "Proposal, Contract, Permit, Engineering, Reports, Administration"}, "summary": "Starter module bindings are configurable and visible in each library."}
    if key == "DASHBOARD_ENGINEERING_ACTIVATION_POLICY":
        return {"summary": "No activation policy selected. Upload and technical verification do not equal professional engineering approval."}
    if key == "DASHBOARD_REPORT_SCOPE_POLICY":
        return {"summary": "Reusable master Reports are separate from project-specific outputs; AMEC confirmation remains open."}
    if key == "DASHBOARD_MASTER_WRITE_PERMISSIONS":
        return {"summary": "Owner-only master-content management is enforced; Business Development and Engineering are read/use roles."}
    if key in {"DASHBOARD_OFFICIAL_PROPOSAL_TEMPLATE", "DASHBOARD_OFFICIAL_PROPOSAL_CHECKLIST", "DASHBOARD_OFFICIAL_CONTRACT_TEMPLATE"}:
        purpose = {"DASHBOARD_OFFICIAL_PROPOSAL_TEMPLATE": ("BD", "PROPOSAL_TEMPLATE"), "DASHBOARD_OFFICIAL_PROPOSAL_CHECKLIST": ("BD", "PROPOSAL_CHECKLIST"), "DASHBOARD_OFFICIAL_CONTRACT_TEMPLATE": ("ADMIN", "CONTRACT_TEMPLATE")}[key]
        resolution = resolve_master_content_purpose(db, module=purpose[0], usage_type=purpose[1])
        return {"resolution": resolution, "summary": f"{resolution['status']} resolver with {resolution['canonical_count']} active canonical item(s). Owner confirmation remains required."}
    if key == "DASHBOARD_SYNOLOGY_CONNECTION":
        synology = next((item for item in _connections(db) if item["name"] == "Synology / document SOR"), {})
        connected = synology.get("production_status") == "Production Connected" and synology.get("status") in {"Connected", "Healthy"}
        return {"summary": "Production Synology connection is verified." if connected else "Production connection is not configured/verified; synthetic connector is available.", "production_status": synology.get("production_status", "Production Not Connected"), "synthetic_status": synology.get("status", "Simulator Check Failed"), "verified": connected}
    if key == "DASHBOARD_FILE_POLICY":
        return {"extensions": [".docx", ".pdf"], "summary": "DOCX and PDF are supported by the current UI; production limits remain configuration-driven."}
    if key == "DASHBOARD_DEFINITION_ARABIC_ALIASES":
        return {"summary": "Deferred; canonical English terms remain authoritative."}
    return {"summary": "Current proposal is available for AMEC review."}


def _history(db: Session, item_id: str) -> list[dict[str, Any]]:
    events = db.scalars(select(AuditEvent).where(AuditEvent.entity_type == "DashboardInputItem", AuditEvent.entity_id == item_id).order_by(AuditEvent.occurred_at.desc()).limit(10)).all()
    return [{"event": event.event_type, "actor": event.actor_id or "System", "at": event.occurred_at.isoformat() if event.occurred_at else None, "note": (event.metadata_json or {}).get("note")} for event in events]


def project_input(db: Session, item: DashboardInputItem) -> dict[str, Any]:
    spec = next(spec for spec in SPECS if spec["key"] == item.input_key)
    state = _current_state(db, spec)
    status = item.status
    if item.input_key == "DASHBOARD_SYNOLOGY_CONNECTION" and not state.get("verified") and status in {"CONFIRMED", "COMPLETE"}:
        status = "WAITING_ON_AMEC_IT"
    return {"key": item.input_key, "title": item.title, "group": item.group_name, "group_label": GROUP_LABELS[item.group_name], "what": item.requested_input, "why": item.why_needed, "current": state, "status": status, "status_label": FRIENDLY_STATUS.get(status, "Needs review"), "blocking": item.blocking_level, "blocking_label": "Technical dependency" if item.blocking_level == "EXTERNAL_TECHNICAL" else "Optional" if item.blocking_level == "OPTIONAL" else "Business input" if item.blocking_level == "BUSINESS" else "Content input" if item.blocking_level == "CONTENT" else "Technical input", "notes": item.notes, "route": item.linked_route, "confirmed_by": item.confirmed_by, "confirmed_at": item.confirmed_at.isoformat() if item.confirmed_at else None, "history": _history(db, item.id)}


def dashboard_inputs_payload(db: Session, *, include_governance: bool = False) -> dict[str, Any]:
    ensure_dashboard_input_registry(db)
    contexts = (CONTEXT_KEY, GOVERNANCE_CONTEXT_KEY) if include_governance else (CONTEXT_KEY,)
    stored = {item.input_key: item for item in db.scalars(select(DashboardInputItem).where(DashboardInputItem.context_key.in_(contexts))).all()}
    items = [project_input(db, stored[spec["key"]]) for spec in SPECS if spec["key"] in stored and (include_governance or spec["key"] in LEGACY_INPUT_KEYS)]
    unresolved = [item for item in items if item["status"] not in {"CONFIRMED", "COMPLETE", "NOT_APPLICABLE", "OPTIONAL"}]
    technical = [item for item in unresolved if item["blocking"] == "EXTERNAL_TECHNICAL"]
    return {"context_key": CONTEXT_KEY, "summary": {"confirmed": len(items) - len(unresolved) - sum(1 for item in items if item["status"] == "OPTIONAL"), "remaining": len(unresolved), "technical_remaining": len(technical), "ready": not unresolved}, "source_blocker_rollup": source_blocker_rollup(db), "groups": [{"key": key, "label": label, "items": [item for item in items if item["group"] == key]} for key, label in GROUP_LABELS.items() if any(item["group"] == key for item in items)], "items": items}


def default_status(input_key: str) -> str:
    return next(spec["status"] for spec in SPECS if spec["key"] == input_key)
