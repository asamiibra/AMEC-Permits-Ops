"""Authenticated Proposal source workspace routes."""
from __future__ import annotations

import hashlib
import io
import json
import os
import re
import zipfile
from copy import deepcopy
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select, true
from sqlalchemy.orm import Session
from lxml import etree

from ..api.dependencies import AuthenticatedPrincipal, authenticated_actor, authenticated_principal_context, require_roles
from ..audit.service import audit
from ..db import get_db
from ..models import ClientAccount, Document, DocumentApprovalState, DocumentType, DocumentVersion, Opportunity, ProposalGenerationAttempt, ProposalRevision, ProposalSourceEvidence, ProposalSourceLink, ProposalSourceStagedFile, ProposalSourceStagingSession, ProposalStalenessEvent, Project, Role
from ..services.proposal_source_workspace import LOGICAL_ROOT, LOGICAL_SOURCE_CATEGORIES, build_effective_proposal_source_manifest, capture, canonical_source_project_identity, configured_source_root, current_source_versions, ensure_editor_revision, projects, save_source_category, save_source_inclusion, source_category, source_included, source_manifest, tree
from ..services.proposal_production_boundary import require_authorized_office
from ..config.settings import get_settings
from ..storage import DocumentStorageService, StorageTarget, create_binary_store
from ..services.proposal_document_package import DocumentPackageError, TextMutation, apply_text_mutations, digest, package_parts
from ..services.proposal_editor_model import import_editor_model
from ..services.proposal_generation_summary import canonical_generation_summary
from ..services.proposal_canonical_audit import audit_proposal, audit_references, CANONICAL_BASELINE_SELECTION, CANONICAL_CLASSIFICATION
from ..services.proposal_intelligence import ProposalDeterministicProvider, execute_proposal_intelligence
from ..services.master_content import resolve_master_content_purpose
from ..services.proposal_technical_report_template import template_contract, template_metadata
from .bd_proposal_routers import ProposalCreate, _create_proposal_record

router = APIRouter(prefix="/api/proposals/sources", tags=["proposal-source-workspace"])
source_role = require_roles(Role.OWNER_SPONSOR, Role.PROCESS_CHAMPION, Role.RESPONSIBLE_ENGINEER, Role.SYSTEM_ADMIN)
source_curate_role = require_roles(Role.OWNER_SPONSOR, Role.PROCESS_CHAMPION, Role.SYSTEM_ADMIN)
sync_role = require_roles(Role.OWNER_SPONSOR, Role.PROCESS_CHAMPION, Role.SYSTEM_ADMIN)
create_role = require_roles(Role.OWNER_SPONSOR, Role.PROCESS_CHAMPION, Role.SYSTEM_ADMIN)


class SourceProposalCreatePayload(BaseModel):
    """Owner choices applied when promoting a synced source project."""

    excluded_source_paths: list[str] = Field(default_factory=list)
    source_categories: dict[str, str] = Field(default_factory=dict)
    defer_generation: bool = False
    staging_session_id: str | None = None


class SourceCategoryUpdatePayload(BaseModel):
    logical_category: str = Field(min_length=1, max_length=60)


class SourceInclusionUpdatePayload(BaseModel):
    included_in_proposal: bool


CANONICAL_AUDIT_REFERENCES = [
    "AMEC-SYN-PROP-0008",
    "AMEC-SYN-PROP-0009",
    "AMEC-SYN-PROP-0010",
    "AMEC-SYN-PROP-0011",
]


class CanonicalAuditPayload(BaseModel):
    references: list[str] = Field(default_factory=lambda: list(CANONICAL_AUDIT_REFERENCES), min_length=1, max_length=50)
    apply: bool = False


def _mark_bound_proposals_stale(db: Session, number: int, manifest_hash: str, reason: str, *, source_project_identity: str) -> None:
    for proposal in db.scalars(select(Opportunity)).all():
        workspace = (proposal.proposal_fields_json or {}).get("source_workspace") or {}
        if workspace.get("source_project_identity") != source_project_identity:
            continue
        if workspace.get("source_manifest_hash") == manifest_hash:
            continue
        current = dict(proposal.proposal_fields_json or {})
        proposal.proposal_fields_json = {**current, "generation_state": "STALE_SOURCE_MANIFEST", "source_changes_available": True, "current_source_manifest_hash": manifest_hash}
        active = db.scalar(select(ProposalStalenessEvent).where(ProposalStalenessEvent.proposal_id == proposal.id, ProposalStalenessEvent.status == "ACTIVE", ProposalStalenessEvent.reason_code == "SOURCE_MANIFEST_CHANGED"))
        if active is None:
            db.add(ProposalStalenessEvent(proposal_id=proposal.id, trigger_type="SOURCE_SCAN", trigger_reference=manifest_hash, reason_code="SOURCE_MANIFEST_CHANGED", impacted_sections=[reason], detected_by="proposal-source-workspace"))


def _source_client_name(folder_name: str, number: int) -> str:
    """Get the human client label from a Synology project folder."""
    prefix = re.match(r"^\d{1,9}\s*-\s*", folder_name)
    value = folder_name[prefix.end():].strip() if prefix else folder_name.strip()
    return value or f"Synology project {number}"


def _ensure_source_project_and_client(db: Session, *, number: int, folder_name: str) -> tuple[Project | None, ClientAccount | None]:
    """Resolve only identities already present in the canonical register.

    A Synology folder is a source identity, not proof of a canonical Client or
    Project. Promotion therefore never manufactures business master data from
    a folder suffix. Unknown folders remain provisional until an Owner maps
    them to the real entities.
    """
    principal = authenticated_principal_context()
    project = db.scalar(select(Project).where(Project.project_number == str(number)))
    if project is None:
        return None, None
    require_authorized_office(db, principal, project_id=project.id)
    return project, None


def _entry(number: int, file_id: str, db: Session) -> dict[str, Any]:
    linked_project = db.scalar(select(Project).where(Project.project_number == str(number)))
    if linked_project is not None:
        require_authorized_office(db, authenticated_principal_context(), project_id=linked_project.id)
    expected = str(file_id).lower()
    for item in tree(number, db)["entries"]:
        if not item["is_directory"] and hashlib.sha256(item["path"].encode()).hexdigest()[:24] == expected:
            return item
    raise HTTPException(404, "SOURCE_FILE_NOT_FOUND")


@router.post("/2026/projects/{number}/staging")
async def stage_owner_sources(
    number: int,
    files: list[UploadFile] = File(...),
    logical_categories: str = Form(default="[]"),
    session_key: str | None = Form(default=None),
    db: Session = Depends(get_db),
    role: Role = Depends(source_curate_role),
):
    """Persist Owner files before Proposal promotion; browser memory is not lifecycle state."""
    try:
        categories = json.loads(logical_categories or "[]")
    except (TypeError, json.JSONDecodeError) as exc:
        raise HTTPException(422, "SOURCE_STAGING_METADATA_INVALID") from exc
    if not isinstance(categories, list) or len(categories) != len(files):
        raise HTTPException(422, "SOURCE_STAGING_METADATA_COUNT_MISMATCH")
    if any(str(category) not in LOGICAL_SOURCE_CATEGORIES for category in categories):
        raise HTTPException(422, "SOURCE_CATEGORY_INVALID")
    discovered = next((row for row in projects(db) if row["number"] == number), None)
    if discovered is None:
        raise HTTPException(404, "SOURCE_PROJECT_NOT_FOUND")
    identity = discovered["source_project_identity"]
    key = session_key or f"owner-source-{uuid4().hex}"
    session = db.scalar(select(ProposalSourceStagingSession).where(ProposalSourceStagingSession.source_project_identity == identity, ProposalSourceStagingSession.session_key == key))
    if session is None:
        session = ProposalSourceStagingSession(session_key=key, source_project_identity=identity, project_number=str(number), status="UPLOADING", created_by=authenticated_actor() or getattr(role, "value", str(role)))
        db.add(session)
        db.flush()
    project = db.scalar(select(Project).where(Project.project_number == str(number)))
    try:
        results = []
        for upload, category in zip(files, categories):
            content = await upload.read()
            sha = hashlib.sha256(content).hexdigest()
            if db.scalar(select(ProposalSourceStagedFile).where(ProposalSourceStagedFile.session_id == session.id, ProposalSourceStagedFile.sha256 == sha)):
                continue
            document = Document(project_id=project.id if project else None, document_type=DocumentType.OTHER, logical_name=upload.filename or "owner-source", language="UNKNOWN", source_system="PROPOSAL_OWNER_STAGING")
            db.add(document)
            db.flush()
            metadata = {"owner_staged": True, "source_project_number": number, "source_project_identity": identity, "logical_category": category, "logical_category_source": "OWNER_OVERRIDE", "included_in_proposal": True, "inclusion_origin": "OWNER", "source_presence_state": "PRESENT", "currentness_state": "CURRENT", "processing_state": "PENDING", "proposal_source_key": f"OWNER_STAGING:{session.id}:{sha}"}
            stored_version = None
            if db.bind is not None and db.bind.dialect.has_table(db.connection(), "storage_operations"):
                store = create_binary_store()
                target = StorageTarget(store.provider_id, getattr(getattr(store, "config", None), "container", None) or getattr(getattr(store, "config", None), "share", "synthetic"), f"proposal-staging/{session.id}")
                stored_version = DocumentStorageService(store).store_version(db, document=document, content=content, filename=upload.filename or "owner-source.bin", mime_type=upload.content_type or "application/octet-stream", target=target, actor=authenticated_actor() or "owner-staging", correlation_id=f"proposal-staging:{session.id}", idempotency_key=f"proposal-staging:{session.id}:{sha}", source_system="PROPOSAL_OWNER_STAGING", metadata=metadata, version_number=1).version
            elif get_settings().synthetic_only and get_settings().app_env.upper() in {"TEST", "DEV", "DEVELOPMENT"}:
                stored_version = DocumentVersion(document_id=document.id, version_number=1, source_filename=upload.filename or "owner-source.bin", source_path_or_reference=f"synthetic-db://proposal-staging/{session.id}/{sha}", sha256=sha, mime_type=upload.content_type or "application/octet-stream", file_size=len(content), language="UNKNOWN", approval_state=DocumentApprovalState.WORKING, source_system="PROPOSAL_OWNER_STAGING", synthetic_content=content, metadata_json=metadata)
                db.add(stored_version)
                db.flush()
            else:
                raise HTTPException(503, "CANONICAL_STORAGE_JOURNAL_REQUIRED")
            db.add(ProposalSourceStagedFile(session_id=session.id, document_version_id=stored_version.id, filename=upload.filename or "owner-source.bin", sha256=sha, logical_category=category, verified=True))
            results.append({"filename": upload.filename, "document_version_id": stored_version.id, "sha256": sha, "verified": True})
        session.status = "READY"
        db.commit()
    except Exception:
        db.rollback()
        raise
    return {"result": "STAGED", "staging_session_id": session.id, "session_key": session.session_key, "status": session.status, "files": results}


@router.get("/2026/projects")
def source_projects(_: Role = Depends(source_role), db: Session = Depends(get_db)):
    settings = get_settings()
    discovered = projects(db)
    # The register needs the same authoritative manifest state that the
    # project workspace uses.  Returning it with each unbound source project
    # avoids a second, stale client-side interpretation of sync readiness.
    for item in discovered:
        try:
            manifest = source_manifest(db, int(item["number"]))
        except Exception:
            manifest = {}
        item.update({
            "completeness_state": manifest.get("completeness_state", "INCOMPLETE"),
            "completeness_reasons": manifest.get("completeness_reasons", []),
            "scan_status": manifest.get("scan_status", "NOT_SYNCED"),
            "source_manifest_hash": manifest.get("source_manifest_hash"),
            "snapshot_at": manifest.get("snapshot_at"),
        })
    return {"logical_root": "Tenders/1- Proposal/2026", "physical_root_configured": settings.source_intake_mode.upper() != "BRIDGE" and configured_source_root().is_absolute(), "projects": discovered}


@router.get("/runtime-version")
def proposal_v1_runtime_version(db: Session = Depends(get_db), _: Role = Depends(source_role)):
    """Expose the non-secret runtime identity used by browser diagnostics."""
    from sqlalchemy import inspect, text
    migration_head = None
    try:
        if inspect(db.bind).has_table("alembic_version"):
            migration_head = db.execute(text("SELECT version_num FROM alembic_version ORDER BY version_num")).scalars().all()
    except Exception:
        migration_head = None
    return {
        "feature": "PROPOSALS_V1",
        "backend_source_sha": os.getenv("SOURCE_VERSION", os.getenv("GIT_SHA", "UNKNOWN")),
        "backend_image_digest": os.getenv("IMAGE_DIGEST", "UNKNOWN"),
        "source_sha": os.getenv("SOURCE_VERSION", os.getenv("GIT_SHA", "UNKNOWN")),
        "image_digest": os.getenv("IMAGE_DIGEST", "UNKNOWN"),
        "api_revision": os.getenv("API_REVISION", "UNKNOWN"),
        "environment": get_settings().app_env,
        "build_timestamp": os.getenv("BUILD_TIMESTAMP", "UNKNOWN"),
        "frontend_build_sha": os.getenv("FRONTEND_BUILD_SHA", os.getenv("VITE_SOURCE_SHA", "UNKNOWN")),
        "migration_head": migration_head or "UNAVAILABLE",
    }


@router.get("/2026/projects/{number}/tree")
def source_tree(number: int, _: Role = Depends(source_role), db: Session = Depends(get_db)):
    try:
        linked_project = db.scalar(select(Project).where(Project.project_number == str(number)))
        if linked_project is not None:
            require_authorized_office(db, authenticated_principal_context(), project_id=linked_project.id)
        return tree(number, db)
    except (FileNotFoundError, OSError) as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get("/2026/projects/{number}/manifest")
def source_manifest_view(number: int, _: Role = Depends(source_role), db: Session = Depends(get_db)):
    try:
        linked_project = db.scalar(select(Project).where(Project.project_number == str(number)))
        if linked_project is not None:
            require_authorized_office(db, authenticated_principal_context(), project_id=linked_project.id)
        return source_manifest(db, number)
    except (FileNotFoundError, OSError) as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get("/2026/projects/{number}/files/{file_id}")
def source_file(number: int, file_id: str, _: Role = Depends(source_role), db: Session = Depends(get_db)):
    item = _entry(number, file_id, db)
    version = current_source_versions(db, number).get(item["path"])
    return {**item, "captured": bool(version), "source_content_hash": version.sha256 if version else None, "source_version": version.version_number if version else None, "source_presence_state": (version.metadata_json or {}).get("source_presence_state", "NOT_CAPTURED") if version else "NOT_CAPTURED", "logical_category": source_category(version) if version else item.get("logical_category"), "category_source": ((version.metadata_json or {}).get("logical_category_source") if version else None) or item.get("category_source", "AUTO_CLASSIFIED"), "included_in_proposal": source_included(version) if version else item.get("included_in_proposal", True), "inclusion_origin": ((version.metadata_json or {}).get("inclusion_origin") if version else None) or item.get("inclusion_origin", "DEFAULT")}


@router.patch("/2026/projects/{number}/files/{file_id}/category")
def save_source_file_category(
    number: int,
    file_id: str,
    payload: SourceCategoryUpdatePayload,
    request: Request,
    db: Session = Depends(get_db),
    role: Role = Depends(source_curate_role),
):
    """Persist one explicit Owner category without writing back to Synology."""
    item = _entry(number, file_id, db)
    version = current_source_versions(db, number).get(item["path"])
    if version is None:
        capture(db, number, actor="source-category-save")
        version = current_source_versions(db, number).get(item["path"])
    if version is None:
        raise HTTPException(404, "SOURCE_FILE_NOT_CAPTURED")
    previous_category = source_category(version)
    try:
        manifest_identity = source_manifest(db, number).get("source_project_identity")
        metadata = save_source_category(version, payload.logical_category, actor=authenticated_actor() or getattr(role, "value", str(role)), db=db, source_project_identity=manifest_identity)
    except ValueError as exc:
        raise HTTPException(422, {"code": str(exc), "allowed": sorted(LOGICAL_SOURCE_CATEGORIES)}) from exc
    audit(db, correlation_id=getattr(request.state, "correlation_id", f"source-category:{version.id}"), event_type="PROPOSAL_SOURCE_CATEGORY_SAVED", entity_type="DocumentVersion", entity_id=version.id, actor_id=authenticated_actor(), before={"logical_category": previous_category}, after={"logical_category": metadata["logical_category"], "source_relative_path": metadata.get("source_relative_path"), "sha256": version.sha256}, metadata={"project_number": number, "file_id": file_id, "synology_write_count": 0})
    db.flush()
    current_manifest = source_manifest(db, number)
    _mark_bound_proposals_stale(db, number, current_manifest["source_manifest_hash"], "CATEGORY_CHANGED", source_project_identity=current_manifest["source_project_identity"])
    db.commit()
    return {**item, "captured": True, "source_content_hash": version.sha256, "source_version": version.version_number, "source_presence_state": metadata.get("source_presence_state", "PRESENT"), "logical_category": metadata["logical_category"], "category_source": metadata["logical_category_source"], "synology_write_count": 0}


@router.patch("/2026/projects/{number}/files/{file_id}/inclusion")
def save_source_file_inclusion(
    number: int,
    file_id: str,
    payload: SourceInclusionUpdatePayload,
    request: Request,
    db: Session = Depends(get_db),
    role: Role = Depends(source_curate_role),
):
    item = _entry(number, file_id, db)
    version = current_source_versions(db, number).get(item["path"])
    if version is None:
        capture(db, number, actor="source-inclusion-save")
        version = current_source_versions(db, number).get(item["path"])
    if version is None:
        raise HTTPException(404, "SOURCE_FILE_NOT_CAPTURED")
    prior = source_included(version)
    manifest_identity = source_manifest(db, number).get("source_project_identity")
    metadata = save_source_inclusion(version, payload.included_in_proposal, actor=authenticated_actor() or getattr(role, "value", str(role)), db=db, source_project_identity=manifest_identity)
    audit(db, correlation_id=getattr(request.state, "correlation_id", f"source-inclusion:{version.id}"), event_type="PROPOSAL_SOURCE_INCLUSION_SAVED", entity_type="DocumentVersion", entity_id=version.id, actor_id=authenticated_actor(), before={"included_in_proposal": prior}, after={"included_in_proposal": metadata["included_in_proposal"], "source_relative_path": metadata.get("source_relative_path"), "sha256": version.sha256}, metadata={"project_number": number, "file_id": file_id, "synology_write_count": 0})
    db.flush()
    current_manifest = source_manifest(db, number)
    _mark_bound_proposals_stale(db, number, current_manifest["source_manifest_hash"], "INCLUSION_CHANGED", source_project_identity=current_manifest["source_project_identity"])
    db.commit()
    return {**item, "captured": True, "source_content_hash": version.sha256, "source_version": version.version_number, "included_in_proposal": metadata["included_in_proposal"], "inclusion_origin": metadata["inclusion_origin"], "synology_write_count": 0}


def _content(number: int, file_id: str, db: Session) -> tuple[dict[str, Any], bytes]:
    item = _entry(number, file_id, db)
    version = current_source_versions(db, number).get(item["path"])
    if not version:
        result = capture(db, number, actor="source-view")
        version = current_source_versions(db, number).get(item["path"])
        if not version:
            raise HTTPException(404, "SOURCE_FILE_NOT_CAPTURED")
    try:
        if version.source_path_or_reference.startswith("storage://"):
            with DocumentStorageService(create_binary_store()).read_verified(version) as stream:
                content = stream.read()
        elif version.synthetic_content is not None:
            content = version.synthetic_content
        else:
            raise HTTPException(404, "SOURCE_FILE_NOT_CAPTURED")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(503, "SOURCE_STORAGE_READ_FAILED") from exc
    if hashlib.sha256(content).hexdigest() != version.sha256:
        raise HTTPException(503, "SOURCE_CONTENT_INTEGRITY_DRIFT")
    return item, content


@router.get("/2026/projects/{number}/files/{file_id}/content")
def source_content(number: int, file_id: str, _: Role = Depends(source_role), db: Session = Depends(get_db)):
    item, content = _content(number, file_id, db)
    return StreamingResponse(io.BytesIO(content), media_type=item["content_type"], headers={"X-Source-Content-SHA256": hashlib.sha256(content).hexdigest(), "Content-Disposition": "inline"})


@router.get("/2026/projects/{number}/files/{file_id}/download")
def source_download(number: int, file_id: str, _: Role = Depends(source_role), db: Session = Depends(get_db)):
    item, content = _content(number, file_id, db)
    safe_name = item["name"].replace('"', "")
    return StreamingResponse(io.BytesIO(content), media_type="application/octet-stream", headers={"X-Source-Content-SHA256": hashlib.sha256(content).hexdigest(), "Content-Disposition": f'attachment; filename="{safe_name}"'})


@router.post("/2026/sync")
def sync_sources(project: int | None = Query(default=None, ge=1), _: Role = Depends(sync_role), db: Session = Depends(get_db)):
    """Reconcile one selected source project, or all projects for admin sync.

    The workspace always supplies ``project``.  Omitting it preserves the
    existing admin/global operation for scheduled or operational callers.
    """
    try:
        discovered = projects(db)
        if project is not None:
            discovered = [row for row in discovered if row["number"] == project]
            if not discovered:
                raise HTTPException(404, "SOURCE_PROJECT_NOT_FOUND")
        runs = [capture(db, row["number"], actor="source-sync") for row in discovered]
        for row in discovered:
            current_manifest = source_manifest(db, row["number"])
            _mark_bound_proposals_stale(db, row["number"], current_manifest["source_manifest_hash"], "SOURCE_VERSION_CHANGED", source_project_identity=current_manifest["source_project_identity"])
    except (FileNotFoundError, OSError) as exc:
        raise HTTPException(503, "SOURCE_ROOT_UNAVAILABLE") from exc
    return {"logical_root": "Tenders/1- Proposal/2026", "runs": runs, "synology_write_count": 0, "auto_proposal_created_for_520_plus": 0, "projects_455_519_auto_onboarded": 0}


@router.get("/canonical-audit")
def canonical_audit(
    references: list[str] | None = Query(default=None),
    db: Session = Depends(get_db),
    _: Role = Depends(source_role),
):
    """Audit persisted active Proposal V1 revisions against the canonical DOCX contract."""
    requested = references or list(CANONICAL_AUDIT_REFERENCES)
    return audit_references(db, requested)


@router.post("/canonical-audit/regenerate")
def canonical_audit_regenerate(
    payload: CanonicalAuditPayload,
    request: Request,
    db: Session = Depends(get_db),
    role: Role = Depends(create_role),
):
    """Dry-run or selectively regenerate exact active Proposal V1 records.

    ``apply`` is deliberately explicit.  Historical revisions remain in the
    database; the existing source-regeneration path creates a new draft and
    marks the previous draft superseded only after the new package validates.
    """
    references = [str(reference).strip() for reference in payload.references if str(reference).strip()]
    before = audit_references(db, references)
    if not payload.apply:
        return {"result": "AUDIT_ONLY", "before": before, "after": before, "operations": []}
    operations: list[dict[str, Any]] = []
    for row in before["rows"]:
        reference = row["proposal_reference"]
        if row.get("classification") == CANONICAL_CLASSIFICATION:
            operations.append({"proposal_reference": reference, "result": "SKIPPED_CURRENT_CANONICAL"})
            continue
        if row.get("source_manifest_completeness_state") != "COMPLETE":
            operations.append({"proposal_reference": reference, "result": "BLOCKED_SOURCE_MANIFEST", "reasons": row.get("source_manifest_completeness_reasons") or []})
            continue
        proposal = db.scalar(select(Opportunity).where(Opportunity.opportunity_reference == reference))
        if proposal is None:
            operations.append({"proposal_reference": reference, "result": "PROPOSAL_NOT_FOUND"})
            continue
        try:
            # Reuse the canonical source regeneration path.  It captures the
            # current Owner category/inclusion decisions, validates the
            # governed baseline, and preserves the prior revision.
            result = regenerate_proposal_from_sources(proposal.id, request=request, db=db, role=role)
            operations.append({"proposal_reference": reference, "result": result.get("result"), "generation_state": result.get("generation_state"), "revision_id": result.get("editor_revision_id")})
        except HTTPException as exc:
            db.rollback()
            operations.append({"proposal_reference": reference, "result": "REGENERATION_FAILED", "error": str(exc.detail)})
    after = audit_references(db, references)
    return {"result": "APPLIED", "before": before, "after": after, "operations": operations}


def _captured_bytes(version: DocumentVersion) -> bytes:
    if version.source_path_or_reference.startswith("storage://"):
        with DocumentStorageService(create_binary_store()).read_verified(version) as stream:
            return stream.read()
    if version.synthetic_content is not None:
        return version.synthetic_content
    raise HTTPException(503, "PROPOSAL_BASELINE_DOCUMENT_UNAVAILABLE")


def _generation_state_for_error(detail: str) -> str:
    return "GENERATION_REVIEW_REQUIRED" if detail.startswith("GENERATION_REVIEW_REQUIRED:") else "FAILED_RETRYABLE"


def _mark_generation_failed(db: Session, proposal_id: str, manifest_hash: str, detail: str) -> None:
    attempt = db.scalar(select(ProposalGenerationAttempt).where(ProposalGenerationAttempt.proposal_id == proposal_id, ProposalGenerationAttempt.manifest_hash == manifest_hash, ProposalGenerationAttempt.generation_kind == "DOCUMENT_CHANGE_PLAN"))
    if attempt is not None:
        attempt.status = _generation_state_for_error(detail)
        attempt.failure_code = detail[:160]
        from datetime import datetime, timezone
        attempt.completed_at = datetime.now(timezone.utc)


def _identity_label(value: Any) -> str:
    """Normalize a project/client label for deterministic identity checks."""
    normalized = re.sub(r"^\s*\d{1,9}\s*[-–—:]\s*", "", str(value or "").strip())
    return re.sub(r"\s+", " ", normalized).strip().casefold()


def _proposal_baseline_identity(db: Session, proposal: Any, selected_versions: list[DocumentVersion]) -> dict[str, str | None]:
    """Derive the expected identity from the Proposal and its source set.

    Source filenames are evidence only.  They are useful for discovering the
    Synology folder label when the synthetic source adapter has no canonical
    Project row, but the Proposal reference/project row remains authoritative
    whenever one is present.
    """
    workspace = (getattr(proposal, "proposal_fields_json", None) or {}).get("source_workspace") or {}
    project_number = str(
        getattr(proposal, "canonical_project_reference", None)
        or getattr(proposal, "provisional_reference", None)
        or workspace.get("project_number")
        or ""
    ).strip() or None
    project_name: str | None = None
    client_name: str | None = None
    client_is_synthetic = False
    project_id = getattr(proposal, "project_id", None)
    if project_id:
        project = db.get(Project, project_id)
        if project is not None:
            project_name = _identity_label(project.project_name) or None
    client_id = getattr(proposal, "client_account_id", None)
    if client_id:
        client = db.get(ClientAccount, client_id)
        if client is not None:
            client_name = _identity_label(client.display_name or client.legal_name) or None
            client_is_synthetic = str(getattr(client, "data_classification", "")).upper() == "SYNTHETIC"

    # Mounted/bridge source captures retain the exact Synology folder in the
    # immutable relative path.  Use it only to fill missing labels.
    folder_name: str | None = None
    for version in selected_versions:
        metadata = version.metadata_json if isinstance(version.metadata_json, dict) else {}
        relative = str(metadata.get("source_relative_path") or "")
        match = re.match(r"^\s*(\d{1,9})\s*[-–—]\s*(.+?)(?:/|$)", relative)
        if match and (project_number is None or match.group(1) == project_number):
            project_number = project_number or match.group(1)
            folder_name = match.group(2).strip()
            break
    folder_identity = _identity_label(folder_name) if folder_name else None
    if folder_identity and (project_name is None or project_name.startswith("project ")):
        project_name = folder_identity
    if folder_identity and (client_name is None or client_is_synthetic):
        client_name = folder_identity
    if client_name is None and project_name is not None:
        # Proposal V1 source promotions may be provisional and have no
        # canonical ClientAccount yet; the mapped project label is the only
        # admissible client identity until Owner mapping is recorded.
        client_name = project_name
    if project_name is None:
        title = str(getattr(proposal, "title", "") or "")
        project_name = _identity_label(re.sub(r"\s+proposal\s*$", "", title, flags=re.IGNORECASE)) or None
    if client_name is None:
        title = str(getattr(proposal, "title", "") or "")
        client_name = _identity_label(re.sub(r"\s+proposal\s*$", "", title, flags=re.IGNORECASE)) or None
    proposal_reference = None
    if project_number:
        proposal_reference = f"AMEC-P-D-2026-Q-{project_number}"
    if proposal_reference is None:
        proposal_reference = str(getattr(proposal, "opportunity_reference", "") or "") or None
    return {
        "project_number": project_number,
        "project_name": project_name,
        "client_name": client_name,
        "proposal_reference": proposal_reference,
    }


def _docx_text(content: bytes) -> str:
    model = import_editor_model(content)
    return "\n".join(str(node.get("text") or "") for node in model.get("nodes", []))


def _docx_identity_matches(content: bytes, expected: dict[str, str | None]) -> bool:
    """Return whether a DOCX body belongs to the expected project."""
    try:
        text = _docx_text(content)
    except (DocumentPackageError, ValueError, TypeError, OSError):
        return False
    normalized = re.sub(r"\s+", " ", text).strip().casefold()
    project_number = expected.get("project_number")
    if project_number:
        references = re.findall(r"amec\s*[-_ ]?p\s*[-_ ]?d\s*[-_ ]?\d{4}\s*[-_ ]?q\s*[-_ ]?(\d+)", normalized, flags=re.IGNORECASE)
        if references and any(str(number) != str(project_number) for number in references):
            return False
    for label, expected_value in (("project", expected.get("project_name")), ("client name", expected.get("client_name"))):
        if not expected_value:
            continue
        match = re.search(rf"{re.escape(label)}\s*:\s*([^\n\r]+)", text, flags=re.IGNORECASE)
        if not match:
            continue
        actual = _identity_label(match.group(1))
        if actual in {"", "to be confirmed by owner", "needs owner review", "tbd", "n/a"}:
            continue
        if actual != expected_value and expected_value not in actual and actual not in expected_value:
            return False
    return True


def _baseline_identity_matches(version: DocumentVersion, expected: dict[str, str | None]) -> bool:
    """Reject a named Proposal DOCX whose body belongs to another project."""
    try:
        content = _captured_bytes(version)
    except (HTTPException, DocumentPackageError, ValueError, TypeError, OSError):
        return False
    # The governed template's Q-454 filename/body is a fixture label, not a
    # business identity.  Its project-bound placeholders are intentionally
    # populated by the generation plan for the selected source project.
    if _template_metadata(version).get("template_baseline") or _template_metadata(version).get("template_id") == "AMEC-PROPOSAL-V1-TECHNICAL-REPORT":
        return True
    return _docx_identity_matches(content, expected)


def _template_metadata(version: DocumentVersion) -> dict[str, Any]:
    """Read template metadata whether it is stored directly or nested by SOR."""
    metadata = version.metadata_json or {}
    nested = metadata.get("engineering_metadata") if isinstance(metadata.get("engineering_metadata"), dict) else {}
    return {**nested, **metadata}


def _baseline_is_complete(version: DocumentVersion) -> bool:
    """Accept only a real AMEC package as an editable Proposal baseline.

    Older Proposal V1 records can contain the original one-page bootstrap
    document.  It is valid DOCX, but it is not the AMEC template and must
    never be selected for generation, rendering, or download.
    """
    try:
        content = _captured_bytes(version)
        model = import_editor_model(content)
        return len(model.get("nodes") or []) >= 24 and len(package_parts(content)) >= 10
    except (HTTPException, DocumentPackageError, ValueError, TypeError, OSError):
        return False


def _validate_generated_docx(proposal: Any, content: bytes, selected_versions: list[DocumentVersion], *, expected_identity: dict[str, str | None] | None = None) -> None:
    """Deterministic business validation before a revision is editable."""
    try:
        model = import_editor_model(content)
    except (DocumentPackageError, ValueError, TypeError) as exc:
        raise HTTPException(409, "FAILED_VALIDATION:DOCX_PACKAGE_INVALID") from exc
    text = "\n".join(str(node.get("text") or "") for node in model.get("nodes", []))
    if any(token.lower() in text.lower() for token in ("<tbd>", "[tbd]", "sample proposal", "xxx")):
        raise HTTPException(409, "GENERATION_REVIEW_REQUIRED:UNRESOLVED_PLACEHOLDER")
    if re.search(r"\[\[[^\]]+\]\]", text):
        raise HTTPException(409, "GENERATION_REVIEW_REQUIRED:UNRESOLVED_TEMPLATE_TOKEN")
    if expected_identity and not _docx_identity_matches(content, expected_identity):
        raise HTTPException(409, "GENERATION_REVIEW_REQUIRED:STALE_PROJECT_FACTS")


def _generation_coverage(baseline_model: dict[str, Any], generated_model: dict[str, Any], mutations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Record an explicit disposition for every detected document section."""
    generated_by_id = {str(node.get("id")): node for node in (generated_model.get("nodes") or []) if isinstance(node, dict)}
    mutation_by_anchor = {str(item.get("anchor")): item for item in mutations if isinstance(item, dict) and item.get("anchor")}
    coverage: list[dict[str, Any]] = []
    for section in baseline_model.get("sections") or []:
        node_ids = [str(node_id) for node_id in (section.get("node_ids") or [])]
        section_mutations = [mutation_by_anchor[node_id] for node_id in node_ids if node_id in mutation_by_anchor]
        section_text = "\n".join(str((generated_by_id.get(node_id) or {}).get("text") or "") for node_id in node_ids)
        citation_keys = sorted({str(key) for item in section_mutations for key in (item.get("citation_keys") or [])})
        if "needs owner review" in section_text.casefold():
            disposition = "NEEDS_OWNER_REVIEW"
            reason = "Required project facts remain unresolved in this section."
        elif section_mutations:
            disposition = "UPDATED"
            reason = "Source-grounded content was applied to the governed baseline."
        else:
            disposition = "KEEP_UNCHANGED"
            reason = "Reusable governed AMEC content was preserved."
        coverage.append({
            "section_id": section.get("section_id"),
            "section_title": section.get("title"),
            "disposition": disposition,
            "mutation_ids": [str(item.get("anchor")) for item in section_mutations],
            "citation_keys": citation_keys,
            "reason": reason,
        })
    return coverage


def _apply_dynamic_building_structure(content: bytes, *, building_count: int, building_count_known: bool) -> bytes:
    """Trim or extend the A-E demonstration pages around the shared model.

    The supplied report demonstrates five buildings; it is not a business
    limit. Known counts remove unused detail pages and inventory rows. Counts
    above five clone the governed E page, preserving its tables/styles while
    replacing semantic indices. An unknown count is retained for Owner review
    so generation never invents a building.
    """
    if not building_count_known:
        return content
    count = max(0, min(int(building_count), 100))
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    with zipfile.ZipFile(io.BytesIO(content), "r") as source:
        parts = {name: source.read(name) for name in source.namelist()}
    xml = parts.get("word/document.xml")
    if not xml:
        return content
    root = etree.fromstring(xml)
    body = root.find("w:body", ns)
    if body is None:
        return content
    children = list(body)
    text_of = lambda element: "".join(element.xpath(".//w:t/text()", namespaces=ns))
    # The Owner DOCX has one section heading followed by the repeated native
    # Word building sections.  Older generated fixtures used a numbered
    # heading, so retain that migration spelling as a fallback.
    starts = [
        i for i, element in enumerate(children)
        if re.search(r"^(?:المبن[ىي])\s+[A-E]$", text_of(element).strip())
    ]
    modification_start = next(
        (i for i, element in enumerate(children)
         if "جدول التعديلات" in text_of(element) or "10 - التعديلات المطلوبة" in text_of(element)),
        len(children) - 1,
    )
    if starts:
        if count < len(starts):
            first_remove = starts[count]
            for element in children[first_remove:modification_start]:
                body.remove(element)
        elif count > len(starts):
            template_start = starts[-1]
            template_nodes = children[template_start:modification_start]
            modification_element = children[modification_start]
            for index in range(len(starts) + 1, count + 1):
                symbol = chr(64 + index) if index <= 26 else str(index)
                cloned = [deepcopy(element) for element in template_nodes]
                for element in cloned:
                    text_nodes = element.xpath(".//w:t", namespaces=ns)
                    joined_text = "".join(node.text or "" for node in text_nodes)
                    if text_nodes:
                        joined_text = joined_text.replace("للمبنى E", f"للمبنى {symbol}").replace("صور المبنى E", f"صور المبنى {symbol}").replace("المبنى E", f"المبنى {symbol}").replace("المبني E", f"المبني {symbol}")
                        if joined_text != "".join(node.text or "" for node in text_nodes):
                            text_nodes[0].text = joined_text
                            for node in text_nodes[1:]:
                                node.text = ""
                    for node in element.xpath(".//w:t", namespaces=ns):
                        if node.text:
                            node.text = node.text.replace("building.5", f"building.{index}").replace("building.{idx}", f"building.{index}").replace("للمبنى E", f"للمبنى {symbol}").replace("المبنى E", f"المبنى {symbol}").replace("المبني E", f"المبني {symbol}")
                            node.text = re.sub(rf"\[\[building\.{index}\.symbol\]\]", symbol, node.text)
                            node.text = re.sub(rf"\[\[building\.{index}\.[^\]]+\]\]", "Needs Owner Review / يحتاج مراجعة المالك", node.text)
                insertion = list(body).index(modification_element)
                for element in cloned:
                    body.insert(insertion, element)
                    insertion += 1
        # Keep the inventory and repeated detail sections driven by the same
        # count. The inventory table is the table containing building.1.symbol.
        for table in body.xpath("./w:tbl", namespaces=ns):
            table_text = text_of(table)
            if not ("building.1.symbol" in table_text or "رمز المبنى" in table_text):
                continue
            rows = table.xpath("./w:tr", namespaces=ns)
            data_rows = rows[1:]
            for row in data_rows[count:]:
                table.remove(row)
            if count > len(data_rows) and data_rows:
                template_row = data_rows[-1]
                for number in range(len(data_rows) + 1, count + 1):
                    symbol = chr(64 + number) if number <= 26 else str(number)
                    cloned = deepcopy(template_row)
                    for node in cloned.xpath(".//w:t", namespaces=ns):
                        value = node.text or ""
                        if re.fullmatch(r"0?\d+", value.strip()):
                            node.text = f"{number:02d}"
                        elif value.strip() == "E":
                            node.text = symbol
                    table.append(cloned)
            break
        # The modification matrix is a second repeatable native table. It is
        # driven by the same building count and uses the same conservative
        # Owner-review placeholders for newly cloned rows.
        for table in body.xpath("./w:tbl", namespaces=ns):
            table_text = text_of(table)
            if "الوضع حسب الرخصة القديمة" not in table_text or "الإجراء المقترح" not in table_text:
                continue
            rows = table.xpath("./w:tr", namespaces=ns)
            data_rows = rows[1:]
            for row in data_rows[count:]:
                table.remove(row)
            if count > len(data_rows) and data_rows:
                template_row = data_rows[-1]
                for number in range(len(data_rows) + 1, count + 1):
                    symbol = chr(64 + number) if number <= 26 else str(number)
                    cloned = deepcopy(template_row)
                    for node in cloned.xpath(".//w:t", namespaces=ns):
                        value = node.text or ""
                        if re.fullmatch(r"0?\d+", value.strip()):
                            node.text = f"{number:02d}"
                        elif "Building E" in value:
                            node.text = value.replace("Building E", f"Building {symbol}")
                    table.append(cloned)
            break
    parts["word/document.xml"] = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as target:
        for name, value in parts.items():
            target.writestr(name, value)
    return output.getvalue()


def _ensure_baseline_template(db: Session, proposal: Any) -> DocumentVersion:
    """Provide the governed AMEC baseline when a live source has no DOCX.

    Synology source folders are not required to contain a prior proposal. The
    Owner still needs a complete editable document, so the immutable AMEC
    template is stored once in managed artifact storage and becomes an explicit
    BASELINE_TEMPLATE source link alongside the live evidence.
    """
    # Production resolves the exact reviewed Content Library binding. A code
    # fixture is valid only for the synthetic test profile and is never a live
    # fallback.
    settings = get_settings()
    if not (settings.synthetic_only and settings.app_env.upper() in {"TEST", "DEV", "DEVELOPMENT"}):
        # Commission the single Owner-approved Arabic technical-report master
        # before resolving the Content Library binding.  Older synthetic text
        # placeholders are upgraded as immutable history by this idempotent
        # command; they can never remain the generation baseline.
        from ..services.master_content import ensure_canonical_proposal_v1_template
        ensure_canonical_proposal_v1_template(db, actor="proposal-v1-template-onboarding")
        resolved = resolve_master_content_purpose(db, module="BD", usage_type="PROPOSAL_TEMPLATE")
        if resolved.get("status") != "RESOLVED" or not resolved.get("item", {}).get("version_id"):
            raise HTTPException(422, "PROPOSAL_BASELINE_TEMPLATE_REQUIRED")
        version = db.get(DocumentVersion, resolved["item"]["version_id"])
        if version is None:
            raise HTTPException(422, "PROPOSAL_BASELINE_TEMPLATE_REQUIRED")
        try:
            import_editor_model(_captured_bytes(version))
        except (DocumentPackageError, ValueError, TypeError) as exc:
            raise HTTPException(422, "PROPOSAL_BASELINE_TEMPLATE_INVALID") from exc
        if not _baseline_is_complete(version):
            raise HTTPException(422, "PROPOSAL_BASELINE_TEMPLATE_INCOMPLETE")
        return version
    existing = db.scalar(
        select(DocumentVersion)
        .join(Document, Document.id == DocumentVersion.document_id)
        .where(
            Document.project_id == proposal.project_id,
            Document.source_system == "PROPOSAL_TEMPLATE_BASELINE",
            DocumentVersion.superseded_by.is_(None),
        )
        .order_by(DocumentVersion.ingested_at.desc())
    )
    if existing is not None and _baseline_is_complete(existing):
        return existing
    # Do not reuse the historical one-page bootstrap artifact.  Keep it
    # immutable for audit, but materialize the current reviewed AMEC package
    # as a new template version so regeneration can replace the bad draft.
    template_path = Path(__file__).resolve().parents[1] / "fixtures" / "AMEC-P-D-2026-Q-TECHNICAL-REPORT.docx"
    try:
        content = template_path.read_bytes()
    except OSError as exc:
        raise HTTPException(503, "PROPOSAL_BASELINE_TEMPLATE_UNAVAILABLE") from exc
    try:
        import_editor_model(content)
    except (DocumentPackageError, ValueError, TypeError) as exc:
        raise HTTPException(503, "PROPOSAL_BASELINE_TEMPLATE_INVALID") from exc
    store = create_binary_store()
    document = Document(
        project_id=proposal.project_id, document_type=DocumentType.OTHER,
        logical_name="AMEC Proposal V1 baseline template", language="EN",
        source_system="PROPOSAL_TEMPLATE_BASELINE",
    )
    db.add(document)
    db.flush()
    target = StorageTarget(
        store.provider_id,
        getattr(getattr(store, "config", None), "container", None)
        or getattr(getattr(store, "config", None), "share", "synthetic"),
        f"proposal-templates/{proposal.project_id}",
    )
    stored = DocumentStorageService(store).store_version(
        db, document=document, content=content,
        filename="AMEC-P-D-2026-Q-TECHNICAL-REPORT.docx",
        mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        target=target, actor="proposal-template",
        correlation_id=f"proposal-template:{proposal.project_id}",
        idempotency_key=f"proposal-template:{proposal.project_id}",
        source_system="PROPOSAL_TEMPLATE_BASELINE",
        metadata={
            "template_baseline": True,
            "sensitivity_class": "INTERNAL",
            "synthetic_non_business_fixture": True,
            "source_presence_state": "PRESENT",
            "template_name": "AMEC Proposal V1 Arabic technical report",
            **template_metadata(),
        },
    )
    return stored.version


def _attach_baseline_template(db: Session, proposal: Any, version: DocumentVersion) -> None:
    """Make the selected template part of the Proposal's governed context."""
    evidence = db.scalar(
        select(ProposalSourceEvidence).where(
            ProposalSourceEvidence.proposal_id == proposal.id,
            ProposalSourceEvidence.source_type == "PROPOSAL_TEMPLATE",
            ProposalSourceEvidence.content_hash == version.sha256,
        )
    )
    if evidence is None:
        evidence = ProposalSourceEvidence(
            proposal_id=proposal.id,
            source_type="PROPOSAL_TEMPLATE",
            source_filename=version.source_filename,
            source_reference=version.source_path_or_reference,
            content_hash=version.sha256,
            content_type=version.mime_type,
            provenance={
                "kind": "proposal_baseline_template",
                "document_version_id": version.id,
                "verification": "READ_BACK_VERIFIED",
            },
            status="CURRENT",
            verification_state="READ_BACK_VERIFIED",
            created_by="proposal-baseline-repair",
        )
        db.add(evidence)
        db.flush()
    link = db.scalar(
        select(ProposalSourceLink).where(
            ProposalSourceLink.proposal_id == proposal.id,
            ProposalSourceLink.document_version_id == version.id,
            ProposalSourceLink.source_role == "BASELINE_TEMPLATE",
        )
    )
    if link is None:
        db.add(ProposalSourceLink(
            proposal_id=proposal.id,
            source_evidence_id=evidence.id,
            document_id=version.document_id,
            document_version_id=version.id,
            source_role="BASELINE_TEMPLATE",
            added_by="proposal-baseline-repair",
        ))
    elif not link.active:
        link.active = True
        link.source_evidence_id = evidence.id


def _prepare_baseline_versions(db: Session, proposal: Any, versions: list[DocumentVersion]) -> list[DocumentVersion]:
    """Preserve evidence while selecting and attaching a reviewed AMEC template."""
    expected_identity = _proposal_baseline_identity(db, proposal, versions)
    prepared: list[DocumentVersion] = []
    valid_baseline = False
    for version in versions:
        # Keep captured DOCX files in the evidence set even when they are an
        # old bootstrap or another project's proposal.  They remain visible
        # to the Owner; the selection predicate below decides what may be the
        # editable baseline.
        prepared.append(version)
        if not _is_recognized_baseline_docx(version):
            continue
        if _baseline_is_complete(version) and _template_metadata(version).get("template_id") == "AMEC-PROPOSAL-V1-TECHNICAL-REPORT":
            valid_baseline = True
        # Recognized but incomplete/cross-project DOCX files are source
        # evidence at most; they are never allowed to become the Proposal
        # document baseline.
    if not valid_baseline:
        template = _ensure_baseline_template(db, proposal)
        _attach_baseline_template(db, proposal, template)
        prepared.append(template)
    return prepared


def _generate_proposal_revision(
    *, request: Request, db: Session, proposal: Any, selected_versions: list[DocumentVersion],
    source_set_hash: str, seeded_editor: dict[str, Any], role: Role,
) -> dict[str, Any]:
    """Run Proposal Intelligence and publish its anchored DOCX result.

    The model receives only the exact active source links assembled by the
    Proposal service.  It returns a strict change plan; this function applies
    those preconditioned mutations to the captured baseline and stores a new
    canonical working revision before the browser opens.
    """
    generation = db.scalar(select(ProposalGenerationAttempt).where(ProposalGenerationAttempt.proposal_id == proposal.id, ProposalGenerationAttempt.manifest_hash == source_set_hash, ProposalGenerationAttempt.generation_kind == "DOCUMENT_CHANGE_PLAN").with_for_update())
    if generation is not None and generation.status == "SUCCEEDED":
        raise HTTPException(409, "GENERATION_ALREADY_SUCCEEDED")
    if generation is not None and generation.status == "RUNNING":
        raise HTTPException(409, "GENERATION_RUNNING")
    if generation is None:
        generation = ProposalGenerationAttempt(proposal_id=proposal.id, manifest_hash=source_set_hash, generation_kind="DOCUMENT_CHANGE_PLAN", attempt_number=1, status="PENDING", created_by=getattr(role, "value", str(role)))
        db.add(generation)
        db.flush()
    else:
        generation.attempt_number = int(generation.attempt_number or 0) + 1
        generation.status = "PENDING"
        generation.failure_code = None
    generation.status = "RUNNING"
    from datetime import datetime, timezone
    generation.started_at = datetime.now(timezone.utc)
    db.commit()
    expected_identity = _proposal_baseline_identity(db, proposal, selected_versions)
    baseline = _select_baseline_docx(selected_versions, expected_identity=expected_identity)
    if baseline is None:
        raise HTTPException(422, "VALID_DOCX_SOURCE_REQUIRED")
    baseline_bytes = _captured_bytes(baseline)
    try:
        import_editor_model(baseline_bytes)
    except (DocumentPackageError, ValueError, TypeError) as exc:
        raise HTTPException(422, "VALID_DOCX_SOURCE_REQUIRED") from exc
    baseline_model = import_editor_model(baseline_bytes)
    baseline_meta = _template_metadata(baseline)
    if baseline_meta.get("template_id") != "AMEC-PROPOSAL-V1-TECHNICAL-REPORT":
        raise HTTPException(422, "PROPOSAL_BASELINE_TEMPLATE_REQUIRED")
    # A one-page stub is not a complete AMEC Proposal baseline.  Fail closed
    # before AI generation rather than exposing a deceptively editable summary.
    if len(baseline_model.get("nodes") or []) < 24 or len(package_parts(baseline_bytes)) < 10:
        raise HTTPException(409, "GENERATION_REVIEW_REQUIRED:INCOMPLETE_BASELINE_DOCUMENT")

    settings = get_settings()
    synthetic_local = settings.synthetic_only and settings.app_env.upper() in {"TEST", "DEV", "DEVELOPMENT"}
    provider = ProposalDeterministicProvider() if synthetic_local else None
    try:
        intelligence = execute_proposal_intelligence(
            db, proposal_id=proposal.id, operation="document-change-plan",
            principal=authenticated_principal_context() or AuthenticatedPrincipal(auth_mode="DEV_HEADER", role=role, user_id=None),
            # A failed provider reservation is terminal for its idempotency
            # key.  Generation is retried when the Owner repeats Create
            # Proposal, so each attempt needs a fresh key; the surrounding
            # source-set/provenance check still makes successful promotion
            # idempotent and prevents duplicate generated revisions.
            idempotency_key=f"proposal-document-generation:{generation.id}",
            correlation_id=getattr(request.state, "correlation_id", str(uuid4())),
            settings=settings, provider=provider,
        )
    except Exception as exc:
        # Preserve the captured Proposal and baseline editor revision so the
        # Owner can retry after a provider/storage outage.
        if isinstance(exc, HTTPException):
            raise
        raise HTTPException(503, "PROPOSAL_AI_GENERATION_FAILED") from exc
    plan = intelligence.get("output") or {}
    if plan.get("template_id") != "AMEC-PROPOSAL-V1-TECHNICAL-REPORT":
        raise HTTPException(409, "PROPOSAL_AI_TEMPLATE_MISMATCH")
    if str(plan.get("template_version") or "") != str(baseline_meta.get("template_version") or ""):
        raise HTTPException(409, "PROPOSAL_AI_TEMPLATE_VERSION_MISMATCH")
    if plan.get("baseline_document_version_id") != baseline.id:
        raise HTTPException(409, "PROPOSAL_AI_BASELINE_MISMATCH")
    baseline_nodes = {str(node.get("id")): node for node in baseline_model.get("nodes", []) if isinstance(node, dict)}
    raw_mutations = []
    for candidate in plan.get("mutations") or []:
        if not isinstance(candidate, dict):
            raw_mutations.append(candidate)
            continue
        mutation = dict(candidate)
        node = baseline_nodes.get(str(mutation.get("anchor"))) or {}
        mutation.setdefault("section", node.get("part") or node.get("block_type") or "Document")
        mutation.setdefault("before", node.get("text") or "")
        mutation.setdefault("after", mutation.get("replacement") or "")
        mutation.setdefault("reason", "Source-grounded Proposal change")
        mutation.setdefault("published_status", "PUBLISHED")
        # A provider may echo an already-correct value.  It is not a document
        # mutation and must not inflate the AI Changes count.
        if str(mutation.get("replacement") or "") == str(mutation.get("before") or ""):
            continue
        raw_mutations.append(mutation)
    plan["mutations"] = raw_mutations
    # A first generation with no source-backed document mutation is not a
    # truthful generated Proposal. Only a later, already verified Proposal may
    # legitimately produce a deterministic no-change result; a first
    # generation must stop for Owner review instead of being marked ready with
    # an unchanged baseline.
    prior_for_zero = db.get(ProposalRevision, seeded_editor.get("editor_revision_id")) if seeded_editor.get("editor_revision_id") else None
    prior_for_zero_provenance = (prior_for_zero.snapshot or {}).get("ai_provenance") if prior_for_zero else {}
    verified_existing_proposal = bool(prior_for_zero_provenance.get("generated_from_ai")) and prior_for_zero_provenance.get("provenance_state") == "RECORDED"
    if not raw_mutations and not verified_existing_proposal:
        raise HTTPException(409, "GENERATION_REVIEW_REQUIRED:AI_NO_DOCUMENT_CHANGES")
    if not raw_mutations:
        plan["status"] = "NO_AI_CHANGES_REQUIRED"
    available_citations = {
        str((item.get("citation_key") or item.get("locator", {}).get("citation_key") or item.get("locator_json", {}).get("citation_key"))) if isinstance(item, dict) else str(item)
        for item in (intelligence.get("citations") or [])
    }
    if not available_citations:
        available_citations = {str(item) for item in (plan.get("citation_keys") or [])}
    for mutation in raw_mutations:
        mutation_citations = {str(item) for item in (mutation.get("citation_keys") or [])} if isinstance(mutation, dict) else set()
        if not mutation_citations or not mutation_citations.issubset(available_citations):
            raise HTTPException(409, "PROPOSAL_AI_MUTATION_CITATION_INVALID")
    try:
        mutations = [TextMutation(str(item["anchor"]), str(item["expected_xml_hash"]), str(item["replacement"])) for item in raw_mutations]
        generated_ai_bytes = apply_text_mutations(baseline_bytes, mutations)
    except (KeyError, TypeError, ValueError, DocumentPackageError) as exc:
        raise HTTPException(409, "PROPOSAL_AI_CHANGE_PLAN_INVALID") from exc
    generated_ai_bytes = _apply_dynamic_building_structure(
        generated_ai_bytes,
        building_count=int(plan.get("building_count") or 0),
        building_count_known=bool(plan.get("building_count_known")),
    )

    # Regeneration must preserve edits already accepted by the Owner.  Rebase
    # the cumulative anchored edits from the prior canonical draft onto the
    # fresh AI output.  If the AI changed document topology and an Owner anchor
    # disappeared, fail closed for review instead of publishing a silent loss.
    prior = prior_for_zero
    prior_snapshot = prior.snapshot if prior and prior.status == "DRAFT" else {}
    owner_mutations_data = prior_snapshot.get("owner_mutations") or []
    owner_mutations_by_anchor = {
        str(item.get("anchor")): item for item in owner_mutations_data
        if isinstance(item, dict) and item.get("anchor")
    }
    # Three-way merge rule: an AI mutation that targets an anchor changed by
    # the Owner cannot silently win.  Preserve the prior draft and require an
    # explicit review, while unrelated AI anchors can be applied safely.
    for item in raw_mutations:
        if not isinstance(item, dict):
            continue
        owner_item = owner_mutations_by_anchor.get(str(item.get("anchor")))
        if owner_item is not None and str(item.get("replacement") or "") != str(owner_item.get("replacement") or ""):
            raise HTTPException(409, "GENERATION_REVIEW_REQUIRED:OWNER_AI_EDIT_CONFLICT")
    owner_mutations: list[TextMutation] = []
    if owner_mutations_data:
        generated_nodes = {str(node.get("id")): node for node in import_editor_model(generated_ai_bytes).get("nodes", []) if isinstance(node, dict)}
        for item in owner_mutations_data:
            if not isinstance(item, dict) or not item.get("anchor"):
                raise HTTPException(409, "OWNER_EDIT_REBASE_REQUIRED")
            node = generated_nodes.get(str(item["anchor"]))
            if node is None or not node.get("editable"):
                raise HTTPException(409, "OWNER_EDIT_REBASE_REQUIRED")
            owner_mutations.append(TextMutation(str(item["anchor"]), str(node.get("xml_hash") or ""), str(item.get("replacement") or "")))
        try:
            generated_bytes = apply_text_mutations(generated_ai_bytes, owner_mutations)
        except (DocumentPackageError, ValueError, TypeError) as exc:
            raise HTTPException(409, "OWNER_EDIT_REBASE_REQUIRED") from exc
    else:
        generated_bytes = generated_ai_bytes
    _validate_generated_docx(proposal, generated_bytes, selected_versions, expected_identity=expected_identity)

    store = create_binary_store()
    generated_document = Document(
        project_id=proposal.project_id, document_type=DocumentType.OTHER,
        logical_name=f"{proposal.opportunity_reference}:ai-generated-proposal",
        language="EN", source_system="PROPOSAL_AI_GENERATION",
    )
    db.add(generated_document)
    db.flush()
    target = StorageTarget(
        store.provider_id,
        getattr(getattr(store, "config", None), "container", None) or getattr(getattr(store, "config", None), "share", "synthetic"),
        f"proposal-generations/{proposal.id}",
    )
    generated = DocumentStorageService(store).store_version(
        db, document=generated_document, content=generated_bytes,
        filename=f"{proposal.opportunity_reference}-revised.docx",
        mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        target=target, actor=getattr(role, "value", str(role)),
        correlation_id=getattr(request.state, "correlation_id", f"proposal-generation:{proposal.id}"),
        idempotency_key=f"proposal-generation:{proposal.id}:{source_set_hash}",
        source_system="PROPOSAL_AI_GENERATION",
        metadata={
            "proposal_id": proposal.id, "source_set_hash": source_set_hash,
            "baseline_document_version_id": baseline.id,
            "baseline_sha256": baseline.sha256,
            "baseline_selection_method": "GOVERNED_MASTER_CONTENT_TEMPLATE",
            "template_id": baseline_meta.get("template_id"),
            "template_version": baseline_meta.get("template_version"),
            "baseline_identity": expected_identity,
            "ai_work_product_id": intelligence.get("work_product_id"),
            "ai_context_snapshot_id": intelligence.get("context_snapshot_id"),
            "evidence_refs": [item.id for item in selected_versions],
        },
    )
    if prior is not None and prior.status == "DRAFT":
        prior.status = "SUPERSEDED"
        from datetime import datetime, timezone
        prior.superseded_at = datetime.now(timezone.utc)
    latest_number = db.scalar(select(ProposalRevision.revision_number).where(ProposalRevision.proposal_id == proposal.id).order_by(ProposalRevision.revision_number.desc())) or 0
    generated_ai_model = import_editor_model(generated_ai_bytes)
    provider_coverage = list(plan.get("generation_coverage") or [])
    coverage = _generation_coverage(baseline_model, generated_ai_model, raw_mutations)
    plan["generation_coverage"] = coverage
    plan["semantic_generation_coverage"] = provider_coverage
    plan["template_contract"] = template_contract()
    plan["coverage_state"] = "PASS" if coverage and all(item.get("disposition") in {"KEEP_UNCHANGED", "UPDATED", "GENERATED", "NEEDS_OWNER_REVIEW"} for item in coverage) else "FAIL"
    plan["full_document_generation"] = "COMPLETE"
    published_mutation_count = len([item for item in raw_mutations if isinstance(item, dict)])
    generation_validation = {
        "state": "PASSED",
        "full_document_generation": "COMPLETE",
        "full_document_validation": "PASS",
        "coverage_state": plan["coverage_state"],
        "sections_considered": len(coverage),
        "sections_needing_owner_review": sum(item.get("disposition") == "NEEDS_OWNER_REVIEW" for item in coverage),
        "docx_package": "VALID",
        "project_identity": "PASSED",
        "source_manifest_hash": source_set_hash,
        "template_id": baseline_meta.get("template_id"),
        "template_version": baseline_meta.get("template_version"),
        "template_contract_version": baseline_meta.get("template_contract_version"),
        "template_selected": True,
        "template_version_pinned": True,
        "source_manifest_frozen": True,
        "all_template_sections_processed": {str(item.get("section_id")) for item in plan.get("semantic_generation_coverage", []) if isinstance(item, dict)} >= set(template_metadata()["semantic_sections"]),
        "protected_approval_fields_not_autofilled": "محمي - مراجعة بشرية" in "\n".join(str(node.get("text") or "") for node in generated_ai_model.get("nodes", [])),
        "arabic_render_valid": any(any("\u0600" <= char <= "\u06ff" for char in str(node.get("text") or "")) for node in generated_ai_model.get("nodes", [])),
        "docx_valid": True,
    }
    snapshot = {
        "editor_model": import_editor_model(generated_bytes),
        "owner_base_model": generated_ai_model,
        "owner_mutations": [
            {"anchor": mutation.anchor, "expected_xml_hash": mutation.expected_xml_hash, "replacement": mutation.replacement}
            for mutation in owner_mutations
        ],
        "owner_edit_base_hash": digest(generated_ai_bytes),
        "baseline_hash": digest(baseline_bytes), "working_hash": digest(generated_bytes),
        "source_set_hash": source_set_hash, "source_ids": [item.id for item in selected_versions],
        "editor_baseline_document_version_id": baseline.id,
        "baseline_selection_method": "GOVERNED_MASTER_CONTENT_TEMPLATE",
        "template_contract": template_contract(),
        "baseline_identity": expected_identity,
        "editor_document_id": generated.document.id,
        "editor_document_version_id": generated.version.id,
        "change_plan": plan,
        "generation_validation": generation_validation,
        "ai_provenance": {
            "generated_from_ai": True,
            "generation_mode": "SYNTHETIC_DETERMINISTIC" if synthetic_local else "GOVERNED_AZURE_OPENAI",
            "provenance_state": "RECORDED", "source_set_hash": source_set_hash,
            "generated_from_manifest_hash": source_set_hash,
            "evidence_refs": [item.id for item in selected_versions],
            "citations": intelligence.get("citations", []),
            "work_product_id": intelligence.get("work_product_id"),
            "context_snapshot_id": intelligence.get("context_snapshot_id"),
            "mutation_count": published_mutation_count,
            "published_ai_mutation_count": published_mutation_count,
            "validation_state": "PASSED",
            "owner_mutation_count": len(owner_mutations),
            "template_id": baseline_meta.get("template_id"),
            "template_version": baseline_meta.get("template_version"),
            "source_provenance": plan.get("fact_pass", []),
        },
    }
    snapshot["generation_summary"] = canonical_generation_summary(type("RevisionSnapshot", (), {"snapshot": snapshot})())
    revision = ProposalRevision(
        proposal_id=proposal.id, revision_number=latest_number + 1, status="DRAFT",
        change_summary={"created_from": "PROPOSAL_AI_GENERATION", "baseline_document_version_id": baseline.id, "mutation_count": published_mutation_count},
        snapshot=snapshot, content_hash=digest(json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode()),
        created_by=getattr(role, "value", str(role)),
    )
    db.add(revision)
    db.flush()
    generation.status = "SUCCEEDED"
    generation.provider_execution_id = intelligence.get("work_product_id")
    generation.completed_at = datetime.now(timezone.utc)
    db.flush()
    return {
        "editor_ready": True, "editor_revision_id": revision.id,
        "editor_revision_number": revision.revision_number,
        "editor_baseline_hash": snapshot["baseline_hash"],
        "ai_generation": {
            "status": "SUCCEEDED", "work_product_id": intelligence.get("work_product_id"),
            "context_snapshot_id": intelligence.get("context_snapshot_id"),
            "mutation_count": published_mutation_count, "published_ai_mutation_count": published_mutation_count, "source_set_hash": source_set_hash,
            "generation_mode": snapshot["ai_provenance"]["generation_mode"],
        },
    }


def _select_baseline_docx(versions: list[DocumentVersion], *, expected_identity: dict[str, str | None] | None = None) -> DocumentVersion:
    """Select exactly one recognized AMEC Proposal baseline."""
    candidates = [version for version in versions if (version.source_filename or "").lower().endswith(".docx")]
    recognized = [version for version in candidates if _is_recognized_baseline_docx(version)]
    if expected_identity is not None:
        recognized = [version for version in recognized if _baseline_identity_matches(version, expected_identity)]
    # A syntactically valid bootstrap/stub is not a baseline.  Filter it
    # before cardinality checks so an old stub cannot shadow the governed
    # template that was added later.
    recognized = [version for version in recognized if _baseline_is_complete(version)]
    # Proposal V1 always starts from the reviewed canonical Arabic technical
    # report. A project DOCX is evidence and is never silently used as the
    # baseline, even when it happens to be complete.
    templates = [version for version in recognized if _template_metadata(version).get("template_id") == "AMEC-PROPOSAL-V1-TECHNICAL-REPORT"]
    if len(templates) == 1:
        return templates[0]
    if len(templates) > 1:
        raise HTTPException(409, "PROPOSAL_BASELINE_SELECTION_REQUIRED")
    # Generic DOCX files (scope briefs, client letters, project descriptions)
    # remain source evidence and never silently become the baseline.
    if not candidates:
        raise HTTPException(422, "VALID_DOCX_SOURCE_REQUIRED")
    raise HTTPException(422, "VALID_DOCX_SOURCE_REQUIRED")


def _is_recognized_baseline_docx(version: DocumentVersion) -> bool:
    metadata = version.metadata_json or {}
    if metadata.get("template_baseline") or metadata.get("source_role") == "BASELINE_TEMPLATE":
        return True
    filename = (version.source_filename or "").lower()
    return bool(re.search(r"(?:amec\s*[-_ ]?p[-_ ]?d|amec.{0,40}proposal|proposal.{0,40}(?:docx|baseline)|baseline.{0,40}(?:docx|proposal)|template.{0,40}(?:docx|proposal))", filename))


@router.post("/2026/projects/{number}/create-proposal")
def create_proposal_from_source_workspace(
    number: int,
    request: Request,
    payload: SourceProposalCreatePayload | None = Body(default=None),
    db: Session = Depends(get_db),
    role: Role = Depends(create_role),
):
    """Create one canonical Proposal from any explicitly selected Draft."""
    discovered = next((row for row in projects(db) if row["number"] == number), None)
    # The Owner has already reviewed the latest explicit Sync result.  Reuse a
    # complete canonical snapshot without starting a second capture lifecycle.
    # A legacy/API caller that never synced receives one compatibility
    # bootstrap capture; once a complete snapshot exists, retries are strictly
    # idempotent and read-only against the source adapter.
    prior_manifest = source_manifest(db, number)
    if prior_manifest.get("completeness_state") == "COMPLETE":
        run = {
            "project_number": number,
            "file_count": len([entry for entry in prior_manifest.get("entries", []) if entry.get("document_version_id")]),
            "captured_count": 0,
            "unchanged_count": len([entry for entry in prior_manifest.get("entries", []) if entry.get("document_version_id")]),
            "state": "SNAPSHOT_REUSED",
            "synology_write_count": 0,
        }
    else:
        run = capture(db, number, actor="source-create-proposal")
    # Bridge captures are attached to the canonical Project row so downstream
    # intake, provenance, and editor records share one project identity.  The
    # mounted synthetic fixture keeps its historical provisional behavior.
    project = db.scalar(select(Project).where(Project.project_number == str(number))) if get_settings().source_intake_mode.upper() == "BRIDGE" else None
    if project is None and get_settings().source_intake_mode.upper() == "BRIDGE":
        # 520+ projects are discovered from the bridge before they have a
        # relational Project row. Promote the exact discovered folder into the
        # same canonical identity boundary used by project 454.
        discovered = next((row for row in projects(db) if row["number"] == number), None)
        if discovered is None:
            raise HTTPException(404, "SOURCE_PROJECT_NOT_FOUND")
        project, client = _ensure_source_project_and_client(db, number=number, folder_name=discovered["folder_name"])
    elif project is not None:
        project, client = _ensure_source_project_and_client(db, number=number, folder_name=project.project_name)
    else:
        client = None
    project_name = (project.project_name if project else f"Project {number}").strip()
    source_folder_name = str((discovered or {}).get("folder_name") or project_name).strip()
    # The Synology folder is the provisional source label for this promotion;
    # canonical ClientAccount mapping remains a separate Owner action.
    client_name = _source_client_name(source_folder_name, number)
    client_id = client.id if client is not None else None
    source_project_identity = canonical_source_project_identity(number=number, folder_name=project_name if project else (discovered or {}).get("folder_name", f"Project {number}"))
    item = _create_proposal_record(ProposalCreate(proposal_description=f"{client_name} Proposal", project_reference=str(number), project_id=project.id if project else None, client_account_id=client_id, client_name=client_name, idempotency_key=f"proposal-source-project:{source_project_identity}", provisional_source_identity=True), request, db, role)
    # The source adapter is synthetic-only in TEST/DEV/Azure pre-production.
    # Mark the Proposal projection accordingly so the shared AI context
    # compiler can prove that the entity and its captured evidence belong to
    # the same non-business fixture boundary. Production/live captures stay
    # NON_SYNTHETIC and remain fail-closed until governed data is configured.
    if (
        get_settings().synthetic_only
        and get_settings().app_env.upper() in {"TEST", "DEV", "DEVELOPMENT"}
    ):
        item.fixture_classification = "SYNTHETIC_OWNER_TEST"
    manifest = source_manifest(db, number)
    if manifest.get("completeness_state") != "COMPLETE":
        db.rollback()
        raise HTTPException(409, {"code": "SOURCE_SNAPSHOT_INCOMPLETE", "reasons": manifest.get("completeness_reasons", []), "scan_status": manifest.get("scan_status")})
    excluded_paths = {path.strip() for path in (payload.excluded_source_paths if payload else []) if path and path.strip()}
    # Categories are server-owned DocumentVersion metadata.  The legacy
    # request field remains accepted for compatibility but never controls AI
    # promotion; an unsaved browser dropdown must not change the source set.
    requested_categories = payload.source_categories if payload else {}
    invalid_categories = sorted({value for value in requested_categories.values() if value not in LOGICAL_SOURCE_CATEGORIES})
    if invalid_categories:
        raise HTTPException(422, {"code": "SOURCE_CATEGORY_INVALID", "allowed": sorted(LOGICAL_SOURCE_CATEGORIES), "values": invalid_categories})
    # Preserve compatibility with older callers that posted exclusions while
    # making the canonical state durable before promotion.
    current_versions = current_source_versions(db, number)
    for path in excluded_paths:
        version = current_versions.get(path)
        if version is not None:
            save_source_inclusion(version, False, actor="source-create-proposal")
    if excluded_paths:
        db.flush()
        manifest = source_manifest(db, number)
    selected_versions = [
        current_versions.get(entry["source_path"])
        for entry in manifest["entries"]
        if entry.get("included") and entry.get("document_version_id") and current_versions.get(entry["source_path"]) is not None
    ]
    selected_versions = [version for version in selected_versions if version is not None]
    staged_versions: list[DocumentVersion] = []
    if payload and payload.staging_session_id:
        staging = db.get(ProposalSourceStagingSession, payload.staging_session_id)
        if staging is None or staging.project_number != str(number) or staging.status != "READY":
            db.rollback()
            raise HTTPException(409, "OWNER_SOURCE_STAGING_NOT_READY")
        staged_rows = db.scalars(select(ProposalSourceStagedFile).where(ProposalSourceStagedFile.session_id == staging.id, ProposalSourceStagedFile.verified == true())).all()
        staged_versions = [version for row in staged_rows if (version := db.get(DocumentVersion, row.document_version_id)) is not None]
        if len(staged_versions) != len(staged_rows):
            db.rollback()
            raise HTTPException(409, "OWNER_SOURCE_STAGING_READBACK_FAILED")
        selected_versions.extend(staged_versions)
        for version, staged in zip(staged_versions, staged_rows):
            manifest["entries"].append({"source_identity": f"OWNER_STAGING:{staging.id}:{staged.sha256}", "source_path": staged.filename, "document_version_id": version.id, "document_id": version.document_id, "sha256": version.sha256, "filename": staged.filename, "content_type": version.mime_type, "size": version.file_size, "source_version_token": version.id, "source_presence_state": "PRESENT", "currentness_state": "CURRENT", "source_role": "OWNER_SOURCE", "effective_category": staged.logical_category, "category_origin": "OWNER", "included": True, "inclusion_origin": "OWNER", "processing_state": "PENDING", "capture_status": "CAPTURED"})
        manifest["entries"].sort(key=lambda entry: (entry["source_path"], entry["source_identity"]))
        manifest["source_manifest_hash"] = hashlib.sha256(json.dumps(manifest["entries"], sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    # Only a complete, recognized AMEC Proposal DOCX for this exact project
    # satisfies the baseline contract.  A filename such as Q-454 is not
    # sufficient when the package is the historical one-page bootstrap or
    # contains another project's facts; those artifacts remain evidence while
    # the reviewed template becomes the editable baseline.
    selected_versions = _prepare_baseline_versions(db, item, selected_versions)
    # Promotion is idempotent. If an Owner repeats it after excluding a file,
    # deactivate the existing Proposal link while leaving the immutable
    # captured source and Synology untouched.
    if excluded_paths:
        for link in db.scalars(select(ProposalSourceLink).where(ProposalSourceLink.proposal_id == item.id, ProposalSourceLink.source_role == "SOURCE_WORKSPACE", ProposalSourceLink.active == true())).all():
            linked_version = db.get(DocumentVersion, link.document_version_id)
            if linked_version and (linked_version.metadata_json or {}).get("source_relative_path") in excluded_paths:
                link.active = False
    hashes: list[str] = []
    for version in selected_versions:
        hashes.append(version.sha256)
        metadata = _template_metadata(version)
        relative_path = metadata.get("source_relative_path")
        is_template = bool(metadata.get("template_baseline"))
        owner_staged = bool(metadata.get("owner_staged"))
        source_type = "PROPOSAL_TEMPLATE" if is_template else ("OWNER_SOURCE" if owner_staged else "SYNOLOGY_FILE")
        source_role = "BASELINE_TEMPLATE" if is_template else ("OWNER_SOURCE" if owner_staged else "SOURCE_WORKSPACE")
        evidence = db.scalar(select(ProposalSourceEvidence).where(ProposalSourceEvidence.proposal_id == item.id, ProposalSourceEvidence.source_type == source_type, ProposalSourceEvidence.content_hash == version.sha256))
        if not evidence:
            logical_category = "BASELINE_TEMPLATE" if is_template else source_category(version)
            evidence = ProposalSourceEvidence(proposal_id=item.id, source_type=source_type, source_filename=version.source_filename, source_reference=version.source_path_or_reference, content_hash=version.sha256, content_type=version.mime_type, provenance={"kind": "proposal_baseline_template" if is_template else "synology_source_workspace", "relative_path": relative_path, "logical_category": logical_category, "document_version_id": version.id, "verification": "READ_BACK_VERIFIED"}, status="CURRENT", verification_state="READ_BACK_VERIFIED", created_by="source-create-proposal")
            db.add(evidence)
            db.flush()
        elif not is_template:
            evidence.provenance = {**(evidence.provenance or {}), "relative_path": relative_path, "logical_category": source_category(version), "document_version_id": version.id}
        linked = db.scalar(select(ProposalSourceLink).where(ProposalSourceLink.proposal_id == item.id, ProposalSourceLink.document_version_id == version.id, ProposalSourceLink.source_role == source_role))
        if not linked:
            db.add(ProposalSourceLink(proposal_id=item.id, source_evidence_id=evidence.id, document_id=version.document_id, document_version_id=version.id, source_role=source_role, added_by="source-create-proposal"))
        elif not linked.active:
            linked.active = True
            linked.source_evidence_id = evidence.id
            linked.added_by = "source-create-proposal"
    manifest_entries = [entry for entry in manifest["entries"] if entry.get("included") and entry.get("document_version_id")]
    # The canonical hash is computed over the complete manifest, including
    # excluded entries and their category/inclusion/currentness fields. This
    # makes an Owner exclusion or category correction a material source-set
    # change instead of silently reusing an older AI result.
    source_manifest_hash = manifest["source_manifest_hash"]
    effective_categories = {str(entry["source_path"]): entry["effective_category"] for entry in manifest_entries}
    item.proposal_fields_json = {**(item.proposal_fields_json or {}), "source_workspace": {"logical_root": LOGICAL_ROOT, "project_number": number, "source_project_identity": manifest.get("source_project_identity") or source_project_identity, "source_set_hash": source_manifest_hash, "source_manifest_hash": source_manifest_hash, "source_manifest_version": manifest.get("source_manifest_version"), "source_manifest": manifest, "captured_count": run["captured_count"], "selected_count": len(selected_versions), "excluded_source_paths": sorted(excluded_paths), "source_categories": effective_categories}}
    editor = ensure_editor_revision(db, item, selected_versions, source_set_hash=source_manifest_hash, actor="source-create-proposal")
    # Persist the Proposal, manifest, source links and baseline before any
    # external AI call. A provider outage must leave a durable retryable
    # Proposal instead of rolling the entire promotion back.
    item.proposal_fields_json = {**(item.proposal_fields_json or {}), "generation_state": "BASELINE_READY" if editor.get("editor_ready") else "BLOCKED_BASELINE"}
    db.commit()
    if payload and payload.defer_generation:
        item.proposal_fields_json = {**(item.proposal_fields_json or {}), "generation_state": "PENDING_OWNER_SOURCES"}
        db.commit()
        return {"result": "CREATED", "proposal_id": item.id, "proposal_reference": item.opportunity_reference, "source_set_hash": source_manifest_hash, "source_manifest_hash": source_manifest_hash, "source_count": len(selected_versions), "excluded_source_count": len(excluded_paths), "capture": run, "generation_state": "PENDING_OWNER_SOURCES", **editor}
    # Promotion is the single causal handoff into Proposal Intelligence.  The
    # generated revision is published before the browser is allowed to open
    # the editor, so the Owner always starts from the source-grounded DOCX.
    latest_revision = db.get(ProposalRevision, editor.get("editor_revision_id")) if editor.get("editor_revision_id") else None
    latest_provenance = ((latest_revision.snapshot or {}).get("ai_provenance") or {}) if latest_revision else {}
    generated_for_hash = latest_provenance.get("source_set_hash") if latest_provenance.get("generated_from_ai") else None
    latest_snapshot = (latest_revision.snapshot or {}) if latest_revision else {}
    latest_baseline = db.get(DocumentVersion, latest_snapshot.get("editor_baseline_document_version_id")) if latest_snapshot.get("editor_baseline_document_version_id") else None
    expected_identity = _proposal_baseline_identity(db, item, selected_versions)
    baseline_identity_ok = bool(latest_baseline and _baseline_identity_matches(latest_baseline, expected_identity))
    ai_generation = editor.get("ai_generation")
    if editor.get("editor_ready") and (generated_for_hash != source_manifest_hash or (generated_for_hash == source_manifest_hash and not baseline_identity_ok)):
        try:
            editor = _generate_proposal_revision(
                request=request, db=db, proposal=item, selected_versions=selected_versions,
                source_set_hash=source_manifest_hash, seeded_editor=editor, role=role,
            )
            ai_generation = editor.get("ai_generation")
        except HTTPException as exc:
            detail = exc.detail if isinstance(exc.detail, str) else json.dumps(exc.detail, sort_keys=True)
            generation_state = _generation_state_for_error(detail)
            _mark_generation_failed(db, item.id, source_manifest_hash, detail)
            item.proposal_fields_json = {**(item.proposal_fields_json or {}), "generation_state": generation_state, "generation_error": detail}
            db.commit()
            return {"result": "GENERATION_REVIEW_REQUIRED" if generation_state == "GENERATION_REVIEW_REQUIRED" else "GENERATION_FAILED_RETRYABLE", "proposal_id": item.id, "proposal_reference": item.opportunity_reference, "source_set_hash": source_manifest_hash, "source_manifest_hash": source_manifest_hash, "source_count": len(selected_versions), "excluded_source_count": len(excluded_paths), "capture": run, "generation_state": generation_state, "generation_error": detail, **editor}
        except Exception:
            db.rollback()
            detail = "PROPOSAL_AI_GENERATION_FAILED"
            _mark_generation_failed(db, item.id, source_manifest_hash, detail)
            item.proposal_fields_json = {**(item.proposal_fields_json or {}), "generation_state": "FAILED_RETRYABLE", "generation_error": detail}
            db.commit()
            return {"result": "GENERATION_FAILED_RETRYABLE", "proposal_id": item.id, "proposal_reference": item.opportunity_reference, "source_set_hash": source_manifest_hash, "source_manifest_hash": source_manifest_hash, "source_count": len(selected_versions), "excluded_source_count": len(excluded_paths), "capture": run, "generation_state": "FAILED_RETRYABLE", "generation_error": detail, **editor}
    elif generated_for_hash == source_manifest_hash and latest_provenance:
        ai_generation = {
            "status": "SUCCEEDED",
            "work_product_id": latest_provenance.get("work_product_id"),
            "context_snapshot_id": latest_provenance.get("context_snapshot_id"),
            "mutation_count": latest_provenance.get("mutation_count", 0),
            "source_set_hash": source_manifest_hash,
            "generation_mode": latest_provenance.get("generation_mode"),
        }
    item.proposal_fields_json = {**(item.proposal_fields_json or {}), "generation_state": "READY_FOR_EDIT" if editor.get("editor_ready") else "BLOCKED_BASELINE"}
    db.commit()
    return {"result": "CREATED", "proposal_id": item.id, "proposal_reference": item.opportunity_reference, "source_set_hash": source_manifest_hash, "source_manifest_hash": source_manifest_hash, "source_count": len(selected_versions), "excluded_source_count": len(excluded_paths), "capture": run, "generation_state": "READY_FOR_EDIT" if editor.get("editor_ready") else "BLOCKED_BASELINE", **editor, **({"ai_generation": ai_generation} if ai_generation else {})}


@router.post("/proposals/{proposal_id}/regenerate")
def regenerate_proposal_from_sources(
    proposal_id: str,
    request: Request,
    db: Session = Depends(get_db),
    role: Role = Depends(create_role),
):
    """Regenerate after Owner-added sources have been linked to a Proposal."""
    from ..models import Opportunity
    proposal = db.get(Opportunity, proposal_id)
    if proposal is None:
        raise HTTPException(404, "PROPOSAL_NOT_FOUND")
    links = db.scalars(select(ProposalSourceLink).where(ProposalSourceLink.proposal_id == proposal.id, ProposalSourceLink.active == true()).order_by(ProposalSourceLink.created_at, ProposalSourceLink.id)).all()
    selected_versions = [version for link in links if (version := db.get(DocumentVersion, link.document_version_id)) is not None]
    if not selected_versions:
        raise HTTPException(422, "PROPOSAL_SOURCE_SET_EMPTY")
    manifest = build_effective_proposal_source_manifest(db, proposal)
    included_ids = {str(entry.get("document_version_id")) for entry in manifest["entries"] if entry.get("included") and entry.get("document_version_id")}
    selected_versions = [version for version in selected_versions if str(version.id) in included_ids]
    selected_versions = _prepare_baseline_versions(db, proposal, selected_versions)
    # Baseline repair can attach a replacement template to an older Proposal.
    # Re-read the effective manifest after that repair; the hash intentionally
    # remains source-only, while the template is now available to AI context.
    manifest = build_effective_proposal_source_manifest(db, proposal)
    source_set_hash = manifest["source_manifest_hash"]
    included_ids = {str(entry.get("document_version_id")) for entry in manifest["entries"] if entry.get("included") and entry.get("document_version_id")}
    selected_versions = [version for version in selected_versions if str(version.id) in included_ids]
    latest = db.scalar(select(ProposalRevision).where(ProposalRevision.proposal_id == proposal.id, ProposalRevision.status == "DRAFT").order_by(ProposalRevision.revision_number.desc()))
    if latest is None:
        editor = ensure_editor_revision(db, proposal, selected_versions, source_set_hash=source_set_hash, actor="source-regenerate-proposal")
    else:
        editor = {"editor_ready": True, "editor_revision_id": latest.id, "editor_revision_number": latest.revision_number, "editor_baseline_hash": (latest.snapshot or {}).get("baseline_hash")}
    provenance = ((latest.snapshot or {}).get("ai_provenance") or {}) if latest else {}
    canonical_audit_row = audit_proposal(db, proposal)
    if not editor.get("editor_ready"):
        db.commit()
        return {"result": "BLOCKED", "source_set_hash": source_set_hash, **editor}
    # A current source hash alone is insufficient: older revisions may have
    # been generated from a non-canonical baseline or may lack a complete
    # generation validation record.  Reconcile every such revision through
    # the same canonical generation path.
    if canonical_audit_row.get("classification") != CANONICAL_CLASSIFICATION:
        try:
            editor = _generate_proposal_revision(request=request, db=db, proposal=proposal, selected_versions=selected_versions, source_set_hash=source_set_hash, seeded_editor=editor, role=role)
        except HTTPException as exc:
            detail = str(exc.detail)
            generation_state = _generation_state_for_error(detail)
            _mark_generation_failed(db, proposal.id, source_set_hash, detail)
            proposal.proposal_fields_json = {**(proposal.proposal_fields_json or {}), "generation_state": generation_state, "generation_error": detail}
            db.commit()
            return {"result": "GENERATION_REVIEW_REQUIRED" if generation_state == "GENERATION_REVIEW_REQUIRED" else "GENERATION_FAILED_RETRYABLE", "proposal_id": proposal.id, "source_set_hash": source_set_hash, "generation_state": generation_state, "generation_error": detail, **editor}
        except Exception:
            db.rollback()
            detail = "PROPOSAL_AI_GENERATION_FAILED"
            _mark_generation_failed(db, proposal.id, source_set_hash, detail)
            proposal.proposal_fields_json = {**(proposal.proposal_fields_json or {}), "generation_state": "FAILED_RETRYABLE", "generation_error": detail}
            db.commit()
            return {"result": "GENERATION_FAILED_RETRYABLE", "proposal_id": proposal.id, "source_set_hash": source_set_hash, "generation_state": "FAILED_RETRYABLE", "generation_error": detail, **editor}
    current_fields = dict(proposal.proposal_fields_json or {})
    current_workspace = dict(current_fields.get("source_workspace") or {})
    current_workspace.update({"source_set_hash": source_set_hash, "source_manifest_hash": source_set_hash, "source_manifest": manifest})
    proposal.proposal_fields_json = {**current_fields, "source_workspace": current_workspace, "generation_state": "READY_FOR_EDIT", "source_set_hash": source_set_hash}
    db.commit()
    return {"result": "REGENERATED", "proposal_id": proposal.id, "source_set_hash": source_set_hash, "source_count": len(selected_versions), **editor}
