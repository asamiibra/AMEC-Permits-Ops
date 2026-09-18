"""Bounded Proposal source workspace and immutable capture index."""
from __future__ import annotations

import hashlib
import json
import mimetypes
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from sqlalchemy import select, true
from sqlalchemy.orm import Session

from ..models import Document, DocumentType, DocumentVersion, DocumentApprovalState, Opportunity, ProposalRevision, ProposalSourceDecision, ProposalSourceLink, Project
from ..storage.proposal_source_tree import BridgeProposalSourceProvider, MountedProposalSource, ProposalSourceProvider, SourceEntry, SourceProject
from ..storage import DocumentStorageService, StorageTarget, create_binary_store
from ..config.settings import get_settings
from .proposal_document_package import DocumentPackageError, digest
from .proposal_editor_model import import_editor_model

LOGICAL_ROOT = "Tenders/1- Proposal/2026"
PILOT = "454 - Al Watan Center"
LOGICAL_SOURCE_CATEGORIES = frozenset({
    "TENDER_DOCUMENTS", "PHOTOS_IMAGES", "EMAIL", "CLIENT_DATA",
    "CLIENT_DOCUMENTS", "PROJECT_INFORMATION", "OTHER_UNCLASSIFIED",
})


def canonical_source_project_identity(*, number: int, folder_name: str, logical_root: str = LOGICAL_ROOT, source_system: str = "QATAR_SYNOLOGY") -> str:
    """Stable source identity; project number is only a display reference."""
    payload = {
        "source_system": source_system,
        "logical_root": logical_root.rstrip("/"),
        "year": logical_root.rstrip("/").split("/")[-1],
        "folder_name": folder_name,
        "folder_identity": f"{logical_root.rstrip('/')}/{folder_name}",
    }
    return "synology-project:" + hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def configured_source_root() -> Path:
    configured = os.getenv("PROPOSAL_SOURCE_ROOT", "")
    if configured:
        return Path(configured).expanduser()
    root = Path(__file__).resolve().parents[3] / "mock-systems" / "proposal-sources" / "Tenders" / "1- Proposal" / "2026"
    return root


def _source(db: Session | None = None) -> ProposalSourceProvider:
    """Select the source implementation without changing Proposal routes."""
    if get_settings().source_intake_mode.upper() == "BRIDGE":
        if db is None:
            raise RuntimeError("BRIDGE_SOURCE_PROVIDER_REQUIRES_DATABASE")
        return BridgeProposalSourceProvider(db)
    return MountedProposalSource(configured_source_root())


def _project(source: ProposalSourceProvider, number: int) -> SourceProject:
    projects = [item for item in source.discover() if item.number == number]
    if not projects:
        raise FileNotFoundError("SOURCE_PROJECT_NOT_FOUND")
    return projects[0]


def _entry(source: ProposalSourceProvider, number: int, relative: str) -> SourceEntry:
    project = _project(source, number)
    prefix = f"{project.folder_name}/"
    if not relative.startswith(prefix):
        raise FileNotFoundError("SOURCE_PATH_OUTSIDE_PROJECT")
    for item in source.inventory(project.folder_name):
        if item.relative_path == relative:
            return item
    raise FileNotFoundError("SOURCE_FILE_NOT_FOUND")


def default_logical_category(relative_path: str, filename: str | None = None) -> str:
    """Classify a source only as an initial suggestion.

    The value is deliberately kept beside the server source index so the
    browser and promotion path cannot drift into different classifications.
    An Owner override is written to DocumentVersion metadata and always wins.
    """
    value = f"{relative_path} {filename or relative_path}".lower()
    ext = (filename or relative_path).lower().rsplit(".", 1)[-1] if "." in (filename or relative_path) else ""
    if ext in {"eml", "msg"} or "email" in value or "correspondence" in value:
        return "EMAIL"
    if ext in {"jpg", "jpeg", "png", "gif", "webp", "heic", "tif", "tiff", "bmp"} or any(token in value for token in ("photo", "image", "screenshot", "drawing", "plan")):
        return "PHOTOS_IMAGES"
    if any(token in value for token in ("client document", "registration", "certificate", "commercial record", " cr ", "identity", " id ")):
        return "CLIENT_DOCUMENTS"
    if any(token in value for token in ("client data", "client information", "contact", "company profile")):
        return "CLIENT_DATA"
    if any(token in value for token in ("tender", "rfp", "rfq", "boq", "scope", "specification", "sow", "schedule")) or ext in {"pdf", "doc", "docx", "xls", "xlsx", "csv"}:
        return "TENDER_DOCUMENTS"
    if any(token in value for token in ("project", "site", "location", "brief", "method statement")):
        return "PROJECT_INFORMATION"
    return "OTHER_UNCLASSIFIED"


def source_processing_state(filename: str, mime_type: str | None) -> str:
    """Explicitly describe source understanding eligibility; never infer AI readiness from capture."""
    name = filename.lower()
    mime = (mime_type or "").lower()
    if name.endswith((".docx", ".doc", ".txt", ".csv", ".eml", ".msg")) or mime.startswith("text/"):
        return "TEXT_EXTRACTED"
    if name.endswith(".pdf") or mime == "application/pdf":
        return "TEXT_EXTRACTED"  # parser may downgrade to METADATA_ONLY at compile time
    if name.endswith((".jpg", ".jpeg", ".png", ".webp", ".heic", ".tif", ".tiff")) or mime.startswith("image/"):
        return "VISION_READY"
    if name.endswith((".xls", ".xlsx", ".xlsm")):
        return "PARTIAL"
    if name.endswith((".dwg", ".dxf", ".zip", ".rar", ".7z")):
        return "UNSUPPORTED"
    return "METADATA_ONLY"


def source_category(version: DocumentVersion, decision: ProposalSourceDecision | None = None) -> str:
    if decision and decision.logical_category in LOGICAL_SOURCE_CATEGORIES:
        return str(decision.logical_category)
    metadata = version.metadata_json if isinstance(version.metadata_json, dict) else {}
    value = str(metadata.get("logical_category") or "").strip().upper()
    return value if value in LOGICAL_SOURCE_CATEGORIES else default_logical_category(
        str(metadata.get("source_relative_path") or version.source_filename or ""), version.source_filename
    )


def source_included(version: DocumentVersion, decision: ProposalSourceDecision | None = None) -> bool:
    if decision is not None:
        return bool(decision.included_in_proposal)
    metadata = version.metadata_json if isinstance(version.metadata_json, dict) else {}
    return bool(metadata.get("included_in_proposal", True))


def _decision_for(
    decisions: dict[str, ProposalSourceDecision],
    version: DocumentVersion | None,
    path: str,
) -> ProposalSourceDecision | None:
    """Resolve a normalized Owner decision for current and legacy source keys."""
    metadata = version.metadata_json if version is not None and isinstance(version.metadata_json, dict) else {}
    for key in (metadata.get("proposal_source_key"), metadata.get("source_relative_path"), path):
        if key and str(key) in decisions:
            return decisions[str(key)]
    suffix = f":{path}"
    return next((row for key, row in decisions.items() if str(key).endswith(suffix)), None)


def canonical_source_decisions(
    db: Session,
    *,
    source_project_identity: str | None,
    versions: list[DocumentVersion] | tuple[DocumentVersion, ...] = (),
) -> dict[str, ProposalSourceDecision]:
    """Resolve Owner decisions across current and legacy source identities.

    Source decisions have historically been keyed by either the canonical
    project identity, the identity persisted on a DocumentVersion, or the
    relative source path/proposal_source_key.  Every Proposal V1 surface uses
    this one resolver so a decision cannot disappear when a Proposal is
    promoted or regenerated.
    """
    candidates = {str(source_project_identity)} if source_project_identity else set()
    for version in versions:
        metadata = version.metadata_json if isinstance(version.metadata_json, dict) else {}
        if metadata.get("source_project_identity"):
            candidates.add(str(metadata["source_project_identity"]))
    if not candidates:
        return {}
    rows = db.scalars(
        select(ProposalSourceDecision)
        .where(ProposalSourceDecision.source_project_identity.in_(candidates))
        .order_by(ProposalSourceDecision.updated_at.desc(), ProposalSourceDecision.decision_version.desc(), ProposalSourceDecision.id.desc())
    ).all()
    # A source can have both a legacy and canonical project identity after a
    # bridge promotion.  The newest Owner decision is the authoritative one;
    # this keeps the resolver deterministic while allowing old records to be
    # read without migration or duplicate fallback code.
    decisions: dict[str, ProposalSourceDecision] = {}
    for row in rows:
        decisions.setdefault(str(row.logical_source_identity), row)
    return decisions


def source_decision_for_version(
    db: Session,
    *,
    source_project_identity: str | None,
    version: DocumentVersion,
    path: str | None = None,
) -> ProposalSourceDecision | None:
    """Resolve the one Owner decision for a version across identity aliases."""
    metadata = version.metadata_json if isinstance(version.metadata_json, dict) else {}
    logical_identity = str(path or metadata.get("proposal_source_key") or metadata.get("source_relative_path") or version.id)
    return _decision_for(
        canonical_source_decisions(db, source_project_identity=source_project_identity, versions=(version,)),
        version,
        logical_identity,
    )


def current_source_versions(db: Session, number: int) -> dict[str, DocumentVersion]:
    """Return exactly one present, non-superseded version per source path."""
    rows = db.scalars(
        select(DocumentVersion)
        .where(DocumentVersion.source_system.in_(("QATAR_SOURCE_INTAKE_BRIDGE", "SYNOLOGY_PROPOSAL_SOURCE")))
        .order_by(DocumentVersion.ingested_at.desc(), DocumentVersion.version_number.desc(), DocumentVersion.id.desc())
    ).all()
    selected: dict[str, DocumentVersion] = {}
    for version in rows:
        metadata = version.metadata_json if isinstance(version.metadata_json, dict) else {}
        if metadata.get("source_project_number") != number or metadata.get("source_presence_state", "PRESENT") != "PRESENT":
            continue
        path = str(metadata.get("source_relative_path") or "")
        if path and version.superseded_by is None and path not in selected:
            selected[path] = version
    return selected


def source_manifest(db: Session, number: int, *, include_excluded: bool = True) -> dict[str, Any]:
    """Build the canonical persisted-source projection used by promotion/AI."""
    with _source(db) as source:
        project = _project(source, number)
        inventory = source.inventory(project.folder_name)
        scan = source._latest_scan(project.folder_name) if hasattr(source, "_latest_scan") else None
    current = current_source_versions(db, number)
    identity = (scan.source_project_identity if scan is not None else None) or canonical_source_project_identity(number=number, folder_name=project.folder_name)
    decisions: dict[str, ProposalSourceDecision] = {}
    if db is not None:
        decisions = canonical_source_decisions(db, source_project_identity=identity, versions=tuple(current.values()))
    historical_by_path: dict[str, DocumentVersion] = {}
    if db is not None:
        for version in db.scalars(select(DocumentVersion).where(DocumentVersion.source_system.in_(("QATAR_SOURCE_INTAKE_BRIDGE", "SYNOLOGY_PROPOSAL_SOURCE"))).order_by(DocumentVersion.ingested_at.desc(), DocumentVersion.version_number.desc())).all():
            metadata = version.metadata_json if isinstance(version.metadata_json, dict) else {}
            if metadata.get("source_project_number") == number and metadata.get("source_relative_path") and metadata.get("source_presence_state") == "MISSING_AT_SOURCE":
                historical_by_path.setdefault(str(metadata["source_relative_path"]), version)
    entries: list[dict[str, Any]] = []
    completeness_reasons: list[str] = []
    if scan is not None and scan.status != "COMPLETED":
        completeness_reasons.append(f"SCAN_{scan.status}")
    for item in inventory:
        if item.is_directory:
            continue
        version = current.get(item.relative_path)
        metadata = version.metadata_json if version and isinstance(version.metadata_json, dict) else {}
        logical_identity = (metadata.get("proposal_source_key") or item.relative_path)
        decision = _decision_for(decisions, version, item.relative_path)
        included = source_included(version, decision) if version else (decision.included_in_proposal if decision else True)
        if not include_excluded and not included:
            continue
        capture_status = getattr(item, "capture_status", "PRESENT")
        if version is None or capture_status not in {"CAPTURED", "PRESENT", "SUCCESS"}:
            completeness_reasons.append(f"{capture_status or 'CAPTURE_MISSING'}:{item.relative_path}")
        entries.append({
            "source_identity": metadata.get("proposal_source_key") or f"PROPOSAL_SOURCE:{number}:{item.relative_path}",
            "source_path": item.relative_path,
            "document_version_id": version.id if version else None,
            "document_id": version.document_id if version else None,
            "sha256": version.sha256 if version else None,
            "filename": item.name,
            "content_type": mimetypes.guess_type(item.name)[0] or "application/octet-stream",
            "size": item.size,
            "source_version_token": metadata.get("source_modified_at") or str(item.modified_ns),
            "source_presence_state": metadata.get("source_presence_state", "MISSING_AT_SOURCE") if version else "MISSING_AT_SOURCE",
            "currentness_state": "CURRENT" if version else "MISSING",
            "source_role": metadata.get("source_role") or "SOURCE_WORKSPACE",
            "effective_category": source_category(version, decision) if version else (decision.logical_category if decision and decision.logical_category else default_logical_category(item.relative_path, item.name)),
            "category_origin": "OWNER" if (decision and decision.category_origin == "OWNER") or metadata.get("logical_category_source") == "OWNER_OVERRIDE" else "AUTO",
            "included": included,
            "inclusion_origin": "OWNER" if (decision and decision.inclusion_origin == "OWNER") or metadata.get("inclusion_origin") == "OWNER" else "DEFAULT",
            "processing_state": metadata.get("processing_state", "PENDING"),
            "capture_status": capture_status,
            "capture_failure_reason": getattr(item, "failure_reason", None),
            "source_scan_id": scan.scan_id if scan is not None else metadata.get("source_scan_id"),
        })
    # A completed scan is the only authority allowed to tombstone a prior
    # path.  Preserve the historical entry in the manifest when the latest
    # enumeration no longer contains it; an incomplete scan never does this.
    if scan is not None and scan.status == "COMPLETED":
        present_paths = {item.relative_path for item in inventory}
        for path, version in {**historical_by_path, **current}.items():
            metadata = version.metadata_json if isinstance(version.metadata_json, dict) else {}
            if path in present_paths:
                continue
            decision = _decision_for(decisions, version, path)
            entries.append({
                "source_identity": metadata.get("proposal_source_key") or f"PROPOSAL_SOURCE:{number}:{path}",
                "source_path": path, "document_version_id": version.id, "document_id": version.document_id,
                "sha256": version.sha256, "filename": version.source_filename,
                "content_type": version.mime_type or "application/octet-stream", "size": version.file_size,
                "source_version_token": metadata.get("source_version_token") or metadata.get("source_modified_at"),
                "source_presence_state": "MISSING_AT_SOURCE", "currentness_state": "MISSING",
                "source_role": metadata.get("source_role") or "SOURCE_WORKSPACE",
                "effective_category": source_category(version, decision),
                "category_origin": "OWNER" if ((decision and decision.category_origin == "OWNER") or metadata.get("logical_category_source") == "OWNER_OVERRIDE") else "AUTO",
                "included": source_included(version, decision),
                "inclusion_origin": "OWNER" if ((decision and decision.inclusion_origin == "OWNER") or metadata.get("inclusion_origin") == "OWNER") else "DEFAULT",
                "processing_state": metadata.get("processing_state", "PENDING"),
                "capture_status": "MISSING_AT_SOURCE", "capture_failure_reason": None,
                "source_scan_id": scan.scan_id,
            })
    canonical = [entry for entry in entries if entry["included"] or include_excluded]
    canonical.sort(key=lambda entry: (entry["source_path"], entry["source_identity"]))
    manifest_hash = hashlib.sha256(json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    completeness = "COMPLETE" if not completeness_reasons else "INCOMPLETE"
    return {
        "source_project_identity": identity,
        "source_project_number": number,
        "source_project_folder_name": project.folder_name,
        "logical_root": LOGICAL_ROOT,
        "snapshot_at": datetime.now(timezone.utc).isoformat(),
        "completeness_state": completeness,
        "completeness_reasons": completeness_reasons,
        "entries": entries,
        "source_manifest_version": "PROPOSAL-V1-MANIFEST-2",
        "source_manifest_hash": manifest_hash,
        "source_snapshot_id": scan.scan_id if scan is not None else None,
        "scan_status": scan.status if scan is not None else "RECEIVED_FILES_ONLY",
    }


def build_effective_proposal_source_manifest(db: Session, proposal: Opportunity, *, include_excluded: bool = True) -> dict[str, Any]:
    """Single manifest builder shared by initial promotion and regeneration."""
    workspace = (proposal.proposal_fields_json or {}).get("source_workspace") or {}
    number = workspace.get("project_number")
    if number is None:
        raise ValueError("PROPOSAL_SOURCE_PROJECT_IDENTITY_REQUIRED")
    manifest = source_manifest(db, int(number), include_excluded=include_excluded)
    source_identity = manifest.get("source_project_identity") or workspace.get("source_project_identity")
    linked_versions = [version for link in db.scalars(select(ProposalSourceLink).where(ProposalSourceLink.proposal_id == proposal.id, ProposalSourceLink.active == true())).all() if (version := db.get(DocumentVersion, link.document_version_id)) is not None]
    decisions = canonical_source_decisions(db, source_project_identity=source_identity, versions=tuple(linked_versions))
    known = {str(entry.get("document_version_id")) for entry in manifest["entries"] if entry.get("document_version_id")}
    current_paths = {str(entry.get("source_path")): str(entry.get("document_version_id")) for entry in manifest["entries"] if entry.get("source_path") and entry.get("document_version_id")}
    for link in db.scalars(select(ProposalSourceLink).where(ProposalSourceLink.proposal_id == proposal.id, ProposalSourceLink.active == true())).all():
        version = db.get(DocumentVersion, link.document_version_id)
        if version is None or version.id in known:
            continue
        metadata = version.metadata_json if isinstance(version.metadata_json, dict) else {}
        if link.source_role == "SOURCE_WORKSPACE" and str(metadata.get("source_relative_path") or "") in current_paths and current_paths[str(metadata.get("source_relative_path") or "")] != str(version.id):
            continue
        decision = _decision_for(decisions, version, str(metadata.get("source_relative_path") or version.source_filename))
        included = source_included(version, decision)
        if not include_excluded and not included:
            continue
        path = str(metadata.get("source_relative_path") or version.source_filename)
        manifest["entries"].append({"source_identity": metadata.get("proposal_source_key") or link.id, "source_path": path, "document_version_id": version.id, "document_id": version.document_id, "sha256": version.sha256, "filename": version.source_filename, "content_type": version.mime_type, "size": version.file_size, "source_version_token": metadata.get("source_version_token"), "source_presence_state": metadata.get("source_presence_state", "PRESENT"), "currentness_state": metadata.get("currentness_state", "CURRENT"), "source_role": link.source_role, "effective_category": source_category(version, decision), "category_origin": "OWNER" if decision and decision.category_origin == "OWNER" else metadata.get("logical_category_source", "AUTO"), "included": included, "inclusion_origin": "OWNER" if decision and decision.inclusion_origin == "OWNER" else metadata.get("inclusion_origin", "DEFAULT"), "processing_state": metadata.get("processing_state", "PENDING"), "capture_status": "CAPTURED"})
    manifest["entries"].sort(key=lambda entry: (entry["source_path"], entry["source_identity"]))
    manifest["source_manifest_hash"] = hashlib.sha256(json.dumps(manifest["entries"], sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return manifest


def save_source_category(version: DocumentVersion, category: str, *, actor: str, db: Session | None = None, source_project_identity: str | None = None) -> dict[str, Any]:
    category = category.strip().upper()
    if category not in LOGICAL_SOURCE_CATEGORIES:
        raise ValueError("SOURCE_CATEGORY_INVALID")
    prior = dict(version.metadata_json or {})
    if db is not None:
        logical_identity = str(prior.get("proposal_source_key") or prior.get("source_relative_path") or version.id)
        identity = source_project_identity or str(prior.get("source_project_identity") or "UNKNOWN")
        decision = source_decision_for_version(db, source_project_identity=identity, version=version, path=logical_identity)
        if decision is None:
            decision = ProposalSourceDecision(source_project_identity=identity, logical_source_identity=logical_identity)
            db.add(decision)
        decision.logical_category = category
        decision.category_origin = "OWNER"
        decision.updated_by = actor
        decision.decision_version = int(decision.decision_version or 0) + 1
        # Keep the canonical DocumentVersion projection in step with the
        # decision ledger.  Context compilation resolves DocumentVersion
        # metadata server-side, so an Owner category must flow into Proposal
        # AI without relying on a browser dropdown or a filename heuristic.
        history = list(prior.get("logical_category_history") or [])
        previous = source_category(version)
        if previous != category or prior.get("logical_category_source") != "OWNER_OVERRIDE":
            history.append({"from": previous, "to": category, "actor": actor})
        version.metadata_json = {
            **prior,
            "logical_category": category,
            "logical_category_source": "OWNER_OVERRIDE",
            "logical_category_history": history[-25:],
        }
        return {"logical_category": category, "logical_category_source": "OWNER_OVERRIDE", "decision_id": decision.id}
    previous = source_category(version)
    history = list(prior.get("logical_category_history") or [])
    if previous != category or prior.get("logical_category_source") != "OWNER_OVERRIDE":
        history.append({"from": previous, "to": category, "actor": actor})
    updated = {
        **prior,
        "logical_category": category,
        "logical_category_source": "OWNER_OVERRIDE",
        "logical_category_history": history[-25:],
    }
    version.metadata_json = updated
    return updated


def save_source_inclusion(version: DocumentVersion, included: bool, *, actor: str, db: Session | None = None, source_project_identity: str | None = None) -> dict[str, Any]:
    prior = dict(version.metadata_json or {})
    if db is not None:
        logical_identity = str(prior.get("proposal_source_key") or prior.get("source_relative_path") or version.id)
        identity = source_project_identity or str(prior.get("source_project_identity") or "UNKNOWN")
        decision = source_decision_for_version(db, source_project_identity=identity, version=version, path=logical_identity)
        if decision is None:
            decision = ProposalSourceDecision(source_project_identity=identity, logical_source_identity=logical_identity)
            db.add(decision)
        decision.included_in_proposal = bool(included)
        decision.inclusion_origin = "OWNER"
        decision.updated_by = actor
        decision.decision_version = int(decision.decision_version or 0) + 1
        version.metadata_json = {**prior, "included_in_proposal": bool(included), "inclusion_origin": "OWNER"}
        return {"included_in_proposal": bool(included), "inclusion_origin": "OWNER", "decision_id": decision.id}
    return_value = {
        **prior,
        "included_in_proposal": bool(included),
        "inclusion_origin": "OWNER",
        "inclusion_history": [*(prior.get("inclusion_history") or []), {"included": bool(included), "actor": actor}][-25:],
    }
    version.metadata_json = return_value
    return return_value


def projects(db: Session | None = None) -> list[dict[str, Any]]:
    bound_source_projects: set[str] = set()
    if db is not None:
        # Only an explicit Proposal V1 source binding consumes a source
        # project.  An unrelated historical Opportunity for the same Project
        # must never hide a newly discovered Synology folder.
        for proposal in db.scalars(select(Opportunity)).all():
            workspace = (proposal.proposal_fields_json or {}).get("source_workspace") or {}
            identity = workspace.get("source_project_identity")
            if identity:
                bound_source_projects.add(str(identity))
    with _source(db) as source:
        rows = []
        for project in source.discover():
            scan = source._latest_scan(project.folder_name) if hasattr(source, "_latest_scan") else None
            identity = (scan.source_project_identity if scan is not None else None) or canonical_source_project_identity(number=project.number, folder_name=project.folder_name)
            if identity in bound_source_projects:
                continue
            entries = source.inventory(project.folder_name)
            # The no-DB helper remains compatible with the synthetic fixture
            # contract; authenticated API callers always receive the
            # server-owned Draft queue state.
            state = "ACTIVE_PILOT" if db is None and project.discovery_class == "PROPOSALS_V1_ACTIVE_PILOT" else "DRAFT_SYNCED"
            rows.append({"number": project.number, "name": project.folder_name, "folder_name": project.folder_name, "source_project_identity": identity, "state": state, "discovery_class": project.discovery_class, "folder_count": sum(item.is_directory for item in entries), "file_count": sum(not item.is_directory for item in entries)})
        return rows


def tree(number: int, db: Session | None = None) -> dict[str, Any]:
    with _source(db) as source:
        project = _project(source, number)
        entries = source.inventory(project.folder_name)
        current = current_source_versions(db, number) if db is not None else {}
        scan = source._latest_scan(project.folder_name) if hasattr(source, "_latest_scan") else None
        identity = (scan.source_project_identity if scan is not None else None) or canonical_source_project_identity(number=number, folder_name=project.folder_name)
        identity_candidates = {identity}
        if db is not None:
            identity_candidates.update(
                str((version.metadata_json or {}).get("source_project_identity"))
                for version in current.values()
                if isinstance(version.metadata_json, dict) and version.metadata_json.get("source_project_identity")
            )
        decision_rows = db.scalars(select(ProposalSourceDecision).where(ProposalSourceDecision.source_project_identity.in_(identity_candidates))).all() if db is not None else []
        decisions = {row.logical_source_identity: row for row in decision_rows}

        def decision_for(version: DocumentVersion | None, path: str) -> ProposalSourceDecision | None:
            """Resolve an Owner decision across pre-identity and bridge keys."""
            metadata = version.metadata_json if version is not None and isinstance(version.metadata_json, dict) else {}
            for key in (metadata.get("proposal_source_key"), metadata.get("source_relative_path"), path):
                if key and str(key) in decisions:
                    return decisions[str(key)]
            # Older captures used a project-number key.  The current canonical
            # key is identity-scoped, but its path suffix remains stable.
            suffix = f":{path}"
            return next((row for key, row in decisions.items() if str(key).endswith(suffix)), None)
        # Preserve the adapter's source ordering and exact names.
        result = []
        for item in entries:
            version = current.get(item.relative_path) if db is not None and not item.is_directory else None
            decision = decision_for(version, item.relative_path)
            result.append({
                "id": hashlib.sha256(item.relative_path.encode()).hexdigest()[:24],
                "path": item.relative_path, "name": item.name, "is_directory": item.is_directory,
                "size": item.size, "modified_ns": item.modified_ns,
                "content_type": mimetypes.guess_type(item.name)[0] or "application/octet-stream",
                "logical_category": source_category(version, decision) if version else (decision.logical_category if decision and decision.logical_category else default_logical_category(item.relative_path, item.name)),
                "category_source": "OWNER_OVERRIDE" if decision and decision.category_origin == "OWNER" else (((version.metadata_json or {}).get("logical_category_source") if version else None) or "AUTO_CLASSIFIED"),
                "category_origin": "OWNER" if decision and decision.category_origin == "OWNER" else "AUTO",
                "included_in_proposal": source_included(version, decision) if version else (decision.included_in_proposal if decision else True),
                "inclusion_origin": "OWNER" if decision and decision.inclusion_origin == "OWNER" else (((version.metadata_json or {}).get("inclusion_origin") if version else None) or "DEFAULT"),
                "source_presence_state": ((version.metadata_json or {}).get("source_presence_state") if version else None) or "NOT_CAPTURED",
                "currentness_state": ((version.metadata_json or {}).get("currentness_state") if version else None) or "NOT_CAPTURED",
            })
        return {"number": number, "name": project.folder_name, "root": project.folder_name, "entries": result}


def capture(db: Session, number: int, *, actor: str = "source-workspace") -> dict[str, Any]:
    with _source(db) as source:
        project = _project(source, number)
        entries = source.inventory(project.folder_name)
        scan = source._latest_scan(project.folder_name) if hasattr(source, "_latest_scan") else None
        source_identity = (scan.source_project_identity if scan is not None else None) or canonical_source_project_identity(number=number, folder_name=project.folder_name)
        owner_decisions = {row.logical_source_identity: row for row in db.scalars(select(ProposalSourceDecision).where(ProposalSourceDecision.source_project_identity == source_identity)).all()}
        files = [item for item in entries if not item.is_directory]
        present_paths = {item.relative_path for item in files}
        historical_rows = db.scalars(
            select(DocumentVersion)
            .where(DocumentVersion.source_system.in_(("QATAR_SOURCE_INTAKE_BRIDGE", "SYNOLOGY_PROPOSAL_SOURCE")))
        ).all()
        enumeration_complete = scan is None or scan.status == "COMPLETED"
        for historical in historical_rows:
            historical_metadata = historical.metadata_json if isinstance(historical.metadata_json, dict) else {}
            if enumeration_complete and historical_metadata.get("source_project_number") == number and historical_metadata.get("source_presence_state", "PRESENT") == "PRESENT" and historical_metadata.get("source_relative_path") not in present_paths and historical.superseded_by is None:
                historical.metadata_json = {**historical_metadata, "source_presence_state": "MISSING_AT_SOURCE", "currentness_state": "MISSING"}
        missing_by_hash: dict[str, list[DocumentVersion]] = {}
        for historical in historical_rows:
            if historical.metadata_json and historical.metadata_json.get("source_project_number") == number and historical.metadata_json.get("source_presence_state") == "MISSING_AT_SOURCE" and historical.superseded_by is None:
                missing_by_hash.setdefault(historical.sha256, []).append(historical)
        reads: dict[str, Any] = {}
        read_failures: dict[str, str] = {}
        for item in files:
            try:
                reads[item.relative_path] = source.capture(item.relative_path)
            except Exception as exc:
                # A signed scan entry remains visible and incomplete when its
                # payload is oversize/unsupported/transiently unavailable.
                read_failures[item.relative_path] = type(exc).__name__
        new_paths_by_hash: dict[str, list[str]] = {}
        for path, read in reads.items():
            new_paths_by_hash.setdefault(read.sha256, []).append(path)
        captured = 0
        unchanged = 0
        for item in files:
            read = reads.get(item.relative_path)
            if read is None:
                continue
            key = f"PROPOSAL_SOURCE:{source_identity}:{item.relative_path}"
            current = captured_version(db, number, item.relative_path)
            if current and current.sha256 == read.sha256:
                # Backfill the explicit fixture marker for databases created
                # before this source bridge carried synthetic provenance. The
                # marker is only ever added in TEST/DEV synthetic mode; a
                # live capture can never be relabelled by this path.
                if get_settings().synthetic_only and get_settings().app_env.upper() in {"TEST", "DEV", "DEVELOPMENT"}:
                    current.metadata_json = {**(current.metadata_json or {}), "synthetic_non_business_fixture": True, "synthetic_only": True, "source_presence_state": "PRESENT", "currentness_state": "CURRENT"}
                unchanged += 1
                continue
            document = current.document if current else Document(document_type=DocumentType.OTHER, logical_name=item.name, language="UNKNOWN", source_system="SYNOLOGY_PROPOSAL_SOURCE")
            if not current:
                db.add(document)
                db.flush()
            metadata = {
                "proposal_source_key": key,
                "source_project_number": number,
                "source_project_identity": source_identity,
                "source_root": LOGICAL_ROOT,
                "source_relative_path": item.relative_path,
                "source_modified_at": read.before_modified_at,
                "capture_actor": actor,
                "source_presence_state": "PRESENT",
                "currentness_state": "CURRENT",
                "included_in_proposal": True,
                "inclusion_origin": "DEFAULT",
                "processing_state": source_processing_state(item.name, mimetypes.guess_type(item.name)[0]),
                # TEST/DEV captures are explicitly synthetic so the shared
                # AI context compiler can prove its safety boundary.  Live
                # bridge captures never inherit this marker.
                "synthetic_non_business_fixture": bool(
                    get_settings().synthetic_only
                    and get_settings().app_env.upper() in {"TEST", "DEV", "DEVELOPMENT"}
                ),
            }
            moved_from = None
            if current is None and len(missing_by_hash.get(read.sha256, [])) == 1 and len(new_paths_by_hash.get(read.sha256, [])) == 1:
                previous = missing_by_hash[read.sha256][0]
                moved_from = (previous.metadata_json or {}).get("source_relative_path")
                previous.metadata_json = {
                    **(previous.metadata_json or {}),
                    "source_presence_state": "MOVED",
                    "currentness_state": "SUPERSEDED",
                    "moved_to": item.relative_path,
                }
                metadata.update({"moved_from": moved_from, "decision_carried_forward_from": previous.id, "decision_carried_forward_at": datetime.now(timezone.utc).isoformat(), "source_presence_state": "PRESENT", "currentness_state": "CURRENT"})
                previous_metadata = previous.metadata_json or {}
                if previous_metadata.get("logical_category_source") == "OWNER_OVERRIDE":
                    metadata.update({"logical_category": previous_metadata.get("logical_category"), "logical_category_source": "OWNER_OVERRIDE", "logical_category_history": list(previous_metadata.get("logical_category_history") or [])})
                if previous_metadata.get("inclusion_origin") == "OWNER":
                    metadata.update({"included_in_proposal": bool(previous_metadata.get("included_in_proposal", True)), "inclusion_origin": "OWNER", "inclusion_history": list(previous_metadata.get("inclusion_history") or [])})
            # A sync may produce a new immutable version for the same source
            # identity. Preserve an explicit Owner classification across that
            # version boundary; path/filename heuristics must never silently
            # replace an existing override.
            prior_metadata = current.metadata_json if current and isinstance(current.metadata_json, dict) else {}
            decision = owner_decisions.get(key) or owner_decisions.get(item.relative_path)
            if decision and decision.logical_category in LOGICAL_SOURCE_CATEGORIES:
                metadata.update({"logical_category": decision.logical_category, "logical_category_source": "OWNER_OVERRIDE"})
            elif prior_metadata.get("logical_category_source") == "OWNER_OVERRIDE" and prior_metadata.get("logical_category") in LOGICAL_SOURCE_CATEGORIES:
                metadata.update({
                    "logical_category": prior_metadata["logical_category"],
                    "logical_category_source": "OWNER_OVERRIDE",
                    "logical_category_history": list(prior_metadata.get("logical_category_history") or []),
                })
            if decision and decision.inclusion_origin == "OWNER":
                metadata.update({"included_in_proposal": bool(decision.included_in_proposal), "inclusion_origin": "OWNER"})
            elif prior_metadata.get("inclusion_origin") == "OWNER" and "included_in_proposal" in prior_metadata:
                metadata.update({"included_in_proposal": bool(prior_metadata["included_in_proposal"]), "inclusion_origin": "OWNER", "inclusion_history": list(prior_metadata.get("inclusion_history") or [])})
            # All new captures use the same verified storage protocol as the
            # rest of the SOR.  The mock provider is permitted only in the
            # synthetic TEST/DEV profile, while SMB/Azure persist outside it.
            storage_tables_ready = db.bind is not None and db.bind.dialect.has_table(db.connection(), "storage_operations")
            if storage_tables_ready:
                store = create_binary_store()
                target = StorageTarget(store.provider_id, getattr(getattr(store, "config", None), "container", None) or getattr(getattr(store, "config", None), "share", "synthetic"), f"proposal-sources/{number}")
                stored = DocumentStorageService(store).store_version(db, document=document, content=read.content, filename=item.name, mime_type=mimetypes.guess_type(item.name)[0] or "application/octet-stream", target=target, actor=actor, correlation_id=f"proposal-source:{number}:{read.sha256}", idempotency_key=f"proposal-source:{number}:{item.relative_path}:{read.sha256}", source_system="SYNOLOGY_PROPOSAL_SOURCE", metadata=metadata, version_number=(current.version_number + 1 if current else 1))
                stored.version.metadata_json = {**(stored.version.metadata_json or {}), **metadata}
            elif get_settings().app_env.upper() in {"TEST", "DEV", "DEVELOPMENT"} and get_settings().synthetic_only:
                # Legacy fixture databases predating the storage journal can
                # still exercise source discovery; production never takes
                # this branch because canonical storage is mandatory there.
                version = DocumentVersion(document_id=document.id, version_number=(current.version_number + 1 if current else 1), source_filename=item.name, source_path_or_reference=f"synthetic-db://proposal-source/{number}/{item.relative_path}", sha256=read.sha256, mime_type=mimetypes.guess_type(item.name)[0] or "application/octet-stream", file_size=read.size, language="UNKNOWN", approval_state=DocumentApprovalState.WORKING, source_system="SYNOLOGY_PROPOSAL_SOURCE", synthetic_content=read.content, metadata_json={**metadata, "synthetic_only": True})
                db.add(version)
                db.flush()
                if current is not None:
                    current.superseded_by = version.id
                    current.approval_state = DocumentApprovalState.SUPERSEDED
                document.current_version_id = version.id
            else:
                raise RuntimeError("CANONICAL_STORAGE_JOURNAL_REQUIRED")
            captured += 1
        db.commit()
        return {"project_number": number, "file_count": len(files), "captured_count": captured, "unchanged_count": unchanged, "state": "DRAFT_SYNCED" if project.discovery_class == "DRAFT_SOURCE_PROJECT" else "ACTIVE_PILOT_READY", "synology_write_count": 0}


def captured_version(db: Session, number: int, relative: str) -> DocumentVersion | None:
    key = f"PROPOSAL_SOURCE:{number}:{relative}"
    # The mounted source adapter writes the historical proposal_source_key,
    # while the live bridge writes the canonical QATAR_SOURCE_INTAKE_BRIDGE
    # metadata (source_project_number/source_relative_path).  Both represent
    # the same immutable source file and must resolve to one workspace row.
    rows = db.scalars(
        select(DocumentVersion)
        .where(DocumentVersion.source_system.in_(("QATAR_SOURCE_INTAKE_BRIDGE", "SYNOLOGY_PROPOSAL_SOURCE")))
        .order_by(DocumentVersion.ingested_at.desc(), DocumentVersion.version_number.desc())
    ).all()
    for version in rows:
        metadata = version.metadata_json or {}
        if metadata.get("proposal_source_key") == key or (metadata.get("source_project_number") == number and str(metadata.get("proposal_source_key") or "").endswith(f":{relative}")):
            return version
        if (
            metadata.get("source_project_number") == number
            and metadata.get("source_relative_path") == relative
            and metadata.get("source_presence_state", "PRESENT") == "PRESENT"
        ):
            return version
    return None


def _version_bytes(version: DocumentVersion) -> bytes | None:
    """Read a captured version through its canonical storage reference."""
    if version.source_path_or_reference.startswith("storage://"):
        try:
            with DocumentStorageService(create_binary_store()).read_verified(version) as stream:
                return stream.read()
        except Exception:
            return None
    return version.synthetic_content


def ensure_editor_revision(
    db: Session,
    proposal: Opportunity,
    versions: list[DocumentVersion],
    *,
    source_set_hash: str,
    actor: str,
) -> dict[str, Any]:
    """Create the first working Option B revision from a captured DOCX.

    Source capture and Proposal creation are useful without a DOCX, so an
    unsupported or malformed source is reported as an explicit readiness
    state.  A revision is seeded only after the server validates the package
    and builds its immutable editor anchors.
    """
    existing = db.scalar(
        select(ProposalRevision)
        .where(ProposalRevision.proposal_id == proposal.id, ProposalRevision.status == "DRAFT")
        .order_by(ProposalRevision.revision_number.desc())
    )
    if existing:
        return {
            "editor_ready": True,
            "editor_revision_id": existing.id,
            "editor_revision_number": existing.revision_number,
            "editor_baseline_hash": (existing.snapshot or {}).get("baseline_hash"),
        }

    candidates = [
        version for version in versions
        if (version.source_filename or "").lower().endswith(".docx")
    ]
    explicit = [version for version in candidates if (version.metadata_json or {}).get("template_baseline") or (version.metadata_json or {}).get("source_role") == "BASELINE_TEMPLATE"]
    named = [version for version in candidates if re.search(r"(?:amec.*p[-_ ]?d|proposal|baseline|template)", (version.source_filename or "").lower())]
    if len(explicit) == 1:
        ordered_candidates = explicit
    elif len(named) == 1:
        ordered_candidates = named
    # A lone DOCX can be a scope brief, client data sheet, or project
    # description.  It is never a Proposal baseline without an explicit role,
    # verified Proposal naming rule, or Owner confirmation.
    elif len(candidates) == 1 and named:
        ordered_candidates = named
    else:
        ordered_candidates = []
    for version in ordered_candidates:
        content = _version_bytes(version)
        if not content:
            continue
        try:
            editor_model = import_editor_model(content)
        except (DocumentPackageError, ValueError, TypeError):
            continue
        snapshot = {
            "editor_model": editor_model,
            "baseline_hash": digest(content),
            "working_hash": digest(content),
            "source_set_hash": source_set_hash,
            "source_ids": [item.id for item in versions],
            "editor_baseline_document_version_id": version.id,
            "ai_provenance": {
                "source_set_hash": source_set_hash,
                "evidence_refs": [item.id for item in versions],
                "provenance_state": "RECORDED",
                "generation_mode": "SYNTHETIC_DETERMINISTIC" if get_settings().synthetic_only else "GOVERNED_SOURCE",
            },
        }
        revision = ProposalRevision(
            proposal_id=proposal.id,
            revision_number=1,
            status="DRAFT",
            change_summary={"created_from": "SOURCE_WORKSPACE", "source_document_version_id": version.id},
            snapshot=snapshot,
            content_hash=digest(json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode()),
            created_by=actor,
        )
        db.add(revision)
        db.flush()
        return {
            "editor_ready": True,
            "editor_revision_id": revision.id,
            "editor_revision_number": revision.revision_number,
            "editor_baseline_hash": snapshot["baseline_hash"],
        }
    return {
        "editor_ready": False,
        "editor_revision_id": None,
        "editor_revision_number": None,
        "editor_baseline_hash": None,
        "editor_blocker": "VALID_DOCX_SOURCE_REQUIRED",
    }
