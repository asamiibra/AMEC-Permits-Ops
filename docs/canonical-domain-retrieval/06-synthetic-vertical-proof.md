# Phase 4 — Synthetic vertical proof

Test module: `backend/tests/test_canonical_domain_retrieval.py`.

The proof uses an in-memory ZIP representing a synthetic DSM/SOR artifact.
It performs controlled source intake, canonical master promotion, source
provenance/currentness, rule classification, field observation, authorized
verification, governed retrieval, cited answer assembly, and a transactional
negative control. No Azure, Synology, SMB, real data, or external AI is used.

Assertions include:

- exactly one `MasterContentItem` and one `Document` are created for the
  reusable source;
- the master points to one current `DocumentVersion` and the citation points
  to that exact version;
- a filled project-specific document is retrievable only as transactional
  evidence and creates zero master content;
- an authorized owner/read-only project caller can retrieve; unauthorized and
  wrong-project callers receive no context;
- V2 creates a new immutable version, preserves V1, moves current retrieval to
  V2, and keeps one master identity;
- historical retrieval explicitly replays V1;
- the cited synthetic answer is factual evidence, not protected approval, and
  reports no canonical mutation.

`SYNTHETIC_VERTICAL_PROOF_PASS=1`

`MASTER_VS_TRANSACTIONAL_CLASSIFICATION_PASS=1`

`CANONICAL_IDENTITY_PRESERVED_PASS=1`

`DOCUMENT_VERSION_LINEAGE_PASS=1`
