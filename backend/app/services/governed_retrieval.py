"""Permission-aware, deterministic retrieval over canonical records.

Retrieval is a read-only projection: canonical IDs, versions, assertions, and
citations remain owned by the existing domain tables.
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import (AssertionStatus, DefinitionEntry, DefinitionRevision, Document,
    DocumentClassification, DocumentVersion, FieldObservation,
    MasterContentGovernanceProfile, MasterContentItem, MasterContentModuleBinding,
    MasterContentSourceProvenance, Role, VerifiedAssertion)
from .master_content import read_master_content_bytes

RETRIEVAL_CONTRACT_VERSION = "1.0"
RETRIEVAL_CANONICAL_WRITE_COUNT = 0
RETRIEVAL_SECOND_CANONICAL_DATABASE_COUNT = 0
AUTHORIZED_MASTER_MODULES = {Role.PROCESS_CHAMPION: "BD", Role.RESPONSIBLE_ENGINEER: "ENGINEERING", Role.PERMIT_PREPARER: "PERMIT"}
OWNER_ROLES = frozenset({Role.OWNER_SPONSOR, Role.SYSTEM_ADMIN})

class RetrievalAccessContext(BaseModel):
    model_config = ConfigDict(frozen=True)
    caller_id: str = Field(min_length=1)
    role: Role
    project_ids: tuple[str, ...] = ()
    purpose: str = Field(default="READ", min_length=1)
    def may_read_project(self, project_id: str | None) -> bool:
        return bool(project_id and (self.role in OWNER_ROLES or project_id in self.project_ids))
    def may_read_master(self, item: MasterContentItem) -> bool:
        return self.role in OWNER_ROLES or bool(AUTHORIZED_MASTER_MODULES.get(self.role) in (item.used_in or []))

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
    pass

def access_context_for_role(role: Role, *, caller_id: str = "synthetic-caller", project_ids: tuple[str, ...] = (), purpose: str = "READ") -> RetrievalAccessContext:
    return RetrievalAccessContext(caller_id=caller_id, role=role, project_ids=project_ids, purpose=purpose)

def _text(value: str | None) -> str:
    return " ".join((value or "").casefold().split())

def _identifier(value: str | None) -> str:
    return re.sub(r"[^\w]", "", (value or "").casefold(), flags=re.UNICODE)

def _text_matches(query: str | None, *values: str | None) -> bool:
    """Compatibility predicate backed by the Step 3 normalized matcher."""
    return _rank(query, tuple(("value", value) for value in values)) is not None

def _rank(query: str | None, fields: tuple[tuple[str, str | None], ...]) -> tuple[int, ...] | None:
    if not query: return (0, 0, 0, 0, 0, 0)
    nq, qi = _text(query), _identifier(query)
    terms = tuple(re.findall(r"[\w]+", nq, flags=re.UNICODE))
    if not terms: return None
    exact_id = exact_title = exact_phrase = best_field = matched = 0
    for index, (kind, value) in enumerate(fields):
        normalized, ident = _text(value), _identifier(value)
        if qi and ident and qi == ident: exact_id = max(exact_id, 2 if kind in {"ref", "official_source"} else 1)
        if nq == normalized and normalized: exact_title = max(exact_title, int(kind in {"title", "term"}))
        if nq in normalized and normalized: exact_phrase = max(exact_phrase, int(kind in {"title", "term", "ref", "official_source"}))
        present = sum(term in set(re.findall(r"[\w]+", normalized, flags=re.UNICODE)) for term in terms)
        if present == len(terms): matched = max(matched, present); best_field = max(best_field, len(fields) - index)
    return (exact_id, exact_title, exact_phrase, int(matched == len(terms)), best_field, matched) if (exact_id or exact_title or exact_phrase or matched) else None

def _sort(candidate: tuple[GovernedRetrievalResult, tuple[int, ...]]) -> tuple[Any, ...]:
    result, rank = candidate; e = result.envelope
    return tuple(-v for v in rank) + (e.canonical_domain, e.canonical_entity_type, e.canonical_entity_id, e.document_version_id or "")

def _content(db: Session, item: MasterContentItem, version: DocumentVersion, access: RetrievalAccessContext) -> str:
    if not access.may_read_master(item): raise UnauthorizedRetrieval("master content is outside caller scope")
    try: payload = read_master_content_bytes(db, version)
    except Exception: payload = str(version.metadata_json.get("synthetic_text", "")).encode()
    return payload.decode("utf-8", errors="replace")

def _master(db: Session, item: MasterContentItem, version: DocumentVersion, access: RetrievalAccessContext, query: RetrievalQuery, *, profile=None, provenance=None, bindings=None, prefetched=False):
    if not access.may_read_master(item): return None
    if not prefetched:
        profile = db.scalar(select(MasterContentGovernanceProfile).where(MasterContentGovernanceProfile.master_content_item_id == item.id))
        provenance = list(db.scalars(select(MasterContentSourceProvenance).where(MasterContentSourceProvenance.document_version_id == version.id)))
        bindings = list(db.scalars(select(MasterContentModuleBinding).where(MasterContentModuleBinding.master_content_id == item.id, MasterContentModuleBinding.active.is_(True))))
    provenance = sorted(provenance or [], key=lambda row: (row.source_reference or "", row.id))
    source = provenance[0].source_reference if provenance else None
    content = _content(db, item, version, access)
    fields = (("ref", item.ref), ("official_source", source), ("official_source", version.source_path_or_reference), ("official_source", profile.official_form_no if profile else None), ("official_source", profile.official_issue_no if profile else None), ("title", item.title), ("description", item.description), ("content", content))
    rank = _rank(query.query, fields)
    if rank is None: return None
    citation = RetrievalCitation(canonical_domain="MASTER_CONTENT", canonical_entity_type="MasterContentItem", canonical_entity_id=item.id, document_id=item.document_id, document_version_id=version.id, locator=f"DocumentVersion:{version.id}", source_hash=version.sha256)
    envelope = GovernedRetrievalEnvelope(canonical_domain="MASTER_CONTENT", canonical_entity_type="MasterContentItem", canonical_entity_id=item.id, master_content_id=item.id, document_id=item.document_id, document_version_id=version.id, source_artifact_id=source, source_currentness_state=profile.currentness_status if profile else None, verification_state="VERIFIED_CURRENT" if profile and profile.currentness_status == "VERIFIED_CURRENT" else "CANONICAL_VERSION", authority_source_class=profile.content_ownership_class if profile else None, superseded=version.id != item.current_document_version_id, sensitivity_class=profile.sensitivity_class if profile else "NONE", relationship_context={"used_in": tuple(item.used_in or []), "bindings": tuple(b.usage_type for b in (bindings or [])), "current_version_id": item.current_document_version_id, "source_references": tuple(v for v in (source, version.source_path_or_reference, profile.official_form_no if profile else None, profile.official_issue_no if profile else None) if v)}, content=content, citation=citation)
    lifecycle = (2 if version.id == item.current_document_version_id else 0, int(bool(profile and profile.currentness_status == "VERIFIED_CURRENT")), int(version.id == item.current_document_version_id))
    return GovernedRetrievalResult(envelope=envelope, score_reason="canonical identity, exact/source rank, and lifecycle rank"), rank + lifecycle

def _transactional(db: Session, version: DocumentVersion, access: RetrievalAccessContext, query: RetrievalQuery, *, document=None, observations=None, assertions=None, classifications=None, prefetched=False):
    document = document if prefetched else db.get(Document, version.document_id)
    if not document or not access.may_read_project(document.project_id) or (query.project_id and query.project_id != document.project_id): return None
    observations = observations if prefetched else list(db.scalars(select(FieldObservation).where(FieldObservation.document_version_id == version.id)))
    observation_ids = tuple(o.id for o in observations)
    assertions = assertions if prefetched else (list(db.scalars(select(VerifiedAssertion).where(VerifiedAssertion.source_observation_id.in_(observation_ids), VerifiedAssertion.status == AssertionStatus.CURRENT))) if observation_ids else [])
    classifications = classifications if prefetched else list(db.scalars(select(DocumentClassification).where(DocumentClassification.document_version_id == version.id)))
    facts = "; ".join(a.display_value for a in sorted(assertions, key=lambda row: row.id))
    content = str(version.metadata_json.get("synthetic_text") or facts or document.logical_name)
    rank = _rank(query.query, (("title", document.logical_name), ("content", content)) + tuple(("verified_fact", a.display_value) for a in assertions))
    if rank is None: return None
    fact_rows = tuple({"field_definition_id": a.field_definition_id, "assertion_id": a.id, "display_value": a.display_value, "semantic_value": a.semantic_value_json} for a in sorted(assertions, key=lambda row: row.id))
    by_field = defaultdict(set)
    for row in fact_rows: by_field[row["field_definition_id"]].add(json.dumps(row["semantic_value"], sort_keys=True, default=str))
    conflicts = tuple(row["assertion_id"] for row in fact_rows if len(by_field[row["field_definition_id"]]) > 1)
    context = {"project_id": document.project_id, "observation_ids": observation_ids, "verified_assertion_ids": tuple(a.id for a in assertions), "classification_ids": tuple(c.id for c in classifications), "verified_assertion_facts": fact_rows}
    if conflicts: context.update(conflict_state="CONFLICTING", conflicting_assertion_ids=conflicts)
    citation = RetrievalCitation(canonical_domain="TRANSACTIONAL_EVIDENCE", canonical_entity_type="DocumentVersion", canonical_entity_id=version.id, document_id=document.id, document_version_id=version.id, locator=f"DocumentVersion:{version.id}", source_hash=version.sha256)
    envelope = GovernedRetrievalEnvelope(canonical_domain="TRANSACTIONAL_EVIDENCE", canonical_entity_type="DocumentVersion", canonical_entity_id=version.id, transactional_entity_id=document.project_id, document_id=document.id, document_version_id=version.id, source_currentness_state="CURRENT" if document.current_version_id == version.id else "HISTORICAL", verification_state="VERIFIED" if assertions else "OBSERVED", authority_source_class="PROJECT_EVIDENCE", superseded=document.current_version_id != version.id, relationship_context=context, content=content, citation=citation)
    return GovernedRetrievalResult(envelope=envelope, score_reason="project membership, verified facts, and current-version rank"), rank + (2 if document.current_version_id == version.id else 0, int(bool(assertions)), int(document.current_version_id == version.id))

def _definition(db: Session, definition: DefinitionEntry, access: RetrievalAccessContext, query: RetrievalQuery):
    if access.role not in OWNER_ROLES and AUTHORIZED_MASTER_MODULES.get(access.role) not in (definition.used_in or []): return None
    revision = db.get(DefinitionRevision, definition.current_revision_id) if definition.current_revision_id else None
    content = revision.description if revision else ""
    fields = (("ref", definition.ref), ("term", definition.term)) + tuple(("term", a) for a in (revision.aliases if revision else [])) + (("description", definition.category), ("content", content))
    rank = _rank(query.query, fields)
    if rank is None: return None
    citation = RetrievalCitation(canonical_domain="MASTER_CONTENT", canonical_entity_type="DefinitionEntry", canonical_entity_id=definition.id, locator_type="DEFINITION_REVISION", locator=f"DefinitionRevision:{revision.id}" if revision else "DefinitionEntry")
    envelope = GovernedRetrievalEnvelope(canonical_domain="MASTER_CONTENT", canonical_entity_type="DefinitionEntry", canonical_entity_id=definition.id, definition_entry_id=definition.id, definition_revision_id=revision.id if revision else None, verification_state="CURRENT_REVISION" if revision else "UNVERIFIED", authority_source_class="DEFINITION_REVISION", relationship_context={"used_in": tuple(definition.used_in or []), "aliases": tuple(revision.aliases if revision else [])}, content=content, citation=citation)
    return GovernedRetrievalResult(envelope=envelope, score_reason="canonical DefinitionEntry, alias, and current revision"), rank + (1, 1, 1)

def _annotate(candidates, query):
    by_fact = defaultdict(list)
    for result, rank in candidates:
        if result.envelope.canonical_domain == "TRANSACTIONAL_EVIDENCE":
            for fact in result.envelope.relationship_context.get("verified_assertion_facts", ()):
                by_fact[(str(result.envelope.transactional_entity_id), str(fact.get("field_definition_id")))].append((result, json.dumps(fact.get("semantic_value"), sort_keys=True, default=str)))
    conflict_ids = defaultdict(set)
    for entries in by_fact.values():
        if len({value for _, value in entries}) > 1:
            ids = {r.envelope.canonical_entity_id for r, _ in entries}
            for r, _ in entries: conflict_ids[r.envelope.canonical_entity_id].update(ids)
    top = candidates[0][1] if candidates else None
    ambiguous = {r.envelope.canonical_entity_id for r, rank in candidates if top is not None and rank == top}
    if len(ambiguous) < 2 or query.master_content_id or query.document_version_id or query.definition_entry_id: ambiguous = set()
    updated = []
    for result, rank in candidates:
        context = dict(result.envelope.relationship_context); entity = result.envelope.canonical_entity_id
        if entity in conflict_ids: context.update(conflict_state="CONFLICTING", conflicting_result_ids=tuple(sorted(conflict_ids[entity])))
        if entity in ambiguous: context.update(ambiguity_state="AMBIGUOUS", ambiguous_result_ids=tuple(sorted(ambiguous)))
        if context != result.envelope.relationship_context: result = result.model_copy(update={"envelope": result.envelope.model_copy(update={"relationship_context": context})})
        updated.append((result, rank))
    return updated

def governed_retrieve(db: Session, query: RetrievalQuery, access: RetrievalAccessContext) -> tuple[GovernedRetrievalResult, ...]:
    candidates = []
    if query.master_content_id or (not query.document_version_id and not query.definition_entry_id):
        statement = select(MasterContentItem)
        if query.master_content_id: statement = statement.where(MasterContentItem.id == query.master_content_id)
        items = [i for i in db.scalars(statement).all() if i.status == "ACTIVE" and i.current_document_version_id and access.may_read_master(i)]
        item_ids = [i.id for i in items]; version_ids = [i.current_document_version_id for i in items]
        if query.document_version_id and query.document_version_id not in version_ids: version_ids.append(query.document_version_id)
        versions = {v.id: v for v in db.scalars(select(DocumentVersion).where(DocumentVersion.id.in_(version_ids))).all()} if version_ids else {}
        profiles = {p.master_content_item_id: p for p in db.scalars(select(MasterContentGovernanceProfile).where(MasterContentGovernanceProfile.master_content_item_id.in_(item_ids))).all()} if item_ids else {}
        provenance = defaultdict(list)
        for p in (db.scalars(select(MasterContentSourceProvenance).where(MasterContentSourceProvenance.document_version_id.in_(version_ids))).all() if version_ids else []): provenance[p.document_version_id].append(p)
        bindings = defaultdict(list)
        for b in (db.scalars(select(MasterContentModuleBinding).where(MasterContentModuleBinding.master_content_id.in_(item_ids), MasterContentModuleBinding.active.is_(True))).all() if item_ids else []): bindings[b.master_content_id].append(b)
        for item in items:
            version = db.get(DocumentVersion, query.document_version_id) if query.document_version_id else versions.get(item.current_document_version_id)
            if version and version.document_id == item.document_id:
                candidate = _master(db, item, version, access, query, profile=profiles.get(item.id), provenance=provenance.get(version.id, []), bindings=bindings.get(item.id, []), prefetched=True)
                if candidate: candidates.append(candidate)
    if query.document_version_id or (not query.master_content_id and not query.definition_entry_id):
        statement = select(DocumentVersion)
        if query.document_version_id: statement = statement.where(DocumentVersion.id == query.document_version_id)
        else:
            statement = statement.join(Document, Document.id == DocumentVersion.document_id)
            if query.project_id: statement = statement.where(Document.project_id == query.project_id if access.role in OWNER_ROLES or query.project_id in access.project_ids else "__NO_AUTHORIZED_PROJECT__")
            elif access.role not in OWNER_ROLES: statement = statement.where(Document.project_id.in_(access.project_ids) if access.project_ids else Document.project_id == "__NO_AUTHORIZED_PROJECT__")
            else: statement = statement.where(Document.project_id.is_not(None))
        versions = db.scalars(statement).all(); version_ids = [v.id for v in versions]
        documents = {d.id: d for d in db.scalars(select(Document).where(Document.id.in_({v.document_id for v in versions}))).all()} if versions and not query.document_version_id else {}
        observations = defaultdict(list)
        for row in (db.scalars(select(FieldObservation).where(FieldObservation.document_version_id.in_(version_ids))).all() if version_ids and not query.document_version_id else []): observations[row.document_version_id].append(row)
        obs_ids = [o.id for rows in observations.values() for o in rows]; assertions = defaultdict(list)
        for row in (db.scalars(select(VerifiedAssertion).where(VerifiedAssertion.source_observation_id.in_(obs_ids), VerifiedAssertion.status == AssertionStatus.CURRENT)).all() if obs_ids and not query.document_version_id else []): assertions[row.source_observation_id].append(row)
        classifications = defaultdict(list)
        for row in (db.scalars(select(DocumentClassification).where(DocumentClassification.document_version_id.in_(version_ids))).all() if version_ids and not query.document_version_id else []): classifications[row.document_version_id].append(row)
        for version in versions:
            rows = observations.get(version.id, []); assertion_rows = [a for o in rows for a in assertions.get(o.id, [])]
            candidate = _transactional(db, version, access, query, document=documents.get(version.document_id), observations=rows, assertions=assertion_rows, classifications=classifications.get(version.id, []), prefetched=not query.document_version_id)
            if candidate: candidates.append(candidate)
    if query.definition_entry_id or (not query.master_content_id and not query.document_version_id):
        statement = select(DefinitionEntry)
        if query.definition_entry_id: statement = statement.where(DefinitionEntry.id == query.definition_entry_id)
        for definition in db.scalars(statement).all():
            candidate = _definition(db, definition, access, query)
            if candidate: candidates.append(candidate)
    unique = {}
    for candidate in candidates:
        e = candidate[0].envelope; key = (e.canonical_domain, e.canonical_entity_type, e.canonical_entity_id, e.document_version_id or e.definition_revision_id or "")
        if key not in unique or _sort(candidate) < _sort(unique[key]): unique[key] = candidate
    ranked = _annotate(list(unique.values()), query); ranked.sort(key=_sort)
    return tuple(result for result, _ in ranked[:query.limit])

def answer_from_retrieval(question: str, results: tuple[GovernedRetrievalResult, ...]) -> GovernedAIAnswer:
    if not results: return GovernedAIAnswer(question=question, answer="No authorized canonical evidence was found.", citations=(), authoritative_fact=False, inference_disclaimer="The response is limited to authorized canonical evidence.")
    first = results[0].envelope; context = first.relationship_context
    if context.get("ambiguity_state") == "AMBIGUOUS": answer, authoritative = "Multiple authorized canonical matches require selection; no single answer was inferred.", False
    elif context.get("conflict_state") == "CONFLICTING": answer, authoritative = "Authorized evidence conflicts; the sources are returned separately for human review.", False
    else: answer, authoritative = first.content, first.verification_state in {"VERIFIED", "VERIFIED_CURRENT", "CURRENT_REVISION"}
    return GovernedAIAnswer(question=question, answer=answer, citations=tuple(r.envelope.citation for r in results), authoritative_fact=authoritative, inference_disclaimer="This synthetic answer reports retrieved evidence; it is not a protected approval and does not change business state.")
