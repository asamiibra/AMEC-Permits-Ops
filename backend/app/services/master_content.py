"""Governed master-content commands over the configured AMEC SOR.

The service deliberately keeps SOR locators and hashes server-side. The API
returns business projections; file bytes are read through this service only.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit.service import audit
from ..config.settings import get_settings, repo_root
from ..models import (
    ContentCategory,
    Document,
    DocumentApprovalState,
    DocumentType,
    DocumentVersion,
    DefinitionEntry,
    DefinitionRevision,
    MasterContentChangeEvent,
    MasterContentDependency,
    MasterContentEventDelivery,
    MasterContentModuleBinding,
    MasterContentReferenceSequence,
    MasterContentIdempotency,
    MasterContentItem,
    MasterContentApplicability,
    RequirementPolicyLineage,
    TechnicalRuleLineage,
    FormAutomationProfile,
    FormMappingRelease,
    FormInstance,
    MasterContentSourceProvenance,
    MaterialChangeEvent,
    Finding,
    FindingStatus,
    NotificationEvent,
    PermitApplication,
    WorkflowTask,
    WorkflowTaskStatus,
    LineageEdge,
)
from ..storage.legacy import legacy_synthetic_adapter
from ..storage.factory import create_binary_store
from ..storage.port import StorageTarget
from ..storage.service import DocumentStorageService
from ..storage.errors import StorageError
from ..fixtures.forme_parity import FORME_ARCHIVE_SHA256, FORME_CATEGORY_LABELS, FORME_MASTER_SPECS
from .forms_governance import ensure_profile, governance_projection

CONTENT_TYPES = {"FORM", "REPORT", "ENGINEERING_WORK"}
ENGINEERING_SOURCE_TYPES = ("REGULATION", "QCS", "MUNICIPALITY_COMMENT", "AUTHORITY_GUIDANCE", "ENGINEERING_STANDARD", "DESIGN_GUIDE", "TECHNICAL_REFERENCE", "OTHER")
ENGINEERING_DISCIPLINES = ("GENERAL", "DESIGN", "ARCHITECTURE", "STRUCTURAL", "CIVIL", "MEP", "FIRE_LIFE_SAFETY", "PERMIT", "OTHER")
SEMANTIC_DESTINATION = {
    "FORM": "MASTER_FORM",
    "REPORT": "MASTER_REPORT",
    "ENGINEERING_WORK": "MASTER_ENGINEERING_WORK",
}
_CATEGORY_GROUPS = {
    "FORM": ["General", "Administration", "Business Development", "Consultant", "Contract", "Engineering", "Design", "Permit", "Municipality", "Finance", "Handover", "Other"],
    "REPORT": ["General", "Business Development", "Commercial", "Design", "Engineering", "Permit", "Municipality", "Project", "Finance", "Handover", "Other"],
    "ENGINEERING_WORK": ["General", "Design", "Regulation", "QCS", "Municipality", "Authority Guidance", "Architecture", "Structural", "Civil", "MEP", "Fire & Life Safety", "Design Guide", "Technical Reference", "Authority Comment", "Other"],
    "DEFINITION": ["Client", "Project", "Proposal", "Contract", "Engineering", "Permit", "Finance", "System", "General", "Other"],
}
DEFAULT_CATEGORIES = [
    {"code": f"{content_type}_{label.upper().replace(' ', '_').replace('&', 'AND')}", "label": label, "description": f"Synthetic/configurable {content_type.replace('_', ' ').title()} category", "allowed_content_types": [content_type], "sort_order": group_index * 100 + index * 10, "source_kind": "SYNTHETIC_CONFIGURABLE"}
    for group_index, (content_type, labels_for_type) in enumerate(_CATEGORY_GROUPS.items())
    for index, label in enumerate(labels_for_type, start=1)
]
DEFAULT_REFERENCE_SEQUENCES = [
    {"content_type": "FORM", "prefix": "F", "padding": 4, "scope": "GLOBAL"},
    {"content_type": "REPORT", "prefix": "R", "padding": 4, "scope": "GLOBAL"},
    {"content_type": "ENGINEERING_WORK", "prefix": "E", "padding": 4, "scope": "GLOBAL"},
    {"content_type": "DEFINITION", "prefix": "D", "padding": 4, "scope": "GLOBAL"},
]
ALLOWED_MODULES = {"MY_WORK", "BD", "ADMIN", "ENGINEERING", "PERMIT", "COMPLETION", "HANDOVER", "BILLING", "ISSUES", "NOTIFICATIONS", "REPORTS", "PROPOSAL", "CONTRACT"}
ALLOWED_USAGE_TYPES = {"AVAILABLE", "TEMPLATE", "REFERENCE", "VALIDATION_SOURCE", "REPORT_SOURCE", "SEMANTIC_SOURCE", "PROPOSAL_TEMPLATE", "PROPOSAL_CHECKLIST", "CONTRACT_TEMPLATE"}
CONTENT_TYPE_MODULES = {
    "FORM": {"MY_WORK", "BD", "ADMIN", "ENGINEERING", "PERMIT", "COMPLETION", "HANDOVER", "BILLING", "PROPOSAL", "CONTRACT"},
    "REPORT": {"BD", "ENGINEERING", "PERMIT", "REPORTS", "PROPOSAL", "CONTRACT", "ADMIN"},
    "ENGINEERING_WORK": {"ENGINEERING", "PERMIT", "ISSUES", "REPORTS"},
    "DEFINITION": {"BD", "ADMIN", "ENGINEERING", "PERMIT", "REPORTS", "PROPOSAL", "CONTRACT"},
}
MODULE_LABELS = {
    "MY_WORK": "My Work",
    "BD": "Business Development",
    "ADMIN": "Administration",
    "ENGINEERING": "Engineering",
    "PERMIT": "Permit",
    "COMPLETION": "Completion",
    "HANDOVER": "Completion / Handover",
    "BILLING": "Billing",
    "ISSUES": "Issues",
    "NOTIFICATIONS": "Notifications",
    "REPORTS": "Reports",
    "PROPOSAL": "Proposals",
    "CONTRACT": "Contracts",
}


def _error(code: str, status: int = 422, **details: Any) -> HTTPException:
    return HTTPException(status_code=status, detail={"code": code, **details})


def _actor(role: Any) -> str:
    return getattr(role, "value", str(role))


def _adapter():
    if _deployed_synthetic():
        raise _error("SYNTHETIC_SOR_NOT_PERSISTENT_ON_SERVERLESS_RUNTIME", 503)
    if os.getenv("VERCEL") and get_settings().synthetic_only:
        root = Path(os.getenv("SYNTHETIC_SOR_ROOT", "/tmp/permitops-synology"))
        for folder in ("master-content/forms", "master-content/reports", "master-content/engineering-works"):
            (root / "synology" / folder).mkdir(parents=True, exist_ok=True)
    return legacy_synthetic_adapter()


def _deployed_synthetic() -> bool:
    return bool(os.getenv("VERCEL")) and get_settings().synthetic_only


def read_master_content_bytes(db: Session, version: DocumentVersion) -> bytes:
    """Read verified master bytes, retaining a durable synthetic TEST fallback."""
    if _deployed_synthetic() and version.synthetic_content is not None:
        return version.synthetic_content
    if version.source_path_or_reference.startswith("storage://"):
        try:
            with DocumentStorageService(create_binary_store()).read_verified(version) as stream:
                return stream.read()
        except StorageError as exc:
            raise _error(exc.code.value, 502) from exc
    return _adapter().read_configured_artifact(version.source_path_or_reference)


def _mapping() -> dict[str, str]:
    try:
        mapping = json.loads(get_settings().master_sor_mapping_json)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise _error("SOR_DESTINATION_UNRESOLVED") from exc
    if not isinstance(mapping, dict):
        raise _error("SOR_DESTINATION_UNRESOLVED")
    return {str(key): str(value) for key, value in mapping.items()}


def _safe_filename(filename: str, ref: str, version_number: int) -> str:
    suffix = Path(filename or "source.bin").suffix.lower()
    if not suffix:
        suffix = ".bin"
    stem = re.sub(r"[^A-Za-z0-9._ -]", "_", Path(filename or "source").stem).strip(" .") or "document"
    return f"{ref}-v{version_number}-{stem[:180]}{suffix}"


def _allowed_file(filename: str, content: bytes) -> None:
    settings = get_settings()
    extension = Path(filename or "").suffix.lower()
    allowed = {item.strip().lower() for item in settings.master_sor_allowed_extensions.split(",") if item.strip()}
    if extension not in allowed:
        raise _error("FILE_TYPE_NOT_ALLOWED", extension=extension)
    if not content:
        raise _error("FILE_REQUIRED")
    if len(content) > settings.master_sor_max_file_size:
        raise _error("FILE_TOO_LARGE", max_bytes=settings.master_sor_max_file_size)


def _category(db: Session, category_id: str | None, content_type: str) -> ContentCategory | None:
    if not category_id:
        return None
    category = db.get(ContentCategory, category_id)
    if not category or not category.active:
        raise _error("CATEGORY_NOT_FOUND")
    if category.allowed_content_types and content_type not in category.allowed_content_types:
        raise _error("CATEGORY_CONTENT_TYPE_NOT_ALLOWED")
    return category


def seed_categories(db: Session) -> None:
    for data in DEFAULT_CATEGORIES:
        existing = db.scalar(select(ContentCategory).where(ContentCategory.code == data["code"]))
        if not existing:
            db.add(ContentCategory(**data))
        elif not getattr(existing, "source_kind", None):
            existing.source_kind = "SYNTHETIC_CONFIGURABLE"
    db.flush()


def seed_reference_sequences(db: Session) -> None:
    for data in DEFAULT_REFERENCE_SEQUENCES:
        existing = db.scalar(select(MasterContentReferenceSequence).where(MasterContentReferenceSequence.content_type == data["content_type"], MasterContentReferenceSequence.scope == data["scope"]))
        if not existing:
            db.add(MasterContentReferenceSequence(**data, current_value=0, active=True))
        else:
            maximum = 0
            prefix_pattern = re.compile(rf"^{re.escape(existing.prefix)}-(\d+)$")
            refs = db.scalars(select(MasterContentItem.ref).where(MasterContentItem.content_type == existing.content_type)).all()
            for ref in refs:
                match = prefix_pattern.match(ref or "")
                if match:
                    maximum = max(maximum, int(match.group(1)))
            existing.current_value = max(existing.current_value, maximum)
    db.flush()


def _allocate_reference(db: Session, content_type: str, requested: str | None = None) -> tuple[str, bool]:
    if requested and requested.strip():
        return requested.strip(), False
    sequence = db.scalar(select(MasterContentReferenceSequence).where(MasterContentReferenceSequence.content_type == content_type, MasterContentReferenceSequence.scope == "GLOBAL", MasterContentReferenceSequence.active.is_(True)).with_for_update())
    if not sequence:
        seed_reference_sequences(db)
        sequence = db.scalar(select(MasterContentReferenceSequence).where(MasterContentReferenceSequence.content_type == content_type, MasterContentReferenceSequence.scope == "GLOBAL", MasterContentReferenceSequence.active.is_(True)).with_for_update())
    if not sequence:
        raise _error("REFERENCE_SEQUENCE_UNAVAILABLE", 503, content_type=content_type)
    prefix_pattern = re.compile(rf"^{re.escape(sequence.prefix)}-(\d+)$")
    existing_max = 0
    for ref in db.scalars(select(MasterContentItem.ref).where(MasterContentItem.content_type == content_type)).all():
        match = prefix_pattern.match(ref or "")
        if match:
            existing_max = max(existing_max, int(match.group(1)))
    sequence.current_value = max(sequence.current_value, existing_max)
    sequence.current_value += 1
    db.flush()
    return f"{sequence.prefix}-{sequence.current_value:0{sequence.padding}d}", True


def _parse_modules(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            value = [part.strip() for part in value.split(",") if part.strip()]
    if not isinstance(value, list):
        raise _error("MODULE_BINDING_NOT_ALLOWED")
    modules = [str(module).strip().upper() for module in value if str(module).strip()]
    if any(module not in ALLOWED_MODULES for module in modules):
        raise _error("MODULE_BINDING_NOT_ALLOWED", modules=modules)
    return list(dict.fromkeys(modules))


def _sync_module_bindings(db: Session, *, item_id: str, modules: list[str], actor: str) -> None:
    existing = db.scalars(select(MasterContentModuleBinding).where(MasterContentModuleBinding.master_content_id == item_id)).all()
    for binding in existing:
        binding.active = binding.module in modules
    for module in modules:
        binding = db.scalar(select(MasterContentModuleBinding).where(MasterContentModuleBinding.master_content_id == item_id, MasterContentModuleBinding.module == module, MasterContentModuleBinding.usage_type == "AVAILABLE"))
        if binding:
            binding.active = True
        else:
            db.add(MasterContentModuleBinding(master_content_id=item_id, module=module, usage_type="AVAILABLE", active=True, created_by=actor))
    db.flush()


def _modules_for(db: Session, *, item_id: str | None = None, definition_id: str | None = None) -> list[str]:
    query = select(MasterContentModuleBinding.module).where(MasterContentModuleBinding.active.is_(True))
    if item_id:
        query = query.where(MasterContentModuleBinding.master_content_id == item_id)
    if definition_id:
        query = query.where(MasterContentModuleBinding.definition_id == definition_id)
    return sorted(set(db.scalars(query).all()))


def resolve_master_content_purpose(db: Session, *, module: str, usage_type: str) -> dict[str, Any]:
    module = module.strip().upper()
    usage_type = usage_type.strip().upper()
    rows = db.scalars(
        select(MasterContentItem)
        .join(MasterContentModuleBinding, MasterContentModuleBinding.master_content_id == MasterContentItem.id)
        .where(
            MasterContentModuleBinding.module == module,
            MasterContentModuleBinding.usage_type == usage_type,
            MasterContentModuleBinding.active.is_(True),
            MasterContentItem.status == "ACTIVE",
            MasterContentItem.needs_review.is_(False),
        )
        .order_by(MasterContentItem.updated_at.desc(), MasterContentItem.ref)
    ).all()
    resolved = []
    for item in rows:
        version = db.get(DocumentVersion, item.current_document_version_id) if item.current_document_version_id else None
        governance = governance_projection(db, item)
        if item.content_type == "FORM":
            # Preserve the frozen purpose bindings for AMEC-owned canonical
            # proposal/contract forms while keeping external, restricted, and
            # reference-only forms out of downstream resolution.
            frozen_purpose = usage_type in {"PROPOSAL_TEMPLATE", "PROPOSAL_CHECKLIST", "CONTRACT_TEMPLATE"}
            profile = governance["profile"]
            is_frozen_amec_form = (
                frozen_purpose
                and profile.get("content_ownership_class") == "AMEC_OWNED"
                and not profile.get("restricted_reference_sample")
            )
            if not is_frozen_amec_form and governance["readiness"]["state"] != "MANUAL_USE_READY":
                continue
        if version:
            resolved.append({"id": item.id, "ref": item.ref, "title": item.title, "content_type": item.content_type, "version_id": version.id, "version": version.version_number, "hash": version.sha256, "source_filename": version.source_filename, "module": module, "purpose": usage_type, "canonical": True})
    return {"module": module, "purpose": usage_type, "status": "RESOLVED" if len(resolved) == 1 else "AMBIGUOUS" if len(resolved) > 1 else "UNRESOLVED", "canonical_count": len(resolved), "item": resolved[0] if len(resolved) == 1 else None, "candidates": resolved, "truth": "DASHBOARD_MASTER_CONTENT"}


def _status(version: DocumentVersion) -> str:
    return str((version.metadata_json or {}).get("master_status", "PENDING_WRITE"))


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _materiality(item: MasterContentItem, previous: DocumentVersion | None, version: DocumentVersion, category_changed: bool = False) -> str:
    if not previous or previous.sha256 != version.sha256 or category_changed or item.content_type == "ENGINEERING_WORK":
        return "MATERIAL"
    return "NON_MATERIAL"


def _delivery_exists(db: Session, event_id: str, delivery_type: str, target_type: str, target_id: str, recipient_role: str = "-") -> bool:
    return bool(db.scalar(select(MasterContentEventDelivery).where(MasterContentEventDelivery.event_id == event_id, MasterContentEventDelivery.delivery_type == delivery_type, MasterContentEventDelivery.target_type == target_type, MasterContentEventDelivery.target_id == target_id, MasterContentEventDelivery.recipient_role == recipient_role)))


def _record_delivery(db: Session, event_id: str, delivery_type: str, target_type: str, target_id: str, recipient_role: str = "-") -> None:
    if not _delivery_exists(db, event_id, delivery_type, target_type, target_id, recipient_role):
        db.add(MasterContentEventDelivery(event_id=event_id, delivery_type=delivery_type, target_type=target_type, target_id=target_id, recipient_role=recipient_role))


def _lineage_once(db: Session, *, project_id: str, source_version: DocumentVersion, downstream_type: str, downstream_id: str, dependency_kind: str, correlation_id: str) -> None:
    if not db.scalar(select(LineageEdge).where(LineageEdge.project_id == project_id, LineageEdge.upstream_type == "DocumentVersion", LineageEdge.upstream_id == source_version.id, LineageEdge.downstream_type == downstream_type, LineageEdge.downstream_id == downstream_id, LineageEdge.dependency_kind == dependency_kind)):
        db.add(LineageEdge(project_id=project_id, upstream_type="DocumentVersion", upstream_id=source_version.id, upstream_version_or_hash=source_version.sha256, downstream_type=downstream_type, downstream_id=downstream_id, downstream_version_or_hash=source_version.sha256, dependency_kind=dependency_kind, correlation_id=correlation_id))


def _project_finding(db: Session, *, item: MasterContentItem, event: MasterContentChangeEvent, dependency: MasterContentDependency, current: DocumentVersion, correlation_id: str) -> Finding | None:
    if not dependency.project_id:
        return None
    application = db.scalar(select(PermitApplication).where(PermitApplication.project_id == dependency.project_id).order_by(PermitApplication.created_at))
    if not application:
        return None
    key = f"MASTER_CONTENT_REVALIDATION:{dependency.id}:{current.id}"
    existing = db.scalar(select(Finding).where(Finding.source_type == "MASTER_CONTENT", Finding.source_reference == key))
    if existing:
        return existing
    finding = Finding(project_id=dependency.project_id, application_id=application.id, source_type="MASTER_CONTENT", source_reference=key, source_timestamp=event.occurred_at, captured_by=event.actor_or_system, title=f"{item.ref} requires review", raw_text=f"Current {item.content_type} version changed while {dependency.downstream_type} {dependency.downstream_id} remained bound to an older version.", normalized_summary=f"Revalidate {dependency.downstream_type} against {item.ref} v{current.version_number}.", language="en", discipline="ENGINEERING" if item.content_type == "ENGINEERING_WORK" else "MASTER_CONTENT", affected_object_type=dependency.downstream_type, affected_object_id=dependency.id, requirement_code="MASTER_CONTENT_REVALIDATION", severity="MAJOR" if item.content_type == "ENGINEERING_WORK" else "ADVISORY", blocking=False, status="OPEN", assignee_role="RESPONSIBLE_ENGINEER" if item.content_type == "ENGINEERING_WORK" else "OWNER", correlation_id=correlation_id, domain="MASTER_CONTENT", owner_persona="ENGINEERING" if item.content_type == "ENGINEERING_WORK" else "OWNER", deep_link=f"/dashboard?content={item.id}")
    db.add(finding)
    db.flush()
    return finding


def _project_task(db: Session, *, dependency: MasterContentDependency, finding: Finding | None, item: MasterContentItem, current: DocumentVersion, correlation_id: str) -> WorkflowTask | None:
    if not finding or dependency.status != "NEEDS_REVALIDATION":
        return None
    existing = db.scalar(select(WorkflowTask).where(WorkflowTask.context_type == "MASTER_CONTENT_DEPENDENCY", WorkflowTask.context_id == dependency.id, WorkflowTask.status.in_((WorkflowTaskStatus.OPEN, WorkflowTaskStatus.IN_PROGRESS))))
    if existing:
        return existing
    task = WorkflowTask(project_id=dependency.project_id, application_id=finding.application_id, finding_id=finding.id, task_type="MASTER_CONTENT_REVALIDATION", title=f"Revalidate {item.ref} v{current.version_number}", description=f"Review the changed {item.content_type} source for {dependency.downstream_type} {dependency.downstream_id}.", owner_role="RESPONSIBLE_ENGINEER" if item.content_type == "ENGINEERING_WORK" else "OWNER", status=WorkflowTaskStatus.OPEN, priority="HIGH" if item.content_type == "ENGINEERING_WORK" else "NORMAL", correlation_id=correlation_id, task_family="MASTER_CONTENT", context_type="MASTER_CONTENT_DEPENDENCY", context_id=dependency.id, blocking=False, next_action_code="MASTER_CONTENT_REVALIDATION", deep_link=f"/dashboard?content={item.id}", evidence_summary={"master_content_id": item.id, "bound_version_id": dependency.bound_document_version_id, "current_version_id": current.id})
    db.add(task)
    db.flush()
    return task


def _project_notifications(db: Session, *, event: MasterContentChangeEvent, item: MasterContentItem, finding: Finding | None, task: WorkflowTask | None, correlation_id: str) -> None:
    roles = ["OWNER", "ENGINEERING"] if item.content_type == "ENGINEERING_WORK" else ["OWNER", "BUSINESS_DEVELOPMENT"]
    for role in roles:
        target_id = f"{event.id}:{role}"
        if _delivery_exists(db, event.id, "NOTIFICATION", "ROLE", role, role):
            continue
        db.add(NotificationEvent(finding_id=finding.id if finding else None, workflow_task_id=task.id if task else None, recipient_role=role, channel="IN_APP", event_type=event.event_type, status="PENDING", subject=f"{item.ref} updated", body_preview=f"{item.content_type.replace('_', ' ').title()} {item.ref} v{event.metadata_json.get('version_number')} is now current.", correlation_id=correlation_id, domain="MASTER_CONTENT", audience=[role], actor=event.actor_or_system, deep_link=f"/dashboard?content={item.id}"))
        _record_delivery(db, event.id, "NOTIFICATION", "ROLE", role, role)


def propagate_master_change(db: Session, event: MasterContentChangeEvent, item: MasterContentItem, current: DocumentVersion) -> dict[str, int]:
    """Evaluate explicit dependencies and project deterministic platform actions."""
    dependencies = db.scalars(select(MasterContentDependency).where(MasterContentDependency.master_content_id == item.id)).all()
    impacts = {"dependencies": len(dependencies), "lineage": 0, "findings": 0, "tasks": 0, "notifications": 0, "governance_revalidation": 0}
    if event.previous_version_id and event.previous_version_id != current.id:
        # Source version pinning is a fail-closed boundary for V2.  Existing
        # active links and released mappings remain auditable, but they cannot
        # continue to resolve after the current source changes.
        for row in db.scalars(select(MasterContentApplicability).where(MasterContentApplicability.master_content_item_id == item.id, MasterContentApplicability.source_document_version_id != current.id, MasterContentApplicability.status == "ACTIVE")).all():
            row.status = "NEEDS_REVALIDATION"
            impacts["governance_revalidation"] += 1
        for model in (RequirementPolicyLineage, TechnicalRuleLineage):
            for row in db.scalars(select(model).where(model.master_content_item_id == item.id, model.document_version_id != current.id, model.governance_status == "ACTIVE")).all():
                row.governance_status = "NEEDS_REVALIDATION"
                impacts["governance_revalidation"] += 1
        for profile in db.scalars(select(FormAutomationProfile).where(FormAutomationProfile.master_content_item_id == item.id, FormAutomationProfile.source_document_version_id != current.id)).all():
            profile.source_version_state = "NEEDS_REVALIDATION"
            profile.automation_status = "NEEDS_REVALIDATION"
            for release in db.scalars(select(FormMappingRelease).where(FormMappingRelease.profile_id == profile.id, FormMappingRelease.status == "RELEASED")).all():
                release.status = "NEEDS_REVALIDATION"
                release.invalidation_reason = "Current master source version changed; owner revalidation required."
                impacts["governance_revalidation"] += 1
            for instance in db.scalars(select(FormInstance).where(FormInstance.profile_id == profile.id, FormInstance.source_document_version_id != current.id, FormInstance.status != "NEEDS_REVALIDATION")).all():
                instance.status = "NEEDS_REVALIDATION"
                instance.invalidation_reason = "Current master source version changed; instance is no longer current."
                impacts["governance_revalidation"] += 1
    for dependency in dependencies:
        if dependency.project_id:
            _lineage_once(db, project_id=dependency.project_id, source_version=current, downstream_type=dependency.downstream_type, downstream_id=dependency.downstream_id, dependency_kind="MASTER_CONTENT_CURRENT_VERSION", correlation_id=event.correlation_id)
            impacts["lineage"] += 1
        needs_revalidation = event.materiality == "MATERIAL" and dependency.policy == "REVALIDATE_ON_CURRENT_CHANGE" and dependency.expected_current_version_id != current.id and dependency.status not in {"COMPLETED", "HISTORICAL"}
        if needs_revalidation:
            dependency.status = "NEEDS_REVALIDATION"
            dependency.expected_current_version_id = current.id
            finding = _project_finding(db, item=item, event=event, dependency=dependency, current=current, correlation_id=event.correlation_id)
            task = _project_task(db, dependency=dependency, finding=finding, item=item, current=current, correlation_id=event.correlation_id)
            if finding:
                impacts["findings"] += 1
                _record_delivery(db, event.id, "FINDING", "Finding", finding.id)
            if task:
                impacts["tasks"] += 1
                _record_delivery(db, event.id, "WORKFLOW_TASK", "WorkflowTask", task.id)
        else:
            finding = None
            task = None
    if dependencies and event.materiality == "MATERIAL":
        before_notifications = len(db.new)
        _project_notifications(db, event=event, item=item, finding=None, task=None, correlation_id=event.correlation_id)
        impacts["notifications"] = len(db.new) - before_notifications
    event.status = "PROCESSED"
    event.metadata_json = {**(event.metadata_json or {}), "propagation": impacts, "processed_at": _now().isoformat()}
    db.flush()
    return impacts


def register_dependency(db: Session, *, item_id: str, downstream_type: str, downstream_id: str, project_id: str | None, dependency_kind: str, actor: str, correlation_id: str) -> dict[str, Any]:
    item = db.get(MasterContentItem, item_id)
    if not item or not item.current_document_version_id:
        raise _error("CONTENT_NOT_FOUND", 404)
    allowed = {"EngineeringReview", "EngineeringReviewRun", "RenderedArtifact", "GeneratedReport", "Proposal", "Contract", "PermitApplication", "Workflow", "Requirement", "FormTemplate", "ReportDefinition"}
    if downstream_type not in allowed:
        raise _error("DEPENDENCY_TYPE_NOT_ALLOWED")
    current = db.get(DocumentVersion, item.current_document_version_id)
    dependency = db.scalar(select(MasterContentDependency).where(MasterContentDependency.master_content_id == item.id, MasterContentDependency.downstream_type == downstream_type, MasterContentDependency.downstream_id == downstream_id, MasterContentDependency.dependency_kind == dependency_kind))
    if not dependency:
        dependency = MasterContentDependency(master_content_id=item.id, bound_document_version_id=current.id, expected_current_version_id=current.id, downstream_type=downstream_type, downstream_id=downstream_id, project_id=project_id, dependency_kind=dependency_kind, created_by=actor)
        db.add(dependency)
        db.flush()
        if project_id:
            _lineage_once(db, project_id=project_id, source_version=current, downstream_type=downstream_type, downstream_id=downstream_id, dependency_kind="MASTER_CONTENT_DEPENDENCY", correlation_id=correlation_id)
    db.commit()
    return {"id": dependency.id, "master_content_id": item.id, "bound_version_id": dependency.bound_document_version_id, "expected_current_version_id": dependency.expected_current_version_id, "downstream_type": dependency.downstream_type, "downstream_id": dependency.downstream_id, "status": dependency.status, "policy": dependency.policy}


def revalidate_dependency(db: Session, *, dependency_id: str, actor: str, correlation_id: str) -> dict[str, Any]:
    dependency = db.get(MasterContentDependency, dependency_id)
    if not dependency:
        raise _error("DEPENDENCY_NOT_FOUND", 404)
    dependency.bound_document_version_id = dependency.expected_current_version_id
    dependency.status = "CURRENT"
    audit(db, correlation_id=correlation_id, event_type="MASTER_CONTENT_DEPENDENCY_REVALIDATED", entity_type="MasterContentDependency", entity_id=dependency.id, actor_id=actor, after={"bound_version_id": dependency.bound_document_version_id})
    db.commit()
    return {"id": dependency.id, "bound_version_id": dependency.bound_document_version_id, "expected_current_version_id": dependency.expected_current_version_id, "status": dependency.status}


def eligible_master_content(db: Session, *, use: str = "ENGINEERING_AI") -> list[dict[str, Any]]:
    rows = []
    for item in db.scalars(select(MasterContentItem).where(MasterContentItem.status == "ACTIVE", MasterContentItem.needs_review.is_(False)).order_by(MasterContentItem.ref)).all():
        version = db.get(DocumentVersion, item.current_document_version_id) if item.current_document_version_id else None
        if not version or _status(version) != "CURRENT" or version.approval_state != DocumentApprovalState.REVIEWED:
            continue
        if use == "ENGINEERING_AI" and item.content_type != "ENGINEERING_WORK":
            continue
        rows.append({"master_content_id": item.id, "ref": item.ref, "content_type": item.content_type, "title": item.title, "document_version_id": version.id, "version": version.version_number, "source_hash": version.sha256, "eligibility": "CURRENT_VERIFIED"})
    return rows


def definition_lookup(db: Session, term: str) -> dict[str, Any] | None:
    definition = db.scalar(select(DefinitionEntry).where(DefinitionEntry.term == term, DefinitionEntry.status == "ACTIVE"))
    return definition_projection(db, definition, include_history=False) if definition else None


OWNER_DEMO_SPECS = {
    "FORM": [
        {"ref": "F-0003", "title": "AMEC Proposal Template", "category": "Business Development", "description": "Canonical Dashboard-managed Proposal rendering template.", "used_in": ["BD", "PROPOSAL"]},
        {"ref": "F-0004", "title": "AMEC Proposal Checklist", "category": "Business Development", "description": "Canonical Dashboard-managed Proposal readiness checklist.", "used_in": ["BD", "PROPOSAL"]},
        {"ref": "F-0005", "title": "AMEC Contract Template", "category": "Contract", "description": "Canonical Dashboard-managed Contract handoff template.", "used_in": ["ADMIN", "CONTRACT"]},
    ],
    "REPORT": [
        {"ref": "R-0001", "title": "Design Review Report", "category": "Design", "description": "Standard design review report template/reference.", "used_in": ["ENGINEERING", "REPORTS"]},
        {"ref": "R-0002", "title": "Project Status Report", "category": "Project", "description": "Standard project status reporting format.", "used_in": ["REPORTS", "ADMIN"]},
    ],
    "ENGINEERING_WORK": [
        {"ref": "E-0001", "title": "Qatar Regulation Example", "category": "Regulation", "description": "Reference example for Qatar regulatory review.", "used_in": ["ENGINEERING", "PERMIT"]},
        {"ref": "E-0002", "title": "QCS Example", "category": "QCS", "description": "Reference example for QCS technical review.", "used_in": ["ENGINEERING", "PERMIT", "REPORTS"], "source_type_code": "QCS", "engineering_metadata": {"discipline": "GENERAL"}},
        {"ref": "E-0003", "title": "Municipality Comment Reference", "category": "Authority Comment", "description": "Reference example for municipality comments and responses.", "used_in": ["ENGINEERING", "PERMIT", "ISSUES"], "source_type_code": "MUNICIPALITY_COMMENT", "engineering_metadata": {"authority": "Municipality", "discipline": "GENERAL"}},
    ],
}
OWNER_DEFINITION_SPECS = [
    {"ref": "D-0001", "term": "Client ID", "category": "Client", "description": "Passport Number or National ID used to identify the client.", "used_in": ["BD", "ADMIN", "PERMIT"]},
    {"ref": "D-0002", "term": "Project Reference", "category": "Project", "description": "The AMEC project reference used to identify a project across ProposalOps.", "used_in": ["BD", "ADMIN", "ENGINEERING", "PERMIT", "REPORTS", "PROPOSAL", "CONTRACT"]},
]


def _confirmed_test_text(row: Any) -> str:
    return " ".join(str(getattr(row, key, "") or "") for key in ("ref", "title", "term", "description")).lower()


def _is_confirmed_test_artifact(row: Any) -> bool:
    text = _confirmed_test_text(row)
    ref = str(getattr(row, "ref", "") or "").upper()
    return any(phrase in text for phrase in ("browser controlled", "deployment probe", "e2e verification")) or ref.startswith(("B-F-", "B-E-", "AF-MSN", "DEPLOY-PROBE-", "E2E-"))


def _demo_category_id(db: Session, content_type: str, label: str) -> str | None:
    categories = db.scalars(select(ContentCategory).where(ContentCategory.active.is_(True))).all()
    matching = [row for row in categories if row.label == label and content_type in (row.allowed_content_types or [])]
    return (sorted(matching, key=lambda row: (0 if row.code.startswith(f"{content_type}_") else 1, row.sort_order, row.code))[0].id if matching else None)


def _forme_category_id(db: Session, label: str) -> str:
    """Return a deterministic configurable category for the FORME mapping."""
    existing = _demo_category_id(db, "FORM", label)
    if existing:
        return existing
    code = "FORM_FORME_" + re.sub(r"[^A-Z0-9]+", "_", label.upper()).strip("_")[:60]
    category = db.scalar(select(ContentCategory).where(ContentCategory.code == code))
    if not category:
        category = ContentCategory(code=code, label=label, description="FORME parity configurable Form category", allowed_content_types=["FORM"], sort_order=500, source_kind="FORME_MAPPING")
        db.add(category)
        db.flush()
    return category.id


def _forme_synthetic_content(spec: dict[str, object]) -> bytes:
    """Create only the approved synthetic MVP representation, never a source binary."""
    return (
        "PROPOSALOPS SYNTHETIC MVP REPRESENTATION\n"
        f"FORME business identity: {spec['title']}\n"
        f"Source package: FORME.zip\n"
        f"Source path: {spec['source_path']}\n"
        "Actual source binary is not embedded in this deployment.\n"
    ).encode("utf-8")


def _forme_metadata(spec: dict[str, object]) -> dict[str, object]:
    return {
        "seed_version": "forme-vercel-parity-v1",
        "stable_key": spec["stable_key"],
        "source_package": "FORME.zip",
        "source_path": spec["source_path"],
        "source_sha256": spec["source_sha256"] or None,
        "source_manifest": "ProposalOps_FORME_Source_Disposition_Manifest_v1",
        "source_archive_sha256": FORME_ARCHIVE_SHA256,
        "disposition": "PROMOTE_MASTER_CURRENT" if spec["status"] == "CURRENT" else "PROMOTE_MASTER_NEEDS_REVIEW",
        "forme_category": spec["category"],
        "forme_used_in": spec["used_in_labels"],
        "synthetic_mvp_representation": True,
    }


def _ensure_forme_category_configuration(db: Session) -> None:
    for label in FORME_CATEGORY_LABELS:
        _forme_category_id(db, label)


def _apply_forme_governance(db: Session, item: MasterContentItem, spec: dict[str, object], *, actor: str) -> None:
    profile = ensure_profile(db, item)
    title = str(spec["title"])
    profile.content_ownership_class = "EXTERNAL_OFFICIAL" if spec["official_form_no"] else "AMEC_OWNED"
    profile.artifact_kind = "UNDERTAKING" if "Undertaking" in title else "AUTHORIZATION" if "Authorization" in title else "CHECKLIST" if "Checklist" in title else "INVOICE" if title == "Invoice Template" else "HANDOVER" if title == "Design Project Handover Form" else "TECHNICAL_WORKSHEET" if title == "External Wall / Roof U-Value Calculation" else "CERTIFICATE_DECLARATION" if title == "Material & Specification Conformity Certificate" else "OTHER"
    profile.publisher_name = "Ministry of Municipality" if str(spec["category"]).startswith("Municipality") else "GSAS / Lusail" if title == "GSAS 3+ Star Undertaking" else "AMEC / FORME source package"
    profile.publisher_unit = str(spec["category"])
    profile.jurisdiction_text = "Qatar"
    profile.official_form_no = spec["official_form_no"]
    profile.official_issue_no = str(spec["source_version"]) if spec.get("source_version") else None
    profile.language_profile = "AR_EN_BILINGUAL" if str(spec["source_path"]).lower().endswith((".pdf", ".docx")) else "OTHER"
    profile.currentness_status = "VERIFIED_CURRENT" if spec["status"] == "CURRENT" else "NEEDS_REVIEW"
    profile.currentness_verified_by = actor
    profile.currentness_verification_note = "FORME disposition projection; synthetic MVP business metadata only."


def _ensure_forme_provenance(db: Session, item: MasterContentItem, spec: dict[str, object], *, actor: str) -> None:
    version = db.get(DocumentVersion, item.current_document_version_id) if item.current_document_version_id else None
    if not version:
        raise RuntimeError(f"FORME parity record has no current version: {spec['stable_key']}")
    if db.scalar(select(MasterContentSourceProvenance).where(MasterContentSourceProvenance.document_version_id == version.id)):
        return
    source_hash = spec["source_sha256"] or "not provided in controlling mapping"
    db.add(MasterContentSourceProvenance(document_version_id=version.id, obtained_from="FORME.zip", obtained_by=actor, source_reference=str(spec["source_path"]), ingest_batch=f"FORME:{FORME_ARCHIVE_SHA256}", provenance_note=f"Source SHA-256: {source_hash}. Business projection only; actual source binary is not embedded in Vercel synthetic mode.", evidence_reference="docs/storage-integration-v1_4/07-forme-disposition.md"))


def _seed_owned_generic_placeholder(item: MasterContentItem) -> bool:
    version = item.document.versions[0] if item.document and item.document.versions else None
    metadata = (version.metadata_json if version else {}) or {}
    return item.created_by == "owner-demo-seed" and bool(version and version.version_number == 1 and "owner-demo" in version.source_filename.lower() and metadata.get("business_ref") == item.ref)


def _archive_obsolete_generic_placeholders(db: Session, *, actor: str) -> dict[str, object]:
    result: dict[str, object] = {"classifications": [], "archived": [], "unclassified": []}
    rows = db.scalars(select(MasterContentItem).where(MasterContentItem.content_type == "FORM", MasterContentItem.ref.in_(["F-0001", "F-0002"]))).all()
    for item in rows:
        classification = {"ref": item.ref, "title": item.title, "id": item.id}
        if item.title not in {"Consultant Form", "Authorization Form"}:
            classification["classification"] = "UNKNOWN"
            result["unclassified"].append(classification)
            continue
        bindings = db.scalars(select(MasterContentModuleBinding).where(MasterContentModuleBinding.master_content_id == item.id, MasterContentModuleBinding.active.is_(True))).all()
        has_non_available_binding = any(binding.usage_type != "AVAILABLE" for binding in bindings)
        dependency_models = (
            (MasterContentDependency, MasterContentDependency.master_content_id),
            (MasterContentApplicability, MasterContentApplicability.master_content_item_id),
            (FormAutomationProfile, FormAutomationProfile.master_content_item_id),
            (RequirementPolicyLineage, RequirementPolicyLineage.master_content_item_id),
            (TechnicalRuleLineage, TechnicalRuleLineage.master_content_item_id),
        )
        has_dependency = any(db.scalar(select(model.id).where(column == item.id)) for model, column in dependency_models)
        if _seed_owned_generic_placeholder(item) and not has_non_available_binding and not has_dependency:
            classification["classification"] = "OBSOLETE_SYNTHETIC_PLACEHOLDER"
            if item.status == "ACTIVE":
                item.status = "ARCHIVED"
                audit(db, correlation_id=f"forme-parity-placeholder:{item.id}", event_type="MASTER_CONTENT_SYNTHETIC_PLACEHOLDER_ARCHIVED", entity_type="MasterContentItem", entity_id=item.id, actor_id=actor, after={"ref": item.ref, "status": "ARCHIVED", "reason": "Superseded by exact FORME parity mapping"})
                result["archived"].append(item.ref)
        else:
            classification["classification"] = "UNKNOWN"
            result["unclassified"].append(classification)
        result["classifications"].append(classification)
    if result["unclassified"]:
        raise RuntimeError(f"FORME_VERCEL_PARITY_REPAIR_BLOCKED_BY_PLACEHOLDER_DEPENDENCY: {result['unclassified']}")
    return result


def _reconcile_forme_masters(db: Session, *, actor: str) -> dict[str, object]:
    _ensure_forme_category_configuration(db)
    created: list[str] = []
    preserved: list[str] = []
    conflicts: list[dict[str, object]] = []
    for spec in FORME_MASTER_SPECS:
        forme_metadata = _forme_metadata(spec)
        existing = db.scalar(select(MasterContentItem).where(MasterContentItem.ref == spec["ref"], MasterContentItem.content_type == "FORM")) if spec["ref"] else None
        if not existing:
            existing = db.scalar(select(MasterContentItem).where(MasterContentItem.content_type == "FORM", MasterContentItem.title == spec["title"]))
        if existing:
            prior_marker = (existing.engineering_metadata or {}).get("forme_parity")
            if prior_marker and prior_marker.get("stable_key") == spec["stable_key"]:
                if prior_marker.get("source_sha256") != forme_metadata.get("source_sha256") or existing.needs_review != (spec["status"] == "NEEDS_REVIEW") or existing.review_note != spec["review_note"]:
                    conflicts.append({"stable_key": spec["stable_key"], "id": existing.id, "reason": "seed-owned record drifted; refusing silent overwrite"})
                _ensure_forme_provenance(db, existing, spec, actor=actor)
                preserved.append(str(spec["stable_key"]))
                continue
            conflicts.append({"stable_key": spec["stable_key"], "id": existing.id, "reason": "title/ref collision without FORME parity ownership"})
            continue
        category_id = _forme_category_id(db, str(spec["category"]))
        result = create_master_content(db, content_type="FORM", ref=spec["ref"], title=str(spec["title"]), category_id=category_id, description=str(spec["description"]), filename=str(spec["filename"]), mime_type=str(spec["mime_type"]), content=_forme_synthetic_content(spec), actor="owner-demo-seed", idempotency_key=f"forme-parity:v1:{spec['stable_key']}", correlation_id=f"forme-parity:v1:{spec['stable_key']}", source_surface="SOURCE_INTAKE_V1_4", used_in=spec["used_in"], engineering_metadata={"forme_parity": forme_metadata}, needs_review=spec["status"] == "NEEDS_REVIEW", review_note=spec["review_note"])
        item = db.get(MasterContentItem, result["id"])
        item.engineering_metadata = {**(item.engineering_metadata or {}), "forme_parity": forme_metadata}
        _apply_forme_governance(db, item, spec, actor=actor)
        _ensure_forme_provenance(db, item, spec, actor=actor)
        created.append(str(spec["stable_key"]))
    if conflicts:
        raise RuntimeError(f"FORME_VERCEL_PARITY_REPAIR_BLOCKED_BY_DATA_CONFLICT: {conflicts}")
    db.commit()
    return {"created": created, "preserved": preserved, "conflicts": conflicts, "current": sum(1 for spec in FORME_MASTER_SPECS if spec["status"] == "CURRENT"), "needs_review": sum(1 for spec in FORME_MASTER_SPECS if spec["status"] == "NEEDS_REVIEW"), "inactive": 0}


def reconcile_owner_demo_dataset(db: Session, *, actor: str = "owner-demo-seed") -> dict[str, Any]:
    """Reconcile the synthetic MVP to core masters plus exact FORME metadata.

    Only seed-owned generic placeholders are archived. FORME parity records
    use stable idempotency keys and synthetic DB-backed content; no source
    binary is copied into the repository or presented as the actual binary.
    Existing unclassified/user-edited collisions stop the bootstrap.
    """
    seed_categories(db)
    seed_reference_sequences(db)
    placeholder_result = _archive_obsolete_generic_placeholders(db, actor=actor)
    db.commit()
    archived_master: list[dict[str, str]] = []
    archived_definitions: list[dict[str, str]] = []
    for item in db.scalars(select(MasterContentItem).where(MasterContentItem.status == "ACTIVE")).all():
        if _is_confirmed_test_artifact(item):
            item.status = "ARCHIVED"
            archived_master.append({"id": item.id, "ref": item.ref, "content_type": item.content_type})
            audit(db, correlation_id=f"owner-demo-cleanup:{item.id}", event_type="MASTER_CONTENT_TEST_ARTIFACT_ARCHIVED", entity_type="MasterContentItem", entity_id=item.id, actor_id=actor, after={"ref": item.ref, "status": "ARCHIVED", "reason": "confirmed browser/deployment test artifact"})
    for definition in db.scalars(select(DefinitionEntry).where(DefinitionEntry.status == "ACTIVE")).all():
        if _is_confirmed_test_artifact(definition):
            definition.status = "ARCHIVED"
            archived_definitions.append({"id": definition.id, "ref": definition.ref or "", "term": definition.term})
            audit(db, correlation_id=f"owner-demo-cleanup:{definition.id}", event_type="DEFINITION_TEST_ARTIFACT_ARCHIVED", entity_type="DefinitionEntry", entity_id=definition.id, actor_id=actor, after={"term": definition.term, "status": "ARCHIVED", "reason": "confirmed browser test artifact"})
    db.commit()

    created_master: list[str] = []
    preserved_master: list[str] = []
    for content_type, specs in OWNER_DEMO_SPECS.items():
        for spec in specs:
            existing = db.scalar(select(MasterContentItem).where(MasterContentItem.content_type == content_type, MasterContentItem.ref == spec["ref"]))
            if existing:
                preserved_master.append(spec["ref"])
                continue
            category_id = _demo_category_id(db, content_type, spec["category"])
            projection = create_master_content(db, content_type=content_type, ref=spec["ref"], title=spec["title"], category_id=category_id, description=spec["description"], filename=f"{spec['ref']}-owner-demo.txt", mime_type="text/plain", content=f"AMEC owner demo source for {spec['ref']}.".encode(), actor=actor, idempotency_key=f"owner-demo:{content_type}:{spec['ref']}", correlation_id=f"owner-demo:{content_type}:{spec['ref']}", used_in=spec["used_in"], source_type_code=spec.get("source_type_code"), engineering_metadata=spec.get("engineering_metadata"))
            created_master.append(projection["ref"])

    # Older TEST rehearsals may have archived a probe at F-0003/F-0004.  Do
    # not resurrect that row or create duplicate truth at the same reference;
    # use a distinct active fallback only when the titled canonical item is
    # unavailable.
    fallback_specs = [
        {"ref": "BD-PROP-001", "title": "AMEC Proposal Template", "category": "Business Development", "description": "Canonical Dashboard-managed Proposal rendering template.", "used_in": ["BD", "PROPOSAL"]},
        {"ref": "BD-CHK-001", "title": "AMEC Proposal Checklist", "category": "Business Development", "description": "Canonical Dashboard-managed Proposal readiness checklist.", "used_in": ["BD", "PROPOSAL"]},
        {"ref": "CT-001", "title": "AMEC Contract Template", "category": "Contract", "description": "Canonical Dashboard-managed Contract handoff template.", "used_in": ["ADMIN", "CONTRACT"]},
    ]
    for spec in fallback_specs:
        if not db.scalar(select(MasterContentItem).where(MasterContentItem.content_type == "FORM", MasterContentItem.title == spec["title"], MasterContentItem.status == "ACTIVE")):
            category_id = _demo_category_id(db, "FORM", spec["category"])
            create_master_content(db, content_type="FORM", ref=spec["ref"], title=spec["title"], category_id=category_id, description=spec["description"], filename=f"{spec['ref']}-owner-demo.txt", mime_type="text/plain", content=f"AMEC owner demo source for {spec['ref']}.".encode(), actor=actor, idempotency_key=f"owner-demo:FORM:{spec['ref']}", correlation_id=f"owner-demo:FORM:{spec['ref']}", used_in=spec["used_in"])

    active_by_title = {item.title: item for item in db.scalars(select(MasterContentItem).where(MasterContentItem.content_type == "FORM", MasterContentItem.status == "ACTIVE")).all()}
    purpose_refs = {
        (active_by_title.get("AMEC Proposal Template"), "BD", "PROPOSAL_TEMPLATE"),
        (active_by_title.get("AMEC Proposal Checklist"), "BD", "PROPOSAL_CHECKLIST"),
        (active_by_title.get("AMEC Contract Template"), "ADMIN", "CONTRACT_TEMPLATE"),
    }
    for item, module, usage_type in purpose_refs:
        if item and not db.scalar(select(MasterContentModuleBinding).where(MasterContentModuleBinding.master_content_id == item.id, MasterContentModuleBinding.module == module, MasterContentModuleBinding.usage_type == usage_type)):
            db.add(MasterContentModuleBinding(master_content_id=item.id, module=module, usage_type=usage_type, active=True, created_by=actor))

    created_definitions: list[str] = []
    preserved_definitions: list[str] = []
    for spec in OWNER_DEFINITION_SPECS:
        active_by_ref = db.scalar(select(DefinitionEntry).where(DefinitionEntry.ref == spec["ref"], DefinitionEntry.status == "ACTIVE"))
        active_by_term = db.scalar(select(DefinitionEntry).where(DefinitionEntry.term == spec["term"], DefinitionEntry.status == "ACTIVE"))
        existing = active_by_ref or active_by_term
        if existing:
            preserved_definitions.append(spec["ref"])
            continue
        definition = DefinitionEntry(ref=spec["ref"], term=spec["term"], category=spec["category"], used_in=spec["used_in"], status="ACTIVE", created_by=actor)
        db.add(definition)
        db.flush()
        revision = DefinitionRevision(definition_id=definition.id, revision_number=1, term=definition.term, category=definition.category, used_in=definition.used_in, description=spec["description"], aliases=[], notes=None, changed_by=actor, change_reason="Owner demo seed", status="CURRENT")
        db.add(revision)
        db.flush()
        definition.current_revision_id = revision.id
        emit_definition_revision_event(db, definition=definition, revision=revision, previous=None, actor=actor, correlation_id=f"owner-demo:DEFINITION:{spec['ref']}")
        for module in definition.used_in:
            db.add(MasterContentModuleBinding(definition_id=definition.id, module=module, usage_type="SEMANTIC_SOURCE", active=True, created_by=actor))
        created_definitions.append(definition.ref)
    db.commit()
    forme_result = _reconcile_forme_masters(db, actor=actor)
    return {"archived_master": archived_master, "archived_definitions": archived_definitions, "created_master": created_master, "preserved_master": preserved_master, "created_definitions": created_definitions, "preserved_definitions": preserved_definitions, "generic_placeholder_analysis": placeholder_result, "forme_parity": forme_result}


def _version_projection(version: DocumentVersion) -> dict[str, Any]:
    metadata = version.metadata_json or {}
    return {
        "id": version.id,
        "version": version.version_number,
        "status": _status(version),
        "file_name": version.source_filename,
        "mime_type": version.mime_type,
        "size_bytes": version.file_size,
        "updated_by": metadata.get("uploaded_by", "Unknown"),
        "updated_at": version.ingested_at.isoformat(),
        "change_reason": metadata.get("change_reason"),
        "change_kind": metadata.get("change_kind", "CREATE"),
        "downloadable": _status(version) in {"CURRENT", "SUPERSEDED"},
        "rendition": {
            "status": version.rendition_status,
            "available": version.rendition_status == "SOURCE_PDF",
            "mime_type": version.rendition_mime_type,
            "size_bytes": version.rendition_file_size,
        },
    }


def item_projection(db: Session, item: MasterContentItem, include_history: bool = False) -> dict[str, Any]:
    current = db.get(DocumentVersion, item.current_document_version_id) if item.current_document_version_id else None
    category = db.get(ContentCategory, item.category_id) if item.category_id else None
    result: dict[str, Any] = {
        "id": item.id,
        "ref": item.ref,
        "content_type": item.content_type,
        "title": item.title,
        "category": {"id": category.id, "code": category.code, "label": category.label} if category else None,
        "description": item.description,
        "used_in": _modules_for(db, item_id=item.id),
        "purpose_bindings": [{"module": binding.module, "usage_type": binding.usage_type, "active": binding.active} for binding in db.scalars(select(MasterContentModuleBinding).where(MasterContentModuleBinding.master_content_id == item.id, MasterContentModuleBinding.active.is_(True)).order_by(MasterContentModuleBinding.module, MasterContentModuleBinding.usage_type)).all()],
        "source_type_code": item.source_type_code,
        "engineering_metadata": item.engineering_metadata or {},
        "status": item.status,
        "needs_review": bool(item.needs_review),
        "review_note": item.review_note,
        "owner_status": "Inactive" if item.status != "ACTIVE" else "Needs Review" if item.needs_review else "Current",
        "version": current.version_number if current else None,
        "version_status": _status(current) if current else "NO_VERSION",
        "current_source_filename": current.source_filename if current else None,
        "current_source_mime_type": current.mime_type if current else None,
        "updated": item.updated_at.isoformat() if item.updated_at else None,
        "storage_status": "Storage verified" if current and _status(current) == "CURRENT" else "Storage unavailable",
        "current_version_id": current.id if current else None,
        "preview": {"status": current.rendition_status, "available": current.rendition_status == "SOURCE_PDF"} if current else {"status": "RENDITION_NOT_AVAILABLE", "available": False},
        "governance": governance_projection(db, item, include_history=include_history),
    }
    if include_history:
        versions = db.scalars(select(DocumentVersion).where(DocumentVersion.document_id == item.document_id).order_by(DocumentVersion.version_number.desc())).all()
        result["versions"] = [_version_projection(version) for version in versions]
    return result


def _verify_and_promote(
    db: Session,
    *,
    item: MasterContentItem,
    document: Document,
    version: DocumentVersion,
    content: bytes,
    configured_destination: str,
    actor: str,
    correlation_id: str,
    source_surface: str = "DASHBOARD",
    previous: DocumentVersion | None,
    category_changed: bool = False,
    used_in_changed: bool = False,
) -> None:
    if _deployed_synthetic():
        # Vercel TEST has no durable binary provider. Keep synthetic bytes in
        # the durable DocumentVersion row and never use instance or /tmp state.
        version.synthetic_content = content
        version.source_path_or_reference = f"synthetic-db://master-content/{item.id}/{version.id}"
        if version.mime_type == "application/pdf" or Path(version.source_filename).suffix.lower() == ".pdf":
            version.rendition_status = "SOURCE_PDF"
            version.rendition_path_or_reference = version.source_path_or_reference
            version.rendition_sha256 = version.sha256
            version.rendition_mime_type = version.mime_type
            version.rendition_file_size = version.file_size
        else:
            version.rendition_status = "RENDITION_NOT_AVAILABLE"
            version.rendition_path_or_reference = None
            version.rendition_sha256 = None
            version.rendition_mime_type = None
            version.rendition_file_size = None
        version.metadata_json = {**(version.metadata_json or {}), "master_status": "VERIFIED", "read_back_verified": True, "storage_provider": "synthetic-db"}
        db.flush()
    elif get_settings().storage_provider.lower() == "smb":
        try:
            store = create_binary_store()
            service = DocumentStorageService(store)
            target = StorageTarget(getattr(store, "provider_id", "smb"), getattr(getattr(store, "config", None), "share", ""), configured_destination)
            service.store_version(
                db,
                document=document,
                content=content,
                filename=version.source_filename,
                mime_type=version.mime_type,
                target=target,
                actor=actor,
                correlation_id=correlation_id,
                idempotency_key=f"master-content:{version.id}:{version.sha256}",
                source_system="MASTER_CONTENT",
                metadata={"master_content_id": item.id, "content_type": item.content_type},
                version_number=version.version_number,
                candidate_version_id=version.id,
            )
        except StorageError as exc:
            version.metadata_json = {**(version.metadata_json or {}), "master_status": exc.code.value}
            db.flush()
            raise _error(exc.code.value, 502) from exc
        if _deployed_synthetic():
            version.synthetic_content = content
        if version.mime_type == "application/pdf" or Path(version.source_filename).suffix.lower() == ".pdf":
            version.rendition_status = "SOURCE_PDF"
            version.rendition_path_or_reference = version.source_path_or_reference
            version.rendition_sha256 = version.sha256
            version.rendition_mime_type = version.mime_type
            version.rendition_file_size = version.file_size
        else:
            version.rendition_status = "RENDITION_NOT_AVAILABLE"
            version.rendition_path_or_reference = None
            version.rendition_sha256 = None
            version.rendition_mime_type = None
            version.rendition_file_size = None
        version.metadata_json = {**(version.metadata_json or {}), "master_status": "VERIFIED", "read_back_verified": True, "storage_provider": "smb"}
        db.flush()
    else:
        adapter = _adapter()
        try:
            target = adapter.resolve_configured_path(configured_destination)
            existing_same_hash = None
            if previous and previous.sha256 == version.sha256 and previous.source_path_or_reference:
                try:
                    existing_same_hash = adapter.verify_artifact(previous.source_path_or_reference, version.sha256, version.file_size)
                except (FileNotFoundError, ValueError, OSError):
                    existing_same_hash = None
            if existing_same_hash and existing_same_hash.get("verified"):
                sor_metadata = existing_same_hash
                version.source_path_or_reference = previous.source_path_or_reference
            else:
                stored = adapter.put_configured_artifact(configured_destination, version.source_filename, content)
                version.source_path_or_reference = stored["path"]
                sor_metadata = adapter.verify_artifact(stored["path"], version.sha256, version.file_size)
            if not sor_metadata.get("verified"):
                version.metadata_json = {**(version.metadata_json or {}), "master_status": "SOR_HASH_MISMATCH"}
                db.commit()
                raise _error("SOR_HASH_MISMATCH", 502)
            if sor_metadata.get("path", "").startswith("/") or target is None:
                raise _error("SOR_READBACK_FAILED", 502)
            if _deployed_synthetic():
                version.synthetic_content = content
            if version.mime_type == "application/pdf" or Path(version.source_filename).suffix.lower() == ".pdf":
                version.rendition_status = "SOURCE_PDF"
                version.rendition_path_or_reference = version.source_path_or_reference
                version.rendition_sha256 = version.sha256
                version.rendition_mime_type = version.mime_type
                version.rendition_file_size = version.file_size
            else:
                # DOCX and other source formats remain authoritative and truthful
                # when no safe server-side converter is configured.
                version.rendition_status = "RENDITION_NOT_AVAILABLE"
                version.rendition_path_or_reference = None
                version.rendition_sha256 = None
                version.rendition_mime_type = None
                version.rendition_file_size = None
            version.metadata_json = {**(version.metadata_json or {}), "master_status": "VERIFIED", "verified_at": version.ingested_at.isoformat()}
            db.flush()
        except HTTPException:
            raise
        except (FileNotFoundError, ValueError, OSError, RuntimeError) as exc:
            version.metadata_json = {**(version.metadata_json or {}), "master_status": "SOR_WRITE_FAILED", "failure": str(exc)}
            db.commit()
            raise _error("SOR_UNAVAILABLE" if isinstance(exc, FileNotFoundError) else "SOR_WRITE_FAILED", 502) from exc

    if previous:
        previous.metadata_json = {**(previous.metadata_json or {}), "master_status": "SUPERSEDED"}
        previous.approval_state = DocumentApprovalState.SUPERSEDED
        previous.superseded_by = version.id
    version.approval_state = DocumentApprovalState.REVIEWED
    version.metadata_json = {**(version.metadata_json or {}), "master_status": "CURRENT", "uploaded_by": actor}
    document.current_version_id = version.id
    item.current_document_version_id = version.id
    category = db.get(ContentCategory, item.category_id) if item.category_id else None
    change_reason = (version.metadata_json or {}).get("change_reason")
    event = MasterContentChangeEvent(master_content_id=item.id, previous_version_id=previous.id if previous else None, new_version_id=version.id, change_type="MASTER_CONTENT_VERSION_PROMOTED", status="APPLIED", correlation_id=correlation_id, actor_or_system=actor, metadata_json={"content_type": item.content_type, "ref": item.ref, "version_number": version.version_number, "source_surface": source_surface, "used_in": item.used_in or []}, event_type="MASTER_CONTENT_CREATED" if previous is None else "MASTER_CONTENT_VERSION_PROMOTED", content_type=item.content_type, business_ref=item.ref, category_snapshot={"id": category.id, "code": category.code, "label": category.label} if category else {}, change_kind=(version.metadata_json or {}).get("change_kind", "MODIFY"), change_reason=change_reason, materiality=_materiality(item, previous, version, category_changed or used_in_changed), source_hash=version.sha256)
    db.add(event)
    db.flush()
    propagate_master_change(db, event, item, version)
    audit(db, correlation_id=correlation_id, event_type="SOR_READBACK_VERIFIED", entity_type="MasterContentItem", entity_id=item.id, actor_id=actor, metadata={"ref": item.ref, "version": version.version_number, "source_surface": source_surface})
    audit(db, correlation_id=correlation_id, event_type="MASTER_CONTENT_VERSION_PROMOTED", entity_type="MasterContentItem", entity_id=item.id, actor_id=actor, before={"version": previous.version_number if previous else None}, after={"version": version.version_number, "status": "CURRENT"}, metadata={"ref": item.ref, "source_surface": source_surface})


def create_master_content(
    db: Session,
    *,
    content_type: str,
    ref: str | None,
    title: str,
    category_id: str | None,
    description: str | None,
    filename: str,
    mime_type: str,
    content: bytes,
    actor: str,
    idempotency_key: str,
    correlation_id: str,
    source_surface: str = "DASHBOARD",
    used_in: Any = None,
    source_type_code: str | None = None,
    engineering_metadata: dict[str, Any] | None = None,
    needs_review: bool = False,
    review_note: str | None = None,
) -> dict[str, Any]:
    content_type = content_type.upper().strip()
    title = title.strip()
    if content_type not in CONTENT_TYPES or not title:
        raise _error("MASTER_CONTENT_METADATA_INVALID")
    if content_type == "ENGINEERING_WORK" and source_type_code and source_type_code.upper() not in ENGINEERING_SOURCE_TYPES:
        raise _error("ENGINEERING_SOURCE_TYPE_NOT_ALLOWED", source_type_code=source_type_code)
    prior_idempotency = db.scalar(select(MasterContentIdempotency).where(MasterContentIdempotency.idempotency_key == idempotency_key))
    if prior_idempotency:
        item = db.get(MasterContentItem, prior_idempotency.master_content_id)
        return item_projection(db, item, include_history=True)
    ref, reference_generated = _allocate_reference(db, content_type, ref)
    _allowed_file(filename, content)
    _category(db, category_id, content_type)
    if db.scalar(select(MasterContentItem).where(MasterContentItem.content_type == content_type, MasterContentItem.ref == ref)):
        raise _error("MASTER_CONTENT_REF_CONFLICT", 409, ref=ref)
    mapping = _mapping()
    destination = mapping.get(SEMANTIC_DESTINATION[content_type])
    if not destination:
        raise _error("SOR_DESTINATION_UNRESOLVED", 503)
    digest = hashlib.sha256(content).hexdigest()
    document = Document(project_id=None, document_type=DocumentType.OTHER, logical_name=title, language="en", source_system="MASTER_CONTENT")
    modules = _parse_modules(used_in)
    item = MasterContentItem(ref=ref, content_type=content_type, title=title, category_id=category_id, description=description, used_in=modules, engineering_metadata=engineering_metadata or {}, source_type_code=source_type_code.upper() if source_type_code else None, status="ACTIVE", needs_review=needs_review, review_note=(review_note or None), document=document, created_by=actor)
    db.add(item)
    db.flush()
    ensure_profile(db, item, ownership="AMEC_OWNED" if actor == "owner-demo-seed" else "NEEDS_REVIEW")
    version = DocumentVersion(document_id=document.id, version_number=1, source_filename=_safe_filename(filename, ref, 1), source_path_or_reference="PENDING", sha256=digest, mime_type=mime_type or "application/octet-stream", file_size=len(content), language="en", approval_state=DocumentApprovalState.WORKING, source_system="MASTER_CONTENT", metadata_json={"master_status": "PENDING_WRITE", "content_type": content_type, "business_ref": ref, "title": title, "description": description, "used_in": modules, "engineering_metadata": engineering_metadata or {}, "reference_generated": reference_generated, "change_kind": "CREATE", "change_reason": "Initial version"})
    db.add(version)
    db.flush()
    try:
        _verify_and_promote(db, item=item, document=document, version=version, content=content, configured_destination=destination, actor=actor, correlation_id=correlation_id, source_surface=source_surface, previous=None)
        _sync_module_bindings(db, item_id=item.id, modules=modules, actor=actor)
        db.add(MasterContentIdempotency(idempotency_key=idempotency_key, master_content_id=item.id, document_version_id=version.id, result_json={"master_content_id": item.id, "document_version_id": version.id}))
        audit(db, correlation_id=correlation_id, event_type="MASTER_CONTENT_CREATED", entity_type="MasterContentItem", entity_id=item.id, actor_id=actor, after={"ref": ref, "content_type": content_type, "version": 1}, metadata={"change_reason": "Initial version", "source_surface": source_surface, "reference_generated": reference_generated})
        db.commit()
    except HTTPException:
        db.rollback() if db.in_transaction() and version.metadata_json.get("master_status") == "PENDING_WRITE" else None
        raise
    return item_projection(db, item, include_history=True)


def create_master_content_version(
    db: Session,
    *,
    item_id: str,
    expected_current_version: int,
    filename: str | None,
    mime_type: str | None,
    content: bytes | None,
    title: str | None,
    category_id: str | None,
    description: str | None,
    change_reason: str,
    actor: str,
    idempotency_key: str,
    correlation_id: str,
    source_surface: str = "DASHBOARD",
    used_in: Any = None,
    engineering_metadata: dict[str, Any] | None = None,
    source_type_code: str | None = None,
    needs_review: bool | None = None,
    review_note: str | None = None,
) -> dict[str, Any]:
    item = db.scalar(select(MasterContentItem).where(MasterContentItem.id == item_id).with_for_update())
    if not item:
        raise _error("CONTENT_NOT_FOUND", 404)
    if item.status != "ACTIVE":
        raise _error("CONTENT_ARCHIVED", 409)
    current = db.get(DocumentVersion, item.current_document_version_id) if item.current_document_version_id else None
    if not current or current.version_number != expected_current_version:
        raise _error("VERSION_CONFLICT", 409, current_version=current.version_number if current else None)
    existing = db.scalar(select(MasterContentIdempotency).where(MasterContentIdempotency.idempotency_key == idempotency_key))
    if existing:
        return item_projection(db, item, include_history=True)
    metadata_only = content is None
    if content is None:
        content = read_master_content_bytes(db, current)
    _allowed_file(filename or current.source_filename, content)
    category = _category(db, category_id, item.content_type) if category_id else db.get(ContentCategory, item.category_id) if item.category_id else None
    prior_category_id = item.category_id
    prior_modules = _modules_for(db, item_id=item.id)
    modules = _parse_modules(used_in) if used_in is not None else prior_modules
    mapping = _mapping()
    destination = mapping.get(SEMANTIC_DESTINATION[item.content_type])
    if not destination:
        raise _error("SOR_DESTINATION_UNRESOLVED", 503)
    next_version = current.version_number + 1
    digest = hashlib.sha256(content).hexdigest()
    document = db.get(Document, item.document_id)
    item.title = (title or item.title).strip()
    item.category_id = category.id if category else item.category_id
    if description is not None:
        item.description = description
    item.used_in = modules
    if needs_review is not None:
        item.needs_review = needs_review
        item.review_note = (review_note or None) if needs_review else None
    if engineering_metadata is not None:
        item.engineering_metadata = engineering_metadata
    if source_type_code is not None:
        if item.content_type == "ENGINEERING_WORK" and source_type_code.upper() not in ENGINEERING_SOURCE_TYPES:
            raise _error("ENGINEERING_SOURCE_TYPE_NOT_ALLOWED", source_type_code=source_type_code)
        item.source_type_code = source_type_code.upper() if item.content_type == "ENGINEERING_WORK" else None
    version = DocumentVersion(document_id=document.id, version_number=next_version, source_filename=_safe_filename(filename or current.source_filename, item.ref, next_version), source_path_or_reference="PENDING", sha256=digest, mime_type=mime_type or current.mime_type, file_size=len(content), language="en", approval_state=DocumentApprovalState.WORKING, source_system="MASTER_CONTENT", metadata_json={"master_status": "PENDING_WRITE", "content_type": item.content_type, "business_ref": item.ref, "title": item.title, "category_id": item.category_id, "description": item.description, "used_in": modules, "engineering_metadata": item.engineering_metadata or {}, "change_kind": "METADATA" if metadata_only else "MODIFY", "change_reason": change_reason, "uploaded_by": actor})
    db.add(version)
    db.flush()
    try:
        _verify_and_promote(db, item=item, document=document, version=version, content=content, configured_destination=destination, actor=actor, correlation_id=correlation_id, source_surface=source_surface, previous=current, category_changed=prior_category_id != item.category_id, used_in_changed=sorted(prior_modules) != sorted(modules))
        _sync_module_bindings(db, item_id=item.id, modules=modules, actor=actor)
        db.add(MasterContentIdempotency(idempotency_key=idempotency_key, master_content_id=item.id, document_version_id=version.id, result_json={"master_content_id": item.id, "document_version_id": version.id}))
        audit(db, correlation_id=correlation_id, event_type="MASTER_CONTENT_VERSION_UPLOADED", entity_type="MasterContentItem", entity_id=item.id, actor_id=actor, after={"ref": item.ref, "version": next_version}, metadata={"change_reason": change_reason, "source_surface": source_surface})
        db.commit()
    except HTTPException:
        raise
    return item_projection(db, item, include_history=True)


def reconcile_item(db: Session, item_id: str, correlation_id: str) -> dict[str, Any]:
    item = db.get(MasterContentItem, item_id)
    if not item or not item.current_document_version_id:
        raise _error("CONTENT_NOT_FOUND", 404)
    version = db.get(DocumentVersion, item.current_document_version_id)
    if _deployed_synthetic() and version.synthetic_content is not None:
        actual = {"verified": hashlib.sha256(version.synthetic_content).hexdigest() == version.sha256 and len(version.synthetic_content) == version.file_size}
    else:
        actual = _adapter().verify_artifact(version.source_path_or_reference, version.sha256, version.file_size)
    if not actual.get("verified"):
        audit(db, correlation_id=correlation_id, event_type="EXTERNAL_MUTATION_DETECTED", entity_type="MasterContentItem", entity_id=item.id, after={"ref": item.ref, "version": version.version_number}, metadata={"code": "SOR_EXTERNAL_MUTATION"})
        db.commit()
        raise _error("SOR_EXTERNAL_MUTATION", 409)
    return item_projection(db, item, include_history=True)


def archive_master_content(db: Session, *, item_id: str, actor: str, correlation_id: str) -> dict[str, Any]:
    item = db.get(MasterContentItem, item_id)
    if not item:
        raise _error("CONTENT_NOT_FOUND", 404)
    item.status = "ARCHIVED"
    current = db.get(DocumentVersion, item.current_document_version_id) if item.current_document_version_id else None
    event = MasterContentChangeEvent(master_content_id=item.id, previous_version_id=current.id if current else None, new_version_id=current.id if current else item.id, change_type="MASTER_CONTENT_ARCHIVED", status="APPLIED", correlation_id=correlation_id, actor_or_system=actor, metadata_json={"ref": item.ref, "version_number": current.version_number if current else None}, event_type="MASTER_CONTENT_ARCHIVED", content_type=item.content_type, business_ref=item.ref, change_kind="ARCHIVE", change_reason="Owner archived content", materiality="MATERIAL", source_hash=current.sha256 if current else None)
    db.add(event)
    audit(db, correlation_id=correlation_id, event_type="MASTER_CONTENT_ARCHIVED", entity_type="MasterContentItem", entity_id=item.id, actor_id=actor, after={"ref": item.ref, "status": "ARCHIVED"})
    db.commit()
    return item_projection(db, item, include_history=True)


def definition_projection(db: Session, definition: DefinitionEntry, include_history: bool = False) -> dict[str, Any]:
    current = db.get(DefinitionRevision, definition.current_revision_id) if definition.current_revision_id else None
    result: dict[str, Any] = {"id": definition.id, "ref": definition.ref, "term": definition.term, "category": definition.category, "description": current.description if current else None, "revision_id": current.id if current else None, "revision": current.revision_number if current else None, "status": definition.status, "updated": definition.updated_at.isoformat() if definition.updated_at else None, "aliases": current.aliases if current else [], "notes": current.notes if current else None, "used_in": _modules_for(db, definition_id=definition.id)}
    if include_history:
        revisions = db.scalars(select(DefinitionRevision).where(DefinitionRevision.definition_id == definition.id).order_by(DefinitionRevision.revision_number.desc())).all()
        result["revisions"] = [{"id": r.id, "revision": r.revision_number, "term": r.term, "category": r.category, "description": r.description, "used_in": r.used_in or [], "aliases": r.aliases, "notes": r.notes, "status": r.status, "changed_by": r.changed_by, "changed_at": r.changed_at.isoformat(), "change_reason": r.change_reason} for r in revisions]
    return result


def emit_definition_revision_event(db: Session, *, definition: DefinitionEntry, revision: DefinitionRevision, previous: DefinitionRevision | None, actor: str, correlation_id: str) -> MasterContentChangeEvent:
    digest = hashlib.sha256(json.dumps({"term": revision.term, "description": revision.description, "aliases": revision.aliases}, sort_keys=True).encode()).hexdigest()
    event = MasterContentChangeEvent(definition_id=definition.id, previous_version_id=previous.id if previous else None, new_version_id=revision.id, change_type="DEFINITION_REVISION_PROMOTED", status="PROCESSED", correlation_id=correlation_id, actor_or_system=actor, metadata_json={"term": revision.term, "revision": revision.revision_number, "version_number": revision.revision_number}, event_type="DEFINITION_REVISION_PROMOTED", content_type="DEFINITION", business_ref=definition.ref or revision.term, change_kind="CREATE" if previous is None else "MODIFY", change_reason=revision.change_reason, materiality="MATERIAL", source_hash=digest)
    db.add(event)
    db.flush()
    for role in ("OWNER", "BUSINESS_DEVELOPMENT", "ENGINEERING"):
        if not _delivery_exists(db, event.id, "NOTIFICATION", "ROLE", role, role):
            db.add(NotificationEvent(recipient_role=role, channel="IN_APP", event_type="DEFINITION_REVISION_PROMOTED", status="PENDING", subject=f"Definition updated: {revision.term}", body_preview=f"Definition revision {revision.revision_number} is current.", correlation_id=correlation_id, domain="MASTER_CONTENT", audience=[role], actor=actor, deep_link="/dashboard"))
            _record_delivery(db, event.id, "NOTIFICATION", "ROLE", role, role)
    audit(db, correlation_id=correlation_id, event_type="DEFINITION_REVISION_PROMOTED", entity_type="DefinitionEntry", entity_id=definition.id, actor_id=actor, after={"revision": revision.revision_number, "term": revision.term})
    return event


def definition_lookup(db: Session, term: str) -> dict[str, Any] | None:
    definition = db.scalar(select(DefinitionEntry).where(DefinitionEntry.term == term, DefinitionEntry.status == "ACTIVE"))
    return definition_projection(db, definition, include_history=False) if definition else None
