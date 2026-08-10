# ProceedProposal

`POST /api/proposals/{proposal_id}/proceed` is a domain command, not a status
PATCH. It verifies Proposal existence, client and description context,
reference state, source evidence and read-back verification. Failure is a 422
`PROPOSAL_INTAKE_INCOMPLETE` envelope with blocker codes. Success advances the
same Proposal to `PROPOSAL_PREPARATION`, creates/reuses a WorkflowTask and
records the BD → Engineering handoff.
