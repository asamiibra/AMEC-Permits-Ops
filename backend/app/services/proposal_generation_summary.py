"""One authoritative generation result for a Proposal V1 revision.

The editor, entry route, and AI Changes view must agree about what was
actually published.  Provider suggestions, citations, and owner edits are
kept separate from the persisted AI change plan.
"""
from __future__ import annotations

from typing import Any


PUBLISHED_STATES = {"PUBLISHED", "APPLIED", ""}


def _published_mutations(plan: dict[str, Any]) -> list[dict[str, Any]]:
    rows = plan.get("mutations") or []
    if not isinstance(rows, list):
        return []
    result: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        # A stored plan is publishable by default for backwards compatibility.
        # Explicit draft/rejected/unpublished rows are never counted as AI
        # document changes.
        state = str(row.get("published_status", row.get("publication_state", ""))).upper()
        if row.get("published") is False or state not in PUBLISHED_STATES:
            continue
        result.append(row)
    return result


def canonical_generation_summary(revision: Any | None) -> dict[str, Any]:
    """Project a revision into the single state consumed by Proposal V1 UI."""
    snapshot = (getattr(revision, "snapshot", None) or {}) if revision is not None else {}
    plan = snapshot.get("change_plan") or {}
    provenance = snapshot.get("ai_provenance") or {}
    validation = snapshot.get("generation_validation") or {}
    published = _published_mutations(plan)
    owner_mutations = snapshot.get("owner_mutations") or []
    if not isinstance(owner_mutations, list):
        owner_mutations = []

    generated_from_ai = provenance.get("generated_from_ai") is True
    document_version_id = snapshot.get("editor_document_version_id")
    validation_state = str(
        validation.get("state")
        or provenance.get("validation_state")
        or ("PASSED" if generated_from_ai and document_version_id and provenance.get("provenance_state") == "RECORDED" else "UNKNOWN")
    ).upper()
    if validation and (
        validation.get("full_document_generation") != "COMPLETE"
        or validation.get("full_document_validation") != "PASS"
        or validation.get("coverage_state") != "PASS"
    ):
        validation_state = "INCOMPLETE"
    no_change = str(plan.get("status") or "").upper() == "NO_AI_CHANGES_REQUIRED"
    if not generated_from_ai:
        state = "BASELINE_REVIEW"
        reason = "AI_GENERATION_REQUIRED"
    elif not published:
        state = "NO_AI_CHANGES_REQUIRED" if no_change and validation_state == "PASSED" else "GENERATION_REVIEW_REQUIRED"
        reason = None if state == "NO_AI_CHANGES_REQUIRED" else str(
            plan.get("review_reason") or "AI_NO_DOCUMENT_MUTATIONS"
        )
    elif not document_version_id or validation_state != "PASSED":
        state = "GENERATION_REVIEW_REQUIRED"
        reason = str(plan.get("review_reason") or "GENERATION_VALIDATION_REQUIRED")
    else:
        state = "READY_FOR_EDIT"
        reason = None

    source_set_hash = provenance.get("generated_from_manifest_hash") or provenance.get("source_set_hash") or snapshot.get("source_set_hash")
    return {
        "state": state,
        "published_ai_mutation_count": len(published),
        "owner_mutation_count": len(owner_mutations),
        "generation_review_reason": reason,
        "generated_from_ai": generated_from_ai,
        "generated_from_manifest_hash": source_set_hash,
        "validation_state": validation_state,
        "full_document_generation": validation.get("full_document_generation", "LEGACY_UNVERIFIED"),
        "full_document_validation": validation.get("full_document_validation", "LEGACY_UNVERIFIED"),
        "document_version_id": document_version_id,
        "published_mutations": published,
        "no_ai_changes_required": state == "NO_AI_CHANGES_REQUIRED",
    }


def persisted_generation_summary(revision: Any, *, summary: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return the summary and persist it in the revision snapshot when needed."""
    value = summary or canonical_generation_summary(revision)
    snapshot = dict(getattr(revision, "snapshot", None) or {})
    if snapshot.get("generation_summary") != value:
        snapshot["generation_summary"] = value
        revision.snapshot = snapshot
    return value
