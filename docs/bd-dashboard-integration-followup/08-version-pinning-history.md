# Version pinning and history

New Proposal configuration resolves the current eligible Dashboard version at read/validation time. Human Accept freezes the exact template and checklist identities, versions, hashes, and relevant Definition revision projections into `ProposalAcceptedRevision`; output artifacts carry that lineage.

Later Dashboard publication cannot rewrite an accepted Proposal revision. Draft currentness is re-evaluated through the live resolver before final validation/acceptance; there is no mixed-version fallback.
