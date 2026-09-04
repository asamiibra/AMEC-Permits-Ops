"""Explicit AuthorityCase-only governed assist preview API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..audit.service import audit
from ..api.dependencies import current_user_role
from ..db import get_db
from ..models import Role
from ..services.governed_prefill import apply_governed_prefill_to_draft, preview_prefill
from .permit_ux_routers import _case_access, _actor

router = APIRouter(prefix="/api/governed-prefill", tags=["governed-prefill"])
ALLOWED = {Role.OWNER_SPONSOR, Role.SYSTEM_ADMIN, Role.PERMIT_PREPARER}


class PrefillPreviewRequest(BaseModel):
    master_content_id: str = Field(min_length=1)
    context_entity_type: str = Field(default="AuthorityCase", min_length=1)
    context_entity_id: str = Field(min_length=1)
    purpose: str = Field(default="FORM_PREPARATION", min_length=1, max_length=120)
    form_instance_id: str | None = Field(default=None, min_length=1)
    expected_document_version_id: str | None = None
    expected_mapping_release_id: str | None = None


class GovernedPrefillApplyRequest(BaseModel):
    form_instance_id: str = Field(min_length=1)
    context_entity_type: str = Field(default="AuthorityCase", min_length=1)
    context_entity_id: str = Field(min_length=1)
    purpose: str = Field(default="FORM_PREPARATION", min_length=1, max_length=120)
    preview_fingerprint: str = Field(min_length=64, max_length=128)
    expected_draft_revision: int = Field(ge=0)
    idempotency_key: str = Field(min_length=1, max_length=200)
    selected_field_keys: list[str] | None = Field(default=None, max_length=100)


@router.post("/preview")
def governed_prefill_preview(payload: PrefillPreviewRequest, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    if role not in ALLOWED or payload.context_entity_type != "AuthorityCase":
        raise HTTPException(status_code=403, detail={"code": "PREFILL_CONTEXT_NOT_ALLOWED"})
    case, _journey, project = _case_access(db, request, role, payload.context_entity_id)
    try:
        return preview_prefill(db, role=role, caller_id=_actor(request, role), project_id=project.id, case_id=case.id, master_content_id=payload.master_content_id, purpose=payload.purpose, form_instance_id=payload.form_instance_id, expected_document_version_id=payload.expected_document_version_id, expected_mapping_release_id=payload.expected_mapping_release_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail={"code": str(exc)}) from exc


@router.post("/apply")
def governed_prefill_apply(payload: GovernedPrefillApplyRequest, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    if role not in ALLOWED or payload.context_entity_type != "AuthorityCase":
        raise HTTPException(status_code=403, detail={"code": "PREFILL_CONTEXT_NOT_ALLOWED"})
    case, _journey, project = _case_access(db, request, role, payload.context_entity_id)
    try:
        result = apply_governed_prefill_to_draft(
            db,
            role=role,
            actor_id=_actor(request, role),
            project_id=project.id,
            case_id=case.id,
            purpose=payload.purpose,
            form_instance_id=payload.form_instance_id,
            preview_fingerprint=payload.preview_fingerprint,
            expected_draft_revision=payload.expected_draft_revision,
            idempotency_key=payload.idempotency_key,
            selected_field_keys=payload.selected_field_keys,
        )
        db.commit()
        return result
    except ValueError as exc:
        db.rollback()
        audit(
            db,
            correlation_id=getattr(request.state, "correlation_id", "governed-prefill-apply"),
            event_type="GOVERNED_PREFILL_APPLY_REJECTED",
            entity_type="FormInstance",
            entity_id=payload.form_instance_id,
            actor_id=_actor(request, role),
            after={"code": str(exc), "preview_fingerprint": payload.preview_fingerprint},
            metadata={"idempotency_key": payload.idempotency_key, "context_id": case.id},
        )
        db.commit()
        raise HTTPException(status_code=409, detail={"code": str(exc)}) from exc
