# Phase 1 — Canonical domain invariants

`DOMAIN_INVARIANTS_FROZEN_PASS=1`

## Master Content

Forms, Reports, Engineering Works, and Definitions are the owner-facing
libraries. Checklist is a Form. Document-backed master identity is:

`MasterContentItem → Document → immutable DocumentVersion`

Definitions retain their semantic authority separately:

`DefinitionEntry → DefinitionRevision`

Invariant: one logical master identity, one canonical version history, many
governed consumers, zero copied master truth.

## Transactional business state

Proposal, Contract, Project, Permit/Authority Case, requirements, forms
instances, engineering deliverables, invoices, construction, completion,
handover, and closeout remain runtime/business objects. Master Content can
inform them through references and governed projections; it does not absorb
them.

## Evidence and provenance

Source intake/document/version → classification/observation → verification →
`VerifiedAssertion` or an equivalent evidence record → typed business/master
projection. Raw extraction, classifier output, and AI inference are not
authoritative business truth.

## Source Documents

Source documents and immutable binary versions are distinct from the business
classification applied to them. A source can be master candidate,
transactional evidence, reference-only, blocked, superseded, or restricted.
Storage-folder taxonomy is not business taxonomy.

## Retrieval / knowledge access

Retrieval is governed read/discovery over canonical records. It is not a
canonical database and owns no writes. Any future derived index must be
rebuildable, traceable to canonical IDs and exact versions, and
non-authoritative for writes.
