"""Authenticated Proposal source workspace routes."""
from __future__ import annotations

import hashlib
import io
import json
import os
import re
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select, true
from sqlalchemy.orm import Session

from ..api.dependencies import AuthenticatedPrincipal, authenticated_actor, authenticated_principal_context, require_roles
from ..audit.service import audit
from ..db import get_db
from ..models import ClientAccount, Document, DocumentApprovalState, DocumentType, DocumentVersion, Opportunity, ProposalGenerationAttempt, ProposalRevision, ProposalSourceEvidence, ProposalSourceLink, ProposalSourceStagedFile, ProposalSourceStagingSession, ProposalStalenessEvent, Project, Role
from ..services.proposal_source_workspace import LOGICAL_ROOT, LOGICAL_SOURCE_CATEGORIES, build_effective_proposal_source_manifest, capture, canonical_source_project_identity, configured_source_root, current_source_versions, ensure_editor_revision, projects, save_source_category, save_source_inclusion, source_category, source_included, source_manifest, tree
from ..services.proposal_production_boundary import require_authorized_office
from ..config.settings import get_settings
from ..storage import DocumentStorageService, StorageTarget, create_binary_store
from ..services.proposal_document_package import DocumentPackageError, TextMutation, apply_text_mutations, digest
from ..services.proposal_editor_model import import_editor_model
from ..services.proposal_intelligence import ProposalDeterministicProvider, execute_proposal_intelligence
from ..services.master_content import resolve_master_content_purpose
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
    return {"logical_root": "Tenders/1- Proposal/2026", "physical_root_configured": settings.source_intake_mode.upper() != "BRIDGE" and configured_source_root().is_absolute(), "projects": projects(db)}


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


def _validate_generated_docx(proposal: Any, content: bytes, selected_versions: list[DocumentVersion]) -> None:
    """Deterministic business validation before a revision is editable."""
    try:
        model = import_editor_model(content)
    except (DocumentPackageError, ValueError, TypeError) as exc:
        raise HTTPException(409, "FAILED_VALIDATION:DOCX_PACKAGE_INVALID") from exc
    text = "\n".join(str(node.get("text") or "") for node in model.get("nodes", []))
    if any(token.lower() in text.lower() for token in ("<tbd>", "[tbd]", "sample proposal", "xxx")):
        raise HTTPException(409, "GENERATION_REVIEW_REQUIRED:UNRESOLVED_PLACEHOLDER")
    proposal_ref = str(getattr(proposal, "opportunity_reference", ""))
    project_ref = str(getattr(proposal, "canonical_project_reference", "") or getattr(proposal, "provisional_reference", ""))
    if proposal_ref and any(value and value not in text for value in (proposal_ref, project_ref)):
        # The baseline may intentionally omit the reference; only reject a
        # clear cross-project leak from the known pilot template.
        if "454" in text and project_ref and project_ref != "454":
            raise HTTPException(409, "FAILED_VALIDATION:SOURCE_PROJECT_MISMATCH")


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
    if existing is not None:
        return existing
    template_path = Path(__file__).resolve().parents[1] / "fixtures" / "AMEC-P-D-2026-Q-454.docx"
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
        filename="AMEC-P-D-2026-Q-454.docx",
        mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        target=target, actor="proposal-template",
        correlation_id=f"proposal-template:{proposal.project_id}",
        idempotency_key=f"proposal-template:{proposal.project_id}",
        source_system="PROPOSAL_TEMPLATE_BASELINE",
        metadata={
            "template_baseline": True,
            "sensitivity_class": "INTERNAL",
            "source_presence_state": "PRESENT",
            "template_name": "AMEC Proposal V1 baseline",
        },
    )
    return stored.version


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
    baseline = _select_baseline_docx(selected_versions)
    if baseline is None:
        raise HTTPException(422, "VALID_DOCX_SOURCE_REQUIRED")
    baseline_bytes = _captured_bytes(baseline)
    try:
        import_editor_model(baseline_bytes)
    except (DocumentPackageError, ValueError, TypeError) as exc:
        raise HTTPException(422, "VALID_DOCX_SOURCE_REQUIRED") from exc

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
    if plan.get("baseline_document_version_id") != baseline.id:
        raise HTTPException(409, "PROPOSAL_AI_BASELINE_MISMATCH")
    baseline_model = import_editor_model(baseline_bytes)
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
    _validate_generated_docx(proposal, generated_bytes, selected_versions)

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
    snapshot = {
        "editor_model": import_editor_model(generated_bytes),
        "owner_base_model": generated_ai_model,
        "owner_mutations": [
            {"anchor": mutation.anchor, "expected_xml_hash": mutation.expected_xml_hash, "replacement": mutation.replacement}
            for mutation in owner_mutations
        ],
        "owner_edit_base_hash": digest(generated_ai_bytes),
        "baseline_hash": digest(generated_bytes), "working_hash": digest(generated_bytes),
        "source_set_hash": source_set_hash, "source_ids": [item.id for item in selected_versions],
        "editor_baseline_document_version_id": baseline.id,
        "editor_document_id": generated.document.id,
        "editor_document_version_id": generated.version.id,
        "change_plan": plan,
        "ai_provenance": {
            "generated_from_ai": True,
            "generation_mode": "SYNTHETIC_DETERMINISTIC" if synthetic_local else "GOVERNED_AZURE_OPENAI",
            "provenance_state": "RECORDED", "source_set_hash": source_set_hash,
            "evidence_refs": [item.id for item in selected_versions],
            "citations": intelligence.get("citations", []),
            "work_product_id": intelligence.get("work_product_id"),
            "context_snapshot_id": intelligence.get("context_snapshot_id"),
            "mutation_count": len(mutations),
            "owner_mutation_count": len(owner_mutations),
        },
    }
    revision = ProposalRevision(
        proposal_id=proposal.id, revision_number=latest_number + 1, status="DRAFT",
        change_summary={"created_from": "PROPOSAL_AI_GENERATION", "baseline_document_version_id": baseline.id, "mutation_count": len(mutations)},
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
            "mutation_count": len(mutations), "source_set_hash": source_set_hash,
            "generation_mode": snapshot["ai_provenance"]["generation_mode"],
        },
    }


def _select_baseline_docx(versions: list[DocumentVersion]) -> DocumentVersion:
    """Select exactly one recognized AMEC Proposal baseline."""
    candidates = [version for version in versions if (version.source_filename or "").lower().endswith(".docx")]
    recognized = [version for version in candidates if _is_recognized_baseline_docx(version)]
    if len(recognized) == 1:
        return recognized[0]
    if len(recognized) > 1:
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
    run = capture(db, number, actor="source-create-proposal")
    discovered = next((row for row in projects(db) if row["number"] == number), None)
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
    client_name = _source_client_name(project_name, number) if get_settings().source_intake_mode.upper() == "BRIDGE" else project_name
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
    # Only a recognized AMEC Proposal DOCX satisfies the baseline contract.
    # An unrelated single DOCX must still fall back to the governed Master
    # Content template instead of producing a false selection blocker.
    if not any(_is_recognized_baseline_docx(version) for version in selected_versions):
        selected_versions.append(_ensure_baseline_template(db, item))
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
        metadata = version.metadata_json or {}
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
    ai_generation = editor.get("ai_generation")
    if editor.get("editor_ready") and generated_for_hash != source_manifest_hash:
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
    source_set_hash = manifest["source_manifest_hash"]
    included_ids = {str(entry.get("document_version_id")) for entry in manifest["entries"] if entry.get("included") and entry.get("document_version_id")}
    selected_versions = [version for version in selected_versions if str(version.id) in included_ids]
    latest = db.scalar(select(ProposalRevision).where(ProposalRevision.proposal_id == proposal.id, ProposalRevision.status == "DRAFT").order_by(ProposalRevision.revision_number.desc()))
    if latest is None:
        editor = ensure_editor_revision(db, proposal, selected_versions, source_set_hash=source_set_hash, actor="source-regenerate-proposal")
    else:
        editor = {"editor_ready": True, "editor_revision_id": latest.id, "editor_revision_number": latest.revision_number, "editor_baseline_hash": (latest.snapshot or {}).get("baseline_hash")}
    provenance = ((latest.snapshot or {}).get("ai_provenance") or {}) if latest else {}
    if not editor.get("editor_ready"):
        db.commit()
        return {"result": "BLOCKED", "source_set_hash": source_set_hash, **editor}
    if not provenance.get("generated_from_ai") or provenance.get("source_set_hash") != source_set_hash:
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
