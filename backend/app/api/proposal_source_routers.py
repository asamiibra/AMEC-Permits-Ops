"""Authenticated Proposal source workspace routes."""
from __future__ import annotations

import hashlib
import io
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..api.dependencies import require_roles
from ..db import get_db
from ..models import Role
from ..services.proposal_source_workspace import captured_version, capture, configured_source_root, projects, tree

router = APIRouter(prefix="/api/proposals/sources", tags=["proposal-source-workspace"])
source_role = require_roles(Role.OWNER_SPONSOR, Role.PROCESS_CHAMPION, Role.RESPONSIBLE_ENGINEER, Role.SYSTEM_ADMIN)


def _entry(number: int, file_id: str) -> dict[str, Any]:
    expected = str(file_id).lower()
    for item in tree(number)["entries"]:
        if not item["is_directory"] and hashlib.sha256(item["path"].encode()).hexdigest()[:24] == expected:
            return item
    raise HTTPException(404, "SOURCE_FILE_NOT_FOUND")


@router.get("/2026/projects")
def source_projects(_: Role = Depends(source_role)):
    return {"logical_root": "Tenders/1- Proposal/2026", "physical_root_configured": configured_source_root().is_absolute(), "projects": projects()}


@router.get("/2026/projects/{number}/tree")
def source_tree(number: int, _: Role = Depends(source_role)):
    try:
        return tree(number)
    except (FileNotFoundError, OSError) as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get("/2026/projects/{number}/files/{file_id}")
def source_file(number: int, file_id: str, _: Role = Depends(source_role), db: Session = Depends(get_db)):
    item = _entry(number, file_id)
    version = captured_version(db, number, item["path"])
    return {**item, "captured": bool(version), "source_content_hash": version.sha256 if version else None, "source_version": version.version_number if version else None, "source_presence_state": (version.metadata_json or {}).get("source_presence_state", "NOT_CAPTURED") if version else "NOT_CAPTURED"}


def _content(number: int, file_id: str, db: Session) -> tuple[dict[str, Any], bytes]:
    item = _entry(number, file_id)
    version = captured_version(db, number, item["path"])
    if not version or version.synthetic_content is None:
        result = capture(db, number, actor="source-view")
        version = captured_version(db, number, item["path"])
        if not version or version.synthetic_content is None:
            raise HTTPException(404, "SOURCE_FILE_NOT_CAPTURED")
    return item, version.synthetic_content


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
        discovered = projects()
        runs = [capture(db, row["number"], actor="source-sync") for row in discovered]
    except (FileNotFoundError, OSError) as exc:
        raise HTTPException(503, "SOURCE_ROOT_UNAVAILABLE") from exc
    return {"logical_root": "Tenders/1- Proposal/2026", "runs": runs, "synology_write_count": 0, "auto_proposal_created_for_520_plus": 0, "projects_455_519_auto_onboarded": 0}
