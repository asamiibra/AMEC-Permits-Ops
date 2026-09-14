"""Typed read-only projection of Source18 official forms for Content Library."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import (
    AuthorityCase,
    Document,
    DocumentApprovalState,
    DocumentVersion,
    ExternalBody,
    Jurisdiction,
    MasterContentItem,
    ServiceType,
    Source18WorkflowTransaction,
)


def _projection(db: Session, transaction: Source18WorkflowTransaction, case: AuthorityCase) -> dict[str, Any]:
    version = db.get(DocumentVersion, transaction.official_form_version_id)
    document = db.get(Document, version.document_id) if version else None
    case_match = case.official_form_version_id == transaction.official_form_version_id
    source18 = bool(version and str(version.source_system or "").upper() == "SOURCE18" and document and str(document.source_system or "").upper() == "SOURCE18")
    document_current = bool(version and document and document.current_version_id == version.id)
    unsuperseded = bool(version and version.superseded_by is None)
    reviewed = bool(version and version.approval_state in {DocumentApprovalState.REVIEWED, DocumentApprovalState.APPROVED})
    metadata_current = str((version.metadata_json or {}).get("official_form_currentness") or "UNKNOWN").upper() == "CURRENT" if version else False
    affirmative_case = str(case.current_official_form_verified or "").upper() in {"TRUE", "CURRENT", "VERIFIED_CURRENT"}
    current = bool(transaction.currentness_state == "CURRENT" and case_match and source18 and document_current and unsuperseded and reviewed and metadata_current and affirmative_case)
    transaction_state = str(transaction.currentness_state or "UNKNOWN").upper()
    metadata_state = str((version.metadata_json or {}).get("official_form_currentness") or "UNKNOWN").upper() if version else "UNKNOWN"
    if current:
        state, reusable = "CURRENT", True
    elif transaction_state in {"STALE", "NOT_CURRENT", "SUPERSEDED"} or metadata_state in {"STALE", "NOT_CURRENT", "SUPERSEDED"}:
        state, reusable = "STALE", False
    else:
        state, reusable = "UNVERIFIED", False
    body = db.get(ExternalBody, case.external_body_id)
    jurisdiction = db.get(Jurisdiction, case.jurisdiction_id)
    service = db.get(ServiceType, case.service_type_id)
    fields = (case.field_authority_schema_json or {}).get("authority_only_fields") or (case.field_authority_schema_json or {}).get("authority_only") or []
    if isinstance(fields, dict):
        fields = [key for key, enabled in fields.items() if enabled]
    return {
        "projection_type": "SOURCE18_OFFICIAL_FORM_READ_ONLY", "authority_owner": "SOURCE18", "read_only": True,
        "title": case.official_form_number or transaction.transaction_type or case.case_reference,
        "source18": {"transaction_id": transaction.id, "authority_case_id": case.id, "case_reference": case.case_reference},
        "document_version": {"id": version.id if version else None, "document_id": version.document_id if version else None, "version_number": version.version_number if version else None, "sha256": version.sha256 if version else None, "source_filename": version.source_filename if version else None, "revision_label": version.revision_label if version else None, "source_reference": version.source_path_or_reference if version else None},
        "binding": {"case_version_matches_transaction": case_match, "document_version_source_system_is_source18": source18, "document_current_version_matches": document_current, "document_version_is_unsuperseded": unsuperseded, "document_version_is_reviewed": reviewed},
        "authority": {"publisher": case.official_form_publisher, "external_body_id": case.external_body_id, "external_body": body.name_en if body else None, "jurisdiction_id": case.jurisdiction_id, "jurisdiction": jurisdiction.name_en if jurisdiction else None, "service_type_id": case.service_type_id, "service_type": service.name_en if service else None, "transaction_type": case.transaction_type or transaction.transaction_type, "official_form_number": case.official_form_number, "official_form_revision": case.official_form_revision, "field_authority_fields": sorted({str(value) for value in fields})},
        "currentness": {"state": state, "reusable": reusable, "source18_transaction_state": transaction.currentness_state, "source18_case_verified": case.current_official_form_verified, "document_metadata_state": (version.metadata_json or {}).get("official_form_currentness") if version else None, "retrieved_at": case.official_form_retrieved_at.isoformat() if case.official_form_retrieved_at else None},
        "provenance": {"source_system": version.source_system if version else None, "source_hash": version.sha256 if version else None, "evidence": (case.field_authority_schema_json or {}).get("currentness_evidence", {})},
        "reuse": {"allowed": reusable, "blocked_reason": None if reusable else "SOURCE18_OFFICIAL_FORM_BINDING_NOT_EXACT_CURRENT"},
    }


def source18_official_form_projection(db: Session, *, include_non_current: bool = True) -> list[dict[str, Any]]:
    rows = []
    for transaction in db.scalars(select(Source18WorkflowTransaction).where(Source18WorkflowTransaction.official_form_version_id.is_not(None)).order_by(Source18WorkflowTransaction.created_at, Source18WorkflowTransaction.id)).all():
        case = db.get(AuthorityCase, transaction.authority_case_id)
        if not case:
            continue
        row = _projection(db, transaction, case)
        if include_non_current or row["reuse"]["allowed"]:
            rows.append(row)
    return rows


def resolve_source18_official_form(db: Session, *, transaction_id: str | None = None, authority_case_id: str | None = None) -> dict[str, Any]:
    rows = source18_official_form_projection(db, include_non_current=False)
    if transaction_id:
        rows = [row for row in rows if row["source18"]["transaction_id"] == transaction_id]
    if authority_case_id:
        rows = [row for row in rows if row["source18"]["authority_case_id"] == authority_case_id]
    return {"status": "RESOLVED" if len(rows) == 1 else "AMBIGUOUS" if rows else "UNRESOLVED", "canonical_count": len(rows), "item": rows[0] if len(rows) == 1 else None, "candidates": rows, "truth": "SOURCE18"}


def source18_authority_item_ids(db: Session) -> set[str]:
    return set(db.scalars(select(MasterContentItem.id).join(DocumentVersion, DocumentVersion.document_id == MasterContentItem.document_id).join(Source18WorkflowTransaction, Source18WorkflowTransaction.official_form_version_id == DocumentVersion.id)).all())
