# Phase 3 — Governed Retrieval Envelope v1.0

Implementation: `backend/app/services/governed_retrieval.py` and
`backend/app/api/retrieval_routers.py`.

The contract is read-only and frozen with Pydantic `ConfigDict(frozen=True)`.

## Identity

The envelope carries `canonical_domain`, `canonical_entity_type`,
`canonical_entity_id`, and optional `master_content_id`,
`transactional_entity_id`, `document_id`, `document_version_id`,
`definition_entry_id`, `definition_revision_id`, `source_artifact_id`, and
`source_intake_id`.

## Authority and provenance

It carries currentness, verification state, source class, superseded state,
sensitivity class, relationship context, and an exact `RetrievalCitation`.
Structured facts point to canonical entity/version IDs; document facts point
to `DocumentVersion` plus a stable locator and source hash.

## Access

`RetrievalAccessContext` is immutable and requires caller, role, purpose, and
explicit project membership. Master access uses the existing owner/module
role semantics. Transactional evidence is returned only when the trusted
context includes the document's project. The service evaluates this before
reading content, so denied source bytes never enter model context.

## API

- `GET /api/retrieval/query`: read-only envelope results;
- `POST /api/retrieval/answer`: deterministic synthetic answer seam over the
  governed results, with citations and `canonical_state_mutated=false`.

There is no generic retrieval mutation endpoint and no retrieval-owned table.

`CROSS_DOMAIN_RETRIEVAL_CONTRACT_PASS=1`

`RETRIEVAL_SECOND_CANONICAL_DATABASE_COUNT=0`

`RETRIEVAL_CANONICAL_WRITE_COUNT=0`
