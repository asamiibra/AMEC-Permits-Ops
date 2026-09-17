"""Bounded Proposal source workspace and immutable capture index."""
from __future__ import annotations

import hashlib
import json
import mimetypes
import os
from pathlib import Path
from typing import Any
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Document, DocumentType, DocumentVersion, DocumentApprovalState, Opportunity, ProposalRevision
from ..storage.proposal_source_tree import BridgeProposalSourceProvider, MountedProposalSource, ProposalSourceProvider, SourceEntry, SourceProject
from ..storage import DocumentStorageService, StorageTarget, create_binary_store
from ..config.settings import get_settings
from .proposal_document_package import DocumentPackageError, digest
from .proposal_editor_model import import_editor_model

LOGICAL_ROOT = "Tenders/1- Proposal/2026"
PILOT = "454 - Al Watan Center"


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


def projects(db: Session | None = None) -> list[dict[str, Any]]:
    with _source(db) as source:
        rows = []
        for project in source.discover():
            entries = source.inventory(project.folder_name)
            rows.append({"number": project.number, "name": project.folder_name, "folder_name": project.folder_name, "state": "ACTIVE_PILOT" if project.discovery_class == "PROPOSALS_V1_ACTIVE_PILOT" else "DRAFT_SYNCED", "discovery_class": project.discovery_class, "folder_count": sum(item.is_directory for item in entries), "file_count": sum(not item.is_directory for item in entries)})
        return rows


def tree(number: int, db: Session | None = None) -> dict[str, Any]:
    with _source(db) as source:
        project = _project(source, number)
        entries = source.inventory(project.folder_name)
        # Preserve the adapter's source ordering and exact names.
        return {"number": number, "name": project.folder_name, "root": project.folder_name, "entries": [{"id": hashlib.sha256(item.relative_path.encode()).hexdigest()[:24], "path": item.relative_path, "name": item.name, "is_directory": item.is_directory, "size": item.size, "modified_ns": item.modified_ns, "content_type": mimetypes.guess_type(item.name)[0] or "application/octet-stream"} for item in entries]}


def capture(db: Session, number: int, *, actor: str = "source-workspace") -> dict[str, Any]:
    with _source(db) as source:
        project = _project(source, number)
        entries = source.inventory(project.folder_name)
        files = [item for item in entries if not item.is_directory]
        captured = 0
        unchanged = 0
        for item in files:
            read = source.capture(item.relative_path)
            key = f"PROPOSAL_SOURCE:{number}:{item.relative_path}"
            current = captured_version(db, number, item.relative_path)
            if current and current.sha256 == read.sha256:
                # Backfill the explicit fixture marker for databases created
                # before this source bridge carried synthetic provenance. The
                # marker is only ever added in TEST/DEV synthetic mode; a
                # live capture can never be relabelled by this path.
                if get_settings().synthetic_only and get_settings().app_env.upper() in {"TEST", "DEV", "DEVELOPMENT"}:
                    current.metadata_json = {**(current.metadata_json or {}), "synthetic_non_business_fixture": True, "synthetic_only": True}
                unchanged += 1
                continue
            document = current.document if current else Document(document_type=DocumentType.OTHER, logical_name=item.name, language="UNKNOWN", source_system="SYNOLOGY_PROPOSAL_SOURCE")
            if not current:
                db.add(document)
                db.flush()
            metadata = {
                "proposal_source_key": key,
                "source_project_number": number,
                "source_root": LOGICAL_ROOT,
                "source_relative_path": item.relative_path,
                "source_modified_at": read.before_modified_at,
                "capture_actor": actor,
                "source_presence_state": "PRESENT",
                # TEST/DEV captures are explicitly synthetic so the shared
                # AI context compiler can prove its safety boundary.  Live
                # bridge captures never inherit this marker.
                "synthetic_non_business_fixture": bool(
                    get_settings().synthetic_only
                    and get_settings().app_env.upper() in {"TEST", "DEV", "DEVELOPMENT"}
                ),
            }
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
        if metadata.get("proposal_source_key") == key:
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
    for version in sorted(candidates, key=lambda item: (item.version_number, item.id)):
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
