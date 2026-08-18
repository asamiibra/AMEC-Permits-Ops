"""Project-scoped ProposalOps intake and synthetic SOR contract."""

from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path
from typing import Any
from uuid import uuid4
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit.service import audit
from ..config.settings import get_settings, repo_root
from ..models import Document, DocumentApprovalState, DocumentType, DocumentVersion, EvidenceArtifact, LineageEdge, Opportunity, Project, ProjectArtifactRecord, ProposalIntakeArtifact, SynologyProjectBootstrap
from ..storage.fixture_exclusion import ensure_fixture_path_allowed
from ..storage.legacy import legacy_synthetic_adapter


SOR_TEMPLATE_VERSION = "SYN-AMEC-PROJECT-FOLDERS-1.0"
SEMANTIC_FOLDER_CONFIG: dict[str, dict[str, str]] = {
    # These labels are resolved from the existing canonical AMEC synthetic
    # project template, not typed into an upload form.
    "CLIENT_SOURCE": {"folder": "01_Client", "label": "Client source"},
    "PROPOSAL_SOURCE": {"folder": "03_Design", "label": "Proposal source"},
    "CONTRACT_SOURCE": {"folder": "04_Permits", "label": "Contract source"},
    "PERMIT_SOURCE": {"folder": "04_Permits", "label": "Permit initiation source"},
    "OPPORTUNITY_SOURCE": {"folder": "05_Correspondence", "label": "Opportunity source"},
    # These mappings are the canonical promotion policy.  Promotion resolves
    # the semantic class through this configuration; it never guesses a
    # physical folder name from the provisional intake path.
    "TENDER_EMAIL_SOURCE": {"folder": "05_Correspondence", "label": "Tender Email source"},
    "TENDER_DOCUMENT_SOURCE": {"folder": "03_Design", "label": "Tender Document source"},
    "TENDER_IMAGE_SOURCE": {"folder": "03_Design", "label": "Tender Image source"},
}
EXPECTED_PROJECT_FOLDERS = ["01_Client", "02_Property", "03_Design", "04_Permits", "05_Correspondence"]
ACTION_CONFIG: dict[str, dict[str, str]] = {
    "CLIENT_LIST": {"artifact_type": "CLIENT_LIST", "semantic_class": "CLIENT_SOURCE"},
    "PROPOSAL_FORM": {"artifact_type": "PROPOSAL_FORM", "semantic_class": "PROPOSAL_SOURCE"},
    "CONTRACT_FORM": {"artifact_type": "CONTRACT_FORM", "semantic_class": "CONTRACT_SOURCE"},
    "PERMIT_INITIATION": {"artifact_type": "PERMIT_INITIATION_SOURCE", "semantic_class": "PERMIT_SOURCE"},
    "NEW_PROPOSAL": {"artifact_type": "OPPORTUNITY_SOURCE", "semantic_class": "OPPORTUNITY_SOURCE"},
    "TENDER_EMAIL": {"artifact_type": "TENDER_EMAIL_SOURCE", "semantic_class": "TENDER_EMAIL_SOURCE"},
    "TENDER_DOCUMENT": {"artifact_type": "TENDER_DOCUMENT_SOURCE", "semantic_class": "TENDER_DOCUMENT_SOURCE"},
    "TENDER_IMAGE": {"artifact_type": "TENDER_IMAGE_SOURCE", "semantic_class": "TENDER_IMAGE_SOURCE"},
    "CLIENT_INFORMATION": {"artifact_type": "CLIENT_SOURCE", "semantic_class": "CLIENT_SOURCE"},
}

INTAKE_SEMANTIC_CONFIG: dict[str, dict[str, str]] = {
    "OPPORTUNITY_SOURCE": {"folder": "00_Proposal_Intake", "label": "New Proposal intake source"},
    "TENDER_EMAIL_SOURCE": {"folder": "01_Tender_Email", "label": "Tender Email source"},
    "TENDER_DOCUMENT_SOURCE": {"folder": "02_Tender_Documents", "label": "Tender Document source"},
    "TENDER_IMAGE_SOURCE": {"folder": "03_Tender_Images", "label": "Tender Photo / Image source"},
    "CLIENT_SOURCE": {"folder": "04_Client_Information", "label": "Client Information source"},
    "PROPOSAL_SOURCE": {"folder": "05_Proposal_Forms", "label": "Proposal Form source"},
}
PROMOTION_POLICY = "COPY_VERIFY_AND_ARCHIVE_SOURCE"
PROMOTABLE_INTAKE_CLASSES = {
    "TENDER_EMAIL_SOURCE",
    "TENDER_DOCUMENT_SOURCE",
    "TENDER_IMAGE_SOURCE",
    "CLIENT_SOURCE",
    "PROPOSAL_SOURCE",
}


def _safe_filename(filename: str) -> str:
    name = Path(filename or "source.bin").name
    name = re.sub(r"[^A-Za-z0-9._ -]", "_", name).strip(" .")
    if not name:
        raise HTTPException(422, "SOURCE_FILENAME_REQUIRED")
    return name[:280]


def _adapter():
    return legacy_synthetic_adapter()


def _reject_serverless_sor_write() -> None:
    """Keep the temporary Vercel runtime from treating its filesystem as SOR."""
    settings = get_settings()
    if os.getenv("VERCEL") and settings.synthetic_only:
        raise HTTPException(503, "SERVERLESS_DOCUMENT_TRANSFER_REQUIRED")


def intake_sor_root() -> Path:
    settings = get_settings()
    root = Path(settings.mock_systems_root)
    if not root.is_absolute():
        root = repo_root() / root
    return root / "synology" / "proposal-intake"


def ingest_provisional_intake_artifact(
    db: Session,
    *,
    opportunity,
    semantic_class: str,
    source_filename: str,
    content_type: str,
    content: bytes,
    actor: str,
    source_revision: str | None,
    idempotency_key: str | None,
    correlation_id: str,
) -> dict[str, Any]:
    _reject_serverless_sor_write()
    if semantic_class not in INTAKE_SEMANTIC_CONFIG:
        raise HTTPException(422, "UNSUPPORTED_INTAKE_SOURCE")
    if not content:
        raise HTTPException(422, "SOURCE_FILE_REQUIRED")
    filename = _safe_filename(source_filename)
    digest = hashlib.sha256(content).hexdigest()
    key = idempotency_key or f"{opportunity.id}:{semantic_class}:{digest}:{source_revision or ''}"
    prior = db.scalar(select(ProposalIntakeArtifact).where(ProposalIntakeArtifact.idempotency_key == key))
    if prior:
        return {"id": prior.id, "status": prior.status, "reused": True, "verification_state": prior.verification_state, "semantic_class": prior.semantic_class, "source_filename": prior.source_filename, "stored_filename": prior.stored_filename, "sor_path": prior.sor_path, "content_hash": prior.content_hash, "reference_state": "PROVISIONAL", "opportunity_reference": prior.opportunity_reference}
    config = INTAKE_SEMANTIC_CONFIG[semantic_class]
    root = intake_sor_root() / opportunity.opportunity_reference
    folder = root / config["folder"]
    folder.mkdir(parents=True, exist_ok=True)
    same = db.scalar(select(ProposalIntakeArtifact).where(ProposalIntakeArtifact.opportunity_id == opportunity.id, ProposalIntakeArtifact.semantic_class == semantic_class, ProposalIntakeArtifact.source_filename == filename).order_by(ProposalIntakeArtifact.created_at.desc()))
    if same and same.content_hash == digest:
        same.idempotency_key = key
        db.flush()
        return {"id": same.id, "status": same.status, "reused": True, "verification_state": same.verification_state, "semantic_class": same.semantic_class, "source_filename": same.source_filename, "stored_filename": same.stored_filename, "sor_path": same.sor_path, "content_hash": same.content_hash, "reference_state": "PROVISIONAL", "opportunity_reference": same.opportunity_reference}
    version = 1 if not same else int((same.metadata_json or {}).get("version", 1)) + 1
    stored = filename if version == 1 else f"{Path(filename).stem}__v{version}{Path(filename).suffix}"
    path = folder / stored
    path.write_bytes(content)
    read_back = path.read_bytes()
    if hashlib.sha256(read_back).hexdigest() != digest:
        raise HTTPException(502, "SOR_READBACK_VERIFICATION_FAILED")
    evidence = EvidenceArtifact(evidence_type=config["label"].upper().replace(" ", "_"), source_reference=str(path), content_hash=digest, synthetic_only=True, label="PROVISIONAL INTAKE SOR EVIDENCE")
    db.add(evidence)
    db.flush()
    record = ProposalIntakeArtifact(opportunity_id=opportunity.id, project_id=opportunity.project_id, opportunity_reference=opportunity.opportunity_reference, artifact_type=ACTION_CONFIG.get(semantic_class, {}).get("artifact_type", semantic_class), semantic_class=semantic_class, source_filename=filename, stored_filename=stored, sor_path=str(path), content_hash=digest, content_type=content_type or "application/octet-stream", file_size=len(content), uploaded_by=actor, source_revision=source_revision, idempotency_key=key, verification_state="READ_BACK_VERIFIED", status="REGISTERED", evidence_artifact_id=evidence.id, supersedes_artifact_id=same.id if same else None, metadata_json={"version": version, "folder_template_version": "SYN-PROPOSAL-INTAKE-1.0", "correlation_id": correlation_id})
    db.add(record)
    db.flush()
    if same:
        same.status = "SUPERSEDED"
    audit(db, correlation_id=correlation_id, event_type="PROVISIONAL_INTAKE_ARTIFACT_REGISTERED", entity_type="ProposalIntakeArtifact", entity_id=record.id, actor_id=actor, after={"opportunity_id": opportunity.id, "opportunity_reference": opportunity.opportunity_reference, "semantic_class": semantic_class, "sor_path": str(path), "sha256": digest, "reference_state": "PROVISIONAL"})
    return {"id": record.id, "status": record.status, "reused": False, "verification_state": record.verification_state, "semantic_class": record.semantic_class, "source_filename": record.source_filename, "stored_filename": record.stored_filename, "sor_path": record.sor_path, "content_hash": record.content_hash, "version": version, "reference_state": "PROVISIONAL", "opportunity_reference": record.opportunity_reference, "evidence_artifact_id": evidence.id}


def resolve_project_target(db: Session, project_id: str, project_reference: str | None = None) -> dict[str, Any]:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "PROJECT_NOT_FOUND")
    if project_reference and project_reference != project.project_number:
        raise HTTPException(409, "PROJECT_REFERENCE_MISMATCH")
    bootstrap = db.scalar(select(SynologyProjectBootstrap).where(SynologyProjectBootstrap.project_id == project.id))
    if not bootstrap or not bootstrap.root_path:
        raise HTTPException(409, "PROJECT_SOR_ROOT_MISSING")
    if not bootstrap.template_applied or sorted(bootstrap.subfolders_json or []) != sorted(EXPECTED_PROJECT_FOLDERS):
        raise HTTPException(409, "SOR_FOLDER_TEMPLATE_DRIFT")
    adapter = _adapter()
    try:
        structure = adapter.ensure_configured_project_structure(bootstrap.root_path, EXPECTED_PROJECT_FOLDERS)
    except FileNotFoundError as exc:
        raise HTTPException(503, "SOR_UNAVAILABLE") from exc
    except RuntimeError as exc:
        raise HTTPException(409, "SOR_FOLDER_TEMPLATE_DRIFT") from exc
    except ValueError as exc:
        raise HTTPException(409, "PROJECT_SOR_ROOT_INVALID") from exc
    return {"project": project, "bootstrap": bootstrap, "adapter": adapter, "structure": structure, "template_version": SOR_TEMPLATE_VERSION}


def _versioned_filename(adapter, root_path: str, folder: str, filename: str, digest: str) -> tuple[str, int, str | None]:
    existing = [item for item in adapter.list_project_files(root_path) if item["path"].startswith(f"{root_path}/{folder}/")]
    same_name = [item for item in existing if item["name"] == filename]
    if any(item.get("sha256") == digest for item in same_name):
        return filename, 0, "EXACT_HASH_REUSE"
    version = len(same_name) + 1
    if not same_name:
        return filename, 1, None
    stem = Path(filename).stem
    suffix = Path(filename).suffix
    return f"{stem}__v{version}{suffix}", version, "NEW_VERSION"


def ingest_project_artifact(
    db: Session,
    *,
    project_id: str,
    action: str,
    source_filename: str,
    content_type: str,
    content: bytes,
    actor: str,
    actor_role: str,
    correlation_id: str,
    project_reference: str | None = None,
    source_revision: str | None = None,
    idempotency_key: str | None = None,
    contract_id: str | None = None,
    opportunity_id: str | None = None,
    permit_application_id: str | None = None,
    simulate_sor: str | None = None,
    config_override: dict[str, str] | None = None,
) -> dict[str, Any]:
    _reject_serverless_sor_write()
    if action not in ACTION_CONFIG and not config_override:
        raise HTTPException(422, "UNSUPPORTED_ORANGE_ACTION")
    if not content:
        raise HTTPException(422, "SOURCE_FILE_REQUIRED")
    target = resolve_project_target(db, project_id, project_reference)
    if simulate_sor == "UNAVAILABLE":
        raise HTTPException(503, "SOR_UNAVAILABLE")
    if simulate_sor == "DRIFT":
        raise HTTPException(409, "SOR_FOLDER_TEMPLATE_DRIFT")
    digest = hashlib.sha256(content).hexdigest()
    idempotency = idempotency_key or f"{project_id}:{action}:{digest}:{source_revision or ''}"
    existing_idempotent = db.scalar(select(ProjectArtifactRecord).where(ProjectArtifactRecord.idempotency_key == idempotency))
    if existing_idempotent:
        return artifact_response(existing_idempotent, reused=True)

    config = config_override or ACTION_CONFIG[action]
    semantic_class = config["semantic_class"]
    folder = SEMANTIC_FOLDER_CONFIG[semantic_class]["folder"]
    filename = _safe_filename(source_filename)
    stored_filename, version, conflict = _versioned_filename(target["adapter"], target["bootstrap"].root_path, folder, filename, digest)
    if conflict == "EXACT_HASH_REUSE":
        prior = db.scalar(select(ProjectArtifactRecord).where(ProjectArtifactRecord.project_id == project_id, ProjectArtifactRecord.semantic_class == semantic_class, ProjectArtifactRecord.content_hash == digest, ProjectArtifactRecord.status == "REGISTERED").order_by(ProjectArtifactRecord.created_at.desc()))
        if prior:
            prior.idempotency_key = idempotency
            db.flush()
            return artifact_response(prior, reused=True)

    prior_version = db.scalar(select(ProjectArtifactRecord).where(ProjectArtifactRecord.project_id == project_id, ProjectArtifactRecord.semantic_class == semantic_class, ProjectArtifactRecord.source_filename == filename, ProjectArtifactRecord.status == "REGISTERED").order_by(ProjectArtifactRecord.created_at.desc()))
    try:
        pushed = target["adapter"].put_artifact(target["bootstrap"].root_path, folder, stored_filename, content)
        verification = target["adapter"].verify_artifact(pushed["path"], digest, len(content))
    except (FileNotFoundError, OSError) as exc:
        raise HTTPException(503, "SOR_WRITE_FAILED") from exc
    if not verification.get("verified"):
        raise HTTPException(502, "SOR_READBACK_VERIFICATION_FAILED")

    document = db.scalar(select(Document).where(Document.project_id == project_id, Document.logical_name == f"{config['artifact_type']}:{filename}"))
    if not document:
        document = Document(project_id=project_id, document_type=DocumentType.OTHER, logical_name=f"{config['artifact_type']}:{filename}", language="EN", source_system="AMEC_SOR_ADAPTER")
        db.add(document)
        db.flush()
    previous_version = db.scalar(select(DocumentVersion).where(DocumentVersion.document_id == document.id).order_by(DocumentVersion.version_number.desc()))
    document_version = DocumentVersion(document_id=document.id, version_number=(previous_version.version_number + 1 if previous_version else 1), source_filename=filename, source_path_or_reference=pushed["path"], sha256=digest, mime_type=content_type or "application/octet-stream", file_size=len(content), language="EN", revision_label=source_revision, approval_state=DocumentApprovalState.WORKING, source_system="AMEC_SOR_ADAPTER", metadata_json={"semantic_class": semantic_class, "folder_template_version": SOR_TEMPLATE_VERSION, "stored_filename": stored_filename, "read_back_sha256": verification["sha256"]})
    db.add(document_version)
    db.flush()
    document.current_version_id = document_version.id
    evidence = EvidenceArtifact(evidence_type=config["artifact_type"], source_reference=pushed["path"], content_hash=digest, synthetic_only=True, label="SYNTHETIC SOR POINTER")
    db.add(evidence)
    db.flush()
    record = ProjectArtifactRecord(project_id=project_id, opportunity_id=opportunity_id, contract_id=contract_id, artifact_type=config["artifact_type"], semantic_class=semantic_class, source_filename=filename, stored_filename=stored_filename, sor_path=pushed["path"], source_revision=source_revision, content_hash=digest, content_type=content_type or "application/octet-stream", file_size=len(content), uploaded_by=actor, folder_template_version=SOR_TEMPLATE_VERSION, document_version_id=document_version.id, evidence_artifact_id=evidence.id, supersedes_record_id=prior_version.id if prior_version else None, idempotency_key=idempotency, verification_state="READ_BACK_VERIFIED", status="REGISTERED", audit_metadata={"actor_role": actor_role, "correlation_id": correlation_id, "version": version, "conflict": conflict})
    db.add(record)
    db.flush()
    if prior_version:
        prior_version.status = "SUPERSEDED"
        if prior_version.document_version_id:
            old_version = db.get(DocumentVersion, prior_version.document_version_id)
            if old_version:
                old_version.superseded_by = document_version.id
                old_version.approval_state = DocumentApprovalState.SUPERSEDED
    db.add(LineageEdge(project_id=project_id, upstream_type="ProjectArtifactRecord", upstream_id=record.id, upstream_version_or_hash=digest, downstream_type="DocumentVersion", downstream_id=document_version.id, downstream_version_or_hash=digest, dependency_kind="SOR_ARTIFACT_VERSION", correlation_id=correlation_id))
    db.add(LineageEdge(project_id=project_id, upstream_type="DocumentVersion", upstream_id=document_version.id, upstream_version_or_hash=digest, downstream_type="EvidenceArtifact", downstream_id=evidence.id, downstream_version_or_hash=digest, dependency_kind="EVIDENCE_POINTER", correlation_id=correlation_id))
    if opportunity_id:
        db.add(LineageEdge(project_id=project_id, upstream_type="DocumentVersion", upstream_id=document_version.id, upstream_version_or_hash=digest, downstream_type="Opportunity", downstream_id=opportunity_id, downstream_version_or_hash=digest, dependency_kind="SOURCE_FOR_PROPOSAL_CONTEXT", correlation_id=correlation_id))
    if contract_id:
        db.add(LineageEdge(project_id=project_id, upstream_type="DocumentVersion", upstream_id=document_version.id, upstream_version_or_hash=digest, downstream_type="Contract", downstream_id=contract_id, downstream_version_or_hash=digest, dependency_kind="SUPPORTING_CONTRACT_SOURCE", correlation_id=correlation_id))
    if permit_application_id:
        db.add(LineageEdge(project_id=project_id, upstream_type="DocumentVersion", upstream_id=document_version.id, upstream_version_or_hash=digest, downstream_type="PermitApplication", downstream_id=permit_application_id, downstream_version_or_hash=digest, dependency_kind="PERMIT_INITIATION_SOURCE", correlation_id=correlation_id))
    audit(db, correlation_id=correlation_id, event_type="PROJECT_ARTIFACT_REGISTERED", entity_type="ProjectArtifactRecord", entity_id=record.id, actor_id=actor, after={"project_id": project_id, "project_reference": target["project"].project_number, "artifact_type": config["artifact_type"], "semantic_class": semantic_class, "sor_path": pushed["path"], "sha256": digest, "version": version, "verification": "READ_BACK_VERIFIED"}, metadata={"actor_role": actor_role, "folder_template_version": SOR_TEMPLATE_VERSION, "cross_project_artifact_write": 0, "correlation_id": correlation_id})
    return artifact_response(record, reused=False)


def _promotion_state(record: ProposalIntakeArtifact, state: str, **extra: Any) -> None:
    metadata = dict(record.metadata_json or {})
    metadata.update({"promotion_state": state, **extra})
    record.metadata_json = metadata


def _source_path_for_promotion(record: ProposalIntakeArtifact) -> Path:
    source_root = intake_sor_root().resolve()
    source_path = Path(record.sor_path).resolve()
    ensure_fixture_path_allowed(str(source_path))
    try:
        source_path.relative_to(source_root)
    except ValueError as exc:
        raise HTTPException(409, "PROVISIONAL_SOURCE_ROOT_INVALID") from exc
    if not source_path.is_file():
        raise HTTPException(409, "PROVISIONAL_SOURCE_MISSING")
    return source_path


def promote_provisional_intake(
    db: Session,
    *,
    opportunity_id: str,
    project_id: str,
    actor: str,
    correlation_id: str,
) -> dict[str, Any]:
    """Reconcile provisional intake into the canonical project SOR.

    The source is copied, read-back verified, registered as the authoritative
    project artifact, and retained as a historical provisional binding.  The
    operation is idempotent on the source-artifact/project pair and refuses a
    pre-existing target conflict instead of overwriting it.
    """
    from ..models import Opportunity

    opportunity = db.get(Opportunity, opportunity_id)
    if not opportunity:
        raise HTTPException(404, "PROPOSAL_NOT_FOUND")
    project = db.get(Project, project_id)
    if not project or not project.project_number:
        raise HTTPException(409, "CANONICAL_PROJECT_REFERENCE_REQUIRED")
    if opportunity.project_id and opportunity.project_id != project_id:
        raise HTTPException(409, "CROSS_PROJECT_PROMOTION_BLOCKED")
    target = resolve_project_target(db, project_id)
    sources = db.scalars(
        select(ProposalIntakeArtifact)
        .where(
            ProposalIntakeArtifact.opportunity_id == opportunity_id,
            ProposalIntakeArtifact.semantic_class.in_(sorted(PROMOTABLE_INTAKE_CLASSES)),
        )
        .order_by(ProposalIntakeArtifact.created_at, ProposalIntakeArtifact.id)
    ).all()
    if not sources:
        raise HTTPException(409, "PROVISIONAL_SOURCES_REQUIRED")

    promoted: list[dict[str, Any]] = []
    for source in sources:
        source_metadata = dict(source.metadata_json or {})
        if source_metadata.get("promotion_state") == "CANONICAL_VERIFIED":
            canonical_id = source_metadata.get("canonical_project_artifact_id")
            canonical = db.get(ProjectArtifactRecord, canonical_id) if canonical_id else None
            if canonical and canonical.project_id == project_id:
                promoted.append({"source_id": source.id, "canonical_artifact_id": canonical.id, "reused": True, "content_hash": source.content_hash, "target_path": canonical.sor_path})
                continue

        if source.semantic_class not in SEMANTIC_FOLDER_CONFIG:
            _promotion_state(source, "PROMOTION_FAILED", reason="SEMANTIC_FOLDER_MAPPING_MISSING")
            db.flush()
            raise HTTPException(409, "SEMANTIC_FOLDER_MAPPING_MISSING")
        source_path = _source_path_for_promotion(source)
        source_bytes = source_path.read_bytes()
        source_digest = hashlib.sha256(source_bytes).hexdigest()
        if source_digest != source.content_hash or len(source_bytes) != source.file_size:
            _promotion_state(source, "PROMOTION_FAILED", reason="SOURCE_HASH_MISMATCH", observed_hash=source_digest)
            db.flush()
            raise HTTPException(409, "PROVISIONAL_SOURCE_HASH_MISMATCH")

        _promotion_state(source, "PROMOTING", canonical_project_id=project_id, canonical_project_reference=project.project_number)
        db.flush()
        folder = SEMANTIC_FOLDER_CONFIG[source.semantic_class]["folder"]
        existing_canonical = next(
            (
                item for item in db.scalars(
                    select(ProjectArtifactRecord).where(
                        ProjectArtifactRecord.project_id == project_id,
                        ProjectArtifactRecord.semantic_class == source.semantic_class,
                        ProjectArtifactRecord.status == "REGISTERED",
                    )
                ).all()
                if (item.audit_metadata or {}).get("source_provisional_artifact_id") == source.id
            ),
            None,
        )
        if existing_canonical:
            verification = target["adapter"].verify_artifact(existing_canonical.sor_path, source.content_hash, source.file_size)
            if not verification.get("verified"):
                _promotion_state(source, "PROMOTION_FAILED", reason="TARGET_READBACK_FAILED", target_path=existing_canonical.sor_path)
                db.flush()
                raise HTTPException(502, "SOR_PROMOTION_READBACK_FAILED")
            source.project_id = project_id
            source.status = "HISTORICAL"
            _promotion_state(source, "CANONICAL_VERIFIED", canonical_project_id=project_id, canonical_project_reference=project.project_number, canonical_project_artifact_id=existing_canonical.id, canonical_sor_path=existing_canonical.sor_path, source_reference_state="PROVISIONAL")
            if not db.scalar(select(LineageEdge).where(LineageEdge.project_id == project_id, LineageEdge.upstream_type == "ProposalIntakeArtifact", LineageEdge.upstream_id == source.id, LineageEdge.downstream_type == "ProjectArtifactRecord", LineageEdge.downstream_id == existing_canonical.id, LineageEdge.dependency_kind == "PROVISIONAL_TO_CANONICAL_SOR_PROMOTION")):
                db.add(LineageEdge(project_id=project_id, upstream_type="ProposalIntakeArtifact", upstream_id=source.id, upstream_version_or_hash=source.content_hash, downstream_type="ProjectArtifactRecord", downstream_id=existing_canonical.id, downstream_version_or_hash=source.content_hash, dependency_kind="PROVISIONAL_TO_CANONICAL_SOR_PROMOTION", correlation_id=correlation_id))
            promoted.append({"source_id": source.id, "canonical_artifact_id": existing_canonical.id, "reused": True, "content_hash": source.content_hash, "target_path": existing_canonical.sor_path})
            continue
        target_files = [
            item for item in target["adapter"].list_project_files(target["bootstrap"].root_path)
            if item["path"].startswith(f"{target['bootstrap'].root_path}/{folder}/") and item["name"] == source.stored_filename
        ]
        if target_files and target_files[0].get("sha256") != source.content_hash:
            _promotion_state(source, "CONFLICT", reason="TARGET_FILENAME_HASH_CONFLICT", target_path=target_files[0]["path"])
            db.flush()
            raise HTTPException(409, "SOR_PROMOTION_TARGET_CONFLICT")

        promotion_config = {"artifact_type": source.artifact_type, "semantic_class": source.semantic_class}
        result = ingest_project_artifact(
            db,
            project_id=project_id,
            action="PROMOTION",
            source_filename=source.source_filename,
            content_type=source.content_type,
            content=source_bytes,
            actor=actor,
            actor_role="PROMOTION_SERVICE",
            correlation_id=correlation_id,
            source_revision=source.source_revision,
            idempotency_key=f"promotion:{source.id}:{project_id}",
            opportunity_id=opportunity_id,
            config_override=promotion_config,
        )
        canonical = db.get(ProjectArtifactRecord, result["id"])
        if not canonical:
            _promotion_state(source, "PROMOTION_FAILED", reason="CANONICAL_REGISTRATION_MISSING")
            db.flush()
            raise HTTPException(500, "SOR_PROMOTION_REGISTRATION_FAILED")
        verification = target["adapter"].verify_artifact(canonical.sor_path, source.content_hash, source.file_size)
        if not verification.get("verified"):
            _promotion_state(source, "PROMOTION_FAILED", reason="TARGET_READBACK_FAILED", target_path=canonical.sor_path)
            db.flush()
            raise HTTPException(502, "SOR_PROMOTION_READBACK_FAILED")

        canonical_metadata = dict(canonical.audit_metadata or {})
        canonical_metadata.update({
            "promotion_policy": PROMOTION_POLICY,
            "source_provisional_artifact_id": source.id,
            "source_opportunity_reference": source.opportunity_reference,
            "source_provisional_path": source.sor_path,
            "canonical_project_reference": project.project_number,
            "cross_project_artifact_write": 0,
        })
        canonical.audit_metadata = canonical_metadata
        source.project_id = project_id
        source.status = "HISTORICAL"
        _promotion_state(source, "CANONICAL_VERIFIED", canonical_project_id=project_id, canonical_project_reference=project.project_number, canonical_project_artifact_id=canonical.id, canonical_sor_path=canonical.sor_path, source_reference_state="PROVISIONAL")
        if not db.scalar(select(LineageEdge).where(LineageEdge.project_id == project_id, LineageEdge.upstream_type == "ProposalIntakeArtifact", LineageEdge.upstream_id == source.id, LineageEdge.downstream_type == "ProjectArtifactRecord", LineageEdge.downstream_id == canonical.id, LineageEdge.dependency_kind == "PROVISIONAL_TO_CANONICAL_SOR_PROMOTION")):
            db.add(LineageEdge(project_id=project_id, upstream_type="ProposalIntakeArtifact", upstream_id=source.id, upstream_version_or_hash=source.content_hash, downstream_type="ProjectArtifactRecord", downstream_id=canonical.id, downstream_version_or_hash=source.content_hash, dependency_kind="PROVISIONAL_TO_CANONICAL_SOR_PROMOTION", correlation_id=correlation_id))
        if not result.get("reused"):
            audit(db, correlation_id=correlation_id, event_type="PROVISIONAL_SOR_PROMOTED", entity_type="ProjectArtifactRecord", entity_id=canonical.id, actor_id=actor, after={"source_artifact_id": source.id, "opportunity_reference": source.opportunity_reference, "project_reference": project.project_number, "source_hash": source.content_hash, "target_path": canonical.sor_path, "promotion_policy": PROMOTION_POLICY, "cross_project_artifact_write": 0})
        promoted.append({"source_id": source.id, "canonical_artifact_id": canonical.id, "reused": bool(result.get("reused")), "content_hash": source.content_hash, "target_path": canonical.sor_path})

    opportunity.project_id = project_id
    opportunity.reference_state = "CANONICAL"
    opportunity.provisional_reference = opportunity.provisional_reference or opportunity.opportunity_reference
    opportunity.canonical_project_reference = project.project_number
    opportunity.canonicalized_at = opportunity.canonicalized_at or datetime.now(timezone.utc)
    opportunity.canonicalized_by = opportunity.canonicalized_by or actor
    if not db.scalar(select(LineageEdge).where(LineageEdge.project_id == project_id, LineageEdge.upstream_type == "ProvisionalReference", LineageEdge.upstream_id == opportunity.provisional_reference, LineageEdge.downstream_type == "Project", LineageEdge.downstream_id == project_id, LineageEdge.dependency_kind == "PROVISIONAL_TO_CANONICAL_REFERENCE")):
        db.add(LineageEdge(project_id=project_id, upstream_type="ProvisionalReference", upstream_id=opportunity.provisional_reference, upstream_version_or_hash="PROVISIONAL", downstream_type="Project", downstream_id=project_id, downstream_version_or_hash=project.project_number, dependency_kind="PROVISIONAL_TO_CANONICAL_REFERENCE", correlation_id=correlation_id))
    db.flush()
    return {"opportunity_id": opportunity.id, "opportunity_reference": opportunity.opportunity_reference, "project_id": project.id, "project_reference": project.project_number, "policy": PROMOTION_POLICY, "trigger": "CANONICAL_PROJECT_REFERENCE_AND_VERIFIED_SOR_ROOT", "source_retained": True, "promotion_state": "CANONICAL_VERIFIED", "promoted": promoted, "cross_project_artifact_writes": 0}


def canonicalize_project_reference(
    db: Session,
    *,
    opportunity_id: str,
    project_id: str,
    actor: str,
    correlation_id: str,
) -> dict[str, Any]:
    """Canonicalize one Proposal identity, promoting sources when eligible."""
    from ..models import Contract, Opportunity, PermitApplication, Quotation

    opportunity = db.get(Opportunity, opportunity_id)
    if not opportunity:
        raise HTTPException(404, "PROPOSAL_NOT_FOUND")
    project = db.get(Project, project_id)
    if not project or not project.project_number:
        raise HTTPException(404, "PROJECT_NOT_FOUND")
    if opportunity.project_id and opportunity.project_id != project_id:
        raise HTTPException(409, {"code": "PROJECT_IDENTITY_CONFLICT", "proposal_project_id": opportunity.project_id, "requested_project_id": project_id})
    related_contracts = db.scalars(select(Contract).join(Quotation).where(Quotation.opportunity_id == opportunity.id)).all()
    for contract in related_contracts:
        if contract.project_id and contract.project_id != project_id:
            raise HTTPException(409, {"code": "PROJECT_IDENTITY_CONFLICT", "contract_id": contract.id, "contract_project_id": contract.project_id, "project_id": project_id})
    opportunity.provisional_reference = opportunity.provisional_reference or opportunity.opportunity_reference
    opportunity.project_id = project_id
    opportunity.reference_state = "CANONICAL"
    opportunity.canonical_project_reference = project.project_number
    opportunity.canonicalized_at = datetime.now(timezone.utc)
    opportunity.canonicalized_by = actor
    for contract in related_contracts:
        contract.project_id = project_id
        permits = db.scalars(select(PermitApplication).where(PermitApplication.controlling_contract_id == contract.id)).all()
        for permit in permits:
            if permit.project_id != project_id:
                raise HTTPException(409, {"code": "PROJECT_IDENTITY_CONFLICT", "permit_id": permit.id, "permit_project_id": permit.project_id, "project_id": project_id})
    if not db.scalar(select(LineageEdge).where(LineageEdge.project_id == project_id, LineageEdge.upstream_type == "ProvisionalReference", LineageEdge.upstream_id == opportunity.provisional_reference, LineageEdge.downstream_type == "Project", LineageEdge.downstream_id == project_id, LineageEdge.dependency_kind == "PROVISIONAL_TO_CANONICAL_REFERENCE")):
        db.add(LineageEdge(project_id=project_id, upstream_type="ProvisionalReference", upstream_id=opportunity.provisional_reference, upstream_version_or_hash="PROVISIONAL", downstream_type="Project", downstream_id=project_id, downstream_version_or_hash=project.project_number, dependency_kind="PROVISIONAL_TO_CANONICAL_REFERENCE", correlation_id=correlation_id))
    audit(db, correlation_id=correlation_id, event_type="PROPOSAL_REFERENCE_CANONICALIZED", entity_type="Opportunity", entity_id=opportunity.id, actor_id=actor, after={"provisional_reference": opportunity.provisional_reference, "canonical_project_reference": project.project_number, "project_id": project_id})
    sources = db.scalars(select(ProposalIntakeArtifact).where(ProposalIntakeArtifact.opportunity_id == opportunity.id, ProposalIntakeArtifact.semantic_class.in_(sorted(PROMOTABLE_INTAKE_CLASSES)))).all()
    if sources:
        # Rollback is handled by the request boundary if promotion fails; no
        # source is marked authoritative before its target read-back passes.
        return promote_provisional_intake(db, opportunity_id=opportunity_id, project_id=project_id, actor=actor, correlation_id=correlation_id)
    db.flush()
    return {"opportunity_id": opportunity.id, "provisional_reference": opportunity.provisional_reference, "project_id": project.id, "project_reference": project.project_number, "canonicalization": "CANONICAL", "promotion_state": "NOT_REQUIRED", "source_retained": True, "cross_project_artifact_writes": 0}


def artifact_response(record: ProjectArtifactRecord, reused: bool = False) -> dict[str, Any]:
    return {"id": record.id, "status": record.status, "verification_state": record.verification_state, "reused": reused, "source_filename": record.source_filename, "stored_filename": record.stored_filename, "semantic_class": record.semantic_class, "sor_path": record.sor_path, "content_hash": record.content_hash, "file_size": record.file_size, "version": record.audit_metadata.get("version", 1), "folder_template_version": record.folder_template_version, "document_version_id": record.document_version_id, "evidence_artifact_id": record.evidence_artifact_id, "supersedes_record_id": record.supersedes_record_id, "project_id": record.project_id}


class ArtifactIngestionService:
    """Single bounded ingestion contract for all ProposalOps source classes.

    The legacy functions above are the storage adapters for provisional and
    canonical roots.  This facade is the only domain-level dispatch point: it
    validates identity and file metadata, then delegates to the appropriate
    adapter while preserving the same hash, read-back, version, evidence and
    lineage behavior.
    """

    ACTION_BY_CLASS = {
        "TENDER_EMAIL_SOURCE": "TENDER_EMAIL",
        "TENDER_DOCUMENT_SOURCE": "TENDER_DOCUMENT",
        "TENDER_IMAGE_SOURCE": "TENDER_IMAGE",
        "CLIENT_SOURCE": "CLIENT_INFORMATION",
        "PROPOSAL_SOURCE": "PROPOSAL_FORM",
        "CONTRACT_SOURCE": "CONTRACT_FORM",
        "PERMIT_INITIATION_SOURCE": "PERMIT_INITIATION",
    }
    MAX_BYTES = 25 * 1024 * 1024

    def ingest(
        self,
        db: Session,
        *,
        business_context_id: str,
        context_type: str,
        artifact_class: str,
        filename: str,
        content_type: str,
        content: bytes,
        actor: str,
        persona: str,
        revision_metadata: dict[str, Any] | None = None,
        correlation_id: str,
        project_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        if artifact_class not in self.ACTION_BY_CLASS:
            raise HTTPException(422, "UNSUPPORTED_INTAKE_SOURCE")
        if not content:
            raise HTTPException(422, "SOURCE_FILE_REQUIRED")
        if len(content) > self.MAX_BYTES:
            raise HTTPException(422, "SOURCE_FILE_TOO_LARGE")
        safe_name = _safe_filename(filename)
        opportunity = db.get(Opportunity, business_context_id) if context_type.upper() in {"PROPOSAL", "OPPORTUNITY"} else None
        if context_type.upper() in {"PROPOSAL", "OPPORTUNITY"} and not opportunity:
            raise HTTPException(404, "PROPOSAL_NOT_FOUND")
        resolved_project_id = project_id or (opportunity.project_id if opportunity else None)
        if opportunity and project_id and opportunity.project_id and opportunity.project_id != project_id:
            raise HTTPException(409, {"code": "PROJECT_IDENTITY_CONFLICT", "proposal_project_id": opportunity.project_id, "requested_project_id": project_id})
        revision = (revision_metadata or {}).get("source_revision")
        action = self.ACTION_BY_CLASS[artifact_class]
        if not resolved_project_id and artifact_class in PROMOTABLE_INTAKE_CLASSES:
            return ingest_provisional_intake_artifact(db, opportunity=opportunity, semantic_class=artifact_class, source_filename=safe_name, content_type=content_type, content=content, actor=actor, source_revision=revision, idempotency_key=idempotency_key, correlation_id=correlation_id)
        if not resolved_project_id:
            raise HTTPException(422, "CANONICAL_PROJECT_REFERENCE_REQUIRED")
        if action == "PERMIT_INITIATION" and context_type.upper() == "PERMIT":
            permit_id = business_context_id
        else:
            permit_id = None
        return ingest_project_artifact(db, project_id=resolved_project_id, action=action, source_filename=safe_name, content_type=content_type, content=content, actor=actor, actor_role=persona, correlation_id=correlation_id, source_revision=revision, idempotency_key=idempotency_key, opportunity_id=opportunity.id if opportunity else None, permit_application_id=permit_id)
