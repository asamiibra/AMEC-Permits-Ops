"""Business-facing Dashboard master content and definitions APIs."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..api.dependencies import current_user_role
from ..audit.service import audit
from ..db import get_db
from ..models import ContentCategory, DefinitionEntry, DefinitionRevision, DocumentVersion, LineageEdge, MasterContentChangeEvent, MasterContentDependency, MasterContentItem, Role
from ..services.backend_realignment import require_capability
from ..services.master_content import (
    CONTENT_TYPES,
    _adapter,
    create_master_content,
    create_master_content_version,
    definition_projection,
    definition_lookup,
    emit_definition_revision_event,
    archive_master_content,
    item_projection,
    eligible_master_content,
    register_dependency,
    revalidate_dependency,
    reconcile_item,
    seed_categories,
)

router = APIRouter(prefix="/api", tags=["master-content"])


def _actor(role: Role) -> str:
    return role.value


def _write_capability(content_type: str) -> str:
    return {"FORM": "MASTER_FORM_WRITE", "REPORT": "MASTER_REPORT_WRITE", "ENGINEERING_WORK": "MASTER_ENGINEERING_WRITE"}.get(content_type.upper(), "MASTER_FORM_WRITE")


class DefinitionCreate(BaseModel):
    term: str = Field(min_length=1, max_length=240)
    description: str = Field(min_length=1)
    ref: str | None = None
    category: str | None = None
    aliases: list[str] = []
    notes: str | None = None
    change_reason: str | None = None


class DefinitionRevisionCreate(BaseModel):
    term: str = Field(min_length=1, max_length=240)
    description: str = Field(min_length=1)
    aliases: list[str] = []
    notes: str | None = None
    change_reason: str = Field(min_length=1)
    expected_revision: int


class DependencyCreate(BaseModel):
    downstream_type: str
    downstream_id: str
    project_id: str | None = None
    dependency_kind: str = "CURRENT_SOURCE"


@router.get("/master-content/categories")
def categories(db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    seed_categories(db)
    db.commit()
    return [{"id": item.id, "code": item.code, "label": item.label, "description": item.description, "allowed_content_types": item.allowed_content_types, "active": item.active, "sort_order": item.sort_order} for item in db.scalars(select(ContentCategory).where(ContentCategory.active.is_(True)).order_by(ContentCategory.sort_order, ContentCategory.label)).all()]


@router.get("/master-content")
def list_master_content(q: str = "", content_type: str | None = None, category_id: str | None = None, include_archived: bool = False, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    query = select(MasterContentItem).order_by(MasterContentItem.content_type, MasterContentItem.ref)
    if not include_archived:
        query = query.where(MasterContentItem.status == "ACTIVE")
    if content_type:
        query = query.where(MasterContentItem.content_type == content_type.upper())
    if category_id:
        query = query.where(MasterContentItem.category_id == category_id)
    if q.strip():
        needle = f"%{q.strip()}%"
        query = query.where(or_(MasterContentItem.title.ilike(needle), MasterContentItem.ref.ilike(needle), MasterContentItem.description.ilike(needle)))
    return [item_projection(db, item) for item in db.scalars(query).all()]


@router.get("/master-content/eligible")
def eligible(use: str = "ENGINEERING_AI", db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    return eligible_master_content(db, use=use)


@router.post("/master-content")
async def create_content(
    request: Request,
    content_type: str = Form(...),
    ref: str = Form(...),
    title: str = Form(...),
    category_id: str | None = Form(default=None),
    description: str | None = Form(default=None),
    file: UploadFile = File(...),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    source_surface: str = Header(default="DASHBOARD", alias="X-Source-Surface"),
    db: Session = Depends(get_db),
    role: Role = Depends(current_user_role),
):
    content_type = content_type.upper()
    require_capability(role, _write_capability(content_type))
    payload = await file.read()
    return create_master_content(db, content_type=content_type, ref=ref, title=title, category_id=category_id, description=description, filename=file.filename or "document.bin", mime_type=file.content_type or "application/octet-stream", content=payload, actor=_actor(role), idempotency_key=idempotency_key or str(uuid.uuid4()), correlation_id=request.state.correlation_id, source_surface=source_surface.upper() if source_surface.upper() in {"DASHBOARD", "ADMINISTRATION"} else "DASHBOARD")


@router.get("/master-content/{item_id}")
def get_content(item_id: str, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    item = db.get(MasterContentItem, item_id)
    if not item:
        raise HTTPException(404, {"code": "CONTENT_NOT_FOUND"})
    return item_projection(db, item, include_history=True)


@router.get("/master-content/{item_id}/dependencies")
def dependencies(item_id: str, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    if not db.get(MasterContentItem, item_id):
        raise HTTPException(404, {"code": "CONTENT_NOT_FOUND"})
    return [{"id": d.id, "downstream_type": d.downstream_type, "downstream_id": d.downstream_id, "project_id": d.project_id, "bound_version_id": d.bound_document_version_id, "expected_current_version_id": d.expected_current_version_id, "status": d.status, "policy": d.policy} for d in db.scalars(select(MasterContentDependency).where(MasterContentDependency.master_content_id == item_id).order_by(MasterContentDependency.created_at)).all()]


@router.post("/master-content/{item_id}/dependencies")
def add_dependency(item_id: str, payload: DependencyCreate, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    return register_dependency(db, item_id=item_id, downstream_type=payload.downstream_type, downstream_id=payload.downstream_id, project_id=payload.project_id, dependency_kind=payload.dependency_kind, actor=_actor(role), correlation_id=request.state.correlation_id)


@router.post("/master-content/dependencies/{dependency_id}/revalidate")
def revalidate_dependency_route(dependency_id: str, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    return revalidate_dependency(db, dependency_id=dependency_id, actor=_actor(role), correlation_id=request.state.correlation_id)


@router.get("/master-content/{item_id}/propagation")
def propagation(item_id: str, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    item = db.get(MasterContentItem, item_id)
    if not item:
        raise HTTPException(404, {"code": "CONTENT_NOT_FOUND"})
    events = db.scalars(select(MasterContentChangeEvent).where(MasterContentChangeEvent.master_content_id == item.id).order_by(MasterContentChangeEvent.occurred_at.desc())).all()
    dependencies = db.scalars(select(MasterContentDependency).where(MasterContentDependency.master_content_id == item.id)).all()
    lineage = []
    for dependency in dependencies:
        if dependency.project_id:
            lineage.extend(db.scalars(select(LineageEdge).where(LineageEdge.project_id == dependency.project_id, LineageEdge.downstream_type == dependency.downstream_type, LineageEdge.downstream_id == dependency.downstream_id)).all())
    return {"item": item_projection(db, item), "dependencies": [{"id": d.id, "downstream_type": d.downstream_type, "downstream_id": d.downstream_id, "status": d.status, "bound_version_id": d.bound_document_version_id, "expected_current_version_id": d.expected_current_version_id} for d in dependencies], "lineage": [{"id": edge.id, "upstream_type": edge.upstream_type, "upstream_id": edge.upstream_id, "upstream_version_or_hash": edge.upstream_version_or_hash, "downstream_type": edge.downstream_type, "downstream_id": edge.downstream_id, "dependency_kind": edge.dependency_kind} for edge in lineage], "events": [{"id": e.id, "event_type": e.event_type, "old_version_id": e.previous_version_id, "new_version_id": e.new_version_id, "materiality": e.materiality, "status": e.status, "metadata": e.metadata_json} for e in events]}


@router.get("/master-content/{item_id}/versions")
def versions(item_id: str, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    item = db.get(MasterContentItem, item_id)
    if not item:
        raise HTTPException(404, {"code": "CONTENT_NOT_FOUND"})
    return item_projection(db, item, include_history=True)["versions"]


@router.post("/master-content/{item_id}/versions")
async def create_version(
    item_id: str,
    request: Request,
    expected_current_version: int = Form(...),
    change_reason: str = Form(...),
    title: str | None = Form(default=None),
    category_id: str | None = Form(default=None),
    description: str | None = Form(default=None),
    file: UploadFile | None = File(default=None),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    source_surface: str = Header(default="DASHBOARD", alias="X-Source-Surface"),
    db: Session = Depends(get_db),
    role: Role = Depends(current_user_role),
):
    item = db.get(MasterContentItem, item_id)
    if not item:
        raise HTTPException(404, {"code": "CONTENT_NOT_FOUND"})
    require_capability(role, _write_capability(item.content_type))
    payload = await file.read() if file else None
    return create_master_content_version(db, item_id=item_id, expected_current_version=expected_current_version, filename=file.filename if file else None, mime_type=file.content_type if file else None, content=payload, title=title, category_id=category_id, description=description, change_reason=change_reason, actor=_actor(role), idempotency_key=idempotency_key or str(uuid.uuid4()), correlation_id=request.state.correlation_id, source_surface=source_surface.upper() if source_surface.upper() in {"DASHBOARD", "ADMINISTRATION"} else "DASHBOARD")


@router.get("/master-content/{item_id}/download")
def download_current(item_id: str, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    item = db.get(MasterContentItem, item_id)
    if not item or not item.current_document_version_id:
        raise HTTPException(404, {"code": "CONTENT_NOT_FOUND"})
    version = db.get(DocumentVersion, item.current_document_version_id)
    return _download(version)


@router.get("/master-content/{item_id}/versions/{version_id}/download")
def download_version(item_id: str, version_id: str, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    item = db.get(MasterContentItem, item_id)
    version = db.get(DocumentVersion, version_id) if item else None
    if not item or not version or version.document_id != item.document_id:
        raise HTTPException(404, {"code": "VERSION_NOT_FOUND"})
    return _download(version)


def _download(version: DocumentVersion):
    try:
        data = _adapter().read_configured_artifact(version.source_path_or_reference)
    except (FileNotFoundError, ValueError, OSError) as exc:
        raise HTTPException(502, {"code": "SOR_UNAVAILABLE"}) from exc
    return StreamingResponse(iter([data]), media_type=version.mime_type, headers={"Content-Disposition": f'attachment; filename="{version.source_filename}"'})


@router.post("/master-content/{item_id}/archive")
def archive_content(item_id: str, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "MASTER_CONTENT_ARCHIVE")
    item = db.get(MasterContentItem, item_id)
    if not item:
        raise HTTPException(404, {"code": "CONTENT_NOT_FOUND"})
    return archive_master_content(db, item_id=item_id, actor=_actor(role), correlation_id=request.state.correlation_id)


@router.post("/master-content/{item_id}/reconcile")
def reconcile(item_id: str, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    return reconcile_item(db, item_id, request.state.correlation_id)


@router.get("/definitions")
def list_definitions(q: str = "", include_archived: bool = False, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    query = select(DefinitionEntry).order_by(DefinitionEntry.term)
    if not include_archived:
        query = query.where(DefinitionEntry.status == "ACTIVE")
    if q.strip():
        query = query.where(DefinitionEntry.term.ilike(f"%{q.strip()}%"))
    return [definition_projection(db, item) for item in db.scalars(query).all()]


@router.post("/definitions")
def create_definition(payload: DefinitionCreate, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "DEFINITION_WRITE")
    if db.scalar(select(DefinitionEntry).where(DefinitionEntry.term == payload.term.strip())):
        raise HTTPException(409, {"code": "DEFINITION_TERM_CONFLICT"})
    definition = DefinitionEntry(ref=payload.ref, term=payload.term.strip(), category=payload.category, status="ACTIVE", created_by=_actor(role))
    db.add(definition)
    db.flush()
    revision = DefinitionRevision(definition_id=definition.id, revision_number=1, term=definition.term, description=payload.description, aliases=payload.aliases, notes=payload.notes, changed_by=_actor(role), change_reason=payload.change_reason or "Initial definition", status="CURRENT")
    db.add(revision)
    db.flush()
    definition.current_revision_id = revision.id
    emit_definition_revision_event(db, definition=definition, revision=revision, previous=None, actor=_actor(role), correlation_id=request.state.correlation_id)
    audit(db, correlation_id=request.state.correlation_id, event_type="DEFINITION_CREATED", entity_type="DefinitionEntry", entity_id=definition.id, actor_id=_actor(role), after={"term": definition.term, "revision": 1})
    db.commit()
    return definition_projection(db, definition, include_history=True)


@router.get("/definitions/{definition_id}")
def get_definition(definition_id: str, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    definition = db.get(DefinitionEntry, definition_id)
    if not definition:
        raise HTTPException(404, {"code": "DEFINITION_NOT_FOUND"})
    return definition_projection(db, definition, include_history=True)


@router.get("/definitions/{definition_id}/revisions")
def definition_revisions(definition_id: str, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    definition = db.get(DefinitionEntry, definition_id)
    if not definition:
        raise HTTPException(404, {"code": "DEFINITION_NOT_FOUND"})
    return definition_projection(db, definition, include_history=True)["revisions"]


@router.post("/definitions/{definition_id}/revisions")
def revise_definition(definition_id: str, payload: DefinitionRevisionCreate, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "DEFINITION_WRITE")
    definition = db.scalar(select(DefinitionEntry).where(DefinitionEntry.id == definition_id).with_for_update())
    if not definition:
        raise HTTPException(404, {"code": "DEFINITION_NOT_FOUND"})
    current = db.get(DefinitionRevision, definition.current_revision_id) if definition.current_revision_id else None
    if not current or current.revision_number != payload.expected_revision:
        raise HTTPException(409, {"code": "DEFINITION_REVISION_CONFLICT", "current_revision": current.revision_number if current else None})
    current.status = "SUPERSEDED"
    revision = DefinitionRevision(definition_id=definition.id, revision_number=current.revision_number + 1, term=payload.term.strip(), description=payload.description, aliases=payload.aliases, notes=payload.notes, changed_by=_actor(role), change_reason=payload.change_reason, status="CURRENT")
    db.add(revision)
    db.flush()
    definition.term = revision.term
    definition.current_revision_id = revision.id
    emit_definition_revision_event(db, definition=definition, revision=revision, previous=current, actor=_actor(role), correlation_id=request.state.correlation_id)
    audit(db, correlation_id=request.state.correlation_id, event_type="DEFINITION_REVISED", entity_type="DefinitionEntry", entity_id=definition.id, actor_id=_actor(role), before={"revision": current.revision_number}, after={"revision": revision.revision_number}, metadata={"change_reason": payload.change_reason})
    db.commit()
    return definition_projection(db, definition, include_history=True)


@router.post("/definitions/{definition_id}/archive")
def archive_definition(definition_id: str, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "DEFINITION_WRITE")
    definition = db.get(DefinitionEntry, definition_id)
    if not definition:
        raise HTTPException(404, {"code": "DEFINITION_NOT_FOUND"})
    definition.status = "ARCHIVED"
    audit(db, correlation_id=request.state.correlation_id, event_type="DEFINITION_ARCHIVED", entity_type="DefinitionEntry", entity_id=definition.id, actor_id=_actor(role), after={"term": definition.term})
    db.commit()
    return definition_projection(db, definition, include_history=True)


@router.get("/definitions/lookup/{term}")
def lookup_definition(term: str, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    result = definition_lookup(db, term)
    if not result:
        raise HTTPException(404, {"code": "DEFINITION_NOT_FOUND"})
    return result
