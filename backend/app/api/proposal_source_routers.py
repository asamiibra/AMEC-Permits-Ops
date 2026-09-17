"""Authenticated Proposal source workspace routes."""
from __future__ import annotations

import hashlib
import io
import json
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..api.dependencies import AuthenticatedPrincipal, authenticated_principal_context, require_roles
from ..db import get_db
from ..models import ClientAccount, Document, DocumentType, DocumentVersion, ProposalRevision, ProposalSourceEvidence, ProposalSourceLink, Project, Role
from ..services.proposal_source_workspace import LOGICAL_ROOT, captured_version, capture, configured_source_root, ensure_editor_revision, projects, tree
from ..config.settings import get_settings
from ..storage import DocumentStorageService, StorageTarget, create_binary_store
from ..services.proposal_document_package import DocumentPackageError, TextMutation, apply_text_mutations, digest
from ..services.proposal_editor_model import import_editor_model
from ..services.proposal_intelligence import ProposalDeterministicProvider, execute_proposal_intelligence
from .bd_proposal_routers import ProposalCreate, _create_proposal_record

router = APIRouter(prefix="/api/proposals/sources", tags=["proposal-source-workspace"])
source_role = require_roles(Role.OWNER_SPONSOR, Role.PROCESS_CHAMPION, Role.RESPONSIBLE_ENGINEER, Role.SYSTEM_ADMIN)
create_role = require_roles(Role.OWNER_SPONSOR, Role.PROCESS_CHAMPION, Role.SYSTEM_ADMIN)


class SourceProposalCreatePayload(BaseModel):
    """Owner choices applied when promoting a synced source project."""

    excluded_source_paths: list[str] = Field(default_factory=list)
    source_categories: dict[str, str] = Field(default_factory=dict)


LOGICAL_SOURCE_CATEGORIES = {
    "TENDER_DOCUMENTS",
    "PHOTOS_IMAGES",
    "EMAIL",
    "CLIENT_DATA",
    "CLIENT_DOCUMENTS",
    "PROJECT_INFORMATION",
    "OTHER_UNCLASSIFIED",
}


def _entry(number: int, file_id: str, db: Session) -> dict[str, Any]:
    expected = str(file_id).lower()
    for item in tree(number, db)["entries"]:
        if not item["is_directory"] and hashlib.sha256(item["path"].encode()).hexdigest()[:24] == expected:
            return item
    raise HTTPException(404, "SOURCE_FILE_NOT_FOUND")


@router.get("/2026/projects")
def source_projects(_: Role = Depends(source_role), db: Session = Depends(get_db)):
    settings = get_settings()
    return {"logical_root": "Tenders/1- Proposal/2026", "physical_root_configured": settings.source_intake_mode.upper() != "BRIDGE" and configured_source_root().is_absolute(), "projects": projects(db)}


@router.get("/2026/projects/{number}/tree")
def source_tree(number: int, _: Role = Depends(source_role), db: Session = Depends(get_db)):
    try:
        return tree(number, db)
    except (FileNotFoundError, OSError) as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get("/2026/projects/{number}/files/{file_id}")
def source_file(number: int, file_id: str, _: Role = Depends(source_role), db: Session = Depends(get_db)):
    item = _entry(number, file_id, db)
    version = captured_version(db, number, item["path"])
    return {**item, "captured": bool(version), "source_content_hash": version.sha256 if version else None, "source_version": version.version_number if version else None, "source_presence_state": (version.metadata_json or {}).get("source_presence_state", "NOT_CAPTURED") if version else "NOT_CAPTURED"}


def _content(number: int, file_id: str, db: Session) -> tuple[dict[str, Any], bytes]:
    item = _entry(number, file_id, db)
    version = captured_version(db, number, item["path"])
    if not version:
        result = capture(db, number, actor="source-view")
        version = captured_version(db, number, item["path"])
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
def sync_sources(_: Role = Depends(source_role), db: Session = Depends(get_db)):
    try:
        discovered = projects(db)
        runs = [capture(db, row["number"], actor="source-sync") for row in discovered]
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
    baseline = next((version for version in selected_versions if (version.source_filename or "").lower().endswith(".docx")), None)
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
            idempotency_key=f"proposal-document-generation:{proposal.id}:{seeded_editor.get('editor_revision_id') or uuid4()}",
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
    raw_mutations = plan.get("mutations") or []
    try:
        mutations = [TextMutation(str(item["anchor"]), str(item["expected_xml_hash"]), str(item["replacement"])) for item in raw_mutations]
        generated_bytes = apply_text_mutations(baseline_bytes, mutations)
    except (KeyError, TypeError, ValueError, DocumentPackageError) as exc:
        raise HTTPException(409, "PROPOSAL_AI_CHANGE_PLAN_INVALID") from exc

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
    prior = db.get(ProposalRevision, seeded_editor.get("editor_revision_id")) if seeded_editor.get("editor_revision_id") else None
    if prior is not None and prior.status == "DRAFT":
        prior.status = "SUPERSEDED"
        from datetime import datetime, timezone
        prior.superseded_at = datetime.now(timezone.utc)
    latest_number = db.scalar(select(ProposalRevision.revision_number).where(ProposalRevision.proposal_id == proposal.id).order_by(ProposalRevision.revision_number.desc())) or 0
    snapshot = {
        "editor_model": import_editor_model(generated_bytes),
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
    # Bridge captures are attached to the canonical Project row so downstream
    # intake, provenance, and editor records share one project identity.  The
    # mounted synthetic fixture keeps its historical provisional behavior.
    project = db.scalar(select(Project).where(Project.project_number == str(number))) if get_settings().source_intake_mode.upper() == "BRIDGE" else None
    project_name = (project.project_name if project else f"Project {number}").strip()
    client_name = project_name.split(" - ", 1)[1].strip() if " - " in project_name else project_name
    # In the live bridge path, use an exact active canonical ClientAccount when
    # the project folder name proves it.  The downstream production guard still
    # rejects ambiguous or missing mappings; no synthetic client is created.
    client_id = None
    if project is not None:
        active_clients = db.scalars(select(ClientAccount).where(ClientAccount.status == "ACTIVE")).all()
        matches = [client.id for client in active_clients if client.display_name and client.display_name.strip().casefold() == client_name.casefold()]
        if len(matches) == 1:
            client_id = matches[0]
    item = _create_proposal_record(ProposalCreate(proposal_description=f"{client_name} Proposal", project_reference=str(number), project_id=project.id if project else None, client_account_id=client_id, client_name=client_name, idempotency_key=f"proposal-source-project:{number}"), request, db, role)
    # The source adapter is synthetic-only in TEST/DEV/Azure pre-production.
    # Mark the Proposal projection accordingly so the shared AI context
    # compiler can prove that the entity and its captured evidence belong to
    # the same non-business fixture boundary. Production/live captures stay
    # NON_SYNTHETIC and remain fail-closed until governed data is configured.
    if get_settings().synthetic_only:
        item.fixture_classification = "SYNTHETIC_OWNER_TEST"
    versions = db.scalars(select(DocumentVersion).where(DocumentVersion.metadata_json["source_project_number"].as_integer() == number).order_by(DocumentVersion.ingested_at)).all()
    excluded_paths = {path.strip() for path in (payload.excluded_source_paths if payload else []) if path and path.strip()}
    requested_categories = payload.source_categories if payload else {}
    invalid_categories = sorted({value for value in requested_categories.values() if value not in LOGICAL_SOURCE_CATEGORIES})
    if invalid_categories:
        raise HTTPException(422, {"code": "SOURCE_CATEGORY_INVALID", "allowed": sorted(LOGICAL_SOURCE_CATEGORIES), "values": invalid_categories})
    selected_versions = [
        version for version in versions
        if (version.metadata_json or {}).get("source_relative_path") not in excluded_paths
    ]
    # Promotion is idempotent. If an Owner repeats it after excluding a file,
    # deactivate the existing Proposal link while leaving the immutable
    # captured source and Synology untouched.
    if excluded_paths:
        for link in db.scalars(select(ProposalSourceLink).where(ProposalSourceLink.proposal_id == item.id, ProposalSourceLink.source_role == "SOURCE_WORKSPACE", ProposalSourceLink.active == True)):  # noqa: E712
            linked_version = next((version for version in versions if version.id == link.document_version_id), None)
            if linked_version and (linked_version.metadata_json or {}).get("source_relative_path") in excluded_paths:
                link.active = False
    hashes: list[str] = []
    for version in selected_versions:
        hashes.append(version.sha256)
        evidence = db.scalar(select(ProposalSourceEvidence).where(ProposalSourceEvidence.proposal_id == item.id, ProposalSourceEvidence.source_type == "SYNOLOGY_FILE", ProposalSourceEvidence.content_hash == version.sha256))
        if not evidence:
            relative_path = (version.metadata_json or {}).get("source_relative_path")
            logical_category = requested_categories.get(relative_path, "OTHER_UNCLASSIFIED")
            evidence = ProposalSourceEvidence(proposal_id=item.id, source_type="SYNOLOGY_FILE", source_filename=version.source_filename, source_reference=version.source_path_or_reference, content_hash=version.sha256, content_type=version.mime_type, provenance={"kind": "synology_source_workspace", "relative_path": relative_path, "logical_category": logical_category, "document_version_id": version.id, "verification": "READ_BACK_VERIFIED"}, status="CURRENT", verification_state="READ_BACK_VERIFIED", created_by="source-create-proposal")
            db.add(evidence)
            db.flush()
        linked = db.scalar(select(ProposalSourceLink).where(ProposalSourceLink.proposal_id == item.id, ProposalSourceLink.document_version_id == version.id, ProposalSourceLink.source_role == "SOURCE_WORKSPACE"))
        if not linked:
            db.add(ProposalSourceLink(proposal_id=item.id, source_evidence_id=evidence.id, document_id=version.document_id, document_version_id=version.id, source_role="SOURCE_WORKSPACE", added_by="source-create-proposal"))
        elif not linked.active:
            linked.active = True
            linked.source_evidence_id = evidence.id
            linked.added_by = "source-create-proposal"
    source_set_hash = hashlib.sha256("".join(sorted(hashes)).encode()).hexdigest()
    item.proposal_fields_json = {**(item.proposal_fields_json or {}), "source_workspace": {"logical_root": LOGICAL_ROOT, "project_number": number, "source_set_hash": source_set_hash, "captured_count": run["captured_count"], "selected_count": len(selected_versions), "excluded_source_paths": sorted(excluded_paths), "source_categories": {key: requested_categories[key] for key in sorted(requested_categories) if key not in excluded_paths}}}
    editor = ensure_editor_revision(db, item, selected_versions, source_set_hash=source_set_hash, actor="source-create-proposal")
    # Promotion is the single causal handoff into Proposal Intelligence.  The
    # generated revision is published before the browser is allowed to open
    # the editor, so the Owner always starts from the source-grounded DOCX.
    latest_revision = db.get(ProposalRevision, editor.get("editor_revision_id")) if editor.get("editor_revision_id") else None
    latest_provenance = ((latest_revision.snapshot or {}).get("ai_provenance") or {}) if latest_revision else {}
    generated_for_hash = latest_provenance.get("source_set_hash") if latest_provenance.get("generated_from_ai") else None
    if editor.get("editor_ready") and generated_for_hash != source_set_hash:
        editor = _generate_proposal_revision(
            request=request, db=db, proposal=item, selected_versions=selected_versions,
            source_set_hash=source_set_hash, seeded_editor=editor, role=role,
        )
    db.commit()
    return {"result": "CREATED", "proposal_id": item.id, "proposal_reference": item.opportunity_reference, "source_set_hash": source_set_hash, "source_count": len(selected_versions), "excluded_source_count": len(excluded_paths), "capture": run, **editor}


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
    links = db.scalars(select(ProposalSourceLink).where(ProposalSourceLink.proposal_id == proposal.id, ProposalSourceLink.active == True).order_by(ProposalSourceLink.created_at, ProposalSourceLink.id)).all()  # noqa: E712
    selected_versions = [version for link in links if (version := db.get(DocumentVersion, link.document_version_id)) is not None]
    if not selected_versions:
        raise HTTPException(422, "PROPOSAL_SOURCE_SET_EMPTY")
    source_set_hash = hashlib.sha256("".join(sorted(version.sha256 for version in selected_versions)).encode()).hexdigest()
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
        editor = _generate_proposal_revision(request=request, db=db, proposal=proposal, selected_versions=selected_versions, source_set_hash=source_set_hash, seeded_editor=editor, role=role)
    db.commit()
    return {"result": "REGENERATED", "proposal_id": proposal.id, "source_set_hash": source_set_hash, "source_count": len(selected_versions), **editor}
