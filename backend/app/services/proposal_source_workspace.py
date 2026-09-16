"""Bounded Proposal source workspace and immutable capture index."""
from __future__ import annotations

import hashlib
import mimetypes
import os
from pathlib import Path
from typing import Any
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Document, DocumentType, DocumentVersion, DocumentApprovalState
from ..storage.proposal_source_tree import MountedProposalSource, SourceEntry, SourceProject
from ..storage import DocumentStorageService, StorageTarget, create_binary_store
from ..config.settings import get_settings

LOGICAL_ROOT = "Tenders/1- Proposal/2026"
PILOT = "454 - Al Watan Center"


def configured_source_root() -> Path:
    configured = os.getenv("PROPOSAL_SOURCE_ROOT", "")
    if configured:
        return Path(configured).expanduser()
    root = Path(__file__).resolve().parents[3] / "mock-systems" / "proposal-sources" / "Tenders" / "1- Proposal" / "2026"
    return root


def _source() -> MountedProposalSource:
    return MountedProposalSource(configured_source_root())


def _project(source: MountedProposalSource, number: int) -> SourceProject:
    projects = [item for item in source.discover() if item.number == number]
    if not projects:
        raise FileNotFoundError("SOURCE_PROJECT_NOT_FOUND")
    return projects[0]


def _entry(source: MountedProposalSource, number: int, relative: str) -> SourceEntry:
    project = _project(source, number)
    prefix = f"{project.folder_name}/"
    if not relative.startswith(prefix):
        raise FileNotFoundError("SOURCE_PATH_OUTSIDE_PROJECT")
    for item in source.inventory(project.folder_name):
        if item.relative_path == relative:
            return item
    raise FileNotFoundError("SOURCE_FILE_NOT_FOUND")


def projects() -> list[dict[str, Any]]:
    with _source() as source:
        rows = []
        for project in source.discover():
            entries = source.inventory(project.folder_name)
            rows.append({"number": project.number, "name": project.folder_name, "folder_name": project.folder_name, "state": "ACTIVE_PILOT" if project.discovery_class == "PROPOSALS_V1_ACTIVE_PILOT" else "DRAFT_SYNCED", "discovery_class": project.discovery_class, "folder_count": sum(item.is_directory for item in entries), "file_count": sum(not item.is_directory for item in entries)})
        return rows


def tree(number: int) -> dict[str, Any]:
    with _source() as source:
        project = _project(source, number)
        entries = source.inventory(project.folder_name)
        # Preserve the adapter's source ordering and exact names.
        return {"number": number, "name": project.folder_name, "root": project.folder_name, "entries": [{"id": hashlib.sha256(item.relative_path.encode()).hexdigest()[:24], "path": item.relative_path, "name": item.name, "is_directory": item.is_directory, "size": item.size, "modified_ns": item.modified_ns, "content_type": mimetypes.guess_type(item.name)[0] or "application/octet-stream"} for item in entries]}


def capture(db: Session, number: int, *, actor: str = "source-workspace") -> dict[str, Any]:
    with _source() as source:
        project = _project(source, number)
        entries = source.inventory(project.folder_name)
        files = [item for item in entries if not item.is_directory]
        captured = 0
        unchanged = 0
        for item in files:
            read = source.capture(item.relative_path)
            key = f"PROPOSAL_SOURCE:{number}:{item.relative_path}"
            versions = db.scalars(select(DocumentVersion).where(DocumentVersion.metadata_json["proposal_source_key"].as_string() == key).order_by(DocumentVersion.version_number.desc())).all()
            current = versions[0] if versions else None
            if current and current.sha256 == read.sha256:
                unchanged += 1
                continue
            document = current.document if current else Document(document_type=DocumentType.OTHER, logical_name=item.name, language="UNKNOWN", source_system="SYNOLOGY_PROPOSAL_SOURCE")
            if not current:
                db.add(document)
                db.flush()
            metadata = {"proposal_source_key": key, "source_project_number": number, "source_root": LOGICAL_ROOT, "source_relative_path": item.relative_path, "source_modified_at": read.before_modified_at, "capture_actor": actor, "source_presence_state": "PRESENT"}
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
    return db.scalar(select(DocumentVersion).where(DocumentVersion.metadata_json["proposal_source_key"].as_string() == key).order_by(DocumentVersion.version_number.desc()))
