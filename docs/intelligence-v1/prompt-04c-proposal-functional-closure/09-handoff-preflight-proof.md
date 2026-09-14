# Handoff preflight proof

GET /api/bd/proposals/{id}/handoff/contract is the server-owned preflight projection. It returns the accepted revision, gate results, blockers, content hash, and explicit downstream boundary flags. The mutate path refreshes this preflight immediately before recording eligibility.
