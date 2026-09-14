"""Content Library Intelligence API.

The client sends only a bounded operation.  Manifest, version, context,
provider, tools, and authority are server-owned.
"""
from __future__ import annotations

from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..api.dependencies import AuthenticatedPrincipal, trusted_current_principal
from ..config.settings import get_settings
from ..db import get_db
from ..models import AIWorkProduct, DefinitionEntry, IntelligenceCitation, MasterContentItem
from ..services.content_library_intelligence import _ensure_definition_scope, execute_content_library_intelligence
from ..services.master_content import authorize_master_content_access

router = APIRouter(prefix="/api/master-content", tags=["content-library-intelligence"])


def _authorize_library_subject(db: Session, principal: AuthenticatedPrincipal, item_id: str) -> str:
    item = db.get(MasterContentItem, item_id)
    if item is not None:
        try:
            authorize_master_content_access(db, item, principal.role, action="AI_READ")
        except HTTPException as exc:
            raise HTTPException(403, detail={"code": "AI_CONTEXT_SCOPE_UNPROVABLE"}) from exc
        return "MASTER_CONTENT_ITEM"
    definition = db.get(DefinitionEntry, item_id)
    if definition is not None:
        try:
            _ensure_definition_scope(principal, definition)
        except HTTPException as exc:
            raise HTTPException(403, detail={"code": "AI_CONTEXT_SCOPE_UNPROVABLE"}) from exc
        return "DEFINITION_ENTRY"
    raise HTTPException(404, detail={"code": "MASTER_CONTENT_NOT_FOUND"})


@router.post("/{item_id}/intelligence/{operation}")
def run_intelligence(
    item_id: str,
    operation: str,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(trusted_current_principal)],
    db: Session = Depends(get_db),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    correlation_id: str | None = Header(default=None, alias="X-Correlation-ID"),
) -> dict[str, object]:
    if not idempotency_key or not idempotency_key.strip():
        raise HTTPException(400, detail={"code": "IDEMPOTENCY_KEY_REQUIRED"})
    correlation = (correlation_id or getattr(request.state, "correlation_id", None) or str(uuid4()))[:100]
    return execute_content_library_intelligence(
        db,
        principal,
        item_id=item_id,
        operation=operation,
        idempotency_key=idempotency_key,
        correlation_id=correlation,
        settings=get_settings(),
    )


@router.get("/{item_id}/intelligence")
def intelligence_history(
    item_id: str,
    principal: Annotated[AuthenticatedPrincipal, Depends(trusted_current_principal)],
    db: Session = Depends(get_db),
) -> dict[str, object]:
    _authorize_library_subject(db, principal, item_id)
    products = db.scalars(
        select(AIWorkProduct)
        .where(
            AIWorkProduct.owning_module == "master_content",
            AIWorkProduct.scope_id == item_id,
        )
        .order_by(AIWorkProduct.created_at.desc())
    ).all()
    return {"item_id": item_id, "work_products": [{
        "id": product.id,
        "skill_id": product.skill_id,
        "skill_version": product.skill_version,
        "skill_manifest_hash": product.skill_manifest_hash,
        "document_version_id": (product.structured_output_json or {}).get("source_identity", {}).get("document_version_id"),
        "state": product.state,
        "output_class": product.output_class,
        "citation_count": product.citation_count,
        "created_at": product.created_at.isoformat() if product.created_at else None,
        "stale_reason": product.stale_reason,
    } for product in products]}


@router.get("/{item_id}/intelligence/work-products/{work_product_id}")
def intelligence_work_product(
    item_id: str,
    work_product_id: str,
    principal: Annotated[AuthenticatedPrincipal, Depends(trusted_current_principal)],
    db: Session = Depends(get_db),
) -> dict[str, object]:
    _authorize_library_subject(db, principal, item_id)
    product = db.get(AIWorkProduct, work_product_id)
    if product is None or product.owning_module != "master_content" or product.scope_id != item_id:
        raise HTTPException(404, detail={"code": "AI_WORK_PRODUCT_NOT_FOUND"})
    citations = db.scalars(
        select(IntelligenceCitation)
        .where(IntelligenceCitation.work_product_id == product.id)
        .order_by(IntelligenceCitation.ordinal)
    ).all()
    return {
        "id": product.id,
        "item_id": item_id,
        "skill_id": product.skill_id,
        "skill_version": product.skill_version,
        "skill_manifest_hash": product.skill_manifest_hash,
        "output_class": product.output_class,
        "state": product.state,
        "stale_reason": product.stale_reason,
        "output": product.structured_output_json,
        "citations": [{
            "ordinal": citation.ordinal,
            "source_type": citation.source_type,
            "source_id": citation.source_id,
            "source_version_or_hash": citation.source_version_or_hash,
            "locator": citation.locator_json,
        } for citation in citations],
        "canonical_state_mutated": False,
        "protected_action_count": 0,
    }
