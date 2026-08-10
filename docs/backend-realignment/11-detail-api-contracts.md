# Detail projections

Purpose-built projections are available at `GET /api/proposals/{id}`,
`GET /api/proposals/{id}/preparation`, `GET /api/contracts/{id}` and
`GET /api/permits/{id}`. They include identity, current values with provenance
status/source count, revisions, sources, handoff/next action and related
records. Missing records return `PROPOSAL_NOT_FOUND`, `CONTRACT_NOT_FOUND` or
`PERMIT_NOT_FOUND` as typed 404 envelopes.
