# Source persistence and integrity

The intake command authorizes the action, resolves Client and optional Project context, creates the Proposal, writes source bytes to the configured synthetic intake SOR, reads them back, verifies hash and size, registers EvidenceArtifact and ProposalIntakeArtifact metadata, and returns the verified result.

An idempotency key is checked before creating a new Opportunity, so retry/double-click reuses the original Proposal and source. Failed or unverified sources are not reported as authoritative.
