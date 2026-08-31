"""Permission-aware, citation-preserving retrieval over canonical records.

This module is deliberately a read-only boundary.  It does not own business
state, source binaries, versions, definitions, or workflow mutations.  A
future derived index may implement the same contract, but the canonical IDs
and source/version citations must remain authoritative.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..models import (
    AssertionStatus,
    DefinitionEntry,
    DefinitionRevision,
    Document,
    DocumentClassification,
    DocumentVersion,
    FieldObservation,
    MasterContentGovernanceProfile,
    MasterContentItem,
    MasterContentModuleBinding,
    MasterContentSourceProvenance,
    Role,
    VerifiedAssertion,
)
from .master_content import read_master_content_bytes


RETRIEVAL_CONTRACT_VERSION = "1.0"
RETRIEVAL_CANONICAL_WRITE_COUNT = 0
RETRIEVAL_SECOND_CANONICAL_DATABASE_COUNT = 0
AUTHORIZED_MASTER_MODULES: dict[Role, str] = {
    Role.PROCESS_CHAMPION: "BD",
    Role.RESPONSIBLE_ENGINEER: "ENGINEERING",
    Role.PERMIT_PREPARER: "PERMIT",
}
OWNER_ROLES = frozenset({Role.OWNER_SPONSOR, Role.SYSTEM_ADMIN})


class RetrievalAccessContext(BaseModel):
    """Trusted authorization context passed by the authenticated boundary.

    Project membership is intentionally explicit.  The HTTP adapter does not
    invent membership from a browser query parameter; production identity
    integration must populate this context from the existing RBAC boundary.
    """

    model_config = ConfigDict(frozen=True)

    caller_id: str = Field(min_length=1)
    role: Role
    project_ids: tuple[str, ...] = ()
    purpose: str = Field(default="READ", min_length=1)

    def may_read_project(self, project_id: str | None) -> bool:
        return bool(project_id and (self.role in OWNER_ROLES or project_id in self.project_ids))

    def may_read_master(self, item: MasterContentItem) -> bool:
        if self.role in OWNER_ROLES:
            return True
        module = AUTHORIZED_MASTER_MODULES.get(self.role)
        if not module:
            return False
        bindings = item.used_in or []
        return module in bindings


class RetrievalQuery(BaseModel):
    model_config = ConfigDict(frozen=True)

    query: str | None = Field(default=None, max_length=500)
    master_content_id: str | None = None
    document_version_id: str | None = None
    definition_entry_id: str | None = None
    project_id: str | None = None
    limit: int = Field(default=20, ge=1, le=50)


class RetrievalCitation(BaseModel):
    model_config = ConfigDict(frozen=True)

    canonical_domain: str
    canonical_entity_type: str
    canonical_entity_id: str
    document_id: str | None = None
    document_version_id: str | None = None
    locator_type: str = "DOCUMENT_VERSION"
    locator: str = ""
    source_hash: str | None = None


class GovernedRetrievalEnvelope(BaseModel):
    """Versioned cross-domain envelope; all IDs point back to canonical data."""

    model_config = ConfigDict(frozen=True)

    contract_version: Literal["1.0"] = RETRIEVAL_CONTRACT_VERSION
    canonical_domain: str
    canonical_entity_type: str
    canonical_entity_id: str
    master_content_id: str | None = None
    transactional_entity_id: str | None = None
    document_id: str | None = None
    document_version_id: str | None = None
    definition_entry_id: str | None = None
    definition_revision_id: str | None = None
    source_artifact_id: str | None = None
    source_intake_id: str | None = None
    source_currentness_state: str | None = None
    verification_state: str
    authority_source_class: str | None = None
    superseded: bool = False
    sensitivity_class: str = "NONE"
    relationship_context: dict[str, Any] = Field(default_factory=dict)
    content: str
    citation: RetrievalCitation


class GovernedRetrievalResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    envelope: GovernedRetrievalEnvelope
    score_reason: str


class GovernedAIAnswer(BaseModel):
    model_config = ConfigDict(frozen=True)

    contract_version: Literal["1.0"] = RETRIEVAL_CONTRACT_VERSION
    question: str
    answer: str
    citations: tuple[RetrievalCitation, ...]
    authoritative_fact: bool
    inference_disclaimer: str
    canonical_state_mutated: bool = False


class UnauthorizedRetrieval(Exception):
    """Raised before content is read into retrieval context."""


def access_context_for_role(role: Role, *, caller_id: str = "synthetic-caller", project_ids: tuple[str, ...] = (), purpose: str = "READ") -> RetrievalAccessContext:
    return RetrievalAccessContext(caller_id=caller_id, role=role, project_ids=project_ids, purpose=purpose)


def _text_matches(query: str | None, *values: str | None) -> bool:
    return _match_rank(query, tuple(("value", value) for value in values)) is not None


def _normalized_text(value: str | None) -> str:
    return " ".join((value or "").casefold().split())


def _normalized_identifier(value: str | None) -> str:
    # Identifiers such as FORM-001 and FORM 001 are the same lookup key, while
    # Unicode word characters retain bilingual references and labels.
    return re.sub(r"[^\w]", "", (value or "").casefold(), flags=re.UNICODE)


def _match_rank(query: str | None, fields: tuple[tuple[str, str | None], ...]) -> tuple[int, ...] | None:
    """Return an explainable, deterministic lexical tier for a candidate.

    This is intentionally a small SQL-backed-candidate ranking layer, not a
    second search engine.  All query terms remain mandatory; the rank only
    orders already matching canonical records.
    """
    if not query:
        return (0, 0, 0, 0, 0, 0)
    normalized_query = _normalized_text(query)
    query_identifier = _normalized_identifier(query)
    terms = tuple(re.findall(r"[\w]+", normalized_query, flags=re.UNICODE))
    if not terms:
        return None
    exact_identifier = 0
    exact_title = 0
    exact_phrase = 0
    best_field = 0
    matched_terms = 0
    for index, (kind, value) in enumerate(fields):
        normalized = _normalized_text(value)
        identifier = _normalized_identifier(value)
        if query_identifier and identifier and query_identifier == identifier:
            exact_identifier = max(exact_identifier, 2 if kind in {"ref", "official_source"} else 1)
        if normalized_query == normalized and normalized:
            exact_title = max(exact_title, 1 if kind in {"title", "term"} else 0)
        if normalized_query in normalized and normalized:
            exact_phrase = max(exact_phrase, 1 if kind in {"title", "term", "ref", "official_source"} else 0)
        field_terms = set(re.findall(r"[\w]+", normalized, flags=re.UNICODE))
        present = sum(term in field_terms for term in terms)
        if present == len(terms):
            matched_terms = max(matched_terms, present)
            # Earlier fields are more authoritative: ref/source, then title,
            # then semantic description/content.
            best_field = max(best_field, len(fields) - index)
    if not (exact_identifier or exact_title or exact_phrase or matched_terms):
        return None
    return (exact_identifier, exact_title, exact_phrase, int(matched_terms == len(terms)), best_field, matched_terms)


def _candidate_sort_key(candidate: tuple[GovernedRetrievalResult, tuple[int, ...]]) -> tuple[Any, ...]:
    result, rank = candidate
    envelope = result.envelope
    return tuple(-value for value in rank) + (
        envelope.canonical_domain,
        envelope.canonical_entity_type,
        envelope.canonical_entity_id,
        envelope.document_version_id or "",
    )


def _master_content(db: Session, item: MasterContentItem, version: DocumentVersion, profile: MasterContentGovernanceProfile | None, provenance: list[MasterContentSourceProvenance], access: RetrievalAccessContext) -> str:
    # Authorization is evaluated before this read.  A denied item never loads
    # source bytes into context, even if the caller knows its canonical ID.
    if not access.may_read_master(item):
        raise UnauthorizedRetrieval("master content is outside caller scope")
    try:
        payload = read_master_content_bytes(db, version)
    except Exception:
        payload = version.metadata_json.get("synthetic_text", "").encode("utf-8")
    return payload.decode("utf-8", errors="replace")


def _master_result(
    db: Session,
    item: MasterContentItem,
    version: DocumentVersion,
    access: RetrievalAccessContext,
    query: RetrievalQuery,
    *,
    profile: MasterContentGovernanceProfile | None = None,
    provenance: list[MasterContentSourceProvenance] | None = None,
    bindings: list[MasterContentModuleBinding] | None = None,
    prefetched: bool = False,
) -> tuple[GovernedRetrievalResult, tuple[int, ...]] | None:
    if not access.may_read_master(item):
        return None
    if not prefetched:
        profile = db.scalar(select(MasterContentGovernanceProfile).where(MasterContentGovernanceProfile.master_content_item_id == item.id))
        provenance = list(db.scalars(select(MasterContentSourceProvenance).where(MasterContentSourceProvenance.document_version_id == version.id)))
        bindings = list(db.scalars(select(MasterContentModuleBinding).where(MasterContentModuleBinding.master_content_id == item.id, MasterContentModuleBinding.active.is_(True))))
    provenance = sorted(provenance or [], key=lambda row: (row.source_reference or "", row.id))
    bindings = bindings or []
    content = _master_content(db, item, version, profile, provenance, access)
    source_reference = provenance[0].source_reference if provenance else None
    fields = (
        ("ref", item.ref),
        ("official_source", source_reference),
        ("official_source", version.source_path_or_reference),
        ("official_source", profile.official_form_no if profile else None),
        ("official_source", profile.official_issue_no if profile else None),
        ("title", item.title),
        ("description", item.description),
        ("content", content),
    )
    match_rank = _match_rank(query.query, fields)
    if match_rank is None:
        return None
    citation = RetrievalCitation(canonical_domain="MASTER_CONTENT", canonical_entity_type="MasterContentItem", canonical_entity_id=item.id, document_id=item.document_id, document_version_id=version.id, locator=f"DocumentVersion:{version.id}", source_hash=version.sha256)
    envelope = GovernedRetrievalEnvelope(
        canonical_domain="MASTER_CONTENT",
        canonical_entity_type="MasterContentItem",
        canonical_entity_id=item.id,
        master_content_id=item.id,
        document_id=item.document_id,
        document_version_id=version.id,
        source_artifact_id=source_reference,
        source_currentness_state=profile.currentness_status if profile else None,
        verification_state="VERIFIED_CURRENT" if profile and profile.currentness_status == "VERIFIED_CURRENT" else "CANONICAL_VERSION",
        authority_source_class=profile.content_ownership_class if profile else None,
        superseded=version.id != item.current_document_version_id,
        sensitivity_class=profile.sensitivity_class if profile else "NONE",
        relationship_context={"used_in": tuple(item.used_in or []), "bindings": tuple(binding.usage_type for binding in bindings), "current_version_id": item.current_document_version_id, "source_references": tuple(value for value in (source_reference, version.source_path_or_reference, profile.official_form_no if profile else None, profile.official_issue_no if profile else None) if value)},
        content=content,
        citation=citation,
    )
    lifecycle_rank = (2 if version.id == item.current_document_version_id else 0, 1 if profile and profile.currentness_status == "VERIFIED_CURRENT" else 0, int(version.id == item.current_document_version_id))
    return GovernedRetrievalResult(envelope=envelope, score_reason="canonical master identity, source reference, and lifecycle rank"), match_rank + lifecycle_rank


def _transactional_results(
    db: Session,
    version: DocumentVersion,
    access: RetrievalAccessContext,
    query: RetrievalQuery,
    *,
    prefetched_document: Document | None = None,
    prefetched_observations: list[FieldObservation] | None = None,
    prefetched_assertions: list[VerifiedAssertion] | None = None,
    prefetched_classifications: list[DocumentClassification] | None = None,
    prefetched: bool = False,
) -> tuple[GovernedRetrievalResult, tuple[int, ...]] | None:
    document = prefetched_document if prefetched else db.get(Document, version.document_id)
    if not document or not access.may_read_project(document.project_id):
        return None
    if query.project_id and query.project_id != document.project_id:
        return None
    observations = prefetched_observations if prefetched else list(db.scalars(select(FieldObservation).where(FieldObservation.document_version_id == version.id)))
    observation_ids = tuple(row.id for row in observations)
    assertions = prefetched_assertions if prefetched else (list(db.scalars(select(VerifiedAssertion).where(VerifiedAssertion.source_observation_id.in_(observation_ids), VerifiedAssertion.status == AssertionStatus.CURRENT))) if observation_ids else [])
    classifications = prefetched_classifications if prefetched else list(db.scalars(select(DocumentClassification).where(DocumentClassification.document_version_id == version.id)))
    facts = "; ".join(assertion.display_value for assertion in sorted(assertions, key=lambda row: row.id))
    content = str(version.metadata_json.get("synthetic_text") or facts or document.logical_name)
    fields = (("title", document.logical_name), ("content", content)) + tuple(("verified_fact", assertion.display_value) for assertion in assertions)
    match_rank = _match_rank(query.query, fields)
    if match_rank is None:
        return None
    fact_rows = tuple({"field_definition_id": assertion.field_definition_id, "assertion_id": assertion.id, "display_value": assertion.display_value, "semantic_value": assertion.semantic_value_json} for assertion in sorted(assertions, key=lambda row: row.id))
    by_field: dict[str, set[str]] = defaultdict(set)
    for row in fact_rows:
        by_field[row["field_definition_id"]].add(json.dumps(row["semantic_value"], sort_keys=True, default=str))
    local_conflict_ids = tuple(row["assertion_id"] for row in fact_rows if len(by_field[row["field_definition_id"]]) > 1)
    relationship_context: dict[str, Any] = {"project_id": document.project_id, "observation_ids": observation_ids, "verified_assertion_ids": tuple(assertion.id for assertion in assertions), "classification_ids": tuple(row.id for row in classifications), "verified_assertion_facts": fact_rows}
    if local_conflict_ids:
        relationship_context.update({"conflict_state": "CONFLICTING", "conflicting_assertion_ids": local_conflict_ids})
    citation = RetrievalCitation(canonical_domain="TRANSACTIONAL_EVIDENCE", canonical_entity_type="DocumentVersion", canonical_entity_id=version.id, document_id=document.id, document_version_id=version.id, locator=f"DocumentVersion:{version.id}", source_hash=version.sha256)
    envelope = GovernedRetrievalEnvelope(
        canonical_domain="TRANSACTIONAL_EVIDENCE",
        canonical_entity_type="DocumentVersion",
        canonical_entity_id=version.id,
        transactional_entity_id=document.project_id,
        document_id=document.id,
        document_version_id=version.id,
        source_currentness_state="CURRENT" if document.current_version_id == version.id else "HISTORICAL",
        verification_state="VERIFIED" if assertions else "OBSERVED",
        authority_source_class="PROJECT_EVIDENCE",
        superseded=document.current_version_id != version.id,
        relationship_context=relationship_context,
        content=content,
        citation=citation,
    )
    lifecycle_rank = (2 if document.current_version_id == version.id else 0, 1 if assertions else 0, int(document.current_version_id == version.id))
    return GovernedRetrievalResult(envelope=envelope, score_reason="project membership, verified facts, and current-version rank"), match_rank + lifecycle_rank


def _definition_result(db: Session, definition: DefinitionEntry, access: RetrievalAccessContext, query: RetrievalQuery) -> tuple[GovernedRetrievalResult, tuple[int, ...]] | None:
    if access.role not in OWNER_ROLES and not set(definition.used_in or []).intersection({AUTHORIZED_MASTER_MODULES.get(access.role, "")}):
        return None
    revision = db.get(DefinitionRevision, definition.current_revision_id) if definition.current_revision_id else None
    content = revision.description if revision else ""
    fields = (("ref", definition.ref), ("term", definition.term)) + tuple(("term", alias) for alias in (revision.aliases if revision else [])) + (("description", definition.category), ("content", content))
    match_rank = _match_rank(query.query, fields)
    if match_rank is None:
        return None
    citation = RetrievalCitation(canonical_domain="MASTER_CONTENT", canonical_entity_type="DefinitionEntry", canonical_entity_id=definition.id, locator_type="DEFINITION_REVISION", locator=f"DefinitionRevision:{revision.id}" if revision else "DefinitionEntry", source_hash=None)
    envelope = GovernedRetrievalEnvelope(canonical_domain="MASTER_CONTENT", canonical_entity_type="DefinitionEntry", canonical_entity_id=definition.id, definition_entry_id=definition.id, definition_revision_id=revision.id if revision else None, verification_state="CURRENT_REVISION" if revision else "UNVERIFIED", authority_source_class="DEFINITION_REVISION", relationship_context={"used_in": tuple(definition.used_in or []), "aliases": tuple(revision.aliases if revision else [])}, content=content, citation=citation)
    return GovernedRetrievalResult(envelope=envelope, score_reason="canonical DefinitionEntry, alias, and current DefinitionRevision"), match_rank + (1, 1, 1)


def _annotate_result_states(candidates: list[tuple[GovernedRetrievalResult, tuple[int, ...]]], query: RetrievalQuery) -> list[tuple[GovernedRetrievalResult, tuple[int, ...]]]:
    """Add explicit conflict/ambiguity state without blending evidence."""
    by_fact: dict[tuple[str, str], list[tuple[GovernedRetrievalResult, str]]] = defaultdict(list)
    for result, rank in candidates:
        if result.envelope.canonical_domain != "TRANSACTIONAL_EVIDENCE":
            continue
        for fact in result.envelope.relationship_context.get("verified_assertion_facts", ()):
            value = json.dumps(fact.get("semantic_value"), sort_keys=True, default=str)
            by_fact[(str(result.envelope.transactional_entity_id), str(fact.get("field_definition_id")))].append((result, value))
    conflict_result_ids: dict[str, set[str]] = defaultdict(set)
    for entries in by_fact.values():
        values = {value for _, value in entries}
        if len(values) <= 1:
            continue
        ids = {result.envelope.canonical_entity_id for result, _ in entries}
        for result, _ in entries:
            conflict_result_ids[result.envelope.canonical_entity_id].update(ids)

    top_rank = candidates[0][1] if candidates else None
    ambiguous_ids = {result.envelope.canonical_entity_id for result, rank in candidates if top_rank is not None and rank == top_rank}
    if len(ambiguous_ids) < 2 or query.master_content_id or query.document_version_id or query.definition_entry_id:
        ambiguous_ids = set()
    updated: list[tuple[GovernedRetrievalResult, tuple[int, ...]]] = []
    for result, rank in candidates:
        context = dict(result.envelope.relationship_context)
        entity_id = result.envelope.canonical_entity_id
        if entity_id in conflict_result_ids:
            context.update({"conflict_state": "CONFLICTING", "conflicting_result_ids": tuple(sorted(conflict_result_ids[entity_id]))})
        if entity_id in ambiguous_ids:
            context.update({"ambiguity_state": "AMBIGUOUS", "ambiguous_result_ids": tuple(sorted(ambiguous_ids))})
        if context != result.envelope.relationship_context:
            result = result.model_copy(update={"envelope": result.envelope.model_copy(update={"relationship_context": context})})
        updated.append((result, rank))
    return updated


def governed_retrieve(db: Session, query: RetrievalQuery, access: RetrievalAccessContext) -> tuple[GovernedRetrievalResult, ...]:
    """Read canonical sources only after evaluating the supplied access context."""
    candidates: list[tuple[GovernedRetrievalResult, tuple[int, ...]]] = []
    if query.master_content_id or (not query.document_version_id and not query.definition_entry_id):
        statement = select(MasterContentItem)
        if query.master_content_id:
            statement = statement.where(MasterContentItem.id == query.master_content_id)
        items = db.scalars(statement).all()
        allowed_items = [item for item in items if item.status == "ACTIVE" and item.current_document_version_id and access.may_read_master(item)]
        version_ids = [item.current_document_version_id for item in allowed_items if item.current_document_version_id]
        if query.document_version_id and query.document_version_id not in version_ids:
            version_ids.append(query.document_version_id)
        versions = {version.id: version for version in db.scalars(select(DocumentVersion).where(DocumentVersion.id.in_(version_ids))).all()} if version_ids else {}
        item_ids = [item.id for item in allowed_items]
        profiles = {profile.master_content_item_id: profile for profile in db.scalars(select(MasterContentGovernanceProfile).where(MasterContentGovernanceProfile.master_content_item_id.in_(item_ids))).all()} if item_ids else {}
        provenance_rows = db.scalars(select(MasterContentSourceProvenance).where(MasterContentSourceProvenance.document_version_id.in_(version_ids))).all() if version_ids else []
        provenance_by_version: dict[str, list[MasterContentSourceProvenance]] = defaultdict(list)
        for row in provenance_rows:
            provenance_by_version[row.document_version_id].append(row)
        binding_rows = db.scalars(select(MasterContentModuleBinding).where(MasterContentModuleBinding.master_content_id.in_(item_ids), MasterContentModuleBinding.active.is_(True))).all() if item_ids else []
        bindings_by_item: dict[str, list[MasterContentModuleBinding]] = defaultdict(list)
        for row in binding_rows:
            bindings_by_item[row.master_content_id].append(row)
        for item in allowed_items:
            # Filter authorization and lifecycle before any source/version
            # bytes are read or the row is admitted to ranking.
            version = db.get(DocumentVersion, query.document_version_id) if query.document_version_id else versions.get(item.current_document_version_id)
            if version and version.document_id != item.document_id:
                continue
            if version:
                result = _master_result(db, item, version, access, query, profile=profiles.get(item.id), provenance=provenance_by_version.get(version.id, []), bindings=bindings_by_item.get(item.id, []), prefetched=True)
                if result:
                    candidates.append(result)
    if query.document_version_id or (not query.master_content_id and not query.definition_entry_id):
        statement = select(DocumentVersion)
        if query.document_version_id:
            statement = statement.where(DocumentVersion.id == query.document_version_id)
        else:
            statement = statement.join(Document, Document.id == DocumentVersion.document_id)
            if query.project_id:
                if access.role not in OWNER_ROLES and query.project_id not in access.project_ids:
                    statement = statement.where(Document.project_id == "__NO_AUTHORIZED_PROJECT__")
                else:
                    statement = statement.where(Document.project_id == query.project_id)
            elif access.role not in OWNER_ROLES:
                if not access.project_ids:
                    statement = statement.where(Document.project_id == "__NO_AUTHORIZED_PROJECT__")
                else:
                    statement = statement.where(Document.project_id.in_(access.project_ids))
            else:
                # Master-content source documents have no project scope and
                # are already handled by the separate discovery branch.
                statement = statement.where(Document.project_id.is_not(None))
        transactional_versions = db.scalars(statement).all()
        transactional_document_ids = {version.document_id for version in transactional_versions}
        transactional_documents = {document.id: document for document in db.scalars(select(Document).where(Document.id.in_(transactional_document_ids))).all()} if transactional_document_ids and not query.document_version_id else {}
        transactional_version_ids = [version.id for version in transactional_versions]
        observation_rows = db.scalars(select(FieldObservation).where(FieldObservation.document_version_id.in_(transactional_version_ids))).all() if transactional_version_ids and not query.document_version_id else []
        observations_by_version: dict[str, list[FieldObservation]] = defaultdict(list)
        for observation in observation_rows:
            observations_by_version[observation.document_version_id].append(observation)
        observation_ids = [observation.id for observation in observation_rows]
        assertion_rows = db.scalars(select(VerifiedAssertion).where(VerifiedAssertion.source_observation_id.in_(observation_ids), VerifiedAssertion.status == AssertionStatus.CURRENT)).all() if observation_ids and not query.document_version_id else []
        assertions_by_observation: dict[str, list[VerifiedAssertion]] = defaultdict(list)
        for assertion in assertion_rows:
            if assertion.source_observation_id:
                assertions_by_observation[assertion.source_observation_id].append(assertion)
        classification_rows = db.scalars(select(DocumentClassification).where(DocumentClassification.document_version_id.in_(transactional_version_ids))).all() if transactional_version_ids and not query.document_version_id else []
        classifications_by_version: dict[str, list[DocumentClassification]] = defaultdict(list)
        for classification in classification_rows:
            classifications_by_version[classification.document_version_id].append(classification)
        for version in transactional_versions:
            observations = observations_by_version.get(version.id, [])
            assertions = [assertion for observation in observations for assertion in assertions_by_observation.get(observation.id, [])]
            result = _transactional_results(db, version, access, query, prefetched_document=transactional_documents.get(version.document_id), prefetched_observations=observations, prefetched_assertions=assertions, prefetched_classifications=classifications_by_version.get(version.id, []), prefetched=not query.document_version_id)
            if result:
                candidates.append(result)
    if query.definition_entry_id or (not query.master_content_id and not query.document_version_id):
        statement = select(DefinitionEntry)
        if query.definition_entry_id:
            statement = statement.where(DefinitionEntry.id == query.definition_entry_id)
        for definition in db.scalars(statement).all():
            if access.role not in OWNER_ROLES and not set(definition.used_in or []).intersection({AUTHORIZED_MASTER_MODULES.get(access.role, "")}):
                continue
            result = _definition_result(db, definition, access, query)
            if result:
                candidates.append(result)
    deduplicated: dict[tuple[str, str, str, str], tuple[GovernedRetrievalResult, tuple[int, ...]]] = {}
    for candidate in candidates:
        envelope = candidate[0].envelope
        key = (envelope.canonical_domain, envelope.canonical_entity_type, envelope.canonical_entity_id, envelope.document_version_id or envelope.definition_revision_id or "")
        previous = deduplicated.get(key)
        if previous is None or _candidate_sort_key(candidate) < _candidate_sort_key(previous):
            deduplicated[key] = candidate
    ranked = _annotate_result_states(list(deduplicated.values()), query)
    ranked.sort(key=_candidate_sort_key)
    return tuple(result for result, _ in ranked[: query.limit])


def answer_from_retrieval(question: str, results: tuple[GovernedRetrievalResult, ...]) -> GovernedAIAnswer:
    """Deterministic synthetic answer seam; it cannot mutate canonical state."""
    if not results:
        return GovernedAIAnswer(question=question, answer="No authorized canonical evidence was found.", citations=(), authoritative_fact=False, inference_disclaimer="The response is limited to authorized canonical evidence.")
    first = results[0].envelope
    states = {first.relationship_context.get("ambiguity_state"), first.relationship_context.get("conflict_state")}
    if "AMBIGUOUS" in states:
        answer = "Multiple authorized canonical matches require selection; no single answer was inferred."
        authoritative = False
    elif "CONFLICTING" in states:
        answer = "Authorized evidence conflicts; the sources are returned separately for human review."
        authoritative = False
    else:
        answer = first.content
        authoritative = first.verification_state in {"VERIFIED", "VERIFIED_CURRENT", "CURRENT_REVISION"}
    return GovernedAIAnswer(question=question, answer=answer, citations=tuple(result.envelope.citation for result in results), authoritative_fact=authoritative, inference_disclaimer="This synthetic answer reports retrieved evidence; it is not a protected approval and does not change business state.")
