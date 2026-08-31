"""Permission-aware, citation-preserving retrieval over canonical records.

This module is deliberately a read-only boundary.  It does not own business
state, source binaries, versions, definitions, or workflow mutations.  A
future derived index may implement the same contract, but the canonical IDs
and source/version citations must remain authoritative.
"""

from __future__ import annotations

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
    if not query:
        return True
    terms = tuple(term for term in query.casefold().split() if term)
    haystack = " ".join(value or "" for value in values).casefold()
    return all(term in haystack for term in terms)


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


def _master_result(db: Session, item: MasterContentItem, version: DocumentVersion, access: RetrievalAccessContext, query: RetrievalQuery) -> GovernedRetrievalResult | None:
    if not access.may_read_master(item):
        return None
    profile = db.scalar(select(MasterContentGovernanceProfile).where(MasterContentGovernanceProfile.master_content_item_id == item.id))
    provenance = list(db.scalars(select(MasterContentSourceProvenance).where(MasterContentSourceProvenance.document_version_id == version.id)))
    content = _master_content(db, item, version, profile, provenance, access)
    if not _text_matches(query.query, item.ref, item.title, item.description, content):
        return None
    source_reference = provenance[0].source_reference if provenance else None
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
        relationship_context={"used_in": tuple(item.used_in or []), "bindings": tuple(binding.usage_type for binding in db.scalars(select(MasterContentModuleBinding).where(MasterContentModuleBinding.master_content_id == item.id, MasterContentModuleBinding.active.is_(True)))), "current_version_id": item.current_document_version_id},
        content=content,
        citation=citation,
    )
    return GovernedRetrievalResult(envelope=envelope, score_reason="canonical master identity and current DocumentVersion")


def _transactional_results(db: Session, version: DocumentVersion, access: RetrievalAccessContext, query: RetrievalQuery) -> GovernedRetrievalResult | None:
    document = db.get(Document, version.document_id)
    if not document or not access.may_read_project(document.project_id):
        return None
    if query.project_id and query.project_id != document.project_id:
        return None
    observations = list(db.scalars(select(FieldObservation).where(FieldObservation.document_version_id == version.id)))
    observation_ids = tuple(row.id for row in observations)
    assertions = list(db.scalars(select(VerifiedAssertion).where(VerifiedAssertion.source_observation_id.in_(observation_ids), VerifiedAssertion.status == AssertionStatus.CURRENT))) if observation_ids else []
    classifications = list(db.scalars(select(DocumentClassification).where(DocumentClassification.document_version_id == version.id)))
    facts = "; ".join(assertion.display_value for assertion in assertions)
    content = str(version.metadata_json.get("synthetic_text") or facts or document.logical_name)
    if not _text_matches(query.query, document.logical_name, content, *(assertion.display_value for assertion in assertions)):
        return None
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
        relationship_context={"project_id": document.project_id, "observation_ids": observation_ids, "verified_assertion_ids": tuple(assertion.id for assertion in assertions), "classification_ids": tuple(row.id for row in classifications)},
        content=content,
        citation=citation,
    )
    return GovernedRetrievalResult(envelope=envelope, score_reason="project membership and evidence lineage")


def _definition_result(db: Session, definition: DefinitionEntry, access: RetrievalAccessContext, query: RetrievalQuery) -> GovernedRetrievalResult | None:
    if access.role not in OWNER_ROLES and not set(definition.used_in or []).intersection({AUTHORIZED_MASTER_MODULES.get(access.role, "")}):
        return None
    revision = db.get(DefinitionRevision, definition.current_revision_id) if definition.current_revision_id else None
    content = revision.description if revision else ""
    if not _text_matches(query.query, definition.term, definition.category, content):
        return None
    citation = RetrievalCitation(canonical_domain="MASTER_CONTENT", canonical_entity_type="DefinitionEntry", canonical_entity_id=definition.id, locator_type="DEFINITION_REVISION", locator=f"DefinitionRevision:{revision.id}" if revision else "DefinitionEntry", source_hash=None)
    envelope = GovernedRetrievalEnvelope(canonical_domain="MASTER_CONTENT", canonical_entity_type="DefinitionEntry", canonical_entity_id=definition.id, definition_entry_id=definition.id, definition_revision_id=revision.id if revision else None, verification_state="CURRENT_REVISION" if revision else "UNVERIFIED", authority_source_class="DEFINITION_REVISION", relationship_context={"used_in": tuple(definition.used_in or [])}, content=content, citation=citation)
    return GovernedRetrievalResult(envelope=envelope, score_reason="canonical DefinitionEntry and DefinitionRevision")


def governed_retrieve(db: Session, query: RetrievalQuery, access: RetrievalAccessContext) -> tuple[GovernedRetrievalResult, ...]:
    """Read canonical sources only after evaluating the supplied access context."""
    results: list[GovernedRetrievalResult] = []
    if query.master_content_id or (not query.document_version_id and not query.definition_entry_id):
        statement = select(MasterContentItem)
        if query.master_content_id:
            statement = statement.where(MasterContentItem.id == query.master_content_id)
        for item in db.scalars(statement).all():
            if item.status != "ACTIVE" or not item.current_document_version_id:
                continue
            version = db.get(DocumentVersion, query.document_version_id) if query.document_version_id else db.get(DocumentVersion, item.current_document_version_id)
            if version and version.document_id != item.document_id:
                continue
            if version:
                result = _master_result(db, item, version, access, query)
                if result:
                    results.append(result)
    if query.document_version_id or (not query.master_content_id and not query.definition_entry_id):
        statement = select(DocumentVersion)
        if query.document_version_id:
            statement = statement.where(DocumentVersion.id == query.document_version_id)
        elif query.project_id:
            statement = statement.join(Document, Document.id == DocumentVersion.document_id).where(Document.project_id == query.project_id)
        for version in db.scalars(statement).all():
            result = _transactional_results(db, version, access, query)
            if result:
                results.append(result)
    if query.definition_entry_id or (not query.master_content_id and not query.document_version_id):
        statement = select(DefinitionEntry)
        if query.definition_entry_id:
            statement = statement.where(DefinitionEntry.id == query.definition_entry_id)
        for definition in db.scalars(statement).all():
            result = _definition_result(db, definition, access, query)
            if result:
                results.append(result)
    return tuple(results[: query.limit])


def answer_from_retrieval(question: str, results: tuple[GovernedRetrievalResult, ...]) -> GovernedAIAnswer:
    """Deterministic synthetic answer seam; it cannot mutate canonical state."""
    if not results:
        return GovernedAIAnswer(question=question, answer="No authorized canonical evidence was found.", citations=(), authoritative_fact=False, inference_disclaimer="The response is limited to authorized canonical evidence.")
    first = results[0].envelope
    return GovernedAIAnswer(question=question, answer=first.content, citations=tuple(result.envelope.citation for result in results), authoritative_fact=first.verification_state in {"VERIFIED", "VERIFIED_CURRENT", "CURRENT_REVISION"}, inference_disclaimer="This synthetic answer reports retrieved evidence; it is not a protected approval and does not change business state.")
