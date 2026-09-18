"""Option B document editor boundary.

The browser exchanges JSON editor models. DOCX parsing and export remain
server responsibilities, and export always starts from the uploaded original
package and applies anchored mutations.
"""
from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import tempfile

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy import select, true
from sqlalchemy.orm import Session
from ..api.dependencies import require_roles
from ..db import get_db
from ..models import Document, DocumentType, DocumentVersion, Opportunity, ProposalRevision, ProposalSourceDecision, ProposalSourceLink, ProposalStalenessEvent, Role
from ..storage import DocumentStorageService, StorageTarget, create_binary_store

from ..services.proposal_document_package import DocumentPackageError, apply_text_mutations, digest, package_parts
from ..services.proposal_editor_model import editor_diff_to_mutations, import_editor_model, tracked_changes
from ..services.proposal_source_workspace import LOGICAL_SOURCE_CATEGORIES, save_source_category, save_source_inclusion, source_manifest

router = APIRouter(prefix="/api/proposals-v1/editor", tags=["proposal-editor-option-b"])
MAX_UPLOAD = 64 * 1024 * 1024
editor_role = require_roles(Role.OWNER_SPONSOR, Role.PROCESS_CHAMPION, Role.RESPONSIBLE_ENGINEER, Role.SYSTEM_ADMIN)
source_curate_role = require_roles(Role.OWNER_SPONSOR, Role.PROCESS_CHAMPION, Role.SYSTEM_ADMIN)


async def _docx(file: UploadFile) -> bytes:
    data = await file.read(MAX_UPLOAD + 1)
    if len(data) > MAX_UPLOAD:
        raise HTTPException(413, "DOCX_PACKAGE_SIZE_LIMIT")
    try:
        package_parts(data)
    except DocumentPackageError as exc:
        raise HTTPException(422, str(exc)) from exc
    return data


def _model(raw: str) -> dict:
    try:
        value = json.loads(raw)
    except (TypeError, json.JSONDecodeError) as exc:
        raise HTTPException(422, "EDITOR_MODEL_JSON_REQUIRED") from exc
    if not isinstance(value, dict):
        raise HTTPException(422, "EDITOR_MODEL_OBJECT_REQUIRED")
    return value


@router.post("/import")
async def import_docx(file: UploadFile = File(...), _: Role = Depends(editor_role)):
    data = await _docx(file)
    return import_editor_model(data)


@router.post("/changes")
async def preview_changes(file: UploadFile = File(...), imported_model: str = Form(...), current_model: str = Form(...), _: Role = Depends(editor_role)):
    data = await _docx(file)
    imported, current = _model(imported_model), _model(current_model)
    # Re-import from bytes and compare the immutable node identity. A client
    # cannot forge an anchor map or precondition by posting JSON alone.
    server_model = import_editor_model(data)
    if server_model.get("nodes") != imported.get("nodes"):
        raise HTTPException(409, "EDITOR_IMPORT_MODEL_STALE")
    try:
        mutations = editor_diff_to_mutations(imported, current)
        changes = tracked_changes(imported, current)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    return {"changes": changes, "mutation_count": len(mutations), "export_path": "ORIGINAL_PACKAGE_TARGETED_MUTATIONS"}


@router.post("/export")
async def export_docx(file: UploadFile = File(...), imported_model: str = Form(...), current_model: str = Form(...), _: Role = Depends(editor_role)):
    data = await _docx(file)
    imported, current = _model(imported_model), _model(current_model)
    if import_editor_model(data).get("nodes") != imported.get("nodes"):
        raise HTTPException(409, "EDITOR_IMPORT_MODEL_STALE")
    try:
        mutations = editor_diff_to_mutations(imported, current)
        output = apply_text_mutations(data, mutations)
    except (ValueError, DocumentPackageError) as exc:
        raise HTTPException(409, str(exc)) from exc
    return StreamingResponse(io.BytesIO(output), media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", headers={"Content-Disposition": 'attachment; filename="proposal-edited.docx"', "X-Proposal-Export-Path": "ORIGINAL_PACKAGE_TARGETED_MUTATIONS"})


@router.post("/preview")
async def true_render_preview(file: UploadFile = File(...), imported_model: str = Form(...), current_model: str = Form(...), _: Role = Depends(editor_role)):
    """Render the actual mutated package with the host Office pipeline."""
    data = await _docx(file)
    imported, current = _model(imported_model), _model(current_model)
    if import_editor_model(data).get("nodes") != imported.get("nodes"):
        raise HTTPException(409, "EDITOR_IMPORT_MODEL_STALE")
    try:
        output = apply_text_mutations(data, editor_diff_to_mutations(imported, current))
    except (ValueError, DocumentPackageError) as exc:
        raise HTTPException(409, str(exc)) from exc
    office = shutil.which("soffice") or shutil.which("libreoffice")
    if not office:
        raise HTTPException(503, "TRUE_RENDER_PIPELINE_UNAVAILABLE")
    with tempfile.TemporaryDirectory(prefix="proposal-preview-") as directory:
        source = os.path.join(directory, "proposal.docx")
        with open(source, "wb") as handle:
            handle.write(output)
        try:
            subprocess.run([office, "--headless", "--convert-to", "pdf", "--outdir", directory, source], check=True, timeout=45, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except (OSError, subprocess.SubprocessError) as exc:
            raise HTTPException(503, "TRUE_RENDER_FAILED") from exc
        pdf = os.path.join(directory, "proposal.pdf")
        if not os.path.isfile(pdf):
            raise HTTPException(503, "TRUE_RENDER_OUTPUT_MISSING")
        with open(pdf, "rb") as handle:
            rendered = handle.read()
    return StreamingResponse(io.BytesIO(rendered), media_type="application/pdf", headers={"Content-Disposition": 'inline; filename="proposal-preview.pdf"', "X-Proposal-Render": "TRUE_DOCX_TO_PDF"})


def _canonical_revision(proposal_id: str, revision_id: str, db: Session) -> tuple[Opportunity, ProposalRevision]:
    proposal = db.get(Opportunity, proposal_id)
    revision = db.scalar(select(ProposalRevision).where(ProposalRevision.id == revision_id, ProposalRevision.proposal_id == proposal_id))
    if not proposal or not revision:
        raise HTTPException(404, "PROPOSAL_REVISION_NOT_FOUND")
    if revision.status != "DRAFT":
        raise HTTPException(409, "PROPOSAL_REVISION_IMMUTABLE")
    return proposal, revision


@router.get("/proposals/{proposal_id}/entry")
def canonical_editor_entry(proposal_id: str, db: Session = Depends(get_db), _: Role = Depends(editor_role)):
    """Resolve every Proposal V1 entry point to its canonical DOCX revision."""
    proposal = db.get(Opportunity, proposal_id)
    if proposal is None:
        raise HTTPException(404, "PROPOSAL_NOT_FOUND")
    workspace = (proposal.proposal_fields_json or {}).get("source_workspace")
    if not isinstance(workspace, dict):
        # This endpoint deliberately does not hijack legacy Proposal routes.
        raise HTTPException(404, "PROPOSAL_V1_EDITOR_ENTRY_NOT_FOUND")
    generation_state = str((proposal.proposal_fields_json or {}).get("generation_state") or "READY_FOR_EDIT")
    revision = db.scalar(select(ProposalRevision).where(ProposalRevision.proposal_id == proposal.id, ProposalRevision.status == "DRAFT").order_by(ProposalRevision.revision_number.desc()))
    blocked_states = {
        "PENDING_OWNER_SOURCES", "GENERATION_PENDING", "RUNNING", "FAILED_RETRYABLE",
        "BLOCKED_BASELINE", "STALE_SOURCE_MANIFEST", "GENERATION_REVIEW_REQUIRED",
        "FAILED_VALIDATION",
    }
    if generation_state in blocked_states:
        return {"proposal_id": proposal.id, "revision_id": None, "revision_number": None, "project_number": workspace.get("project_number"), "source_project_identity": workspace.get("source_project_identity"), "generation_state": generation_state, "editor_mode": "PROGRESS" if generation_state in {"PENDING_OWNER_SOURCES", "GENERATION_PENDING", "RUNNING"} else "RECOVERY", "editable": False, "retry_allowed": generation_state in {"FAILED_RETRYABLE", "GENERATION_REVIEW_REQUIRED"}, "blocker": (proposal.proposal_fields_json or {}).get("generation_error"), "route": f"/proposals/{proposal.id}/editor"}
    if revision is None:
        raise HTTPException(409, "PROPOSAL_V1_EDITOR_REVISION_REQUIRED")
    return {
        "proposal_id": proposal.id,
        "revision_id": revision.id,
        "revision_number": revision.revision_number,
        "generation_state": generation_state,
        "editor_mode": "EDIT" if generation_state == "READY_FOR_EDIT" else "BASELINE_REVIEW",
        "editable": generation_state == "READY_FOR_EDIT",
        "retry_allowed": False,
        "project_number": workspace.get("project_number"),
        "route": f"/proposals/{proposal.id}/editor",
    }


@router.get("/proposals/{proposal_id}/sources")
def active_proposal_sources(proposal_id: str, db: Session = Depends(get_db), _: Role = Depends(editor_role)):
    """Return the active, citation-addressable source set inside a Proposal."""
    proposal = db.get(Opportunity, proposal_id)
    if proposal is None:
        raise HTTPException(404, "PROPOSAL_NOT_FOUND")
    workspace = (proposal.proposal_fields_json or {}).get("source_workspace") or {}
    number = workspace.get("project_number")
    decision_rows = {row.logical_source_identity: row for row in db.scalars(select(ProposalSourceDecision).where(ProposalSourceDecision.source_project_identity == workspace.get("source_project_identity"))).all()} if workspace.get("source_project_identity") else {}
    rows = db.scalars(
        select(ProposalSourceLink)
        .where(ProposalSourceLink.proposal_id == proposal_id, ProposalSourceLink.active == true())
        .order_by(ProposalSourceLink.created_at, ProposalSourceLink.id)
    ).all()
    sources = []
    for link in rows:
        version = db.get(DocumentVersion, link.document_version_id)
        if version is None:
            continue
        metadata = version.metadata_json or {}
        decision = decision_rows.get(str(metadata.get("proposal_source_key") or metadata.get("source_relative_path") or ""))
        path = metadata.get("source_relative_path")
        source_number = metadata.get("source_project_number", number)
        file_id = __import__("hashlib").sha256(path.encode()).hexdigest()[:24] if path and source_number else None
        sources.append({
            "link_id": link.id,
            "document_version_id": version.id,
            "filename": version.source_filename,
            "source_role": link.source_role,
            "logical_category": decision.logical_category if decision and decision.logical_category else metadata.get("logical_category"),
            "included_in_proposal": decision.included_in_proposal if decision else metadata.get("included_in_proposal", True),
            "sha256": version.sha256,
            "source_path": path,
            "view_route": f"/api/proposals/sources/2026/projects/{source_number}/files/{file_id}/content" if file_id else (f"/api/bd/proposals/{proposal_id}/sources/{link.source_evidence_id}/content" if link.source_evidence_id else None),
            "download_route": f"/api/proposals/sources/2026/projects/{source_number}/files/{file_id}/download" if file_id else (f"/api/bd/proposals/{proposal_id}/sources/{link.source_evidence_id}/content" if link.source_evidence_id else None),
        })
    return {"proposal_id": proposal_id, "source_manifest_hash": workspace.get("source_manifest_hash"), "sources": sources}


def _active_source_link(proposal_id: str, link_id: str, db: Session) -> tuple[Opportunity, ProposalSourceLink, DocumentVersion]:
    proposal = db.get(Opportunity, proposal_id)
    link = db.scalar(select(ProposalSourceLink).where(ProposalSourceLink.id == link_id, ProposalSourceLink.proposal_id == proposal_id, ProposalSourceLink.active == true()))
    version = db.get(DocumentVersion, link.document_version_id) if link else None
    if proposal is None or link is None or version is None:
        raise HTTPException(404, "PROPOSAL_SOURCE_NOT_FOUND")
    return proposal, link, version


@router.patch("/proposals/{proposal_id}/sources/{link_id}/category")
def update_active_source_category(proposal_id: str, link_id: str, payload: dict[str, str], db: Session = Depends(get_db), _: Role = Depends(source_curate_role)):
    proposal, link, version = _active_source_link(proposal_id, link_id, db)
    category = str(payload.get("logical_category") or "").upper()
    if category not in LOGICAL_SOURCE_CATEGORIES:
        raise HTTPException(422, "SOURCE_CATEGORY_INVALID")
    workspace = (proposal.proposal_fields_json or {}).get("source_workspace") or {}
    metadata = save_source_category(version, category, actor="proposal-editor", db=db, source_project_identity=workspace.get("source_project_identity"))
    proposal.proposal_fields_json = {**(proposal.proposal_fields_json or {}), "generation_state": "STALE_SOURCE_MANIFEST", "source_changes_available": True}
    db.add(ProposalStalenessEvent(proposal_id=proposal.id, trigger_type="ACTIVE_SOURCE", trigger_reference=version.id, reason_code="SOURCE_MANIFEST_CHANGED", impacted_sections=["CATEGORY_CHANGED"], detected_by="proposal-editor"))
    db.commit()
    return {"proposal_id": proposal_id, "link_id": link_id, "logical_category": metadata["logical_category"], "generation_state": "STALE_SOURCE_MANIFEST"}


@router.patch("/proposals/{proposal_id}/sources/{link_id}/inclusion")
def update_active_source_inclusion(proposal_id: str, link_id: str, payload: dict[str, bool], db: Session = Depends(get_db), _: Role = Depends(source_curate_role)):
    proposal, link, version = _active_source_link(proposal_id, link_id, db)
    workspace = (proposal.proposal_fields_json or {}).get("source_workspace") or {}
    metadata = save_source_inclusion(version, bool(payload.get("included_in_proposal", True)), actor="proposal-editor", db=db, source_project_identity=workspace.get("source_project_identity"))
    proposal.proposal_fields_json = {**(proposal.proposal_fields_json or {}), "generation_state": "STALE_SOURCE_MANIFEST", "source_changes_available": True}
    db.add(ProposalStalenessEvent(proposal_id=proposal.id, trigger_type="ACTIVE_SOURCE", trigger_reference=version.id, reason_code="SOURCE_MANIFEST_CHANGED", impacted_sections=["INCLUSION_CHANGED"], detected_by="proposal-editor"))
    db.commit()
    return {"proposal_id": proposal_id, "link_id": link_id, "included_in_proposal": metadata["included_in_proposal"], "generation_state": "STALE_SOURCE_MANIFEST"}


@router.get("/proposals/{proposal_id}/revisions/{revision_id}/mutations/{anchor}/evidence")
def mutation_evidence(proposal_id: str, revision_id: str, anchor: str, db: Session = Depends(get_db), _: Role = Depends(editor_role)):
    """Resolve an anchored AI mutation to its exact frozen source citations."""
    proposal, revision = _canonical_revision(proposal_id, revision_id, db)
    plan = (revision.snapshot or {}).get("change_plan") or {}
    mutation = next((item for item in (plan.get("mutations") or []) if item.get("anchor") == anchor), None)
    if mutation is None:
        raise HTTPException(404, "PROPOSAL_MUTATION_NOT_FOUND")
    workspace = (proposal.proposal_fields_json or {}).get("source_workspace") or {}
    entries = {str(item.get("document_version_id")): item for item in (workspace.get("source_manifest") or {}).get("entries", []) if item.get("document_version_id")}
    citations = []
    for key in mutation.get("citation_keys") or []:
        citation = next((item for item in (revision.snapshot.get("ai_provenance", {}).get("citations") or []) if (item.get("locator_json", {}).get("citation_key") or item.get("citation_key")) == key), None)
        if citation is None:
            continue
        version_id = citation.get("source_id") or citation.get("source_version_or_hash")
        entry = entries.get(str(version_id), {})
        citations.append({"citation_key": key, "document_version_id": version_id, "sha256": citation.get("source_version_or_hash"), "source_path": entry.get("source_path"), "filename": entry.get("filename"), "logical_category": entry.get("effective_category"), "locator": citation.get("locator_json") or citation.get("locator")})
    return {"proposal_id": proposal_id, "revision_id": revision_id, "mutation": mutation, "citations": citations}


@router.get("/proposals/{proposal_id}/revisions/{revision_id}")
def load_canonical_editor_revision(proposal_id: str, revision_id: str, db: Session = Depends(get_db), _: Role = Depends(editor_role)):
    """Load the server-owned editor state by canonical Proposal identity."""
    _, revision = _canonical_revision(proposal_id, revision_id, db)
    snapshot = revision.snapshot or {}
    return {"proposal_id": proposal_id, "revision_id": revision.id, "revision_number": revision.revision_number, "status": revision.status, "editor_model": snapshot.get("editor_model"), "baseline_hash": snapshot.get("baseline_hash"), "working_hash": snapshot.get("working_hash"), "source_set_hash": snapshot.get("source_set_hash"), "change_plan": snapshot.get("change_plan", {}), "ai_provenance": snapshot.get("ai_provenance", {})}


@router.get("/proposals/{proposal_id}/revisions/{revision_id}/document")
def download_canonical_editor_document(proposal_id: str, revision_id: str, db: Session = Depends(get_db), _: Role = Depends(editor_role)):
    """Return the exact DOCX package represented by a working revision.

    The browser receives bytes only through this verified server-owned path;
    it never needs to infer a source path or persist a DOCX itself.
    """
    _, revision = _canonical_revision(proposal_id, revision_id, db)
    snapshot = revision.snapshot or {}
    version_id = snapshot.get("editor_document_version_id") or snapshot.get("editor_baseline_document_version_id")
    version = db.get(DocumentVersion, version_id) if version_id else None
    if version is None:
        raise HTTPException(404, "PROPOSAL_REVISION_DOCUMENT_NOT_FOUND")
    try:
        if version.source_path_or_reference.startswith("storage://"):
            with DocumentStorageService(create_binary_store()).read_verified(version) as stream:
                content = stream.read()
        elif version.synthetic_content is not None:
            content = version.synthetic_content
        else:
            raise HTTPException(404, "PROPOSAL_REVISION_DOCUMENT_NOT_FOUND")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(503, "PROPOSAL_REVISION_DOCUMENT_READ_FAILED") from exc
    if digest(content) != version.sha256:
        raise HTTPException(503, "PROPOSAL_REVISION_DOCUMENT_INTEGRITY_DRIFT")
    return StreamingResponse(
        io.BytesIO(content),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": 'inline; filename="proposal-revision.docx"',
            "X-Proposal-Document-SHA256": digest(content),
        },
    )


@router.post("/proposals/{proposal_id}/revisions/{revision_id}/save")
async def save_canonical_editor_revision(
    proposal_id: str,
    revision_id: str,
    request: Request,
    file: UploadFile = File(...),
    imported_model: str = Form(...),
    current_model: str = Form(...),
    change_plan: str = Form(default="{}"),
    evidence_refs: str = Form(default="[]"),
    db: Session = Depends(get_db),
    role: Role = Depends(editor_role),
):
    """Persist a bounded Option B edit against one canonical working revision."""
    proposal, revision = _canonical_revision(proposal_id, revision_id, db)
    data = await _docx(file)
    imported, current = _model(imported_model), _model(current_model)
    server_model = import_editor_model(data)
    if server_model.get("nodes") != imported.get("nodes"):
        raise HTTPException(409, "EDITOR_IMPORT_MODEL_STALE")
    try:
        mutations = editor_diff_to_mutations(imported, current)
        plan = json.loads(change_plan or "{}")
        refs = json.loads(evidence_refs or "[]")
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        raise HTTPException(422, "EDITOR_CHANGE_PLAN_OR_EVIDENCE_INVALID") from exc
    if not isinstance(plan, dict) or not isinstance(refs, list):
        raise HTTPException(422, "EDITOR_CHANGE_PLAN_OR_EVIDENCE_INVALID")
    output = apply_text_mutations(data, mutations)
    baseline_hash, working_hash = digest(data), digest(output)
    prior = revision.snapshot or {}
    # Keep a cumulative, anchored edit set relative to the generated revision
    # that the Owner first opened.  A later save receives the already edited
    # DOCX, so diffing only against that file would lose earlier edits when a
    # source regeneration creates a new AI revision.
    owner_base_model = prior.get("owner_base_model") or prior.get("editor_model") or imported
    try:
        owner_mutations = editor_diff_to_mutations(owner_base_model, current)
    except (ValueError, TypeError) as exc:
        raise HTTPException(409, "EDITOR_OWNER_EDIT_REBASE_REQUIRED") from exc
    serialized_owner_mutations = [
        {"anchor": mutation.anchor, "expected_xml_hash": mutation.expected_xml_hash, "replacement": mutation.replacement}
        for mutation in owner_mutations
    ]
    source_ids = prior.get("source_ids", [])
    source_set_hash = prior.get("source_set_hash") or digest(json.dumps(source_ids, sort_keys=True, separators=(",", ":")).encode())
    document_id = prior.get("editor_document_id")
    document = db.get(Document, document_id) if document_id else None
    if not document:
        document = Document(project_id=proposal.project_id, document_type=DocumentType.OTHER, logical_name=f"{proposal.opportunity_reference}:proposal-editor", language="EN", source_system="PROPOSAL_EDITOR")
        db.add(document)
        db.flush()
    store = create_binary_store()
    target = StorageTarget(store.provider_id, getattr(getattr(store, "config", None), "container", None) or getattr(getattr(store, "config", None), "share", "synthetic"), f"proposal-editors/{proposal_id}/{revision_id}")
    stored = DocumentStorageService(store).store_version(db, document=document, content=output, filename="proposal-edited.docx", mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", target=target, actor=getattr(role, "value", str(role)), correlation_id=getattr(request.state, "correlation_id", f"proposal-editor:{revision_id}"), idempotency_key=f"proposal-editor:{revision_id}:{working_hash}", source_system="PROPOSAL_EDITOR", metadata={"proposal_id": proposal_id, "revision_id": revision_id, "baseline_hash": baseline_hash, "source_set_hash": source_set_hash, "change_plan": plan, "evidence_refs": refs})
    revision.snapshot = {
        **prior,
        "editor_model": current,
        "owner_base_model": owner_base_model,
        "owner_mutations": serialized_owner_mutations,
        "owner_edit_base_hash": prior.get("owner_edit_base_hash") or prior.get("working_hash") or baseline_hash,
        "baseline_hash": baseline_hash,
        "working_hash": working_hash,
        "source_set_hash": source_set_hash,
        "editor_document_id": document.id,
        "editor_document_version_id": stored.version.id,
        "change_plan": plan,
        "ai_provenance": {"evidence_refs": refs, "mutation_count": len(mutations), "owner_mutation_count": len(owner_mutations), "provenance_state": "RECORDED"},
    }
    revision.content_hash = digest(json.dumps(revision.snapshot, sort_keys=True, separators=(",", ":")).encode())
    revision.change_summary = {**(revision.change_summary or {}), "editor_saved": True, "mutation_count": len(mutations), "working_hash": working_hash}
    db.commit()
    return {"result": "SAVED", "proposal_id": proposal_id, "revision_id": revision.id, "content_hash": revision.content_hash, "baseline_hash": baseline_hash, "working_hash": working_hash, "source_set_hash": source_set_hash, "document_version_id": stored.version.id, "tracked_changes": tracked_changes(imported, current), "change_plan": plan, "ai_provenance": revision.snapshot["ai_provenance"]}
