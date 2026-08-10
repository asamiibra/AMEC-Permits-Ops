"""Business-facing Dashboard master content and definitions APIs."""

from __future__ import annotations

import uuid
import json
from typing import Any

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..api.dependencies import current_user_role
from ..audit.service import audit
from ..db import get_db
from ..config.settings import get_settings
from ..models import ContentCategory, DefinitionEntry, DefinitionRevision, DocumentVersion, LineageEdge, MasterContentChangeEvent, MasterContentDependency, MasterContentItem, MasterContentModuleBinding, MasterContentReferenceSequence, Role
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
    read_master_content_bytes,
    register_dependency,
    revalidate_dependency,
    reconcile_item,
    seed_categories,
    seed_reference_sequences,
    _parse_modules,
    _sync_module_bindings,
    _allocate_reference,
    ALLOWED_MODULES,
    ALLOWED_USAGE_TYPES,
    reconcile_owner_demo_dataset,
)

router = APIRouter(prefix="/api", tags=["master-content"])


@router.post("/test-support/master-content/owner-cleanup")
def owner_test_cleanup(db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    if get_settings().app_env.upper() != "TEST":
        raise HTTPException(404, {"code": "TEST_SUPPORT_NOT_AVAILABLE"})
    require_capability(role, "MASTER_CONTENT_BINDING_WRITE")
    return {"status": "APPLIED", **reconcile_owner_demo_dataset(db, actor="e2e-cleanup")}


def _actor(role: Role) -> str:
    return role.value


def _json_object(value: str | None, code: str = "MASTER_CONTENT_METADATA_INVALID") -> dict[str, Any] | None:
    if not value:
        return None
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise HTTPException(422, {"code": code}) from exc
    if not isinstance(parsed, dict):
        raise HTTPException(422, {"code": code})
    return parsed


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
    used_in: list[str] = []


class DefinitionRevisionCreate(BaseModel):
    term: str = Field(min_length=1, max_length=240)
    description: str = Field(min_length=1)
    aliases: list[str] = []
    notes: str | None = None
    change_reason: str = Field(min_length=1)
    expected_revision: int
    category: str | None = None
    used_in: list[str] | None = None


class MetadataPatch(BaseModel):
    title: str | None = None
    category_id: str | None = None
    description: str | None = None
    used_in: list[str] | None = None
    engineering_metadata: dict[str, Any] | None = None
    change_reason: str = Field(min_length=1)


class BindingPayload(BaseModel):
    module: str
    usage_type: str = "AVAILABLE"
    active: bool = True


class AIAssistRequest(BaseModel):
    request_type: str
    source_version_id: str | None = None


class DependencyCreate(BaseModel):
    downstream_type: str
    downstream_id: str
    project_id: str | None = None
    dependency_kind: str = "CURRENT_SOURCE"


@router.get("/master-content/categories")
def categories(db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    seed_categories(db)
    seed_reference_sequences(db)
    db.commit()
    return [{"id": item.id, "code": item.code, "label": item.label, "description": item.description, "allowed_content_types": item.allowed_content_types, "active": item.active, "sort_order": item.sort_order, "source_kind": item.source_kind} for item in db.scalars(select(ContentCategory).where(ContentCategory.active.is_(True)).order_by(ContentCategory.sort_order, ContentCategory.label)).all()]


@router.get("/master-content")
def list_master_content(q: str = "", content_type: str | None = None, category_id: str | None = None, category_label: str | None = None, status: str | None = None, module: str | None = None, include_archived: bool = False, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    query = select(MasterContentItem).order_by(MasterContentItem.content_type, MasterContentItem.ref)
    if status:
        query = query.where(MasterContentItem.status == status.upper())
    elif not include_archived:
        query = query.where(MasterContentItem.status == "ACTIVE")
    if content_type:
        query = query.where(MasterContentItem.content_type == content_type.upper())
    if category_id:
        query = query.where(MasterContentItem.category_id == category_id)
    if q.strip():
        needle = f"%{q.strip()}%"
        query = query.where(or_(MasterContentItem.title.ilike(needle), MasterContentItem.ref.ilike(needle), MasterContentItem.description.ilike(needle)))
    rows = [item_projection(db, item) for item in db.scalars(query).all()]
    if category_label:
        rows = [row for row in rows if (row.get("category") or {}).get("label") == category_label]
    if module:
        rows = [row for row in rows if module.upper() in row.get("used_in", [])]
    return [{**row, "serial_number": index + 1} for index, row in enumerate(rows)]


@router.get("/master-content/eligible")
def eligible(use: str = "ENGINEERING_AI", db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    return eligible_master_content(db, use=use)


@router.post("/master-content/ai-assist")
def ai_assist_disabled(payload: AIAssistRequest, role: Role = Depends(current_user_role)):
    raise HTTPException(409, {"code": "AI_ASSIST_NOT_ENABLED", "request_type": payload.request_type})


@router.post("/master-content")
async def create_content(
    request: Request,
    content_type: str = Form(...),
    ref: str | None = Form(default=None),
    title: str = Form(...),
    category_id: str | None = Form(default=None),
    description: str | None = Form(default=None),
    used_in: str | None = Form(default=None),
    engineering_metadata: str | None = Form(default=None),
    file: UploadFile = File(...),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    source_surface: str = Header(default="DASHBOARD", alias="X-Source-Surface"),
    db: Session = Depends(get_db),
    role: Role = Depends(current_user_role),
):
    content_type = content_type.upper()
    require_capability(role, _write_capability(content_type))
    payload = await file.read()
    parsed_metadata = _json_object(engineering_metadata)
    return create_master_content(db, content_type=content_type, ref=ref, title=title, category_id=category_id, description=description, filename=file.filename or "document.bin", mime_type=file.content_type or "application/octet-stream", content=payload, actor=_actor(role), idempotency_key=idempotency_key or str(uuid.uuid4()), correlation_id=request.state.correlation_id, source_surface=source_surface.upper() if source_surface.upper() in {"DASHBOARD", "ADMINISTRATION"} else "DASHBOARD", used_in=used_in, engineering_metadata=parsed_metadata)


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


@router.patch("/master-content/{item_id}/metadata")
def patch_metadata(item_id: str, payload: MetadataPatch, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    item = db.get(MasterContentItem, item_id)
    if not item:
        raise HTTPException(404, {"code": "CONTENT_NOT_FOUND"})
    require_capability(role, _write_capability(item.content_type))
    current = db.scalar(select(DocumentVersion).where(DocumentVersion.id == item.current_document_version_id)) if item.current_document_version_id else None
    if not current:
        raise HTTPException(409, {"code": "METADATA_REQUIRES_CURRENT_VERSION"})
    if payload.category_id is not None:
        from ..services.master_content import _category
        _category(db, payload.category_id, item.content_type)
        item.category_id = payload.category_id
    if payload.title is not None:
        item.title = payload.title.strip()
    if payload.description is not None:
        item.description = payload.description
    if payload.used_in is not None:
        modules = _parse_modules(payload.used_in)
        item.used_in = modules
        _sync_module_bindings(db, item_id=item.id, modules=modules, actor=_actor(role))
    if payload.engineering_metadata is not None:
        item.engineering_metadata = payload.engineering_metadata
    audit(db, correlation_id=request.state.correlation_id, event_type="MASTER_CONTENT_METADATA_UPDATED", entity_type="MasterContentItem", entity_id=item.id, actor_id=_actor(role), after={"ref": item.ref, "title": item.title, "category_id": item.category_id, "description": item.description, "used_in": item.used_in, "current_version_id": current.id}, metadata={"change_reason": payload.change_reason, "document_version_unchanged": True})
    db.commit()
    return item_projection(db, item, include_history=True)


@router.get("/master-content/{item_id}/module-bindings")
def get_module_bindings(item_id: str, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    if not db.get(MasterContentItem, item_id):
        raise HTTPException(404, {"code": "CONTENT_NOT_FOUND"})
    return [{"id": binding.id, "module": binding.module, "usage_type": binding.usage_type, "active": binding.active, "created_by": binding.created_by} for binding in db.scalars(select(MasterContentModuleBinding).where(MasterContentModuleBinding.master_content_id == item_id).order_by(MasterContentModuleBinding.module)).all()]


@router.put("/master-content/{item_id}/module-bindings")
def put_module_bindings(item_id: str, payload: list[BindingPayload], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "MASTER_CONTENT_BINDING_WRITE")
    item = db.get(MasterContentItem, item_id)
    if not item:
        raise HTTPException(404, {"code": "CONTENT_NOT_FOUND"})
    seen = set()
    for row in payload:
        module = row.module.strip().upper()
        usage_type = row.usage_type.strip().upper()
        if module not in ALLOWED_MODULES or usage_type not in ALLOWED_USAGE_TYPES:
            raise HTTPException(422, {"code": "MODULE_BINDING_NOT_ALLOWED", "module": module, "usage_type": usage_type})
        seen.add((module, usage_type))
    existing = db.scalars(select(MasterContentModuleBinding).where(MasterContentModuleBinding.master_content_id == item_id)).all()
    for binding in existing:
        binding.active = (binding.module, binding.usage_type) in seen
    for module, usage_type in seen:
        binding = db.scalar(select(MasterContentModuleBinding).where(MasterContentModuleBinding.master_content_id == item_id, MasterContentModuleBinding.module == module, MasterContentModuleBinding.usage_type == usage_type))
        if binding:
            binding.active = True
        else:
            db.add(MasterContentModuleBinding(master_content_id=item_id, module=module, usage_type=usage_type, active=True, created_by=_actor(role)))
    item.used_in = sorted({module for module, _ in seen})
    audit(db, correlation_id=request.state.correlation_id, event_type="MASTER_CONTENT_MODULE_BINDINGS_UPDATED", entity_type="MasterContentItem", entity_id=item.id, actor_id=_actor(role), after={"used_in": item.used_in})
    db.commit()
    return item_projection(db, item, include_history=True)


@router.post("/master-content/{item_id}/versions")
async def create_version(
    item_id: str,
    request: Request,
    expected_current_version: int = Form(...),
    change_reason: str = Form(...),
    title: str | None = Form(default=None),
    category_id: str | None = Form(default=None),
    description: str | None = Form(default=None),
    used_in: str | None = Form(default=None),
    engineering_metadata: str | None = Form(default=None),
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
    parsed_metadata = _json_object(engineering_metadata)
    return create_master_content_version(db, item_id=item_id, expected_current_version=expected_current_version, filename=file.filename if file else None, mime_type=file.content_type if file else None, content=payload, title=title, category_id=category_id, description=description, change_reason=change_reason, actor=_actor(role), idempotency_key=idempotency_key or str(uuid.uuid4()), correlation_id=request.state.correlation_id, source_surface=source_surface.upper() if source_surface.upper() in {"DASHBOARD", "ADMINISTRATION"} else "DASHBOARD", used_in=used_in, engineering_metadata=parsed_metadata)


@router.get("/master-content/{item_id}/download")
def download_current(item_id: str, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    item = db.get(MasterContentItem, item_id)
    if not item or not item.current_document_version_id:
        raise HTTPException(404, {"code": "CONTENT_NOT_FOUND"})
    version = db.get(DocumentVersion, item.current_document_version_id)
    return _download(db, version)


@router.get("/master-content/{item_id}/versions/{version_id}/download")
def download_version(item_id: str, version_id: str, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    item = db.get(MasterContentItem, item_id)
    version = db.get(DocumentVersion, version_id) if item else None
    if not item or not version or version.document_id != item.document_id:
        raise HTTPException(404, {"code": "VERSION_NOT_FOUND"})
    return _download(db, version)


@router.get("/master-content/{item_id}/versions/{version_id}/rendition")
def download_rendition(item_id: str, version_id: str, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    item = db.get(MasterContentItem, item_id)
    version = db.get(DocumentVersion, version_id) if item else None
    if not item or not version or version.document_id != item.document_id:
        raise HTTPException(404, {"code": "VERSION_NOT_FOUND"})
    if version.rendition_status != "SOURCE_PDF" or not version.rendition_path_or_reference:
        raise HTTPException(409, {"code": "RENDITION_NOT_AVAILABLE"})
    return _download(db, version, path_override=version.rendition_path_or_reference, mime_override=version.rendition_mime_type or "application/pdf")


def _download(db: Session, version: DocumentVersion, path_override: str | None = None, mime_override: str | None = None):
    try:
        data = read_master_content_bytes(db, version) if not path_override or path_override == version.source_path_or_reference else _adapter().read_configured_artifact(path_override)
    except (FileNotFoundError, ValueError, OSError) as exc:
        raise HTTPException(502, {"code": "SOR_UNAVAILABLE"}) from exc
    return StreamingResponse(iter([data]), media_type=mime_override or version.mime_type, headers={"Content-Disposition": f'attachment; filename="{version.source_filename}"'})


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
def list_definitions(q: str = "", category: str | None = None, status: str | None = None, module: str | None = None, include_archived: bool = False, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    query = select(DefinitionEntry).order_by(DefinitionEntry.term)
    if status:
        query = query.where(DefinitionEntry.status == status.upper())
    elif not include_archived:
        query = query.where(DefinitionEntry.status == "ACTIVE")
    if category:
        query = query.where(DefinitionEntry.category == category)
    if q.strip():
        query = query.where(DefinitionEntry.term.ilike(f"%{q.strip()}%"))
    rows = [definition_projection(db, item) for item in db.scalars(query).all()]
    if module:
        rows = [row for row in rows if module.upper() in row.get("used_in", [])]
    return [{**row, "serial_number": index + 1} for index, row in enumerate(rows)]


@router.post("/definitions")
def create_definition(payload: DefinitionCreate, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "DEFINITION_WRITE")
    if db.scalar(select(DefinitionEntry).where(DefinitionEntry.term == payload.term.strip())):
        raise HTTPException(409, {"code": "DEFINITION_TERM_CONFLICT"})
    ref, generated = _allocate_reference(db, "DEFINITION", payload.ref)
    modules = _parse_modules(payload.used_in)
    definition = DefinitionEntry(ref=ref, term=payload.term.strip(), category=payload.category, used_in=modules, status="ACTIVE", created_by=_actor(role))
    db.add(definition)
    db.flush()
    revision = DefinitionRevision(definition_id=definition.id, revision_number=1, term=definition.term, category=payload.category, used_in=modules, description=payload.description, aliases=payload.aliases, notes=payload.notes, changed_by=_actor(role), change_reason=payload.change_reason or "Initial definition", status="CURRENT")
    db.add(revision)
    db.flush()
    definition.current_revision_id = revision.id
    emit_definition_revision_event(db, definition=definition, revision=revision, previous=None, actor=_actor(role), correlation_id=request.state.correlation_id)
    for module in modules:
        db.add(MasterContentModuleBinding(definition_id=definition.id, module=module, usage_type="SEMANTIC_SOURCE", active=True, created_by=_actor(role)))
    audit(db, correlation_id=request.state.correlation_id, event_type="DEFINITION_CREATED", entity_type="DefinitionEntry", entity_id=definition.id, actor_id=_actor(role), after={"ref": ref, "term": definition.term, "revision": 1}, metadata={"reference_generated": generated, "used_in": modules})
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


@router.get("/definitions/{definition_id}/module-bindings")
def definition_module_bindings(definition_id: str, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    if not db.get(DefinitionEntry, definition_id):
        raise HTTPException(404, {"code": "DEFINITION_NOT_FOUND"})
    return [{"id": binding.id, "module": binding.module, "usage_type": binding.usage_type, "active": binding.active} for binding in db.scalars(select(MasterContentModuleBinding).where(MasterContentModuleBinding.definition_id == definition_id).order_by(MasterContentModuleBinding.module)).all()]


@router.put("/definitions/{definition_id}/module-bindings")
def put_definition_module_bindings(definition_id: str, payload: list[BindingPayload], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "DEFINITION_WRITE")
    definition = db.get(DefinitionEntry, definition_id)
    if not definition:
        raise HTTPException(404, {"code": "DEFINITION_NOT_FOUND"})
    seen = set()
    for row in payload:
        module = row.module.strip().upper()
        usage_type = row.usage_type.strip().upper()
        if module not in ALLOWED_MODULES or usage_type not in ALLOWED_USAGE_TYPES:
            raise HTTPException(422, {"code": "MODULE_BINDING_NOT_ALLOWED", "module": module, "usage_type": usage_type})
        seen.add((module, usage_type))
    existing = db.scalars(select(MasterContentModuleBinding).where(MasterContentModuleBinding.definition_id == definition_id)).all()
    for binding in existing:
        binding.active = (binding.module, binding.usage_type) in seen
    for module, usage_type in seen:
        binding = db.scalar(select(MasterContentModuleBinding).where(MasterContentModuleBinding.definition_id == definition_id, MasterContentModuleBinding.module == module, MasterContentModuleBinding.usage_type == usage_type))
        if binding:
            binding.active = True
        else:
            db.add(MasterContentModuleBinding(definition_id=definition_id, module=module, usage_type=usage_type, active=True, created_by=_actor(role)))
    definition.used_in = sorted({module for module, _ in seen})
    audit(db, correlation_id=request.state.correlation_id, event_type="DEFINITION_MODULE_BINDINGS_UPDATED", entity_type="DefinitionEntry", entity_id=definition_id, actor_id=_actor(role), after={"used_in": definition.used_in})
    db.commit()
    return definition_projection(db, definition, include_history=True)


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
    modules = _parse_modules(payload.used_in) if payload.used_in is not None else definition.used_in or []
    definition.category = payload.category if payload.category is not None else definition.category
    definition.used_in = modules
    revision = DefinitionRevision(definition_id=definition.id, revision_number=current.revision_number + 1, term=payload.term.strip(), category=definition.category, used_in=modules, description=payload.description, aliases=payload.aliases, notes=payload.notes, changed_by=_actor(role), change_reason=payload.change_reason, status="CURRENT")
    db.add(revision)
    db.flush()
    definition.term = revision.term
    definition.current_revision_id = revision.id
    emit_definition_revision_event(db, definition=definition, revision=revision, previous=current, actor=_actor(role), correlation_id=request.state.correlation_id)
    existing_bindings = db.scalars(select(MasterContentModuleBinding).where(MasterContentModuleBinding.definition_id == definition.id)).all()
    for binding in existing_bindings:
        binding.active = binding.module in modules
    for module in modules:
        if not db.scalar(select(MasterContentModuleBinding).where(MasterContentModuleBinding.definition_id == definition.id, MasterContentModuleBinding.module == module, MasterContentModuleBinding.usage_type == "SEMANTIC_SOURCE")):
            db.add(MasterContentModuleBinding(definition_id=definition.id, module=module, usage_type="SEMANTIC_SOURCE", active=True, created_by=_actor(role)))
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
