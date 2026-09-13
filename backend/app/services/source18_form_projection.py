"""Read-only Content Library projection of Source18 official forms.

Source18 owns official-form identity, currentness, and authority-field truth.
This adapter deliberately performs no writes and does not create a second
official-form registry.  A row is reusable only when the Source18 transaction,
AuthorityCase, and exact DocumentVersion all agree on currentness.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import (
    AuthorityCase,
    DocumentVersion,
    ExternalBody,
    Jurisdiction,
    ServiceType,
    Source18WorkflowTransaction,
)


def _currentness(case: AuthorityCase, transaction: Source18WorkflowTransaction, version: DocumentVersion | None) -> tuple[str, bool]:
    """Return a conservative display state and whether reuse is permitted."""
    if not version:
        return "UNRESOLVED", False
    transaction_state = str(transaction.currentness_state or "UNKNOWN").upper()
    document_state = str((version.metadata_json or {}).get("official_form_currentness") or "UNKNOWN").upper()
    case_state = str(case.current_official_form_verified or "UNKNOWN").upper()
    if transaction_state == "CURRENT" and document_state == "CURRENT" and case_state in {"TRUE", "CURRENT", "VERIFIED_CURRENT"}:
        return "CURRENT", True
    if transaction_state in {"STALE", "NOT_CURRENT", "SUPERSEDED"} or document_state in {"STALE", "NOT_CURRENT", "SUPERSEDED"} or case_state in {"FALSE", "NOT_CURRENT", "VERIFIED_NOT_CURRENT"}:
        return "STALE", False
    return "UNVERIFIED", False


def _authority_only_fields(case: AuthorityCase) -> list[str]:
    schema = case.field_authority_schema_json or {}
    fields = schema.get("authority_only_fields") or schema.get("authority_only") or []
    if isinstance(fields, dict):
        fields = [key for key, value in fields.items() if value]
    return sorted({str(value) for value in fields})


def _projection(db: Session, transaction: Source18WorkflowTransaction, case: AuthorityCase) -> dict[str, Any]:
    version = db.get(DocumentVersion, transaction.official_form_version_id)
    case_version_matches = case.official_form_version_id == transaction.official_form_version_id
    version_is_source18 = bool(version and str(version.source_system or "").upper() == "SOURCE18")
    body = db.get(ExternalBody, case.external_body_id)
    jurisdiction = db.get(Jurisdiction, case.jurisdiction_id)
    service = db.get(ServiceType, case.service_type_id)
    currentness, reusable = _currentness(case, transaction, version)
    if not case_version_matches or not version_is_source18:
        currentness, reusable = "UNRESOLVED", False
    return {
        "projection_type": "SOURCE18_OFFICIAL_FORM_READ_ONLY",
        "read_only": True,
        "authority_owner": "SOURCE18",
        "title": case.official_form_number or transaction.transaction_type or case.case_reference,
        "source18": {
            "transaction_id": transaction.id,
            "authority_case_id": case.id,
            "case_reference": case.case_reference,
        },
        "document_version": {
            "id": version.id if version else None,
            "document_id": version.document_id if version else None,
            "version_number": version.version_number if version else None,
            "sha256": version.sha256 if version else None,
            "source_filename": version.source_filename if version else None,
            "revision_label": version.revision_label if version else None,
            "source_reference": version.source_path_or_reference if version else None,
        },
        "binding": {
            "case_version_matches_transaction": case_version_matches,
            "document_version_source_system_is_source18": version_is_source18,
        },
        "authority": {
            "publisher": case.official_form_publisher,
            "external_body_id": case.external_body_id,
            "external_body": body.name_en if body else None,
            "jurisdiction_id": case.jurisdiction_id,
            "jurisdiction": jurisdiction.name_en if jurisdiction else None,
            "service_type_id": case.service_type_id,
            "service_type": service.name_en if service else None,
            "transaction_type": case.transaction_type or transaction.transaction_type,
            "official_form_number": case.official_form_number,
            "official_form_revision": case.official_form_revision,
            "field_authority_fields": _authority_only_fields(case),
        },
        "currentness": {
            "state": currentness,
            "reusable": reusable,
            "source18_transaction_state": transaction.currentness_state,
            "source18_case_verified": case.current_official_form_verified,
            "document_metadata_state": (version.metadata_json or {}).get("official_form_currentness") if version else None,
            "retrieved_at": case.official_form_retrieved_at.isoformat() if case.official_form_retrieved_at else None,
        },
        "provenance": {
            "source_system": version.source_system if version else None,
            "source_hash": version.sha256 if version else None,
            "evidence": (case.field_authority_schema_json or {}).get("currentness_evidence", {}),
        },
        "reuse": {
            "allowed": reusable,
            "blocked_reason": None if reusable else "SOURCE18_OFFICIAL_FORM_BINDING_NOT_EXACT_CURRENT",
        },
    }


def source18_official_form_projection(db: Session, *, include_non_current: bool = True) -> list[dict[str, Any]]:
    """Read Source18 official-form bindings as a typed, non-authoritative view."""
    rows: list[dict[str, Any]] = []
    transactions = db.scalars(
        select(Source18WorkflowTransaction)
        .where(Source18WorkflowTransaction.official_form_version_id.is_not(None))
        .order_by(Source18WorkflowTransaction.created_at, Source18WorkflowTransaction.id)
    ).all()
    for transaction in transactions:
        case = db.get(AuthorityCase, transaction.authority_case_id)
        if not case:
            continue
        row = _projection(db, transaction, case)
        if include_non_current or row["reuse"]["allowed"]:
            rows.append(row)
    return rows


def resolve_source18_official_form(db: Session, *, transaction_id: str | None = None, authority_case_id: str | None = None) -> dict[str, Any]:
    """Resolve exactly one current Source18 form, failing closed on ambiguity."""
    statement = select(Source18WorkflowTransaction).where(Source18WorkflowTransaction.official_form_version_id.is_not(None))
    if transaction_id:
        statement = statement.where(Source18WorkflowTransaction.id == transaction_id)
    if authority_case_id:
        statement = statement.where(Source18WorkflowTransaction.authority_case_id == authority_case_id)
    candidates = []
    for transaction in db.scalars(statement.order_by(Source18WorkflowTransaction.created_at, Source18WorkflowTransaction.id)).all():
        case = db.get(AuthorityCase, transaction.authority_case_id)
        if case:
            row = _projection(db, transaction, case)
            if row["reuse"]["allowed"]:
                candidates.append(row)
    if len(candidates) == 1:
        return {"status": "RESOLVED", "canonical_count": 1, "item": candidates[0], "candidates": candidates, "truth": "SOURCE18"}
    return {"status": "AMBIGUOUS" if candidates else "UNRESOLVED", "canonical_count": len(candidates), "item": None, "candidates": candidates, "truth": "SOURCE18"}


def source18_authority_item_ids(db: Session) -> set[str]:
    """Return no Content Library IDs: authority is intentionally not duplicated."""
    return set()
