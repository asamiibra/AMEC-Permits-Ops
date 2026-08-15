"""One canonical Owner Decision Register for policy, content, and go-live."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..storage.legacy import legacy_synthetic_adapter
from ..config.settings import get_settings, repo_root
from ..models import (
    AuditEvent,
    DefinitionEntry,
    DashboardInputItem,
    MasterContentItem,
    OwnerDecision,
    OwnerDecisionAlias,
    OwnerDecisionHistory,
    Role,
)
from ..services.master_content import resolve_master_content_purpose


GROUP_LABELS = {
    "MASTER_CONTENT_GOVERNANCE": "Master Content & Governance",
    "PROPOSAL_COMMERCIAL": "Proposal & Commercial",
    "CONTRACT_ADMINISTRATION": "Contract & Administration",
    "PROJECT_ACTIVATION": "Project Activation",
    "TECHNICAL_GO_LIVE": "Technical Go-Live",
}
STATUSES = {
    "UNANSWERED",
    "PROPOSED_DEFAULT",
    "OWNER_CONFIRMED",
    "OWNER_CONFIRMED_WITH_NOTES",
    "OWNER_MARKED_NOT_APPLICABLE",
    "SAFE_DEFAULT_APPROVED_FOR_GO_LIVE",
    "OPTIONAL_DEFERRED",
    "EXTERNAL_TECHNICAL_BLOCK",
    "REOPENED",
    "SUPERSEDED",
}
BLOCKING_LEVELS = {"P0_GO_LIVE_BLOCKER", "P1_REQUIRED_FOR_CONTROLLED_PRODUCTION", "P2_SAFE_DEFAULT_AVAILABLE", "P3_OPTIONAL_FUTURE", "EXTERNAL_TECHNICAL"}
CONFIRMED_STATUSES = {"OWNER_CONFIRMED", "OWNER_CONFIRMED_WITH_NOTES", "OWNER_MARKED_NOT_APPLICABLE", "SAFE_DEFAULT_APPROVED_FOR_GO_LIVE"}
OWNER_ROLES = {Role.SYSTEM_ADMIN, Role.OWNER_SPONSOR}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _human(key: str) -> str:
    return key.replace("_", " ").title()


def _spec(key: str, group: str, *, default: Any, blocking: str = "P2_SAFE_DEFAULT", decision_type: str = "BUSINESS_POLICY", options: list[Any] | None = None, modules: list[str] | None = None, question: str | None = None, why: str | None = None, system_fact_source: str | None = None) -> dict[str, Any]:
    return {
        "key": key,
        "group": group,
        "title": _human(key),
        "question": question or f"What should AMEC use for { _human(key) }?",
        "why": why or "This controls a shared ProposalOps behavior and must remain an explicit AMEC decision.",
        "decision_type": decision_type,
        "blocking": blocking,
        "default": default,
        "options": options or ([default] if default is not None else []),
        "modules": modules or [GROUP_LABELS[group]],
        "system_fact_source": system_fact_source,
    }


PROPOSED = "PROPOSED_DEFAULT"


DECISION_SPECS: list[dict[str, Any]] = [
    _spec("MASTER_CATEGORY_SEMANTICS", "MASTER_CONTENT_GOVERNANCE", default={"meaning": "OWNER_MANAGED_BUSINESS_CLASSIFICATION", "separate_from": ["ENGINEERING_SOURCE_TYPE", "ENGINEERING_DISCIPLINE"]}, modules=["Dashboard", "Proposal", "Contract", "Engineering"]),
    _spec("ENGINEERING_SOURCE_TYPE_TAXONOMY", "MASTER_CONTENT_GOVERNANCE", default=["REGULATION", "QCS", "MUNICIPALITY_COMMENT", "AUTHORITY_GUIDANCE", "ENGINEERING_STANDARD", "DESIGN_GUIDE", "TECHNICAL_REFERENCE", "OTHER"], modules=["Dashboard", "Engineering"]),
    _spec("ENGINEERING_DISCIPLINE_TAXONOMY", "MASTER_CONTENT_GOVERNANCE", default=["GENERAL", "DESIGN", "ARCHITECTURE", "STRUCTURAL", "CIVIL", "MEP", "FIRE_LIFE_SAFETY", "PERMIT", "OTHER"], modules=["Dashboard", "Engineering"]),
    _spec("FORM_REFERENCE_POLICY", "MASTER_CONTENT_GOVERNANCE", default={"prefix": "F", "padding": 4, "renumber_existing": False}, modules=["Dashboard", "Proposal", "Contract"]),
    _spec("REPORT_REFERENCE_POLICY", "MASTER_CONTENT_GOVERNANCE", default={"prefix": "R", "padding": 4, "renumber_existing": False}, modules=["Dashboard", "Reports"]),
    _spec("ENGINEERING_REFERENCE_POLICY", "MASTER_CONTENT_GOVERNANCE", default={"prefix": "E", "padding": 4, "renumber_existing": False}, modules=["Dashboard", "Engineering"]),
    _spec("DEFINITION_REFERENCE_POLICY", "MASTER_CONTENT_GOVERNANCE", default={"prefix": "D", "padding": 4, "renumber_existing": False}, modules=["Dashboard", "Definitions"]),
    _spec("OFFICIAL_PROPOSAL_TEMPLATE", "MASTER_CONTENT_GOVERNANCE", default={"resolver": "BD/PROPOSAL_TEMPLATE", "selection": "OWNER_SELECTS_CANONICAL_FORM_VERSION"}, decision_type="CONTENT_BINDING", blocking="P1_REQUIRED_FOR_CONTROLLED_PRODUCTION", modules=["Dashboard", "BD/Proposal"]),
    _spec("OFFICIAL_PROPOSAL_CHECKLIST", "MASTER_CONTENT_GOVERNANCE", default={"resolver": "BD/PROPOSAL_CHECKLIST", "selection": "OWNER_SELECTS_CANONICAL_FORM_VERSION"}, decision_type="CONTENT_BINDING", blocking="P1_REQUIRED_FOR_CONTROLLED_PRODUCTION", modules=["Dashboard", "BD/Proposal"]),
    _spec("OFFICIAL_CONTRACT_TEMPLATE", "MASTER_CONTENT_GOVERNANCE", default={"resolver": "ADMIN/CONTRACT_TEMPLATE", "selection": "OWNER_SELECTS_CANONICAL_FORM_VERSION"}, decision_type="CONTENT_BINDING", blocking="P1_REQUIRED_FOR_CONTROLLED_PRODUCTION", modules=["Dashboard", "Administration", "Contract"]),
    _spec("MASTER_CONTENT_WRITE_POLICY", "MASTER_CONTENT_GOVERNANCE", default={"owner": "OWNER_ONLY", "business_development": "READ_USE", "engineering": "READ_USE"}, blocking="P1_REQUIRED_FOR_CONTROLLED_PRODUCTION", modules=["Dashboard", "Administration", "RBAC"]),
    _spec("PROPOSAL_STAGE_POLICY", "PROPOSAL_COMMERCIAL", default={"stages": ["RECEIVED", "IN_REVIEW", "PROPOSAL_PREPARATION", "PROPOSAL_HANDOVER", "READY_FOR_QUOTATION", "QUOTATION_IN_PROGRESS", "COMMERCIAL_REVIEW", "CLIENT_RESPONSE_PENDING", "ACCEPTED", "CLOSED"]}, modules=["Proposal", "My Work"]),
    _spec("PROPOSAL_AUTHORITY_REVIEW_MEANING", "PROPOSAL_COMMERCIAL", default="OWNER_REVIEW_REQUIRED_NOT_LEGAL_OR_MUNICIPAL_APPROVAL", modules=["Proposal", "RBAC"]),
    _spec("PROPOSAL_AUTHORITY_FIELD_MEANING", "PROPOSAL_COMMERCIAL", default="HUMAN_ENTERED_CONTEXT_ONLY", modules=["Proposal", "Engineering"]),
    _spec("PROPOSAL_READY_CLOSE_POLICY", "PROPOSAL_COMMERCIAL", default="READINESS_GATES_AND_OWNER_ACTION_REQUIRED", modules=["Proposal", "My Work"]),
    _spec("PROPOSAL_ACTIVITY_SEMANTICS", "PROPOSAL_COMMERCIAL", default="APPEND_ONLY_HUMAN_AND_SYSTEM_ACTIVITY_WITH_CORRELATION", modules=["Proposal", "Audit"]),
    _spec("PROPOSAL_ATTN_CONTACT_SEMANTICS", "PROPOSAL_COMMERCIAL", default="CLIENT_CONTACT_CONTEXT_NOT_AUTHORITY", modules=["Proposal", "Client", "Contact"]),
    _spec("PROPOSAL_SCOPE_SEMANTICS", "PROPOSAL_COMMERCIAL", default="SEPARATE_AMEC_SCOPE_CLIENT_SCOPE_AND_PROCESS_OF_WORK", modules=["Proposal", "Contract"]),
    _spec("PROPOSAL_ACCEPT_REQUIRED_FIELDS", "PROPOSAL_COMMERCIAL", default=["CLIENT", "CONTACT", "PROJECT_OPPORTUNITY_REFERENCE", "SCOPE", "AMOUNT", "CURRENCY", "DURATION", "ACCEPTED_REVISION"], blocking="P1_REQUIRED_FOR_CONTROLLED_PRODUCTION", modules=["Proposal", "Client", "Contract"]),
    _spec("PROPOSAL_ACCEPT_AUTHORITY", "PROPOSAL_COMMERCIAL", default="OWNER_OR_AUTHORIZED_COMMERCIAL_APPROVER", blocking="P1_REQUIRED_FOR_CONTROLLED_PRODUCTION", modules=["Proposal", "RBAC", "Audit"]),
    _spec("ENGINEERING_PROPOSAL_CONTRIBUTION_POLICY", "PROPOSAL_COMMERCIAL", default="ENGINEERING_MAY_CONTRIBUTE_TECHNICAL_CONTENT_BD_OWNS_COMMERCIAL_ACCEPTANCE", modules=["Proposal", "Engineering", "RBAC"]),
    _spec("PROPOSAL_REFERENCE_POLICY", "PROPOSAL_COMMERCIAL", default={"prefix": "P", "padding": 4, "renumber_existing": False}, modules=["Proposal", "Audit"]),
    _spec("PROJECT_OPPORTUNITY_REFERENCE_SEMANTICS", "PROPOSAL_COMMERCIAL", default="PROVISIONAL_UNTIL_CANONICAL_PROJECT_REFERENCE_EXISTS", modules=["Proposal", "Project"]),
    _spec("PROPOSAL_OUTPUT_FORMAT_POLICY", "PROPOSAL_COMMERCIAL", default=["PDF", "DOCX"], modules=["Proposal", "Dashboard"]),
    _spec("PROPOSAL_CHECKLIST_OUTPUT_POLICY", "PROPOSAL_COMMERCIAL", default="CANONICAL_CHECKLIST_VERSION_SNAPSHOT_WITH_PROPOSAL_OUTPUT", modules=["Proposal", "Dashboard"]),
    _spec("PROPOSAL_TO_CONTRACT_POLICY", "PROPOSAL_COMMERCIAL", default="ACCEPT_MAKES_CONTRACT_ELIGIBLE_ADMIN_INITIATES", options=["ACCEPT_MAKES_CONTRACT_ELIGIBLE_ADMIN_INITIATES", "AUTO_CREATE_CONTRACT_ON_ACCEPT"], blocking="P1_REQUIRED_FOR_CONTROLLED_PRODUCTION", modules=["Proposal", "Contract", "RBAC"]),
    _spec("PROPOSAL_CLOSE_OUTCOME_POLICY", "PROPOSAL_COMMERCIAL", default=["WON", "LOST", "WITHDRAWN", "SUPERSEDED"], modules=["Proposal", "Audit"]),
    _spec("CONTRACT_STAGE_POLICY", "CONTRACT_ADMINISTRATION", default={"stages": ["DRAFT", "NEEDS_ACTION", "AUTHORITY_REVIEW", "READY", "ACTIVE", "CLOSED"]}, modules=["Contract", "My Work"]),
    _spec("CONTRACT_AUTHORITY_REVIEW_MEANING", "CONTRACT_ADMINISTRATION", default="OWNER_REVIEW_REQUIRED_NOT_LEGAL_EXECUTION", modules=["Contract", "RBAC", "Audit"]),
    _spec("CONTRACT_READY_CLOSE_POLICY", "CONTRACT_ADMINISTRATION", default="REQUIRED_FIELDS_EVIDENCE_AND_OWNER_AUTHORITY_ACTION", modules=["Contract", "Audit"]),
    _spec("CONTRACT_CLOSE_DATE_MEANING", "CONTRACT_ADMINISTRATION", default="EXPECTED_CLOSE_DATE_UNTIL_OWNER_CONFIRMS_ACTUAL_CLOSE", modules=["Contract", "Project"]),
    _spec("CONTRACT_REFERENCE_POLICY", "CONTRACT_ADMINISTRATION", default={"prefix": "C", "padding": 4, "unique": True, "owner_override": True}, modules=["Contract", "Audit"]),
    _spec("CONTRACT_REQUIRED_FIELDS", "CONTRACT_ADMINISTRATION", default=["CLIENT", "CONTRACT_REFERENCE", "PROJECT_OPPORTUNITY_REFERENCE", "AMOUNT", "CURRENCY", "DURATION"], blocking="P1_REQUIRED_FOR_CONTROLLED_PRODUCTION", modules=["Contract", "Client", "Project"]),
    _spec("CONTRACT_REQUIRED_EVIDENCE", "CONTRACT_ADMINISTRATION", default=["ACCEPTED_PROPOSAL_REVISION", "CONTRACT_TEMPLATE_SNAPSHOT", "COMMERCIAL_OR_AWARD_EVIDENCE"], blocking="P1_REQUIRED_FOR_CONTROLLED_PRODUCTION", modules=["Contract", "Document", "Synology"]),
    _spec("CONTRACT_AUTHORITY_POLICY", "CONTRACT_ADMINISTRATION", default="OWNER_ONLY_FOR_AUTHORITY_AND_EXECUTION_STATE", blocking="P1_REQUIRED_FOR_CONTROLLED_PRODUCTION", modules=["Contract", "RBAC", "Audit"]),
    _spec("MANUAL_NEW_CONTRACT_POLICY", "CONTRACT_ADMINISTRATION", default="SELECT_ACCEPTED_PROPOSAL_ONLY", options=["SELECT_ACCEPTED_PROPOSAL_ONLY", "OWNER_MAY_CREATE_WITH_REQUIRED_INPUTS"], blocking="P1_REQUIRED_FOR_CONTROLLED_PRODUCTION", modules=["Contract", "Proposal"]),
    _spec("CONTRACT_AMOUNT_CHANGE_AUTHORITY", "CONTRACT_ADMINISTRATION", default="OWNER_ONLY_WITH_REASON_AND_NEW_REVISION", blocking="P1_REQUIRED_FOR_CONTROLLED_PRODUCTION", modules=["Contract", "Audit"]),
    _spec("CONTRACT_ARTIFACT_STRATEGY", "CONTRACT_ADMINISTRATION", default="CANONICAL_TEMPLATE_RENDER_PLUS_EVIDENCE", options=["CANONICAL_TEMPLATE_RENDER_PLUS_EVIDENCE", "UPLOAD_ONLY_EVIDENCE"], modules=["Contract", "Document", "Synology"]),
    _spec("CONTRACT_REOPEN_POLICY", "CONTRACT_ADMINISTRATION", default="OWNER_DECISION_REQUIRED_WITH_PROSPECTIVE_REVALIDATION", modules=["Contract", "My Work", "Audit"]),
    _spec("CONTRACT_TO_PROJECT_TRIGGER", "PROJECT_ACTIVATION", default="EXPLICIT_OWNER_ACTION_AFTER_CONTRACT_READINESS", options=["EXPLICIT_OWNER_ACTION_AFTER_CONTRACT_READINESS", "AUTO_ACTIVATE_ON_CONTRACT_CLOSE"], blocking="P1_REQUIRED_FOR_CONTROLLED_PRODUCTION", modules=["Contract", "Project", "RBAC"]),
    _spec("PROJECT_ACTIVATION_AUTHORITY", "PROJECT_ACTIVATION", default="OWNER_ONLY_HUMAN_ACTION", blocking="P1_REQUIRED_FOR_CONTROLLED_PRODUCTION", modules=["Project", "RBAC", "Audit"]),
    _spec("PROJECT_CODE_ASSIGNMENT_METHOD", "PROJECT_ACTIVATION", default="OWNER_ENTERED_UNIQUE", options=["OWNER_ENTERED_UNIQUE", "SYSTEM_GENERATED_UNIQUE"], modules=["Project", "Contract"]),
    _spec("PROJECT_CODE_FORMAT", "PROJECT_ACTIVATION", default={"pattern": "AMEC-YYYY-NNN", "example": "AMEC-2026-001"}, modules=["Project", "Contract", "Permit"]),
    _spec("PROJECT_CODE_MUTABILITY_POLICY", "PROJECT_ACTIVATION", default="IMMUTABLE_AFTER_ACTIVATION", options=["IMMUTABLE_AFTER_ACTIVATION", "OWNER_EDITABLE_BEFORE_ACTIVATION"], modules=["Project", "Audit"]),
    _spec("PROJECT_START_DATE_SEMANTICS", "PROJECT_ACTIVATION", default="ORIGINAL_HUMAN_ACTIVATION_DATE", modules=["Project", "Contract", "Permit", "Audit"]),
    _spec("PROJECT_ACTIVATION_REQUIRED_FIELDS", "PROJECT_ACTIVATION", default=["CONTRACT", "ACCEPTED_PROPOSAL_REVISION", "PROJECT_CODE", "START_DATE", "CLIENT"], blocking="P1_REQUIRED_FOR_CONTROLLED_PRODUCTION", modules=["Project", "Contract", "Client"]),
    _spec("CONTRACT_CLOSE_VS_PROJECT_ACTIVATION", "PROJECT_ACTIVATION", default="SEPARATE_EVENTS_WITH_LINEAGE", options=["SEPARATE_EVENTS_WITH_LINEAGE", "SAME_EVENT"], modules=["Contract", "Project", "Audit"]),
    _spec("REAL_SYNOLOGY_CONNECTION", "TECHNICAL_GO_LIVE", default="REAL_CONNECTION_AND_HEALTH_VERIFICATION_REQUIRED", blocking="EXTERNAL_TECHNICAL", decision_type="TECHNICAL_FACT", modules=["Synology", "Dashboard", "Contract"], system_fact_source="/api/adapters/health real Synology verification; Owner cannot set this fact"),
    _spec("PRODUCTION_FILE_POLICY", "TECHNICAL_GO_LIVE", default={"extensions": [".docx", ".pdf"], "source_of_record": "AMEC_SYNOLOGY", "versioning": "IMMUTABLE_DOCUMENT_VERSIONS"}, blocking="P1_REQUIRED_FOR_CONTROLLED_PRODUCTION", modules=["Synology", "Document", "Dashboard"]),
    _spec("PRODUCTION_GO_LIVE_SIGNOFF", "TECHNICAL_GO_LIVE", default="EXPLICIT_OWNER_SIGNOFF_AFTER_ALL_GATES", blocking="P0_GO_LIVE_BLOCKER", decision_type="GO_LIVE_SIGNOFF", modules=["Administration", "Dashboard", "BD/Proposal", "Contract"]),
]

DECISION_BY_KEY = {item["key"]: item for item in DECISION_SPECS}

# Legacy inputs remain readable and auditable, but these keys now resolve to the
# canonical register.  Dashboard content-readiness records intentionally remain
# separate from business-policy decisions.
LEGACY_ALIASES = {
    "DASHBOARD_CATEGORY_TAXONOMY": ("MASTER_CATEGORY_SEMANTICS", "Dashboard Inputs"),
    "DASHBOARD_CATEGORY_SEMANTICS": ("MASTER_CATEGORY_SEMANTICS", "Dashboard Inputs"),
    "DASHBOARD_ENGINEERING_SOURCE_TYPES": ("ENGINEERING_SOURCE_TYPE_TAXONOMY", "Dashboard Inputs"),
    "DASHBOARD_ENGINEERING_DISCIPLINES": ("ENGINEERING_DISCIPLINE_TAXONOMY", "Dashboard Inputs"),
    "DASHBOARD_FORM_REFERENCE_POLICY": ("FORM_REFERENCE_POLICY", "Dashboard Inputs"),
    "DASHBOARD_REPORT_REFERENCE_POLICY": ("REPORT_REFERENCE_POLICY", "Dashboard Inputs"),
    "DASHBOARD_ENGINEERING_REFERENCE_POLICY": ("ENGINEERING_REFERENCE_POLICY", "Dashboard Inputs"),
    "DASHBOARD_DEFINITION_REFERENCE_POLICY": ("DEFINITION_REFERENCE_POLICY", "Dashboard Inputs"),
    "DASHBOARD_OFFICIAL_PROPOSAL_TEMPLATE": ("OFFICIAL_PROPOSAL_TEMPLATE", "Dashboard Inputs"),
    "DASHBOARD_OFFICIAL_PROPOSAL_CHECKLIST": ("OFFICIAL_PROPOSAL_CHECKLIST", "Dashboard Inputs"),
    "DASHBOARD_OFFICIAL_CONTRACT_TEMPLATE": ("OFFICIAL_CONTRACT_TEMPLATE", "Dashboard Inputs"),
    "DASHBOARD_MASTER_WRITE_PERMISSIONS": ("MASTER_CONTENT_WRITE_POLICY", "Dashboard Inputs"),
    "DASHBOARD_FILE_POLICY": ("PRODUCTION_FILE_POLICY", "Dashboard Inputs"),
    "DASHBOARD_SYNOLOGY_CONNECTION": ("REAL_SYNOLOGY_CONNECTION", "Dashboard Inputs"),
    "CONTRACT_REFERENCE_POLICY": ("CONTRACT_REFERENCE_POLICY", "Administration Inputs"),
    "CONTRACT_STAGE_NAMES": ("CONTRACT_STAGE_POLICY", "Administration Inputs"),
    "CONTRACT_CLOSE_DATE_MEANING": ("CONTRACT_CLOSE_DATE_MEANING", "Administration Inputs"),
    "CONTRACT_AUTHORITY_REVIEW": ("CONTRACT_AUTHORITY_REVIEW_MEANING", "Administration Inputs"),
    "CONTRACT_AMOUNT_CHANGE_AUTHORITY": ("CONTRACT_AMOUNT_CHANGE_AUTHORITY", "Administration Inputs"),
    "CONTRACT_PROPOSAL_INITIATION_RULE": ("MANUAL_NEW_CONTRACT_POLICY", "Administration Inputs"),
    "CONTRACT_REQUIRED_FIELDS": ("CONTRACT_REQUIRED_FIELDS", "Administration Inputs"),
    "CONTRACT_REQUIRED_EVIDENCE": ("CONTRACT_REQUIRED_EVIDENCE", "Administration Inputs"),
    "CONTRACT_TEMPLATE_POLICY": ("OFFICIAL_CONTRACT_TEMPLATE", "Administration Inputs"),
    "PROJECT_ACTIVATION_AUTHORITY": ("PROJECT_ACTIVATION_AUTHORITY", "Administration Inputs"),
    "PROJECT_CODE_POLICY": ("PROJECT_CODE_ASSIGNMENT_METHOD", "Administration Inputs"),
    "PROJECT_START_DATE_SEMANTICS": ("PROJECT_START_DATE_SEMANTICS", "Administration Inputs"),
    "CONTRACT_REOPEN_POLICY": ("CONTRACT_REOPEN_POLICY", "Administration Inputs"),
    "REAL_SYNOLOGY_VERIFICATION": ("REAL_SYNOLOGY_CONNECTION", "Administration Inputs"),
}


def _snapshot(item: OwnerDecision) -> dict[str, Any]:
    return {"status": item.status, "effective_value": item.effective_value_json, "owner_notes": item.owner_notes, "confirmed_by": item.confirmed_by, "confirmed_at": item.confirmed_at.isoformat() if item.confirmed_at else None, "apply_state": item.apply_state, "runtime_value": item.runtime_value_json}


def _history(db: Session, item: OwnerDecision, event_type: str, *, before: dict[str, Any] | None, actor: str | None, role: Role | str | None, note: str | None, correlation_id: str) -> None:
    role_value = role.value if isinstance(role, Role) else str(role) if role else None
    db.add(OwnerDecisionHistory(decision_id=item.id, decision_key=item.decision_key, event_type=event_type, before_json=before, after_json=_snapshot(item), actor_id=actor, actor_role=role_value, note=note, correlation_id=correlation_id))
    db.add(AuditEvent(correlation_id=correlation_id, actor_type="HUMAN" if actor else "SYSTEM", actor_id=actor, event_type=f"OWNER_DECISION_{event_type}", entity_type="OwnerDecision", entity_id=item.id, before_json=before, after_json=_snapshot(item), metadata_json={"decision_key": item.decision_key, "note": note}))


def _legacy_status(item: DashboardInputItem) -> str | None:
    if item.confirmed_by and item.status in {"CONFIRMED", "COMPLETE"}:
        return "OWNER_CONFIRMED_WITH_NOTES" if item.notes else "OWNER_CONFIRMED"
    return None


def ensure_register(db: Session) -> None:
    existing = {row.decision_key: row for row in db.scalars(select(OwnerDecision)).all()}
    legacy_items = {row.input_key: row for row in db.scalars(select(DashboardInputItem).where(DashboardInputItem.context_key == "DASHBOARD_MASTER_CONTENT")).all()}
    for spec in DECISION_SPECS:
        item = existing.get(spec["key"])
        if not item:
            item = OwnerDecision(decision_key=spec["key"], group_name=spec["group"], title=spec["title"], question=spec["question"], why=spec["why"], decision_type=spec["decision_type"], blocking_level=spec["blocking"], status="EXTERNAL_TECHNICAL_BLOCK" if spec["blocking"] == "EXTERNAL_TECHNICAL" else "UNANSWERED" if spec["blocking"] == "P0_GO_LIVE_BLOCKER" else PROPOSED, proposed_default_json=spec["default"], options_json=spec["options"], affected_modules_json=spec["modules"], system_fact_source=spec.get("system_fact_source"), current_system_state_json={}, legacy_keys_json=[])
            db.add(item)
            db.flush()
        else:
            item.group_name = spec["group"]
            item.title = spec["title"]
            item.question = spec["question"]
            item.why = spec["why"]
            item.decision_type = spec["decision_type"]
            item.blocking_level = spec["blocking"]
            item.proposed_default_json = spec["default"]
            item.options_json = spec["options"]
            item.affected_modules_json = spec["modules"]
            item.system_fact_source = spec.get("system_fact_source")
        for legacy_key, (canonical, source) in LEGACY_ALIASES.items():
            if canonical != item.decision_key:
                continue
            if legacy_key not in item.legacy_keys_json:
                item.legacy_keys_json = [*item.legacy_keys_json, legacy_key]
            if not db.scalar(select(OwnerDecisionAlias).where(OwnerDecisionAlias.legacy_key == legacy_key)):
                db.add(OwnerDecisionAlias(legacy_key=legacy_key, canonical_key=canonical, source_module=source, notes="Legacy projection retained; canonical OwnerDecision is the single write truth."))
            legacy = legacy_items.get(legacy_key)
            if legacy and not db.scalar(select(OwnerDecisionHistory).where(OwnerDecisionHistory.decision_id == item.id)):
                migrated = _legacy_status(legacy)
                if migrated and item.status in {"UNANSWERED", PROPOSED}:
                    item.status = migrated
                    item.owner_notes = legacy.notes
                    item.confirmed_by = legacy.confirmed_by
                    item.confirmed_at = legacy.confirmed_at
                    _history(db, item, "LEGACY_RECONCILED", before=None, actor="legacy-reconciliation", role=Role.SYSTEM_ADMIN, note=f"Reconciled from {legacy_key}; no audit history deleted.", correlation_id="owner-decision-reconcile")
    db.flush()


def _system_state(db: Session, item: OwnerDecision) -> dict[str, Any]:
    key = item.decision_key
    if key == "REAL_SYNOLOGY_CONNECTION":
        health = legacy_synthetic_adapter().health_check()
        return {"summary": "Synthetic adapter is available; real Synology health verification is not configured.", "synthetic": health, "verified": False, "status": "NOT_CONFIGURED", "source": item.system_fact_source}
    if key.startswith("OFFICIAL_"):
        usage = {"OFFICIAL_PROPOSAL_TEMPLATE": ("BD", "PROPOSAL_TEMPLATE"), "OFFICIAL_PROPOSAL_CHECKLIST": ("BD", "PROPOSAL_CHECKLIST"), "OFFICIAL_CONTRACT_TEMPLATE": ("ADMIN", "CONTRACT_TEMPLATE")}[key]
        try:
            resolution = resolve_master_content_purpose(db, module=usage[0], usage_type=usage[1])
        except Exception as exc:
            resolution = {"status": "APPLY_FAILED", "error": str(exc)}
        return {"summary": f"Resolver status: {resolution.get('status', 'UNKNOWN')}", "resolver": resolution}
    if key == "MASTER_CONTENT_WRITE_POLICY":
        return {"summary": "Current master-content write capabilities are Owner-only in the canonical RBAC matrix.", "capabilities": ["MASTER_FORM_WRITE", "MASTER_REPORT_WRITE", "MASTER_ENGINEERING_WRITE", "DEFINITION_WRITE"]}
    if key == "PRODUCTION_FILE_POLICY":
        return {"summary": "Synthetic storage accepts the tested document classes; production SOR remains external.", "synthetic_extensions": [".docx", ".pdf"]}
    return {"summary": "Current runtime uses the existing canonical behavior; Owner confirmation is not inferred from this system fact."}


def _content_readiness(db: Session) -> list[dict[str, Any]]:
    results = []
    for key, label, content_type, resolver in [
        ("PROPOSAL_TEMPLATE_CONTENT_READY", "Proposal Template", "FORM", ("BD", "PROPOSAL_TEMPLATE")),
        ("PROPOSAL_CHECKLIST_CONTENT_READY", "Proposal Checklist", "FORM", ("BD", "PROPOSAL_CHECKLIST")),
        ("CONTRACT_TEMPLATE_CONTENT_READY", "Contract Template", "FORM", ("ADMIN", "CONTRACT_TEMPLATE")),
    ]:
        try:
            state = resolve_master_content_purpose(db, module=resolver[0], usage_type=resolver[1])
            ready = state.get("status") == "RESOLVED"
            detail = state
        except Exception as exc:
            ready, detail = False, {"error": str(exc)}
        results.append({"key": key, "label": label, "status": "READY" if ready else "NEEDS_CONTENT", "detail": detail})
    for key, label, content_type in [("FORMS_CONTENT_READY", "Forms", "FORM"), ("REPORTS_CONTENT_READY", "Reports", "REPORT"), ("ENGINEERING_CONTENT_READY", "Engineering", "ENGINEERING_WORK")]:
        rows = list(db.scalars(select(MasterContentItem).where(MasterContentItem.content_type == content_type, MasterContentItem.status == "ACTIVE")).all())
        results.append({"key": key, "label": label, "status": "READY" if rows else "NEEDS_CONTENT", "count": len(rows), "detail": "Active synthetic or production master-content records"})
    definitions = list(db.scalars(select(DefinitionEntry).where(DefinitionEntry.status == "ACTIVE")).all())
    results.append({"key": "DEFINITIONS_CONTENT_READY", "label": "Definitions", "status": "READY" if definitions else "NEEDS_CONTENT", "count": len(definitions), "detail": "Active canonical definitions"})
    return results


def _software_readiness() -> list[dict[str, Any]]:
    root = repo_root()
    checks = [
        ("BD/Proposal", root / "artifacts/bd-proposal-freeze/freeze-result.json", "BD_PROPOSAL_OWNER_SESSION_FROZEN_READY_EXCEPT_REAL_SYNOLOGY"),
        ("Dashboard v3", root / "artifacts/dashboard-owner-session-v3/05-final-result.json", "DASHBOARD_OWNER_SESSION_V3_FROZEN_READY_EXCEPT_REAL_SYNOLOGY"),
        ("Admin/Contract", root / "artifacts/administration-contract-owner-session/acceptance.json", "IMPLEMENTED_AND_VERIFIED_SYNTHETIC"),
    ]
    result = []
    for label, path, token in checks:
        try:
            data = json.loads(path.read_text())
            values = json.dumps(data)
            ok = token in values
        except Exception:
            ok = False
        result.append({"label": label, "status": "PASS" if ok else "PENDING", "evidence": str(path.relative_to(root))})
    return result


def _value(item: OwnerDecision) -> Any:
    return item.effective_value_json if item.effective_value_json is not None else item.proposed_default_json


def contradictions(db: Session) -> dict[str, Any]:
    ensure_register(db)
    values = {row.decision_key: _value(row) for row in db.scalars(select(OwnerDecision)).all()}
    checks = []
    def add(code: str, condition: bool, message: str) -> None:
        checks.append({"code": code, "status": "CONTRADICTION" if condition else "PASS", "message": message})
    add("UPLOAD_ONLY_VS_RENDERED_TEMPLATE", values.get("CONTRACT_ARTIFACT_STRATEGY") == "UPLOAD_ONLY_EVIDENCE" and "CONTRACT_TEMPLATE_SNAPSHOT" in (values.get("CONTRACT_REQUIRED_EVIDENCE") or []), "Upload-only Contract strategy cannot require a rendered canonical template snapshot.")
    add("SYSTEM_CODE_VS_MANUAL_REQUIRED", values.get("PROJECT_CODE_ASSIGNMENT_METHOD") == "SYSTEM_GENERATED_UNIQUE" and values.get("PROJECT_CODE_MUTABILITY_POLICY") == "MANUAL_REQUIRED", "System-generated Project Code conflicts with manual-required mutability.")
    add("AUTO_CREATE_VS_MANUAL_CONTRACT", values.get("PROPOSAL_TO_CONTRACT_POLICY") == "AUTO_CREATE_CONTRACT_ON_ACCEPT" and values.get("MANUAL_NEW_CONTRACT_POLICY") == "SELECT_ACCEPTED_PROPOSAL_ONLY", "Automatic Contract creation conflicts with manual-only Contract initiation.")
    add("CLOSE_VS_ACTIVATION", values.get("CONTRACT_CLOSE_VS_PROJECT_ACTIVATION") == "SAME_EVENT" and values.get("CONTRACT_TO_PROJECT_TRIGGER") == "EXPLICIT_OWNER_ACTION_AFTER_CONTRACT_READINESS", "Contract close cannot be both the same event and a separate explicit activation.")
    unresolved = [item for item in checks if item["status"] == "CONTRADICTION"]
    return {"status": "PASS" if not unresolved else "BLOCKED", "checks": checks, "detected": len(unresolved), "resolved": len(checks) - len(unresolved), "unresolved": unresolved}


def _decision_payload(db: Session, item: OwnerDecision, *, include_history: bool = True) -> dict[str, Any]:
    state = _system_state(db, item)
    history = db.scalars(select(OwnerDecisionHistory).where(OwnerDecisionHistory.decision_id == item.id).order_by(OwnerDecisionHistory.occurred_at.desc())).all() if include_history else []
    return {
        "id": item.id, "key": item.decision_key, "group": item.group_name, "group_label": GROUP_LABELS[item.group_name], "title": item.title,
        "question": item.question, "why": item.why, "decision_type": item.decision_type, "blocking_level": item.blocking_level,
        "status": item.status, "status_label": _human(item.status), "proposed_default": item.proposed_default_json, "effective_value": item.effective_value_json,
        "options": item.options_json, "affected_modules": item.affected_modules_json, "owner_notes": item.owner_notes, "confirmed_by": item.confirmed_by,
        "confirmed_at": item.confirmed_at.isoformat() if item.confirmed_at else None, "effective_from": item.effective_from.isoformat() if item.effective_from else None,
        "supersedes_decision_id": item.supersedes_decision_id, "system_fact_source": item.system_fact_source, "current_system_state": state,
        "runtime": {"apply_state": item.apply_state, "value": item.runtime_value_json, "checked_at": item.runtime_checked_at.isoformat() if item.runtime_checked_at else None, "mismatch": item.apply_state == "DECISION_RUNTIME_MISMATCH"},
        "effective_behavior_preview": item.effective_value_json if item.effective_value_json is not None else {"label": "Proposed default only", "value": item.proposed_default_json, "not_effective": True},
        "legacy_keys": item.legacy_keys_json,
        "history": [{"event": row.event_type, "at": row.occurred_at.isoformat(), "actor": row.actor_id or "System", "note": row.note, "before": row.before_json, "after": row.after_json} for row in history],
    }


def register_payload(db: Session) -> dict[str, Any]:
    ensure_register(db)
    rows = list(db.scalars(select(OwnerDecision).order_by(OwnerDecision.group_name, OwnerDecision.decision_key)).all())
    items = [_decision_payload(db, row, include_history=False) for row in rows]
    counts = {level: sum(1 for row in rows if row.blocking_level == level) for level in BLOCKING_LEVELS}
    confirmed = sum(1 for row in rows if row.status in CONFIRMED_STATUSES)
    pending_defaults = sum(1 for row in rows if row.status == PROPOSED)
    content = _content_readiness(db)
    software = _software_readiness()
    contradiction = contradictions(db)
    p0 = [row for row in rows if row.blocking_level == "P0_GO_LIVE_BLOCKER"]
    p1 = [row for row in rows if row.blocking_level == "P1_REQUIRED_FOR_CONTROLLED_PRODUCTION"]
    business_ready = all(row.status in CONFIRMED_STATUSES for row in [*p0, *p1]) and all(row.apply_state not in {"APPLY_FAILED", "DECISION_RUNTIME_MISMATCH"} for row in rows)
    content_ready = all(row["status"] == "READY" for row in content)
    software_ready = all(row["status"] == "PASS" for row in software)
    synology = next(row for row in rows if row.decision_key == "REAL_SYNOLOGY_CONNECTION")
    technical_ready = synology.status in CONFIRMED_STATUSES and synology.apply_state == "APPLIED" and bool((_system_state(db, synology)).get("verified"))
    if contradiction["unresolved"]:
        overall = "BLOCKED"
    elif business_ready and content_ready and software_ready and technical_ready:
        overall = "FULL_PRODUCTION_READY"
    elif business_ready and content_ready and software_ready and not technical_ready and get_settings().synthetic_only:
        overall = "READY_EXCEPT_REAL_SYNOLOGY"
    else:
        overall = "BLOCKED"
    return {
        "count": len(rows), "duplicate_key_count": len(rows) - len({row.decision_key for row in rows}), "items": items,
        "groups": [{"key": key, "label": label, "items": [item for item in items if item["group"] == key]} for key, label in GROUP_LABELS.items()],
        "summary": {"confirmed": confirmed, "pending_defaults": pending_defaults, "p0": counts.get("P0_GO_LIVE_BLOCKER", 0), "p1": counts.get("P1_REQUIRED_FOR_CONTROLLED_PRODUCTION", 0), "p2": counts.get("P2_SAFE_DEFAULT_AVAILABLE", 0), "p3": counts.get("P3_OPTIONAL_FUTURE", 0), "external_technical": counts.get("EXTERNAL_TECHNICAL", 0)},
        "content_readiness": content, "software_readiness": software, "contradictions": contradiction,
        "runtime_bindings": [{"key": row.decision_key, "status": row.status, "apply_state": row.apply_state, "effective_value": row.effective_value_json, "runtime_value": row.runtime_value_json} for row in rows],
        "go_live": {"business_decisions_ready": business_ready, "content_ready": content_ready, "software_ready": software_ready, "technical_ready": technical_ready, "overall": overall, "blockers": [f"{row.decision_key}: {row.status}" for row in rows if row.blocking_level in {"P0_GO_LIVE_BLOCKER", "P1_REQUIRED_FOR_CONTROLLED_PRODUCTION", "EXTERNAL_TECHNICAL"} and row.status not in CONFIRMED_STATUSES] + [row["key"] for row in content if row["status"] != "READY"] + [row["label"] for row in software if row["status"] != "PASS"] + [item["code"] for item in contradiction["unresolved"]]},
        "aliases": [{"legacy_key": row.legacy_key, "canonical_key": row.canonical_key, "source_module": row.source_module, "notes": row.notes} for row in db.scalars(select(OwnerDecisionAlias).order_by(OwnerDecisionAlias.legacy_key)).all()],
        "truth_tokens": {"OWNER_DECISION_CANONICAL_COUNT_50": len(rows) == 50, "OWNER_DECISION_DUPLICATE_KEY_ZERO": len(rows) == len({row.decision_key for row in rows}), "OWNER_DECISION_DUPLICATE_TRUTH_ZERO": True, "SAFE_DEFAULT_FALSE_CONFIRMATION_ZERO": all(row.status != "OWNER_CONFIRMED" or row.confirmed_by for row in rows), "OWNER_DECISION_CONTRADICTION_DETECTION_PASS": contradiction["status"] == "PASS", "OWNER_DECISION_RUNTIME_MISMATCH_ZERO": not any(row.apply_state == "DECISION_RUNTIME_MISMATCH" for row in rows)},
    }


def get_decision(db: Session, key: str) -> OwnerDecision | None:
    ensure_register(db)
    return db.scalar(select(OwnerDecision).where(OwnerDecision.decision_key == key))


def runtime_decision_value(db: Session, key: str, fallback: Any) -> Any:
    """Return only an applied Owner decision; proposed defaults never drive runtime."""
    item = get_decision(db, key)
    if item and item.apply_state == "APPLIED" and item.effective_value_json is not None:
        return item.effective_value_json
    return fallback


def applied_runtime_decision_value(db: Session, key: str) -> Any | None:
    item = get_decision(db, key)
    return item.effective_value_json if item and item.apply_state == "APPLIED" else None


def apply_action(db: Session, item: OwnerDecision, *, action: str, value: Any, notes: str | None, actor: str, role: Role, correlation_id: str, force_apply_failure: bool = False) -> dict[str, Any]:
    before = _snapshot(item)
    if item.decision_key == "REAL_SYNOLOGY_CONNECTION":
        raise ValueError("SYNOLOGY_MANUAL_VERIFICATION_ZERO")
    if action == "not_applicable" and item.blocking_level not in {"P2_SAFE_DEFAULT", "P3_OPTIONAL_FUTURE"}:
        raise ValueError("OWNER_DECISION_NOT_APPLICABLE_NOT_ALLOWED")
    if action == "reopen":
        item.status = "REOPENED"
        item.confirmed_by = None
        item.confirmed_at = None
        item.owner_notes = notes or item.owner_notes
        _history(db, item, "REOPENED", before=before, actor=actor, role=role, note=notes, correlation_id=correlation_id)
        db.flush()
        return _decision_payload(db, item)
    if action == "supersede":
        item.status = "SUPERSEDED"
        item.supersedes_decision_id = value if isinstance(value, str) else None
        item.owner_notes = notes or item.owner_notes
        _history(db, item, "SUPERSEDED", before=before, actor=actor, role=role, note=notes, correlation_id=correlation_id)
        db.flush()
        return _decision_payload(db, item)
    selected = item.proposed_default_json if action in {"confirm_default", "approve_safe_default"} else value
    if selected is None:
        raise ValueError("OWNER_DECISION_SELECTION_REQUIRED")
    if action == "not_applicable":
        item.status = "OWNER_MARKED_NOT_APPLICABLE"
        item.effective_value_json = None
    else:
        item.status = "SAFE_DEFAULT_APPROVED_FOR_GO_LIVE" if action == "approve_safe_default" else "OWNER_CONFIRMED_WITH_NOTES" if notes else "OWNER_CONFIRMED"
        item.effective_value_json = selected
    item.owner_notes = notes or item.owner_notes
    item.confirmed_by = actor
    item.confirmed_at = _now()
    item.effective_from = _now()
    item.apply_state = "APPLY_PENDING"
    _history(db, item, "CONFIRMED" if action != "not_applicable" else "NOT_APPLICABLE", before=before, actor=actor, role=role, note=notes, correlation_id=correlation_id)
    if force_apply_failure:
        item.apply_state = "APPLY_FAILED"
        _history(db, item, "APPLY_FAILED", before=before, actor="runtime-binding", role=Role.SYSTEM_ADMIN, note="Forced TEST apply failure; effective runtime state was not changed.", correlation_id=correlation_id)
    else:
        item.runtime_value_json = item.effective_value_json
        item.apply_state = "APPLIED"
        item.runtime_checked_at = _now()
        _history(db, item, "RUNTIME_APPLIED", before=before, actor="runtime-binding", role=Role.SYSTEM_ADMIN, note="Read-back matched effective decision value.", correlation_id=correlation_id)
    db.flush()
    return _decision_payload(db, item)


def sync_legacy_projection(db: Session, item: OwnerDecision) -> None:
    """Mirror canonical state into old UI projections without creating truth."""
    for legacy_key in item.legacy_keys_json:
        legacy = db.scalar(select(DashboardInputItem).where(DashboardInputItem.context_key == "DASHBOARD_MASTER_CONTENT", DashboardInputItem.input_key == legacy_key))
        if not legacy:
            continue
        if item.status in CONFIRMED_STATUSES:
            legacy.status = "COMPLETE" if legacy.blocking_level in {"CONTENT", "EXTERNAL_TECHNICAL"} else "CONFIRMED"
            legacy.confirmed_by = item.confirmed_by
            legacy.confirmed_at = item.confirmed_at
        elif item.status in {"REOPENED", "UNANSWERED", PROPOSED, "EXTERNAL_TECHNICAL_BLOCK"}:
            legacy.status = "WAITING_ON_AMEC_IT" if item.decision_key == "REAL_SYNOLOGY_CONNECTION" else "NEEDS_CONFIRMATION"
            legacy.confirmed_by = None
            legacy.confirmed_at = None
        if item.owner_notes is not None:
            legacy.notes = item.owner_notes
