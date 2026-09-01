"""Explicit AuthorityCase-only governed assist preview API."""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from ..api.dependencies import current_user_role
from ..db import get_db
from ..models import Role
from ..services.governed_prefill import preview_prefill
from .permit_ux_routers import _case_access, _actor

router = APIRouter(prefix="/api/governed-prefill", tags=["governed-prefill"])
ALLOWED = {Role.OWNER_SPONSOR, Role.SYSTEM_ADMIN, Role.PERMIT_PREPARER}

class PrefillPreviewRequest(BaseModel):
    master_content_id: str = Field(min_length=1)
    context_entity_type: str = Field(default="AuthorityCase", min_length=1)
    context_entity_id: str = Field(min_length=1)
    purpose: str = Field(default="FORM_PREPARATION", min_length=1, max_length=120)
    expected_document_version_id: str | None = None
    expected_mapping_release_id: str | None = None

@router.post("/preview")
def governed_prefill_preview(payload: PrefillPreviewRequest, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    if role not in ALLOWED or payload.context_entity_type != "AuthorityCase": raise HTTPException(status_code=403, detail={"code": "PREFILL_CONTEXT_NOT_ALLOWED"})
    case, _journey, project = _case_access(db, request, role, payload.context_entity_id)
    try:
        return preview_prefill(db, role=role, caller_id=_actor(request, role), project_id=project.id, case_id=case.id, master_content_id=payload.master_content_id, purpose=payload.purpose, expected_document_version_id=payload.expected_document_version_id, expected_mapping_release_id=payload.expected_mapping_release_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail={"code": str(exc)}) from exc
