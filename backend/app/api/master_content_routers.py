"""Business-facing Dashboard master content and definitions APIs."""

from __future__ import annotations

import uuid
import json
from typing import Any

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import or_, select, true
from sqlalchemy.orm import Session

from ..api.dependencies import current_user_role
from ..audit.service import audit
from ..db import get_db
from ..config.settings import get_settings
from ..models import ContentCategory, DefinitionEntry, DefinitionRevision, DocumentVersion, LineageEdge, MasterContentChangeEvent, MasterContentDependency, MasterContentItem, MasterContentModuleBinding, MasterContentReferenceSequence, MasterContentQualityFlag, MasterContentGovernanceProfile, Role
from ..services.backend_realignment import persona_for_role, require_capability
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
    ENGINEERING_SOURCE_TYPES,
    ENGINEERING_DISCIPLINES,
    resolve_master_content_purpose,
)
from ..services.forms_governance import (
    add_provenance,
    add_quality_flag,
    add_source_section,
    evaluate_readiness,
    governance_projection,
    resolve_quality_flag,
    set_currentness,
    source_blocker_rollup,
    update_source_section,
    update_governance,
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


def _role_can_see(role: Role, row: dict[str, Any]) -> bool:
    persona = persona_for_role(role)
    if persona in {"OWNER", "SYSTEM_ADMIN"}:
        return True
    module = "BD" if persona == "BUSINESS_DEVELOPMENT" else "ENGINEERING"
    return module in row.get("used_in", [])


def _definition_role_can_see(role: Role, row: dict[str, Any]) -> bool:
    persona = persona_for_role(role)
    if persona in {"OWNER", "SYSTEM_ADMIN"}:
        return True
    module = "BD" if persona == "BUSINESS_DEVELOPMENT" else "ENGINEERING"
    return module in row.get("used_in", [])


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
    source_type_code: str | None = None
    change_reason: str = Field(min_length=1)
    needs_review: bool | None = None
    review_note: str | None = Field(default=None, max_length=500)


class BindingPayload(BaseModel):
    module: str
    usage_type: str = "AVAILABLE"
    active: bool = True


class CategoryPayload(BaseModel):
    code: str = Field(min_length=1, max_length=80)
    label: str = Field(min_length=1, max_length=160)
    description: str | None = None
    allowed_content_types: list[str] = []
    sort_order: int = 100
    source_kind: str = "OWNER_CONFIGURED"


class CategoryPatch(BaseModel):
    label: str | None = None
    description: str | None = None
    allowed_content_types: list[str] | None = None
    sort_order: int | None = None
    active: bool | None = None


class ReferencePolicyPayload(BaseModel):
    prefix: str = Field(min_length=1, max_length=20)
    padding: int = Field(ge=1, le=8)


class AIAssistRequest(BaseModel):
    request_type: str
    source_version_id: str | None = None


class DependencyCreate(BaseModel):
    downstream_type: str
    downstream_id: str
    project_id: str | None = None
    dependency_kind: str = "CURRENT_SOURCE"


class GovernancePatch(BaseModel):
    content_ownership_class: str | None = None
    artifact_kind: str | None = None
    publisher_name: str | None = None
    publisher_unit: str | None = None
    jurisdiction_text: str | None = None
    official_form_no: str | None = None
    official_issue_no: str | None = None
    official_issue_date: Any | None = None
    language_profile: str | None = None
    sensitivity_class: str | None = None
    contains_pii: bool | None = None
    contains_signature: bool | None = None
    contains_stamp: bool | None = None
    contains_financial_data: bool | None = None
    contains_project_specific_data: bool | None = None
    restricted_reference_sample: bool | None = None
    currentness_verification_note: str | None = None


class CurrentnessPayload(BaseModel):
    action: str
    note: str | None = None


class ProvenancePayload(BaseModel):
    obtained_from: str = Field(min_length=1)
    obtained_by: str | None = None
    obtained_at: Any | None = None
    source_reference: str | None = None
    ingest_batch: str | None = None
    provenance_note: str | None = None
    evidence_reference: str | None = None


class QualityFlagPayload(BaseModel):
    code: str
    severity: str = "WARNING"
    description: str = Field(min_length=1)
    evidence_note: str | None = None
    recommended_next_action: str | None = None
    document_version_id: str | None = None


class QualityFlagResolution(BaseModel):
    status: str
    resolution: str = Field(min_length=1)


class SourceSectionPayload(BaseModel):
    document_version_id: str
    section_key: str = Field(min_length=1)
    label: str = Field(min_length=1)
    locator_type: str = "PAGE_RANGE"
    page_start: int | None = None
    page_end: int | None = None
    locator_payload: dict[str, Any] = {}
    description: str | None = None


class SourceSectionPatch(BaseModel):
    document_version_id: str | None = None
    section_key: str | None = None
    label: str | None = None
    locator_type: str | None = None
    page_start: int | None = None
    page_end: int | None = None
    locator_payload: dict[str, Any] | None = None
    description: str | None = None
    status: str | None = None


@router.get("/master-content/categories")
def categories(db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    seed_categories(db)
    seed_reference_sequences(db)
    db.commit()
    return [{"id": item.id, "code": item.code, "label": item.label, "description": item.description, "allowed_content_types": item.allowed_content_types, "active": item.active, "sort_order": item.sort_order, "source_kind": item.source_kind} for item in db.scalars(select(ContentCategory).where(ContentCategory.active == true()).order_by(ContentCategory.sort_order, ContentCategory.label)).all()]


@router.post("/master-content/categories")
def create_category(payload: CategoryPayload, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "MASTER_CATEGORY_WRITE")
    code = payload.code.strip().upper()
    types = [item.strip().upper() for item in payload.allowed_content_types]
    if any(item not in {"FORM", "REPORT", "ENGINEERING_WORK", "DEFINITION"} for item in types):
        raise HTTPException(422, {"code": "CATEGORY_CONTENT_TYPE_INVALID"})
    if db.scalar(select(ContentCategory).where(ContentCategory.code == code)):
        raise HTTPException(409, {"code": "CATEGORY_CODE_CONFLICT"})
    category = ContentCategory(code=code, label=payload.label.strip(), description=payload.description, allowed_content_types=types, sort_order=payload.sort_order, source_kind=payload.source_kind.strip().upper())
    db.add(category)
    audit(db, correlation_id=request.state.correlation_id, event_type="MASTER_CATEGORY_CREATED", entity_type="ContentCategory", entity_id=category.id, actor_id=_actor(role), after={"code": code, "label": category.label})
    db.commit()
    return {"id": category.id, "code": category.code, "label": category.label, "description": category.description, "allowed_content_types": category.allowed_content_types, "active": category.active, "sort_order": category.sort_order, "source_kind": category.source_kind}


@router.patch("/master-content/categories/{category_id}")
def patch_category(category_id: str, payload: CategoryPatch, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "MASTER_CATEGORY_WRITE")
    category = db.get(ContentCategory, category_id)
    if not category:
        raise HTTPException(404, {"code": "CATEGORY_NOT_FOUND"})
    if payload.label is not None:
        category.label = payload.label.strip()
    if payload.description is not None:
        category.description = payload.description
    if payload.allowed_content_types is not None:
        category.allowed_content_types = [item.strip().upper() for item in payload.allowed_content_types]
    if payload.sort_order is not None:
        category.sort_order = payload.sort_order
    if payload.active is not None:
        category.active = payload.active
    audit(db, correlation_id=request.state.correlation_id, event_type="MASTER_CATEGORY_UPDATED", entity_type="ContentCategory", entity_id=category.id, actor_id=_actor(role), after={"label": category.label, "active": category.active})
    db.commit()
    return {"id": category.id, "code": category.code, "label": category.label, "description": category.description, "allowed_content_types": category.allowed_content_types, "active": category.active, "sort_order": category.sort_order, "source_kind": category.source_kind}


@router.get("/master-content/reference-policies")
def reference_policies(db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    seed_reference_sequences(db)
    db.commit()
    return [{"content_type": row.content_type, "prefix": row.prefix, "padding": row.padding, "scope": row.scope, "next_reference": f"{row.prefix}-{row.current_value + 1:0{row.padding}d}", "renumber_existing": False} for row in db.scalars(select(MasterContentReferenceSequence).where(MasterContentReferenceSequence.active == true()).order_by(MasterContentReferenceSequence.content_type)).all()]


@router.put("/master-content/reference-policies/{content_type}")
def put_reference_policy(content_type: str, payload: ReferencePolicyPayload, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "MASTER_CATEGORY_WRITE")
    content_type = content_type.strip().upper()
    if content_type not in {"FORM", "REPORT", "ENGINEERING_WORK", "DEFINITION"}:
        raise HTTPException(422, {"code": "REFERENCE_CONTENT_TYPE_INVALID"})
    seed_reference_sequences(db)
    row = db.scalar(select(MasterContentReferenceSequence).where(MasterContentReferenceSequence.content_type == content_type, MasterContentReferenceSequence.scope == "GLOBAL"))
    row.prefix = payload.prefix.strip().upper()
    row.padding = payload.padding
    audit(db, correlation_id=request.state.correlation_id, event_type="MASTER_REFERENCE_POLICY_UPDATED", entity_type="MasterContentReferenceSequence", entity_id=row.id, actor_id=_actor(role), after={"content_type": content_type, "prefix": row.prefix, "padding": row.padding, "renumber_existing": False})
    db.commit()
    return {"content_type": row.content_type, "prefix": row.prefix, "padding": row.padding, "scope": row.scope, "next_reference": f"{row.prefix}-{row.current_value + 1:0{row.padding}d}", "renumber_existing": False}


@router.get("/master-content/resolvers/{module}/{purpose}")
def purpose_resolver(module: str, purpose: str, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    module = module.strip().upper()
    if persona_for_role(role) == "BUSINESS_DEVELOPMENT" and module != "BD":
        raise HTTPException(403, {"code": "MASTER_CONTENT_NOT_APPLICABLE"})
    if persona_for_role(role) == "ENGINEERING" and module not in {"ENGINEERING", "PERMIT", "REPORTS"}:
        raise HTTPException(403, {"code": "MASTER_CONTENT_NOT_APPLICABLE"})
    return resolve_master_content_purpose(db, module=module, usage_type=purpose)


@router.get("/master-content/consumer-resolvers/{consumer}")
def consumer_resolvers(consumer: str, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    consumer = consumer.strip().upper()
    persona = persona_for_role(role)
    if persona == "BUSINESS_DEVELOPMENT":
        consumer = "BD"
    elif persona == "ENGINEERING":
        consumer = "ENGINEERING"
    purpose_map = {"BD": [("BD", "PROPOSAL_TEMPLATE"), ("BD", "PROPOSAL_CHECKLIST")], "ADMIN": [("ADMIN", "CONTRACT_TEMPLATE")]}
    resolved = [{"module": module, "purpose": purpose, "resolution": resolve_master_content_purpose(db, module=module, usage_type=purpose)} for module, purpose in purpose_map.get(consumer, [])]
    return {"consumer": consumer, "resolvers": resolved, "truth": "DASHBOARD_MASTER_CONTENT"}


@router.get("/master-content")
def list_master_content(q: str = "", content_type: str | None = None, category_id: str | None = None, category_label: str | None = None, status: str | None = None, owner_status: str | None = None, module: str | None = None, ownership: str | None = None, artifact_kind: str | None = None, publisher: str | None = None, currentness: str | None = None, readiness: str | None = None, quality_state: str | None = None, restricted_sample: bool | None = None, language: str | None = None, include_archived: bool = False, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    query = select(MasterContentItem).order_by(MasterContentItem.content_type, MasterContentItem.ref)
    normalized_owner_status = owner_status.replace("_", " ").upper() if owner_status else None
    if normalized_owner_status == "INACTIVE":
        include_archived = True
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
        query = query.outerjoin(MasterContentGovernanceProfile, MasterContentGovernanceProfile.master_content_item_id == MasterContentItem.id).where(or_(MasterContentItem.title.ilike(needle), MasterContentItem.ref.ilike(needle), MasterContentItem.description.ilike(needle), MasterContentGovernanceProfile.official_form_no.ilike(needle)))
    rows = [item_projection(db, item) for item in db.scalars(query).all()]
    rows = [row for row in rows if _role_can_see(role, row)]
    if normalized_owner_status:
        rows = [row for row in rows if row.get("owner_status", "").upper() == normalized_owner_status]
    if q.strip():
        needle = q.strip().lower()
        rows = [row for row in rows if needle in row.get("title", "").lower() or needle in row.get("ref", "").lower() or needle in (row.get("description") or "").lower() or needle in (row.get("governance", {}).get("profile", {}).get("official_form_no") or "").lower()]
    if category_label:
        rows = [row for row in rows if (row.get("category") or {}).get("label") == category_label]
    if module:
        rows = [row for row in rows if module.upper() in row.get("used_in", [])]
    def matches(row: dict[str, Any]) -> bool:
        governance = row.get("governance", {})
        profile = governance.get("profile", {})
        readiness_row = governance.get("readiness", {})
        flags = governance.get("quality_flags", [])
        return all((not value or expected in actual) for value, expected, actual in (
            (ownership, ownership.upper() if ownership else "", profile.get("content_ownership_class", "")),
            (artifact_kind, artifact_kind.upper() if artifact_kind else "", profile.get("artifact_kind", "")),
            (currentness, currentness.upper() if currentness else "", profile.get("currentness_status", "")),
            (readiness, readiness.upper() if readiness else "", readiness_row.get("state", "")),
            (language, language.upper() if language else "", profile.get("language_profile", "")),
        )) and (not publisher or publisher.lower() in " ".join(filter(None, [profile.get("publisher_name"), profile.get("publisher_unit")])).lower()) and (restricted_sample is None or profile.get("restricted_reference_sample") is restricted_sample) and (not quality_state or any(flag.get("status") == quality_state.upper() for flag in flags))
    rows = [row for row in rows if matches(row)]
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
    source_type_code: str | None = Form(default=None),
    engineering_metadata: str | None = Form(default=None),
    needs_review: bool = Form(default=False),
    review_note: str | None = Form(default=None),
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
    return create_master_content(db, content_type=content_type, ref=ref, title=title, category_id=category_id, description=description, filename=file.filename or "document.bin", mime_type=file.content_type or "application/octet-stream", content=payload, actor=_actor(role), idempotency_key=idempotency_key or str(uuid.uuid4()), correlation_id=request.state.correlation_id, source_surface=source_surface.upper() if source_surface.upper() in {"DASHBOARD", "ADMINISTRATION"} else "DASHBOARD", used_in=used_in, source_type_code=source_type_code, engineering_metadata=parsed_metadata, needs_review=needs_review, review_note=review_note)


@router.get("/master-content/{item_id}")
def get_content(item_id: str, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    item = db.get(MasterContentItem, item_id)
    if not item:
        raise HTTPException(404, {"code": "CONTENT_NOT_FOUND"})
    projection = item_projection(db, item, include_history=True)
    if not _role_can_see(role, projection):
        raise HTTPException(403, {"code": "MASTER_CONTENT_NOT_APPLICABLE", "persona": persona_for_role(role)})
    return projection


def _governed_item(db: Session, item_id: str) -> MasterContentItem:
    item = db.get(MasterContentItem, item_id)
    if not item:
        raise HTTPException(404, {"code": "CONTENT_NOT_FOUND"})
    return item


@router.get("/master-content/governance/options")
def governance_options(db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    return {"ownership": ["AMEC_OWNED", "EXTERNAL_OFFICIAL", "EXTERNAL_REFERENCE", "REFERENCE_SAMPLE", "NEEDS_REVIEW"], "artifact_kind": ["AUTHORITY_FORM", "AMEC_FORM", "CHECKLIST", "UNDERTAKING", "AUTHORIZATION", "SERVICE_REQUEST", "CERTIFICATE_DECLARATION", "TECHNICAL_WORKSHEET", "INVOICE", "HANDOVER", "OTHER", "UNKNOWN"], "currentness": ["UNVERIFIED", "VERIFIED_CURRENT", "VERIFIED_NOT_CURRENT", "NEEDS_REVIEW"], "language": ["AR", "EN", "AR_EN_BILINGUAL", "OTHER"], "quality_state": ["OPEN", "ACCEPTED_RISK", "RESOLVED", "NOT_APPLICABLE"]}


@router.get("/master-content/governance/blocker-rollup")
def governance_blocker_rollup(db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    return source_blocker_rollup(db)


@router.get("/master-content/{item_id}/governance")
def get_governance(item_id: str, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    item = _governed_item(db, item_id)
    projection = item_projection(db, item, include_history=True)
    if not _role_can_see(role, projection):
        raise HTTPException(403, {"code": "MASTER_CONTENT_NOT_APPLICABLE"})
    return projection["governance"]


@router.patch("/master-content/{item_id}/governance")
def patch_governance(item_id: str, payload: GovernancePatch, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "MASTER_CONTENT_GOVERNANCE_WRITE")
    return update_governance(db, _governed_item(db, item_id), payload.model_dump(exclude_none=True), actor=_actor(role), correlation_id=request.state.correlation_id)


@router.post("/master-content/{item_id}/currentness")
def currentness(item_id: str, payload: CurrentnessPayload, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "MASTER_SOURCE_VERIFY_CURRENTNESS")
    return set_currentness(db, _governed_item(db, item_id), action=payload.action, actor=_actor(role), note=payload.note, correlation_id=request.state.correlation_id)


@router.post("/master-content/{item_id}/provenance")
def provenance(item_id: str, payload: ProvenancePayload, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "MASTER_CONTENT_GOVERNANCE_WRITE")
    item = _governed_item(db, item_id)
    version = db.get(DocumentVersion, item.current_document_version_id) if item.current_document_version_id else None
    if not version: raise HTTPException(409, {"code": "METADATA_REQUIRES_CURRENT_VERSION"})
    return add_provenance(db, item, version, payload.model_dump(exclude_none=True), actor=_actor(role), correlation_id=request.state.correlation_id)


@router.post("/master-content/{item_id}/quality-flags")
def create_quality_flag(item_id: str, payload: QualityFlagPayload, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "MASTER_SOURCE_MANAGE_QUALITY")
    return add_quality_flag(db, _governed_item(db, item_id), payload.model_dump(exclude_none=True), actor=_actor(role), correlation_id=request.state.correlation_id)


@router.patch("/master-content/{item_id}/quality-flags/{flag_id}")
def patch_quality_flag(item_id: str, flag_id: str, payload: QualityFlagResolution, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "MASTER_SOURCE_MANAGE_QUALITY")
    item = _governed_item(db, item_id)
    flag = db.get(MasterContentQualityFlag, flag_id)
    if not flag or flag.master_content_item_id != item.id: raise HTTPException(404, {"code": "QUALITY_FLAG_NOT_FOUND"})
    return resolve_quality_flag(db, item, flag, status=payload.status, resolution=payload.resolution, actor=_actor(role), correlation_id=request.state.correlation_id)


@router.post("/master-content/{item_id}/source-sections")
def create_source_section(item_id: str, payload: SourceSectionPayload, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "MASTER_SOURCE_SECTION_MANAGE")
    return add_source_section(db, _governed_item(db, item_id), payload.model_dump(exclude_none=True), actor=_actor(role), correlation_id=request.state.correlation_id)


@router.patch("/master-content/{item_id}/source-sections/{section_id}")
def patch_source_section(item_id: str, section_id: str, payload: SourceSectionPatch, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "MASTER_SOURCE_SECTION_MANAGE")
    item = _governed_item(db, item_id)
    from ..models import MasterContentSourceSection
    section = db.get(MasterContentSourceSection, section_id)
    if not section or section.master_content_item_id != item.id: raise HTTPException(404, {"code": "SOURCE_SECTION_NOT_FOUND"})
    return update_source_section(db, item, section, payload.model_dump(exclude_none=True), actor=_actor(role), correlation_id=request.state.correlation_id)


@router.post("/master-content/{item_id}/readiness/evaluate")
def evaluate_content_readiness(item_id: str, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "MASTER_READINESS_EVALUATE")
    item = _governed_item(db, item_id)
    result = evaluate_readiness(db, item, persist=True)
    audit(db, correlation_id=request.state.correlation_id, event_type="MASTER_CONTENT_READINESS_EVALUATED", entity_type="MasterContentItem", entity_id=item.id, actor_id=_actor(role), after=result)
    db.commit()
    return result


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
    if payload.needs_review is not None:
        item.needs_review = payload.needs_review
        item.review_note = (payload.review_note or None) if payload.needs_review else None
    if payload.engineering_metadata is not None:
        item.engineering_metadata = payload.engineering_metadata
    if payload.source_type_code is not None:
        if item.content_type != "ENGINEERING_WORK" or payload.source_type_code.upper() not in ENGINEERING_SOURCE_TYPES:
            raise HTTPException(422, {"code": "ENGINEERING_SOURCE_TYPE_NOT_ALLOWED"})
        item.source_type_code = payload.source_type_code.upper()
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
    # A frozen canonical consumer purpose is deterministic proof for these
    # AMEC templates; unrelated Forms remain unclassified until governed.
    if any(usage_type in {"PROPOSAL_TEMPLATE", "PROPOSAL_CHECKLIST", "CONTRACT_TEMPLATE"} for _, usage_type in seen):
        from ..services.forms_governance import ensure_profile
        ensure_profile(db, item, ownership="AMEC_OWNED").content_ownership_class = "AMEC_OWNED"
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
    source_type_code: str | None = Form(default=None),
    engineering_metadata: str | None = Form(default=None),
    needs_review: bool | None = Form(default=None),
    review_note: str | None = Form(default=None),
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
    return create_master_content_version(db, item_id=item_id, expected_current_version=expected_current_version, filename=file.filename if file else None, mime_type=file.content_type if file else None, content=payload, title=title, category_id=category_id, description=description, change_reason=change_reason, actor=_actor(role), idempotency_key=idempotency_key or str(uuid.uuid4()), correlation_id=request.state.correlation_id, source_surface=source_surface.upper() if source_surface.upper() in {"DASHBOARD", "ADMINISTRATION"} else "DASHBOARD", used_in=used_in, source_type_code=source_type_code, engineering_metadata=parsed_metadata, needs_review=needs_review, review_note=review_note)


@router.get("/master-content/{item_id}/download")
def download_current(item_id: str, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    item = db.get(MasterContentItem, item_id)
    if not item or not item.current_document_version_id:
        raise HTTPException(404, {"code": "CONTENT_NOT_FOUND"})
    version = db.get(DocumentVersion, item.current_document_version_id)
    if item_projection(db, item).get("governance", {}).get("profile", {}).get("restricted_reference_sample"):
        require_capability(role, "MASTER_RESTRICTED_SAMPLE_DOWNLOAD")
    return _download(db, version)


@router.get("/master-content/{item_id}/versions/{version_id}/download")
def download_version(item_id: str, version_id: str, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    item = db.get(MasterContentItem, item_id)
    version = db.get(DocumentVersion, version_id) if item else None
    if not item or not version or version.document_id != item.document_id:
        raise HTTPException(404, {"code": "VERSION_NOT_FOUND"})
    if item_projection(db, item).get("governance", {}).get("profile", {}).get("restricted_reference_sample"):
        require_capability(role, "MASTER_RESTRICTED_SAMPLE_DOWNLOAD")
    return _download(db, version)


@router.get("/master-content/{item_id}/versions/{version_id}/rendition")
def download_rendition(item_id: str, version_id: str, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    item = db.get(MasterContentItem, item_id)
    version = db.get(DocumentVersion, version_id) if item else None
    if not item or not version or version.document_id != item.document_id:
        raise HTTPException(404, {"code": "VERSION_NOT_FOUND"})
    if version.rendition_status != "SOURCE_PDF" or not version.rendition_path_or_reference:
        raise HTTPException(409, {"code": "RENDITION_NOT_AVAILABLE"})
    if item_projection(db, item).get("governance", {}).get("profile", {}).get("restricted_reference_sample"):
        require_capability(role, "MASTER_RESTRICTED_SAMPLE_VIEW")
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
    rows = [row for row in rows if _definition_role_can_see(role, row)]
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
    projection = definition_projection(db, definition, include_history=True)
    if not _definition_role_can_see(role, projection):
        raise HTTPException(403, {"code": "DEFINITION_NOT_APPLICABLE", "persona": persona_for_role(role)})
    return projection


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
