# Exact Contract handoff v2

Status: `PROTECTED_AND_REGRESSION_VERIFIED`

The existing Admin Contract path is reused. Handoff resolves the accepted Proposal revision, creates/reuses Contract lineage against that exact revision, and returns `forms_driven_v2` from the accepted snapshot rather than re-resolving mutable current Proposal state. The response explicitly reports that legal Contract execution, Project code creation, AuthorityCase creation, and RegulatoryJourney creation are false/Owner-controlled boundaries.

Unaccepted or unresolved commercial-only drafts are blocked from handoff. Existing Admin Contract regressions pass on PostgreSQL after teardown was updated to delete the new `ProposalSourceLink` rows before source evidence.
