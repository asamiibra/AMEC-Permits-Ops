# Phase 4 — Citation and lineage proof

Every returned result includes a structured citation, not display-only text.

- reusable master answer → `MasterContentItem.id`, `Document.id`, exact
  current `DocumentVersion.id`, stable locator, and SHA-256;
- transactional evidence → project/document/version identity plus current
  verified assertion IDs in relationship context;
- historical replay → explicit V1 `DocumentVersion.id`, marked superseded,
  and still separately retrievable;
- definitions → `DefinitionEntry` and current `DefinitionRevision` IDs.

`CITATION_TRACEABILITY_PASS=1`

`HISTORICAL_VERSION_REPLAY_PASS=1`
