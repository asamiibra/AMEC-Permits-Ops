"""Audit and reconciliation helpers for Proposal V1 canonical documents.

The register is intentionally not used as evidence here.  This module reads
the persisted editable ``ProposalRevision`` snapshot, its referenced
``DocumentVersion`` rows, and the current source manifest.  It is therefore
safe to use for a dry-run audit before creating a new revision.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import select, true
from sqlalchemy.orm import Session

from ..models import DocumentVersion, Opportunity, ProposalRevision, ProposalSourceLink
from ..services.proposal_generation_summary import canonical_generation_summary
from ..services.proposal_source_workspace import build_effective_proposal_source_manifest
from ..services.proposal_technical_report_template import TEMPLATE_ID, TEMPLATE_VERSION


CANONICAL_BASELINE_SELECTION = "GOVERNED_MASTER_CONTENT_TEMPLATE"
CANONICAL_CLASSIFICATION = "CURRENT_CANONICAL_AI_GENERATED"
CLASSIFICATIONS = {
    CANONICAL_CLASSIFICATION,
    "OLD_REVISION_NEEDS_REGENERATION",
    "GENERATION_FAILED",
    "SOURCE_MANIFEST_STALE",
    "TEMPLATE_MISMATCH",
    "PROVENANCE_MISSING",
}


def _latest_editable_revision(db: Session, proposal_id: str) -> ProposalRevision | None:
    return db.scalar(
        select(ProposalRevision)
        .where(ProposalRevision.proposal_id == proposal_id, ProposalRevision.status == "DRAFT")
        .order_by(ProposalRevision.revision_number.desc())
    )


def _version(db: Session, version_id: str | None) -> DocumentVersion | None:
    return db.get(DocumentVersion, version_id) if version_id else None


def _coverage(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    coverage = ((snapshot.get("change_plan") or {}).get("generation_coverage") or [])
    return coverage if isinstance(coverage, list) else []


def _manifest(db: Session, proposal: Opportunity) -> dict[str, Any]:
    try:
        return build_effective_proposal_source_manifest(db, proposal)
    except (KeyError, TypeError, ValueError):
        return {
            "source_manifest_hash": None,
            "completeness_state": "INCOMPLETE",
            "completeness_reasons": ["SOURCE_MANIFEST_UNAVAILABLE"],
            "scan_status": "UNAVAILABLE",
            "entries": [],
        }


def audit_proposal(db: Session, proposal: Opportunity) -> dict[str, Any]:
    """Return a persisted-revision audit row and its regeneration class."""
    from ..api.proposal_source_routers import (
        _baseline_is_complete,
        _captured_bytes,
        _docx_identity_matches,
        _proposal_baseline_identity,
    )

    revision = _latest_editable_revision(db, proposal.id)
    snapshot = dict(revision.snapshot or {}) if revision else {}
    provenance = dict(snapshot.get("ai_provenance") or {})
    summary = canonical_generation_summary(revision)
    workspace = (proposal.proposal_fields_json or {}).get("source_workspace") or {}
    manifest = _manifest(db, proposal)
    current_manifest_hash = manifest.get("source_manifest_hash")
    baseline_id = snapshot.get("editor_baseline_document_version_id")
    editor_id = snapshot.get("editor_document_version_id")
    baseline = _version(db, baseline_id)
    editor = _version(db, editor_id)
    baseline_meta = dict((baseline.metadata_json or {}) if baseline else {})
    template_contract = snapshot.get("template_contract") or {}
    template_id = provenance.get("template_id") or template_contract.get("template_id") or baseline_meta.get("template_id")
    template_version = provenance.get("template_version") or template_contract.get("template_version") or baseline_meta.get("template_version")
    generated_hash = provenance.get("generated_from_manifest_hash") or provenance.get("source_set_hash") or snapshot.get("source_set_hash")

    classification: str
    reasons: list[str] = []
    if revision is None:
        classification = "PROVENANCE_MISSING"
        reasons.append("NO_EDITABLE_REVISION")
    elif not provenance.get("generated_from_ai"):
        classification = "OLD_REVISION_NEEDS_REGENERATION" if editor is not None else "PROVENANCE_MISSING"
        reasons.append("REVISION_NOT_GENERATED_BY_PROPOSAL_AI")
    elif template_id != TEMPLATE_ID or str(template_version or "") != TEMPLATE_VERSION or snapshot.get("baseline_selection_method") != CANONICAL_BASELINE_SELECTION:
        classification = "TEMPLATE_MISMATCH"
        reasons.append("CANONICAL_TEMPLATE_CONTRACT_MISMATCH")
    elif not current_manifest_hash or generated_hash != current_manifest_hash or manifest.get("completeness_state") != "COMPLETE":
        classification = "SOURCE_MANIFEST_STALE"
        reasons.extend(manifest.get("completeness_reasons") or [])
        if generated_hash != current_manifest_hash:
            reasons.append("GENERATED_SOURCE_MANIFEST_HASH_MISMATCH")
    else:
        validation = snapshot.get("generation_validation") or {}
        package_valid = False
        identity_valid = False
        try:
            if editor is not None:
                content = _captured_bytes(editor)
                package_valid = _baseline_is_complete(editor)
                identity_valid = _docx_identity_matches(content, _proposal_baseline_identity(db, proposal, [editor]))
        except Exception:
            package_valid = False
        if not editor or not snapshot.get("editor_document_version_id") or not package_valid or not identity_valid:
            classification = "GENERATION_FAILED"
            reasons.append("GENERATED_DOCX_UNAVAILABLE_OR_INVALID")
        elif summary.get("state") not in {"READY_FOR_EDIT", "NO_AI_CHANGES_REQUIRED"} or validation.get("full_document_generation") != "COMPLETE" or validation.get("full_document_validation") != "PASS":
            classification = "GENERATION_FAILED"
            reasons.append("GENERATION_VALIDATION_INCOMPLETE")
        else:
            classification = CANONICAL_CLASSIFICATION

    if classification not in CLASSIFICATIONS:  # pragma: no cover - defensive contract guard
        classification = "GENERATION_FAILED"
    source_links = db.scalars(
        select(ProposalSourceLink).where(ProposalSourceLink.proposal_id == proposal.id, ProposalSourceLink.active == true())
    ).all()
    source_ids = [link.document_version_id for link in source_links]
    return {
        "proposal_id": proposal.id,
        "proposal_reference": proposal.opportunity_reference,
        "project_number": workspace.get("project_number") or proposal.canonical_project_reference or proposal.provisional_reference,
        "project_name": _proposal_baseline_identity(db, proposal, [] if not source_ids else [v for link in source_links if (v := _version(db, link.document_version_id)) is not None]).get("project_name"),
        "current_revision_id": revision.id if revision else None,
        "current_revision_number": revision.revision_number if revision else None,
        "current_revision_status": revision.status if revision else None,
        "baseline_selection_method": snapshot.get("baseline_selection_method"),
        "template_id": template_id,
        "template_version": template_version,
        "baseline_document_version_id": baseline_id,
        "baseline_sha256": baseline.sha256 if baseline else snapshot.get("baseline_hash"),
        "editor_document_version_id": editor_id,
        "editor_document_sha256": editor.sha256 if editor else snapshot.get("working_hash"),
        "ai_provenance": {
            "generated_from_ai": provenance.get("generated_from_ai") is True,
            "template_id": provenance.get("template_id"),
            "template_version": provenance.get("template_version"),
            "source_set_hash": provenance.get("source_set_hash") or provenance.get("generated_from_manifest_hash"),
            "work_product_id": provenance.get("work_product_id"),
        },
        "current_source_manifest_hash": current_manifest_hash,
        "source_manifest_completeness_state": manifest.get("completeness_state"),
        "source_manifest_completeness_reasons": manifest.get("completeness_reasons") or [],
        "source_manifest_scan_status": manifest.get("scan_status"),
        "generation_state": (proposal.proposal_fields_json or {}).get("generation_state") or summary.get("state"),
        "generation_summary": summary,
        "AI_mutation_count": provenance.get("published_ai_mutation_count", provenance.get("mutation_count", summary.get("published_ai_mutation_count", 0))),
        "generation_coverage": _coverage(snapshot),
        "classification": classification,
        "classification_reasons": sorted(set(reasons)),
        "source_version_count": len(source_ids),
        "rendered_and_downloaded_document_version_id": editor_id,
        "rendered_and_downloaded_document_sha256": editor.sha256 if editor else None,
    }


def audit_references(db: Session, references: list[str]) -> dict[str, Any]:
    """Audit exact references without mutating any record."""
    rows: list[dict[str, Any]] = []
    missing: list[str] = []
    for reference in references:
        proposal = db.scalar(select(Opportunity).where(Opportunity.opportunity_reference == reference))
        if proposal is None:
            missing.append(reference)
            continue
        rows.append(audit_proposal(db, proposal))
    return {"references": references, "missing_references": missing, "rows": rows, "mutated": False}

