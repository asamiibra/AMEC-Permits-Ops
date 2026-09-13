"""Deterministic provider citation projection and validation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .contracts import AIContextManifest, AIContextItem
from .errors import AIError
from .structured_output import TechnicalMethodologyDraft, StructuredOutputDefinition


@dataclass(frozen=True)
class ProviderEvidence:
    citation_key: str
    content_trust_class: str
    content: str
    canonical_entity_type: str
    canonical_entity_id: str
    document_version_id: str | None
    verification_state: str
    source_currentness_state: str | None


def build_evidence(manifest: AIContextManifest) -> tuple[ProviderEvidence, ...]:
    return tuple(
        ProviderEvidence(
            citation_key=f"CIT-{index:03d}",
            content_trust_class=item.content_trust_class,
            content=item.content,
            canonical_entity_type=item.canonical_entity_type,
            canonical_entity_id=item.canonical_entity_id,
            document_version_id=item.document_version_id,
            verification_state=item.verification_state,
            source_currentness_state=item.source_currentness_state,
        )
        for index, item in enumerate(manifest.items, 1)
    )


def validate_citations(draft: TechnicalMethodologyDraft, manifest: AIContextManifest) -> dict[str, dict[str, Any]]:
    evidence = {item.citation_key: item for item in build_evidence(manifest)}
    manifest_items = {f"CIT-{index:03d}": item for index, item in enumerate(manifest.items, 1)}
    keys = [key for section in draft.sections for key in section.citation_keys]
    keys.extend(key for assumption in draft.assumptions for key in assumption.citation_keys)
    if any(key not in evidence for key in keys):
        raise AIError("AI_CITATION_VALIDATION_FAILED", status_code=502)
    return {
        key: {
            "citation_key": item.citation_key,
            "content_trust_class": item.content_trust_class,
            "canonical_entity_type": item.canonical_entity_type,
            "canonical_entity_id": item.canonical_entity_id,
            "document_id": manifest_item.citation.document_id,
            "document_version_id": item.document_version_id,
            "locator_type": manifest_item.citation.locator_type,
            "locator": manifest_item.citation.locator,
            "source_hash": manifest_item.citation.source_hash,
            "verification_state": item.verification_state,
            "source_currentness_state": item.source_currentness_state,
        }
        for key, item in evidence.items()
        for manifest_item in (manifest_items[key],)
        if key in set(keys)
    }


def validate_compiled_citations(
    output: Any,
    compiled_context: Any,
    definition: StructuredOutputDefinition,
) -> tuple[dict[str, Any], ...]:
    """Map model citation keys only to the frozen P04 context items."""

    try:
        keys = tuple(definition.citation_keys(output))
    except Exception as exc:
        raise AIError("AI_CITATION_VALIDATION_FAILED", status_code=502) from exc
    if definition.requires_grounding and not keys:
        raise AIError("AI_CITATION_VALIDATION_FAILED", status_code=502)
    if any(not isinstance(key, str) or not key.startswith("CIT-") for key in keys):
        raise AIError("AI_CITATION_VALIDATION_FAILED", status_code=502)

    context_items = tuple(compiled_context.items)
    by_key = {f"CIT-{index:03d}": item for index, item in enumerate(context_items, 1)}
    ordered_keys = tuple(dict.fromkeys(keys))
    if any(key not in by_key for key in ordered_keys):
        raise AIError("AI_CITATION_VALIDATION_FAILED", status_code=502)

    citations: list[dict[str, Any]] = []
    for ordinal, key in enumerate(ordered_keys, 1):
        item = by_key[key]
        citations.append(
            {
                "ordinal": ordinal,
                "source_type": item.dependency_type,
                "source_id": item.dependency_id,
                "source_version_or_hash": item.dependency_version_or_hash,
                "locator_json": {
                    "context_snapshot_id": compiled_context.context_snapshot_id,
                    "context_key": item.key,
                    "citation_key": key,
                },
            }
        )
    return tuple(citations)
