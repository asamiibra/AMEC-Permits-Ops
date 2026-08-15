# Proposal → Contract handoff

Contract creation is gated by an accepted Proposal revision. The Contract stores `accepted_proposal_revision_id` and consumes that immutable snapshot; it does not read mutable current Proposal fields as its authority. Proposal acceptance does not execute Contract creation. Proposal surfaces retain Create Contract/View Contract cross-links to the same canonical Contract.
