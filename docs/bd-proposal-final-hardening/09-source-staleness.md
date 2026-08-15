# Source staleness

Replacing a current source preserves the prior evidence as `CONFLICT`, links the new current evidence with `supersedes_id`, and creates a typed `ProposalStalenessEvent` with impacted sections. Superseded history remains visible but does not permanently block readiness; active staleness requires explicit Owner review/clear before Accept.
